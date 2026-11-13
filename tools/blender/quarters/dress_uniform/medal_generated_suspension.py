"""#130 smaller generated ring, solder fillet and tangent-continuous fabric wrap."""
import argparse
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import activate, join_named
from aging_support import components
from medal_interlink import reciprocal_interlink, section_contours, disc_crossings, contains
from medal_solder_checks import sewn_ribbon_samples, suspension_measurements
from reduced_clearance import crossing_pairs
from tunic_details import binding, extract_ribbon, geometry_hash, points


def part(source, indices, name):
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.verts.ensure_lookup_table()
    selected = set(indices)
    bmesh.ops.delete(mesh, geom=[v for v in mesh.verts if v.index not in selected], context='VERTS')
    mesh.to_mesh(obj.data)
    mesh.free()
    return obj


def assign(obj, positions):
    for vertex, position in zip(obj.data.vertices, positions):
        vertex.co = position
    obj.data.update()


def union(first, second):
    activate(first)
    modifier = first.modifiers.new('LocalSolderUnion', 'BOOLEAN')
    modifier.operation, modifier.solver, modifier.object = 'UNION', 'EXACT', second
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(second, do_unlink=True)


def body_channels(obj, origin, frame):
    positions = points(obj)
    local = np.einsum('ij,kj->ik', positions-origin, frame)
    result = {}
    for face in obj.data.polygons:
        if face.material_index >= 2 or local[list(face.vertices),2].min() > .0155:
            continue
        corners = {tuple(positions[obj.data.loops[i].vertex_index]):
                   {layer.name: tuple(layer.data[i].uv) for layer in obj.data.uv_layers}
                   for i in face.loop_indices}
        result[tuple(sorted(corners))] = (corners, obj.data.materials[face.material_index].name, face.use_smooth)
    return result


def restore_body_channels(obj, origin, frame, expected):
    positions = points(obj)
    local = np.einsum('ij,kj->ik', positions-origin, frame)
    retained = set()
    for face in obj.data.polygons:
        if face.material_index >= 2 or local[list(face.vertices),2].min() > .0155:
            continue
        key = tuple(sorted(tuple(positions[i]) for i in face.vertices))
        corners, material, smooth = expected[key]
        assert obj.data.materials[face.material_index].name == material
        face.use_smooth = smooth
        for i in face.loop_indices:
            for name, uv in corners[tuple(positions[obj.data.loops[i].vertex_index])].items():
                obj.data.uv_layers[name].data[i].uv = uv
        retained.add(key)
    assert retained == set(expected), 'Body topology outside the solder joint changed'


def unwrap_new(obj):
    activate(obj)
    while obj.data.uv_layers:
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
    obj.data.uv_layers.new(name='DetailUV')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    layer = obj.data.uv_layers.active
    for value in layer.data:
        value.uv = (.845 + value.uv.x * .12, .005 + value.uv.y * .115)
    layer.name = 'DetailUV'
    bake = obj.data.uv_layers.get('BakeUV') or obj.data.uv_layers.new(name='BakeUV')
    for a, b in zip(layer.data, bake.data):
        b.uv = a.uv
    colours = obj.data.color_attributes.get('RibbonColours') or obj.data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
    for value in colours.data:
        value.color = (1, 1, 1, 1)


