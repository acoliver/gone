"""Target-led sofa pass 11. Scratch exports never imply publication approval."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import boundary_hausdorff, decimate
from cloth_metrics import lip_lift, save_surface, surface_metrics
from common import surface_tree
from fabric_mesh import join, material, new_object
from sofa_decay_policy import ORDER
from sofa_full_decay import ROOT, checkpoint
from sofa_pass8_finish import clearance, save_lip_classes
from sofa_pass9_finish import carry_clearance, points
from sofa_pass10_mesh import fair_interior
from sofa_pass11_mesh import cut_gash, curl_gashes, fill_small_wear, gash_field, lean_back, seat_bowl, set_points, simplify_boundary, surface_area


def reduce_cover(dense, target):
    working = dense.copy()
    working.data = dense.data.copy()
    bpy.context.collection.objects.link(working)
    simplification = simplify_boundary(working)
    low, report = decimate(working, target, protect=.001, keep_factor=15)
    bpy.data.objects.remove(working, do_unlink=True)
    report['boundary_simplification'] = simplification
    report['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, low)
    return low, report


def remove_specks(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = set(bm.faces)
    remove = []
    while remaining:
        face = remaining.pop()
        pending, component = [face], {face}
        while pending:
            for edge in pending.pop().edges:
                for other in edge.link_faces:
                    if other in remaining:
                        remaining.remove(other)
                        component.add(other)
                        pending.append(other)
        if sum(f.calc_area() for f in component) < .001:
            remove.extend(component)
    bmesh.ops.delete(bm, geom=remove, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    return len(remove)


def gash_spec(name, obj, index):
    cx = obj.matrix_world.translation.x
    if name.startswith('Seat'):
        return dict(centre=[cx+(-.025, .055, -.045)[index], -.295, .43],
                    tangent=[1, 0, 0], across=[0, 1, 0], half_length=(.118, .090, .125)[index],
                    half_width=(.048, .038, .052)[index], seed=9801+index*37)
    centre = Vector((cx+(-.07, .13, -.10)[index], -.4, .535))
    hit, _, _, _ = surface_tree(obj).ray_cast(centre, Vector((0, 1, 0)))
    if hit is None:
        raise ValueError(f'{name}: target seam gash misses the forward cover')
    return dict(centre=list(hit), tangent=[0, 0, 1], across=[1, 0, 0],
                half_length=(.070, .060, .070)[index], half_width=.035, seed=9912+index*37,
                depth_max=hit.y+.028, rag_scale=.35)


def foam_core(name, spec, reference):
    rng = np.random.default_rng(spec['seed'])
    sectors, rings = 28, 3
    front = []
    for ring in range(rings+1):
        radius = ring/rings*.82
        angles = [0.] if not ring else np.arange(sectors)*2*np.pi/sectors
        for angle in angles:
            u = spec['half_length']*radius*np.cos(angle)
            centre = np.array(spec['centre'])+np.array(spec['tangent'])*u
            width = -gash_field([centre], spec)[0]
            position = centre+np.array(spec['across'])*width*radius*np.sin(angle)*.72
            hit, _, _, _ = reference.ray_cast(Vector((position[0], -.6, position[2])), Vector((0, 1, 0)))
            if hit is None:
                raise ValueError(f'{name}: exposed foam has no cover depth reference')
            position[1] = hit.y+.009+rng.uniform(.001, .005)
            front.append(position)
    faces = [(0, 1+i, 1+(i+1)%sectors) for i in range(sectors)]
    for ring in range(1, rings):
        a, b = 1+(ring-1)*sectors, 1+ring*sectors
        for i in range(sectors):
            j = (i+1)%sectors
            faces.extend([(a+i, b+i, b+j), (a+i, b+j, a+j)])
    vertices = list(front)
    outer = 1+(rings-1)*sectors
    back = len(vertices)
    vertices.append(np.array(spec['centre'])+[0, .035, 0])
    for i in range(sectors):
        j = (i+1)%sectors
        faces.append((outer+j, outer+i, back))
    foam = new_object(name+'_ExposedFoam', vertices, faces, material('Foam_Exposed_'+name, (.40, .26, .12)))
    for polygon in foam.data.polygons:
        polygon.use_smooth = False
    return foam


def replace_dense(name, low):
    old = bpy.data.objects[name]
    bpy.data.objects.remove(old, do_unlink=True)
    dense = low.copy()
    dense.data = low.data.copy()
    bpy.context.collection.objects.link(dense)
    dense.name = name
    dense['aged_export'] = False
    return dense


def save_geometry(out, record):
    for name in [*ORDER, 'Throw']:
        dense, low = bpy.data.objects[name], bpy.data.objects[name+'_GameContact']
        item = record['throw'] if name == 'Throw' else record['cushions'][name]
        item.update(dense_metrics=surface_metrics(dense), game_metrics=surface_metrics(low))
        reduction = item['reduction' if name == 'Throw' else 'cover_decimation']
        reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(dense, low)
        stem = 'throw' if name == 'Throw' else name
        save_surface(dense, out/(stem+'-dense.npz'))
        save_surface(low, out/(stem+'-game.npz'))
        bm = bmesh.new()
        bm.from_mesh(low.data)
        layer = bm.verts.layers.deform.active
        group = low.vertex_groups['Panel tear'].index
        segments = [[tuple(low.matrix_world@v.co) for v in edge.verts] for edge in bm.edges
                    if edge.is_boundary and max(v[layer].get(group, 0.) for v in edge.verts) >= .5]
        bm.free()
        np.savez_compressed(out/(stem+'-gash-seeds.npz'), segments=np.array(segments).reshape(-1, 2, 3))
        if name == 'Throw':
            continue
        part = record['pass11']['parts'][name]
        part['area_ratio_after_cut_and_finish'] = surface_area(dense)/part['source_area_m2']
        item['G5'] = lip_lift(dense)
        save_lip_classes(dense, out/(name+'-lip-classes.npz'))
        for suffix, level in [('DenseResidue', 'dense'), ('Residue', 'game')]:
            save_surface(bpy.data.objects[name+'_'+suffix], out/(name+'-'+level+'-residue.npz'))
    checkpoint(out, record, 'geometry.blend')


def geometry(source, out):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    record['pass11'] = dict(source=str(source), target='docs/art/quarters/sheets/sofa/aged-target.png',
                            method='retained solve with explicit target-led finishing; not a new gravity simulation', parts={})
    for i, name in enumerate(ORDER):
        low = bpy.data.objects[name+'_GameContact']
        low.modifiers.clear()
        if low.vertex_groups.get('Keep'):
            low.vertex_groups.remove(low.vertex_groups['Keep'])
        area = surface_area(low)
        item = dict(source_area_m2=area, removed_speck_faces=remove_specks(low))
        item['patched_small_wear'] = fill_small_wear(low)
        if name.startswith('Seat'):
            set_points(low, seat_bowl(points(low), low.matrix_world.translation.x, (.026, .034, .029)[i]))
        else:
            item['lean'] = lean_back(low, (15, 14, 12)[i-3], floor=.416)
        item['fairing'] = fair_interior(low, maximum=.010 if name.startswith('Back') else .003,
                                        iterations=12 if name.startswith('Back') else 4, nonshrinking=True)
        reference = surface_tree(low)
        spec = gash_spec(name, low, i%3)
        item['gash'] = cut_gash(low, spec, spacing=.010 if i >= 3 else .008)
        item['curl'] = curl_gashes(low)
        print('GASH_BEFORE_REDUCTION', name, json.dumps(item), flush=True)
        dense = replace_dense(name, low)
        low.name = name+'_CutSource'
        bpy.data.objects.remove(low, do_unlink=True)
        reduced, reduction = reduce_cover(dense, 1900 if i < 3 else 2600)
        reduced.name = name+'_GameContact'
        reduced['aged_export'] = False
        record['cushions'][name]['cover_decimation'] = reduction
        if i >= 3:
            foam = foam_core(name, spec, reference)
            dense_foam = foam.copy()
            dense_foam.data = foam.data.copy()
            bpy.context.collection.objects.link(dense_foam)
            join(bpy.data.objects[name+'_Residue'], [foam])
            join(bpy.data.objects[name+'_DenseResidue'], [dense_foam])
        item['area_ratio_after_cut_and_finish'] = surface_area(dense)/area
        record['pass11']['parts'][name] = item
        print('PASS11_PART', name, json.dumps(item), flush=True)
    low = bpy.data.objects['Throw_GameContact']
    low.modifiers.clear()
    if low.vertex_groups.get('Keep'):
        low.vertex_groups.remove(low.vertex_groups['Keep'])
    crease = dict(centre=[1.085, .035, .747], tangent=[0, 1, 0], across=[0, 0, 1],
                  half_length=.085, half_width=.009, seed=9967)
    record['pass11']['throw_crease'] = cut_gash(low, crease, spacing=.006)
    record['pass11']['throw_curl'] = curl_gashes(low, amplitude=.0035)
    dense = replace_dense('Throw', low)
    bpy.data.objects.remove(low, do_unlink=True)
    low, reduction = reduce_cover(dense, 2800)
    low.name = 'Throw_GameContact'
    low['aged_export'] = False
    record['throw']['reduction'] = reduction
    supports = [bpy.data.objects[n] for n in ['Frame', 'Feet', 'Rivets', 'DecayFloor']]
    supports += [bpy.data.objects[n+'_Residue'] for n in ORDER]
    covers = [bpy.data.objects[n+'_GameContact'] for n in [*ORDER, 'Throw']]
    originals = {o.name: points(o) for o in covers}
    checkpoint(out, record, 'geometry-preclearance.blend')
    record['pass11']['clearance'] = clearance(supports+covers, {o.name for o in covers}, maximum=.008, iterations=12)
    for name in [*ORDER, 'Throw']:
        report = carry_clearance(bpy.data.objects[name], bpy.data.objects[name+'_GameContact'], originals[name+'_GameContact'])
        print('DENSE_TRANSFER', name, report, flush=True)
        if not np.isfinite(points(bpy.data.objects[name])).all():
            raise ValueError(f'{name}: dense clearance transfer generated non-finite positions')
    save_geometry(out, record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'tmp/age/pass10/geometry.blend')
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass11')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    geometry(args.source, args.out)
