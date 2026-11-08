"""Pass-8 joint seat/back solves and one-corner, pinned-cap throw.

No game asset is published by this runner. Acceptance owns publication.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import decimate, boundary_hausdorff
from cloth_metrics import lip_lift, save_surface, surface_metrics
from common import assert_collision_clear, assert_surface_clear, collision, midsurface, recalc
from fabric_mesh import new_object
from foam_collapse import largest_shell
from sofa_decay_joint import restore_part
from sofa_decay_policy import ORDER, cushion_plan
from sofa_decay_throw import install_contacts
from sofa_full_decay import ROOT, initialize, checkpoint, residue_pair, envelope_for, open_cover_bottom, back_splits
from sofa_partitions import fitted_back_barriers, clear_partitions, pair_crossings
from sofa_pass8_mesh import clean_mesh, mesh_quality, welt_release, tie_pins, split_world
from sofa_pass8_solver import cloth, solve
from sofa_pass8_finish import lip_curl, clearance, save_lip_classes, initial_contacts

RESIDUE = ROOT/'tmp/age/pass5/residue-stable/seat-residue.npz'


def back_residue(obj, plan):
    dense, low, report = residue_pair(obj, plan, RESIDUE)
    for part in [dense, low]:
        inverse = part.matrix_world.inverted()
        for v in part.data.vertices:
            p = part.matrix_world@v.co
            p.y = .350+(p.y-.245)*.17
            v.co = inverse@p
        recalc(part)
    report['placement'] = 'lower return at y=0.335..0.365, outside settled seat space'
    return dense, low, report


def envelope(obj, residue, plan):
    result = envelope_for(obj, residue, plan)
    if plan['back']:
        key = result.data.shape_keys.key_blocks['Powder filling']
        inverse = result.matrix_world.inverted()
        for v, fitted in zip(key.data, obj.data.vertices):
            p = obj.matrix_world@fitted.co
            q = result.matrix_world@v.co
            q.y = .350+(p.y-.348)*.12
            v.co = inverse@q
    return result


def prepare(name, out):
    obj = bpy.data.objects[name]
    plan = cushion_plan(name)
    plan.update(frames=900, collapse_frames=180, residue_warp=True,
                settled_contacts=[], rest_mode='fitted', pins=0)
    largest_shell(obj)
    reference = len(obj.data.vertices)
    dense, residue, reduction = back_residue(obj, plan) if plan['back'] else residue_pair(obj, plan, RESIDUE)
    driver = envelope(obj, residue, plan)
    open_cover_bottom(obj, plan['back'])
    density = clean_mesh(obj)
    if plan['back']:
        tears = back_splits(obj, plan['seed'])
    else:
        from seat_tears import author
        tears = author(obj, obj.matrix_world.translation.x, plan['seed'])
    tear_group = obj.vertex_groups.new(name='Panel tear')
    lip_index = obj.vertex_groups['Lip shrink'].index
    for v in obj.data.vertices:
        if any(g.group == lip_index and g.weight >= .5 for g in v.groups):
            tear_group.add([v.index], 1., 'REPLACE')
    release = welt_release(obj, plan['back'])
    pins, patches = tie_pins(obj) if plan['back'] else ({}, [])
    plan['pins'] = len(pins)
    welt = obj.vertex_groups.new(name='Welt')
    for v in obj.data.vertices:
        welt.add([v.index], .1 if abs(v.normal.z) < .5 else 1., 'REPLACE')
    quality = mesh_quality(obj)
    if not quality['pass']:
        raise ValueError(f'{name}: splits damaged element quality: {quality}')
    detail = dict(reference_vertices=reference, dense=density, tears=tears,
                  residue_decimation=reduction, plan=plan, welt_release=release,
                  tie_patches=patches, mesh_quality=quality,
                  split_contacts={'exclusions': 0}, partitions=[])
    return obj, detail, driver, pins


def combine(states, label):
    vertices, faces, uvs, groups, pins = [], [], [], {}, {}
    reference = 0
    for obj, detail, _, local_pins in states:
        start = len(vertices)
        vertices.extend(tuple(obj.matrix_world@v.co) for v in obj.data.vertices)
        for face in obj.data.polygons:
            faces.append(tuple(start+i for i in face.vertices))
            uvs.append([tuple(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices])
        for group in obj.vertex_groups:
            values = groups.setdefault(group.name, {})
            for v in obj.data.vertices:
                for entry in v.groups:
                    if entry.group == group.index:
                        values[start+v.index] = entry.weight
        groups['Part '+obj.name] = {i: 1. for i in range(start, len(vertices))}
        pins.update({start+i: w for i, w in local_pins.items()})
        reference += detail['reference_vertices']
        obj.hide_render = True
        obj['aged_export'] = False
    joint = new_object(label, vertices, faces, states[0][0].data.materials[0])
    joint['aged_export'] = False
    for face, pattern in zip(joint.data.polygons, uvs):
        for index, uv in zip(face.loop_indices, pattern):
            joint.data.uv_layers.active.data[index].uv = uv
    for name, values in groups.items():
        group = joint.vertex_groups.new(name=name)
        for index, weight in values.items():
            group.add([index], weight, 'REPLACE')
    return joint, reference, pins


def contacts():
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and
            any(m.type == 'COLLISION' for m in o.modifiers)]


def stage(out, record, back=False):
    names = ORDER[3:] if back else ORDER[:3]
    bpy.context.scene.frame_set(1)
    if not back:
        record['seat_back_barriers'] = fitted_back_barriers()
    else:
        clear_partitions()
        for name in ORDER[:3]:
            collision(bpy.data.objects[name+'_GameContact'], .001)
    states = [prepare(name, out) for name in names]
    joint, reference, pins = combine(states, 'JointBacks' if back else 'JointSeats')
    bpy.context.view_layer.update()
    assert_surface_clear(joint)
    assert_collision_clear(joint)
    c5 = initial_contacts(joint, contacts())
    if back:
        for name in ORDER[3:]:
            for seat in ORDER[:3]:
                count = pair_crossings(bpy.data.objects[name+'_Residue'], bpy.data.objects[seat+'_GameContact'])
                if count:
                    raise ValueError(f'C5: {name} residue crosses {seat}: {count}')
    mod, settings = cloth(joint, reference, pins=pins)
    label = 'backs' if back else 'seats'
    record[label+'_setup'] = {'parts': list(names), 'settings': settings,
                              'mesh_quality': mesh_quality(joint), 'pins': len(pins), 'C5_pass': True}
    checkpoint(out, record, label+'-prepared.blend')
    result = solve(joint, mod, out, label)
    record[label+'_simulation'] = result
    # Store the solve before the optional finishing operations, so a failed
    # reduction cannot discard the actual simulated state.
    checkpoint(out, record, label+'-solved.blend')
    lows = []
    for obj, detail, driver, _ in states:
        restore_part(joint, obj)
        detail['lip_curl'] = lip_curl(obj, detail['plan']['seed'])
        detail.update(settings=settings, simulation=result, dense_metrics=surface_metrics(obj), G5=lip_lift(obj))
        save_surface(obj, out/(obj.name+'-dense.npz'))
        save_lip_classes(obj, out/(obj.name+'-lip-classes.npz'))
        save_surface(bpy.data.objects[obj.name+'_DenseResidue'], out/(obj.name+'-dense-residue.npz'))
        save_surface(bpy.data.objects[obj.name+'_Residue'], out/(obj.name+'-game-residue.npz'))
        low, reduction = decimate(obj, 2000 if back else 2400, protect=.002, keep_factor=4)
        low.name = obj.name+'_GameContact'
        low['aged_export'] = False
        low.hide_render = True
        lows.append((obj, low, detail, reduction))
        bpy.data.objects.remove(driver, do_unlink=True)
    bpy.data.objects.remove(joint, do_unlink=True)
    supports = [o for o in contacts() if not o.name.startswith('CushionPartition_')]
    repair = clearance(supports+[low for _, low, _, _ in lows], {low.name for _, low, _, _ in lows})
    record[label+'_clearance'] = repair
    for obj, low, detail, reduction in lows:
        reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(obj, low)
        detail['cover_decimation'] = reduction
        detail['game_metrics'] = surface_metrics(low)
        save_surface(low, out/(obj.name+'-game.npz'))
        record['cushions'][obj.name] = detail
    clear_partitions()
    checkpoint(out, record, 'cushions.blend' if back else 'seats.blend')
    return record


def throw(out, record):
    bpy.context.scene.frame_set(1)
    contact_settings = install_contacts()
    obj = bpy.data.objects['Throw']
    obj.modifiers.clear()
    midsurface(obj)
    reference = len(obj.data.vertices)
    density = clean_mesh(obj)
    # Only the rear 65 mm bridge survives this single crest run.
    cut = split_world(obj, [(1.095, y, .802) for y in np.linspace(-.44, .075, 130)])
    points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    pins = {int(i): 1. for i in np.flatnonzero((points[:, 0] < 1.078) &
            (points[:, 0] > .98) & (points[:, 2] > .785))}
    if not pins:
        raise ValueError('Throw cap has no pins')
    assert_surface_clear(obj)
    assert_collision_clear(obj)
    initial_contacts(obj, contacts())
    mod, config = cloth(obj, reference, 'wool', quality=30, pins=pins)
    record['throw'] = dict(density=density, splits={'runs': [cut], 'split_share': cut['split_length_m']/.58,
                            'reference_crest_length_m': .58, 'pins': len(pins)},
                           settings=config, collider_friction_percent=contact_settings)
    checkpoint(out, record, 'throw-prepared.blend')
    simulation = solve(obj, mod, out, 'throw', collapse_frames=0)
    record['throw']['simulation'] = simulation
    save_surface(obj, out/'throw-dense.npz')
    low, reduction = decimate(obj, 3200, protect=.002, keep_factor=4)
    low.name = 'Throw_GameContact'
    low['aged_export'] = False
    low.hide_render = True
    record['throw']['clearance'] = clearance(contacts()+[low], {low.name})
    reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(obj, low)
    record['throw'].update(reduction=reduction, dense_metrics=surface_metrics(obj), game_metrics=surface_metrics(low))
    save_surface(low, out/'throw-game.npz')
    checkpoint(out, record, 'throw.blend')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass8')
    parser.add_argument('--stage', choices=['seats', 'backs', 'throw'], required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    controls = json.loads((args.out/'controls.json').read_text())
    if not controls['pass']:
        raise ValueError('Early controls must pass before production')
    if args.source:
        bpy.ops.wm.open_mainfile(filepath=str(args.source))
        record = json.loads(bpy.context.scene['sofa_decay_record'])
    else:
        record = initialize()
        record['method'] = 'pass 8: clean level-1 joint seats, joint tied backs, pinned-cap throw; no exclusions or rest carrier'
        frame = bpy.data.objects['Frame']
        p = np.array([frame.matrix_world@v.co for v in frame.data.vertices])
        record['rear_frame_bounds_m'] = [p.min(0).tolist(), p.max(0).tolist()]
        record['rear_rail_policy'] = 'Use the fitted Frame back rail from assemble.fit_frame; no synthetic rear slab.'
        floor = bpy.data.objects['DecayFloor']
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.)
        for vertex in bm.verts:
            vertex.co.x *= 8
            vertex.co.y *= 8
            vertex.co.z = vertex.co.z*.1-.05
        bm.to_mesh(floor.data)
        bm.free()
    if args.stage == 'throw':
        throw(args.out, record)
    else:
        stage(args.out, record, args.stage == 'backs')