def finish_solder(obj, origin, frame, preserved_faces):
    """Remove only joint fragments collapsed by stored world-coordinate precision."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    joint = []
    for vertex in mesh.verts:
        local = np.einsum('j,kj->k', np.array(vertex.co)-origin, frame)
        if .0155 < local[2] < .0162 and abs(local[0]) < .004:
            joint.append(vertex)
    bmesh.ops.remove_doubles(mesh, verts=joint, dist=4e-8)
    edges = [e for e in mesh.edges if all(v in joint for v in e.verts)]
    bmesh.ops.dissolve_degenerate(mesh, edges=edges, dist=4e-8)
    assert all(e.is_manifold for e in mesh.edges), 'Stored-precision solder remains closed'
    zero = [face for face in mesh.faces if face.calc_area() == 0]
    for face in zero:
        signature = tuple(sorted(tuple(vertex.co) for vertex in face.verts))
        assert signature in preserved_faces, 'Stored-precision solder created a zero-area face'
    print('Preserved inherited zero-area body faces:', len(zero), flush=True)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    positions = points(obj)
    for face in obj.data.polygons:
        local = np.einsum('ij,kj->ik', positions[list(face.vertices)]-origin, frame)
        if not (local[:,2].min() > .0155 and local[:,2].max() < .0162):
            continue
        uv = np.array([obj.data.uv_layers['DetailUV'].data[i].uv[:] for i in face.loop_indices])
        a, b = uv[1:-1]-uv[0], uv[2:]-uv[0]
        if np.min(abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])) > 1e-15:
            continue
        normal = np.cross(local-local[0], np.roll(local,-1,axis=0)-local[0]).sum(0)
        assert np.linalg.norm(normal) > 0
        normal /= np.linalg.norm(normal)
        x = local[np.linalg.norm(local-local[0],axis=1).argmax()]-local[0]
        x /= np.linalg.norm(x)
        y = np.cross(normal,x)
        projected = np.c_[np.einsum('ij,j->i',local-local[0],x), np.einsum('ij,j->i',local-local[0],y)]
        chart = (projected-projected.min(0))/.05 + [.847,.005]
        assert chart.max(0)[0] < .965 and chart.max(0)[1] < .12
        for name in ['DetailUV','BakeUV']:
            for i,value in zip(face.loop_indices,chart):
                obj.data.uv_layers[name].data[i].uv = value


def torus(center, radius, wire, major, minor, material):
    vertices, faces = [], []
    for i in range(major):
        a = 2 * np.pi * i / major
        radial = np.array([np.cos(a), 0, np.sin(a)])
        for j in range(minor):
            b = 2 * np.pi * j / minor
            vertices.append(center + (radius + wire * np.cos(b)) * radial + [0, wire * np.sin(b), 0])
    for i in range(major):
        for j in range(minor):
            faces.append((i*minor+j, ((i+1)%major)*minor+j, ((i+1)%major)*minor+(j+1)%minor, i*minor+(j+1)%minor))
    mesh = bpy.data.meshes.new('LeanRoundWireLoop')
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new('LeanRoundWireLoop', mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh); bm.free()
    for face in mesh.polygons:
        face.use_smooth = True
    return obj


def fabric_path(bounds, approach, approach_normals, count=22):
    """Saved sewn approach, smooth free bend and offset quarter circles over the bar."""
    lo, hi = bounds[:, 1:]
    radius = .00068
    front = np.array([lo[0] - radius, hi[1]])
    start = approach[-1]
    controls = np.array([start, start+[0,.0042], start+[0,.0072], start+[0,.0082], [front[0]-.008,hi[1]+.005], front+[0,-.0035], front])
    path, normals = list(approach), list(approach_normals)
    for t in [.2,.45,.75,.9,1.]:
        weights = [math.comb(6,k)*t**k*(1-t)**(6-k) for k in range(7)]
        derivative = [math.comb(5,k)*t**k*(1-t)**(5-k) for k in range(6)]
        p = np.einsum('i,ij->j',weights,controls)
        d = np.einsum('i,ij->j',derivative,6*np.diff(controls,axis=0))
        normal = np.array([d[1], -d[0]]) / np.linalg.norm(d)
        path.append(p); normals.append(normal)
    for angle in np.linspace(np.pi, np.pi/2, 6)[1:]:
        path.append([lo[0]+radius*np.cos(angle), hi[1]+radius*np.sin(angle)])
        normals.append([-np.cos(angle), -np.sin(angle)])
    path.append([hi[0], hi[1]+radius]); normals.append([0, -1])
    for angle in np.linspace(np.pi/2, 0, 6)[1:]:
        path.append([hi[0]+radius*np.cos(angle), hi[1]+radius*np.sin(angle)])
        normals.append([-np.cos(angle), -np.sin(angle)])
    tip = bounds[:, 2].mean() + .00020
    for z in np.linspace(hi[1], tip, 4)[1:]:
        path.append([hi[0]+radius, z]); normals.append([-1, 0])
    assert len(path) == count
    return np.array(path), np.array(normals), controls


def build(baseline, generated_source, output, major, minor, pilot_major=None):
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    for state in ['working', 'pilot']:
        major_count = pilot_major if state == 'pilot' and pilot_major is not None else major
        bpy.ops.wm.open_mainfile(filepath=str(baseline / f'tunic-{state}.blend'))
        old = bpy.data.objects['Medal']
        frame_record = json.loads(old['medal_frame'])
        origin, frame = np.array(frame_record['origin']), np.array(frame_record['frame'])
        local = lambda obj: np.einsum('ij,kj->ik', points(obj)-origin, frame)
        preserved_channels = body_channels(old, origin, frame)
        metadata = {k: v.to_list() if hasattr(v, 'to_list') else v for k, v in old.items()}
        frozen = {o.name: geometry_hash(o) for o in bpy.context.scene.objects if o.type == 'MESH' and o != old}
        sewn = sewn_ribbon_samples(old)
        old_attachment = json.loads(old['attachment'])
        rear = np.array(old_attachment['base_blender_m'])[:len(old_attachment['metal_base_vertex_indices'])]
        ribbon = extract_ribbon(old)
        saved_ribbon = points(ribbon)
        saved_local = local(ribbon)
        with bpy.data.libraries.load(str(generated_source / f'tunic-{state}.blend'), link=False) as (_, dest):
            dest.objects = ['Medal']
        source = dest.objects[0]
        bpy.context.collection.objects.link(source)
        groups = sorted(components(source), key=lambda ids: local(source)[ids, 2].mean())
        body, ring, bar = [part(source, ids, name) for ids, name in zip(groups[:3], ['SolderedBody', 'GeneratedRing', 'CentredBar'])]
        for obj in [body, ring, bar]:
            for i in range(2): obj.data.materials[i] = old.data.materials[i]
        bp, rp, barp = [local(obj) for obj in [body, ring, bar]]
        original_body = points(body).copy()
        preserved_faces = {tuple(sorted(map(tuple, original_body[list(face.vertices)]))) for face in body.data.polygons}
        axes = np.linalg.svd(rp-rp.mean(0), full_matrices=False)[2][[2,1,0]]
        axes[0] *= -np.sign(axes[0,0]); axes[1] *= -np.sign(axes[1,1]); axes[2] *= np.sign(axes[2,2])
        angle = math.radians(55)
        rotation = np.array([[1,0,0], [0,math.cos(angle),-math.sin(angle)], [0,math.sin(angle),math.cos(angle)]])
        rp = np.einsum('ij,kj->ik',np.einsum('ij,kj->ik',rp-rp.mean(0),axes),rotation)
        rp[:, 2] += bp[:, 2].max() - .00025 - rp[:, 2].min()
        bottom = rp[:, 2] < rp[:, 2].min() + .00008
        rp[:, 1] += -.00035 - rp[bottom, 1].mean()
        rp[:, 0] -= rp[bottom, 0].mean()
        ring_plane = float(rp[:, 0].mean())
        assign(body, bp*1000); assign(ring, rp*1000)
        before = np.concatenate([bp, rp])*1000
        union(body, ring)
        bm = bmesh.new(); bm.from_mesh(body.data)
        new = [v for v in bm.verts if np.linalg.norm(before-np.array(v.co), axis=1).min() > 1e-5]
        seams = [e for e in bm.edges if all(v in new for v in e.verts) and e.calc_face_angle(0) > .05]
        seams = sorted(seams,key=lambda edge: -edge.calc_length())[:2]
        print(state, 'FILLET_SEAMS', len(seams), [[list(v.co) for v in e.verts] for e in seams], flush=True)
        assert seams, 'Local union must create a solder seam'
        bmesh.ops.bevel(bm, geom=seams, offset=.06, segments=2, affect='EDGES', clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(body.data); bm.free()
        assign(body, origin + np.einsum('ij,jk->ik',points(body)/1000,frame))
        # Restore untouched coordinates exactly after the millimetre-space union.
        kd = KDTree(len(body.data.vertices))
        for i, p in enumerate(points(body)): kd.insert(Vector(p), i)
        kd.balance()
        restored = 0
        for p in original_body:
            _, i, distance = kd.find(Vector(p))
            if distance < 1e-7:
                body.data.vertices[i].co = p; restored += 1
        body.data.update()
        finish_solder(body, origin, frame, preserved_faces)
        body.data.calc_loop_triangles()
        bp = local(body)
        body_faces = [t.vertices[:] for t in body.data.loop_triangles]
        barp[:, 0] += (saved_local[:,0].min()+saved_local[:,0].max()-barp[:,0].min()-barp[:,0].max())/2
        wire, radius = .0004, .0028
        center_x = (saved_local[:,0].min()+saved_local[:,0].max())/2 + .0008
        candidates = []
        contours = section_contours(bp,body_faces,ring_plane)
        for y in np.linspace(-.0048, -.0010, 39):
            for z in np.linspace(.0212, .0240, 57):
                loop = dict(center_m=[center_x,float(y),float(z)], radius_m=radius, wire_radius_m=wire, normal=[0.,1.,0.], up=[0.,0.,1.], major_segments=major_count, wire_segments=minor)
                theta = np.arange(major_count)*2*np.pi/major_count
                line = np.array(loop['center_m']) + radius*np.c_[np.cos(theta),np.zeros(major_count),np.sin(theta)]
                cuts = disc_crossings(line,np.array([ring_plane,0,0]),np.array([1,0,0]))
                through = [p for p in cuts if p[2]>.0162 and sum(contains(curve,p[1:]) for curve in contours)>=2]
                if len(through)==1: candidates.append((loop,None))
        assert candidates, 'Generated-size ring must admit a reciprocal interlink'
        # Test real solids at each candidate; seat the loop against the upper ring arc.
        chosen = None
        from build import tree
        body_tree = tree(body)
        best_bearing, collisions = 1., 0
        print(state, 'INTERLINK_CANDIDATES',len(candidates),'ring_bounds',rp.min(0).tolist(),rp.max(0).tolist(),flush=True)
        for loop, proof in sorted(candidates, key=lambda c: (-c[0]['center_m'][2], abs(c[0]['center_m'][1]+.0034))):
            center = np.array(loop['center_m'])
            link = torus(center*1000, radius*1000, wire*1000, major_count, minor, old.data.materials[0])
            assign(link, origin + np.einsum('ij,jk->ik',points(link)/1000,frame))
            if crossing_pairs(link, body):
                collisions += 1
                bpy.data.objects.remove(link, do_unlink=True); continue
            bearing = min(body_tree.find_nearest(Vector(p))[3] for p in points(link))
            best_bearing = min(best_bearing,bearing)
            if bearing > .0001:
                bpy.data.objects.remove(link, do_unlink=True); continue
            try: proof = reciprocal_interlink(bp,body_faces,ring_plane,loop)
            except AssertionError:
                bpy.data.objects.remove(link,do_unlink=True); continue
            chosen = (loop, link, proof, bearing); break
        print(state,'LINK_SEARCH',best_bearing,collisions,flush=True)
        assert chosen is not None, 'Closed loop must interlink within bearing tolerance'
        loop, link, proof, bearing = chosen
        center = np.array(loop['center_m'])
        barp[:, 2] += center[2] + radius - .00015 - barp[:, 2].min()
        barp[:, 1] += np.array(json.loads(metadata['eyelet'])['bar_bounds_m'])[0,1] - barp[:, 1].min() + (.0004 if state == 'pilot' else 0)
        bounds = np.array([barp.min(0), barp.max(0)])
        assign(bar, barp*1000)
        assign(link, local(link)*1000)
        union(bar, link)
        unwrap_new(bar)
        assign(bar, origin + np.einsum('ij,jk->ik',points(bar)/1000,frame))
        # Reuse every existing ribbon corner and its UV/colour channels.
        # The saved approach stays behind the return until it clears the linked wire.
        approach = np.array([saved_local[64+i*14:78+i*14,1:].mean(0) for i in range(3)])
        approach_normals = np.array([(saved_local[64+i*14,1:]-saved_local[71+i*14,1:])/.0008 for i in range(3)])
        approach_normals /= np.linalg.norm(approach_normals,axis=1)[:,None]
        path, normals, controls = fabric_path(bounds, approach, approach_normals)
        folded = saved_local.copy()
        for row, (yz, normal) in enumerate(zip(path, normals)):
            for side in range(2):
                ids = np.arange(64+row*14+side*7, 64+row*14+(side+1)*7)
                folded[ids, 1:] = yz + normal*(.0004 if side == 0 else -.0004)
        world = origin + np.einsum('ij,jk->ik',folded,frame)
        world[:64] = saved_ribbon[:64]
        assign(ribbon, world)
        for face in ribbon.data.polygons: face.use_smooth = True
        checks = {name:len(crossing_pairs(a,b)) if b is not None else len(crossing_pairs(a)) for name,a,b in [('ribbon_self',ribbon,None),('ribbon_metal',ribbon,body),('ribbon_bar',ribbon,bar),('ribbon_wool',ribbon,bpy.data.objects['TunicBody']),('bar_body',bar,body)]}
        print(state, 'CANDIDATE', loop, 'bounds', bounds.tolist(), 'crossings', checks, flush=True)
        if checks['ribbon_self']:
            ribbon.data.calc_loop_triangles()
            print('SELF_ROWS',[[[int(i) for i in ribbon.data.loop_triangles[t].vertices] for t in pair] for pair in crossing_pairs(ribbon)[:16]],flush=True)
        assert not any(checks.values()), checks
        body_count = len(body.data.vertices)
        ribbon_base_local = np.array(json.loads(metadata['ribbon_loop'])['source_sew_base_indices'])
        ribbon_base_positions = points(ribbon)[ribbon_base_local]
        bpy.data.objects.remove(source, do_unlink=True)
        bpy.data.objects.remove(old, do_unlink=True)
        obj = join_named([body,bar,ribbon], 'Medal'); obj.data.name = 'Medal'
        bpy.ops.object.material_slot_remove_unused()
        for face in obj.data.polygons:
            if face.material_index < 2:
                for i in face.loop_indices:
                    obj.data.color_attributes['RibbonColours'].data[i].color = (1,1,1,1)
        restore_body_channels(obj, origin, frame, preserved_channels)
        for key, value in metadata.items(): obj[key] = value
        pos = points(obj)
        kd = KDTree(body_count)
        for i, p in enumerate(pos[:body_count]): kd.insert(Vector(p),i)
        kd.balance()
        ids = [kd.find(Vector(p))[1] for p in rear]
        np.testing.assert_array_equal(pos[ids],rear)
        metal_ids = {i for face in obj.data.polygons if face.material_index < 2 for i in face.vertices}
        ribbon_ids = set(range(len(pos))) - metal_ids
        ribbon_tree = KDTree(len(ribbon_ids))
        for i in ribbon_ids: ribbon_tree.insert(Vector(pos[i]), i)
        ribbon_tree.balance()
        ribbon_base = [ribbon_tree.find(Vector(p))[1] for p in ribbon_base_positions]
        np.testing.assert_array_equal(pos[ribbon_base], ribbon_base_positions)
        bases = ids + ribbon_base
        old_attachment.update(metal_base_vertex_indices=ids, base_vertex_indices=bases, base_blender_m=pos[bases].tolist())
        obj['attachment'] = json.dumps(old_attachment)
        body_ids = [i for i,p in enumerate(local(obj)[:body_count]) if p[2] <= .01608]
        obj['body_vertex_indices'] = body_ids
        frame_record['body_vertices'] = len(body_ids); obj['medal_frame'] = json.dumps(frame_record)
        ribbon_record = json.loads(metadata['ribbon_loop'])
        ribbon_record.update(construction='Smooth hanging bend with tangent-continuous offset rounded wrap over generated bar', front_fold_station_m=[float((bounds[0,0]+bounds[1,0])/2), float(bounds[0,1]-.00068), float(bounds[1,2])], wrap_centerline_m=path.tolist(), wrap_normals=normals.tolist(), approach_controls_m=controls.tolist(), bend_radius_m=.00068)
        obj['ribbon_loop'] = json.dumps(ribbon_record)
        eyelet = json.loads(metadata['eyelet'])
        eyelet.update(uniform_ring_scale=1., embed_m=.00025, ring_plane_x_m=ring_plane, bar_bounds_m=bounds.tolist(), suspender_loop=loop, solder_fillet_radius_m=.00006, solder_fillet_edges=len(seams), ribbon_loop=ribbon_record)
        obj['eyelet'] = json.dumps(eyelet)
        obj.data.calc_loop_triangles()
        solid = sum(t.material_index < 2 for t in obj.data.loop_triangles)
        fitted = json.loads(obj['fitted_medal']); fitted['solid_triangles'] = solid; obj['fitted_medal'] = json.dumps(fitted)
        if state == 'pilot':
            aged = json.loads(bpy.context.scene['tunic5_record'])
            aged['bindings']['Medal'] = binding(obj,[sorted(metal_ids),sorted(ribbon_ids)],bpy.data.objects['TunicBody'],True)
            bpy.context.scene['tunic5_record'] = json.dumps(aged)
        np.testing.assert_array_equal(sewn_ribbon_samples(obj),sewn)
        assert all(geometry_hash(bpy.data.objects[n]) == h for n,h in frozen.items())
        print(state,'SOLIDS',[(len(ids),local(obj)[ids].min(0).tolist(),local(obj)[ids].max(0).tolist()) for ids in components(obj)],flush=True)
        checks.update(suspension_measurements(obj))
        count = 0
        for mesh in bpy.context.scene.objects:
            if mesh.type == 'MESH' and mesh.get('aged_export' if state == 'pilot' else 'export'):
                mesh.data.calc_loop_triangles(); count += len(mesh.data.loop_triangles)
        report[state] = dict(checks=checks, uniform_ring_scale=1., metal_triangles=solid, body_ring_triangles=len(body_faces), bar_loop_triangles=solid-len(body_faces), ribbon_triangles=740, garment_triangles=count, restored_body_vertices=restored, loop=loop, bar_bounds_m=bounds.tolist())
        atlas = dict(uv=[[obj.data.uv_layers['DetailUV'].data[i].uv[:] for i in t.loops] for t in obj.data.loop_triangles if t.material_index < 2], upward=[float(obj.data.polygons[t.polygon_index].normal.z) for t in obj.data.loop_triangles if t.material_index < 2])
        (output.parent/f'{state}-atlas.json').write_text(json.dumps(atlas))
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output/f'tunic-{state}.blend'))
        (output.parent.parent/'hardware.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','generated-source','output']: p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--major',type=int,default=32); p.add_argument('--minor',type=int,default=8)
    p.add_argument('--pilot-major',type=int,default=36)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    build(a.baseline.resolve(), a.generated_source.resolve(), a.output.resolve(), a.major, a.minor, a.pilot_major)
