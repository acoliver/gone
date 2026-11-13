"""Mount the accepted #130 baked medal and fold only the lower sewn ribbon."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from tunic_details import binding, extract_ribbon, geometry_hash, points
from build import activate, export as clean_export, join_named, recalc, tree
from common import export as aged_export
from detail_clearance import continuous_gap, triangles
from aging_support import components
from reduced_clearance import crossing_pairs


def loop_ribbon(obj, origin, frame):
    old = obj.data
    local = np.einsum('ij,kj->ik', points(obj)-origin, frame)
    assert len(local) == 70, 'Expected saved seven-row, five-column ribbon skins'
    uv_names = [u.name for u in old.uv_layers]
    values = {}
    for polygon in old.polygons:
        for index in polygon.loop_indices:
            vertex = old.loops[index].vertex_index
            values[vertex] = np.r_[*[old.uv_layers[n].data[index].uv[:] for n in uv_names],
                                   old.color_attributes['RibbonColours'].data[index].color[:]]
    vertices, attributes = local.tolist(), [values[i] for i in range(70)]
    stations = np.array([0., .25, .35, .5, .65, .75, 1.])
    def interpolate(side, row, t):
        u = t * 4
        a = min(int(u), 3); f = u - a
        i = side * 35 + row * 5 + a
        return (1-f)*local[i]+f*local[i+1], (1-f)*values[i]+f*values[i+1]
    def append(p, attr):
        vertices.append(p); attributes.append(attr)
        return len(vertices)-1
    top = []
    for side in range(2):
        ids = []
        for t in stations:
            if t in [0., .25, .5, .75, 1.]:
                ids.append(side*35+5+int(t*4))
            else:
                p, attr = interpolate(side, 1, t)
                ids.append(append(p.tolist(), attr))
        top.append(ids)
    faces = []
    face_attributes = []
    for polygon in old.polygons:
        ids = list(polygon.vertices)
        if any(i % 35 < 5 for i in ids):
            continue
        expanded, corner_values = [], []
        old_values = [np.r_[*[old.uv_layers[n].data[i].uv[:] for n in uv_names], old.color_attributes['RibbonColours'].data[i].color[:]] for i in polygon.loop_indices]
        for corner, (a, b) in enumerate(zip(ids, ids[1:]+ids[:1])):
            expanded.append(a)
            va, vb = old_values[corner], old_values[(corner+1)%len(ids)]
            corner_values.append(va)
            for side in range(2):
                if a in top[side] and b in top[side]:
                    ia, ib = top[side].index(a), top[side].index(b)
                    if abs(ia-ib) > 1:
                        step = 1 if ib > ia else -1
                        for index in range(ia+step,ib,step):
                            expanded.append(top[side][index])
                            fraction = (stations[index]-stations[ia])/(stations[ib]-stations[ia])
                            corner_values.append(va*(1-fraction)+vb*fraction)
        faces.append(expanded)
        face_attributes.append(corner_values)
    # The centre relief slot clears the linked jump ring and the integral claw.
    # Each remaining tongue makes a full U under the straight bar.
    path = [(-3.2, 21.6), (-3.2, 20.8), (-3.2, 18.43)]
    for angle in np.linspace(np.pi, 1.5*np.pi, 9)[1:]:
        path.append((-2.42+.78*np.cos(angle), 18.43+.78*np.sin(angle)))
    path.append((-1.58, 17.65))
    for angle in np.linspace(-.5*np.pi, 0, 9)[1:]:
        path.append((-1.58+.78*np.cos(angle), 18.43+.78*np.sin(angle)))
    path.extend([(-.8, 20.), (-.8, 21.6)])
    path = np.array(path)*.001
    tangent = np.gradient(path, axis=0)
    outward = np.c_[tangent[:, 1], -tangent[:, 0]]
    outward /= np.linalg.norm(outward, axis=1)[:, None]
    layers = [top]
    for k, (yz, direction) in enumerate(zip(path, outward)):
        row = []
        for side in range(2):
            ids = []
            for t in stations:
                base, low_attr = interpolate(side, 0, t)
                _, high_attr = interpolate(side, 1, t)
                # Longitudinal UVs follow the fold without resetting at the turn.
                fraction = (k+1)/(len(path)+1)
                attr = high_attr*(1-fraction)+low_attr*fraction
                p = np.array([base[0], *yz])
                p[1:] += direction * (.0004 if side == 0 else -.0004)
                ids.append(append(p.tolist(), attr))
            row.append(ids)
        layers.append(row)
    for k in range(len(layers)-1):
        previous, following = layers[k:k+2]
        segments = range(6) if k == 0 else [0, 1, 4, 5]
        for j in segments:
            for side in range(2):
                faces.append([previous[side][j], previous[side][j+1], following[side][j+1], following[side][j]])
        boundaries = [0, 6] if k == 0 else [0, 2, 4, 6]
        for j in boundaries:
            faces.append([previous[0][j], following[0][j], following[1][j], previous[1][j]])
    for row, segments in [(layers[1], [2, 3]), (layers[-1], [0, 1, 4, 5])]:
        for j in segments:
            faces.append([row[0][j], row[1][j], row[1][j+1], row[0][j+1]])
    used = sorted({i for face in faces for i in face})
    remap = {v: i for i, v in enumerate(used)}
    data = bpy.data.meshes.new('LoopedSewnRibbon')
    world = origin + np.einsum('ij,jk->ik', np.array(vertices)[used], frame)
    data.from_pydata(world.tolist(), [], [[remap[i] for i in f] for f in faces])
    data.materials.append(old.materials[0])
    corners = {}
    for polygon in data.polygons:
        for corner, index in enumerate(polygon.loop_indices):
            loop = data.loops[index]
            corners[index] = face_attributes[polygon.index][corner] if polygon.index < len(face_attributes) else attributes[used[loop.vertex_index]]
    for n, name in enumerate(uv_names):
        layer = data.uv_layers.new(name=name)
        for loop in data.loops:
            layer.data[loop.index].uv = corners[loop.index][n*2:n*2+2]
    color = data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
    for loop in data.loops:
        color.data[loop.index].color = corners[loop.index][-4:]
    obj.data = data
    recalc(obj)
    for polygon in data.polygons:
        polygon.use_smooth = True
    upper = [i for i in used if i < 70]
    np.testing.assert_allclose(points(obj)[[remap[i] for i in upper]], origin+np.einsum('ij,jk->ik', local[upper], frame), atol=3e-8)
    obj['ribbon_support_indices'] = [remap[i] for i in used if 40 <= i < 70]
    return dict(upper_positions_uv_colours_exact=True, lower_edit_above_body_datum_m=.0236,
                width_m=float(local[:5, 0].max()-local[:5, 0].min()),
                folded_tongues=2, central_relief_slot_width_m=float((local[4,0]-local[0,0])*.30),
                loop_wrap_degrees=180, cloth_thickness_m=.0008,
                bar_nominal_loop_clearance_m=.0001, loop_bottom_local_z_m=.01725,
                explanation='Two continuous U-folds over the existing bar; central lower relief slot clears its linked ring and claw. Upper skins, UVs, colours and RibbonBar unchanged.')


def mount(source, candidates, out):
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, state in [('working', 'remembered'), ('pilot', 'present')]:
        bpy.ops.wm.open_mainfile(filepath=str(source / f'tunic-{name}.blend'))
        frozen = {o.name: geometry_hash(o) for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'Medal'}
        old = bpy.data.objects['Medal']; body = bpy.data.objects['TunicBody']
        metadata = {key: old[key] for key in ['fitted_medal', 'eyelet', 'medal_frame']}
        saved_frame = json.loads(metadata['medal_frame'])
        origin, frame = np.array(saved_frame['origin']), np.array(saved_frame['frame'])
        ribbon = extract_ribbon(old)
        with bpy.data.libraries.load(str(candidates / f'medal-pbr-{state}.blend'), link=False) as (_, destination):
            destination.objects = ['MedalLow']
        metal, = destination.objects
        bpy.context.collection.objects.link(metal)
        local = points(metal)
        original = local.copy()
        reverse = np.flatnonzero(abs(local[:, 1]) < 1e-8)
        normal = -frame[1]
        metal.data.calc_loop_triangles()
        fs = np.array([t.vertices[:] for t in metal.data.loop_triangles])
        gap = continuous_gap((origin+np.einsum('ij,jk->ik', local, frame))[fs], triangles(body), normal)
        origin += normal * (.00025-gap)
        # Only hidden reverse vertices can follow the existing frozen support.
        support = tree(body)
        for i in reverse:
            world = origin + local[i] @ frame
            hit = support.ray_cast(Vector(world+normal*.02), Vector(-normal), .04)[0]
            assert hit is not None
            distance = np.dot(world-np.array(hit), normal)
            local[i, 1] += max(0., distance-.0017)
        gap = continuous_gap((origin+np.einsum('ij,jk->ik', local, frame))[fs], triangles(body), normal)
        origin += normal * (.000251-gap)
        print(name, 'reverse fit', float(np.max(abs(local-original))), 'origin', origin.tolist(), flush=True)
        loop = loop_ribbon(ribbon, origin, frame)
        from mathutils import Matrix
        transform = Matrix.Translation(Vector(origin)) @ Matrix(frame.T.tolist()).to_4x4()
        metal.data.transform(transform)
        # A hidden-reverse fit does not change the baked front, UVs or suspension.
        for i in reverse:
            metal.data.vertices[int(i)].co = origin + local[i] @ frame
        for index, mat in enumerate(metal.data.materials):
            mat.name = ('MedalEnamel_Aged' if name == 'pilot' else 'MedalEnamel') if index else 'MedalBrass_'+state
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    node.image.pack()
        # Match both UV sets by name; the ribbon retains its existing coordinates.
        metal.data.uv_layers[0].name = 'DetailUV'
        bake = metal.data.uv_layers.new(name='BakeUV')
        for dst, src in zip(bake.data, metal.data.uv_layers['DetailUV'].data): dst.uv = src.uv
        for mat in metal.data.materials:
            for node in mat.node_tree.nodes:
                if node.type in ['UVMAP', 'NORMAL_MAP']: node.uv_map = 'DetailUV'
        colors = metal.data.color_attributes.new(name='RibbonColours', type='FLOAT_COLOR', domain='CORNER')
        for c in colors.data: c.color = (1, 1, 1, 1)
        count = len(metal.data.vertices)
        ribbon_bases = [count+i for i in ribbon['ribbon_support_indices']]
        bpy.data.objects.remove(old, do_unlink=True)
        for material in list(bpy.data.materials):
            if material.users == 0: bpy.data.materials.remove(material)
        metal.data.materials[1].name = 'MedalEnamel_Aged' if name == 'pilot' else 'MedalEnamel'
        for material in metal.data.materials: material.use_backface_culling = True
        obj = join_named([metal, ribbon], 'Medal')
        obj['export'] = name == 'working'; obj['aged_export'] = name == 'pilot'
        current = points(obj)
        bases = reverse.tolist()+ribbon_bases
        obj['attachment'] = json.dumps(dict(base_blender_m=current[bases].tolist(), support='TunicBody',
                metal_base_vertex_indices=reverse.tolist(), base_vertex_indices=bases,
                nominal_offset_range_m=[.00025, .0018]))
        for key, value in metadata.items(): obj[key] = value
        fitted = json.loads(metadata['fitted_medal'])
        features = json.loads(obj['feature_names'])
        body_ids = sorted({i for face in metal.data.polygons if face.index < 8270 and metal.data.attributes['FeatureRegion'].data[face.index].value != features.index('bail') for i in face.vertices})
        fitted.update(relief_m=.00118, body_depth_m=float(np.ptp(local[body_ids,1])), body_diameter_m=.032,
                      photoreal_source='medal-low.blend', solid_triangles=8270)
        assert .002 <= fitted['body_depth_m'] <= .004, fitted['body_depth_m']
        obj['body_vertex_indices'] = body_ids
        obj['fitted_medal'] = json.dumps(fitted)
        obj['eyelet'] = json.dumps(dict(json.loads(metadata['eyelet']), construction='integral claw, separate jump ring and solid bar', ribbon_loop=loop))
        obj['medal_frame'] = json.dumps(dict(origin=origin.tolist(), frame=frame.tolist(), body_vertices=3017))
        obj['ribbon_loop'] = json.dumps(loop)
        new_binding = binding(obj, [list(range(count)), list(range(count,len(current)))], body, True)
        if name == 'pilot':
            record = json.loads(bpy.context.scene['tunic5_record'])
            record['bindings']['Medal'] = new_binding
            bpy.context.scene['tunic5_record'] = json.dumps(record)
        assert all(geometry_hash(bpy.data.objects[n]) == h for n,h in frozen.items())
        actual_gap = continuous_gap(triangles(obj)[:8270], triangles(body), normal)
        distances = [support.find_nearest(Vector(current[i]))[3] for i in reverse]
        assert actual_gap >= .00025-1e-8, actual_gap
        assert max(distances) <= .002, distances
        assert len(reverse) >= 25
        report[name] = dict(ribbon=loop, reverse_anchors=len(reverse), reverse_support_min_max_m=[min(distances),max(distances)],
                continuous_metal_clearance_m=actual_gap, mounting_translation_m=origin-np.array(saved_frame['origin']),
                hidden_reverse_max_motion_m=float(np.max(abs(local-original))),
                non_medal_geometry_exact=True)
        report[name]['mounting_translation_m'] = report[name]['mounting_translation_m'].tolist()
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0: bpy.data.meshes.remove(mesh)
        for material in list(bpy.data.materials):
            if material.users == 0: bpy.data.materials.remove(material)
        obj.data.materials[1].name = 'MedalEnamel_Aged' if name == 'pilot' else 'MedalEnamel'
        for mesh_obj in bpy.context.scene.objects:
            if mesh_obj.type == 'MESH' and mesh_obj.get('aged_export' if name == 'pilot' else 'export'):
                mesh_obj.data.name = mesh_obj.name
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(out/f'tunic-{name}.blend'))
        (clean_export if name == 'working' else aged_export)(out / ('dress_uniform.glb' if name == 'working' else 'dress_uniform_aged.glb'))
    (out/'mounting.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--materials', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    mount(a.sources.resolve(), a.materials.resolve(), a.output.resolve())
