"""Pass-9 sofa trial. Production publication remains acceptance-gated."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import boundary_hausdorff, decimate
from cloth_metrics import lip_lift, save_surface, surface_metrics
from common import assert_collision_clear, assert_surface_clear, collision
from sofa_decay_joint import restore_part
from sofa_decay_policy import ORDER
from sofa_decay_throw import install_contacts
from sofa_full_decay import ROOT, checkpoint, initialize
from sofa_partitions import clear_partitions, fitted_back_barriers, pair_crossings
from sofa_pass8 import combine, contacts, prepare, prepare_throw
from sofa_pass8_finish import clearance, initial_contacts, save_lip_classes
from sofa_pass8_mesh import mesh_quality, split_world, tie_pins
from sofa_pass8_solver import cloth, solve
from sofa_pass9_finish import carry_clearance, open_lips, points
from sofa_pass9_physics import tune



def prepare_part(name, out):
    obj, detail, driver, pins = prepare(name, out)
    detail['plan']['frames'] = 2400
    if name.startswith('Back'):
        p = points(obj)
        lo, hi = p.min(0), p.max(0)
        releases = [split_world(obj, [(x, .275, z) for z in np.linspace(.433, .828, 80)])
                    for x in [lo[0]+.012, hi[0]-.012]]
        pins, patches = tie_pins(obj)
        quality = mesh_quality(obj)
        if not quality['pass']:
            raise ValueError(f'{name}: side-release element quality failed: {quality}')
        detail.update(side_boxing_release=releases, tie_patches=patches, mesh_quality=quality,
                      filling_driver='opened side boxing, static lower-return residue, gentle inward load')
    return obj, detail, driver, pins


def stage(out, record, back=False):
    names = ORDER[3:] if back else ORDER[:3]
    bpy.context.scene.frame_set(1)
    if not back:
        record['seat_back_barriers'] = fitted_back_barriers()
    else:
        clear_partitions()
        for name in ORDER[:3]:
            collision(bpy.data.objects[name+'_GameContact'], .001)
        collision(bpy.data.objects['Throw'], .001)
    states = [prepare_part(name, out) for name in names]
    joint, reference, pins = combine(states, 'JointBacks' if back else 'JointSeats')
    bpy.context.view_layer.update()
    assert_surface_clear(joint)
    assert_collision_clear(joint)
    initial_contacts(joint, contacts())
    if back:
        for name in names:
            for seat in ORDER[:3]:
                count = pair_crossings(bpy.data.objects[name+'_Residue'], bpy.data.objects[seat+'_GameContact'])
                if count:
                    raise ValueError(f'C5: {name} residue crosses {seat}: {count}')
    label = 'backs' if back else 'seats'
    mod, settings = cloth(joint, reference, pins=pins, frames=2400, quality=30 if back else 20)
    tune(joint, mod, settings, label)
    record[label+'_setup'] = {'parts': list(names), 'settings': settings,
                              'mesh_quality': mesh_quality(joint), 'pins': len(pins), 'C5_pass': True}
    checkpoint(out, record, label+'-prepared.blend')
    result = solve(joint, mod, out, label, frames=2400, collapse_frames=600)
    record[label+'_simulation'] = result
    checkpoint(out, record, label+'-solved.blend')
    finish_parts(joint, states, out, record, back)


def finish_parts(joint, states, out, record, back=False):
    label = 'backs' if back else 'seats'
    settings = record[label+'_setup']['settings']
    result = record[label+'_simulation']
    lows = []
    for obj, detail, driver, _ in states:
        restore_part(joint, obj)
        detail['lip_curl'] = open_lips(obj, detail['plan']['seed'])
        detail.update(settings=settings, simulation=result)
        low, reduction = decimate(obj, 2000 if back else 2400, protect=.002, keep_factor=4)
        low.name = obj.name+'_GameContact'
        low['aged_export'] = False
        low.hide_render = True
        lows.append((obj, low, detail, reduction, points(low)))
        if driver is not None:
            bpy.data.objects.remove(driver, do_unlink=True)
    bpy.data.objects.remove(joint, do_unlink=True)
    supports = [o for o in contacts() if not o.name.startswith('CushionPartition_')]
    record[label+'_clearance'] = clearance(supports+[low for _, low, _, _, _ in lows],
                                          {low.name for _, low, _, _, _ in lows})
    for obj, low, detail, reduction, original in lows:
        detail['dense_clearance'] = carry_clearance(obj, low, original)
        detail.update(dense_metrics=surface_metrics(obj), game_metrics=surface_metrics(low), G5=lip_lift(obj))
        reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(obj, low)
        detail['cover_decimation'] = reduction
        save_surface(obj, out/(obj.name+'-dense.npz'))
        save_surface(low, out/(obj.name+'-game.npz'))
        save_lip_classes(obj, out/(obj.name+'-lip-classes.npz'))
        for level in ['DenseResidue', 'Residue']:
            save_surface(bpy.data.objects[obj.name+'_'+level], out/(obj.name+('-dense-residue.npz' if level == 'DenseResidue' else '-game-residue.npz')))
        record['cushions'][obj.name] = detail
    clear_partitions()
    checkpoint(out, record, 'cushions.blend' if back else 'seats.blend')


def throw(out, record):
    bpy.context.scene.frame_set(1)
    contact_settings = install_contacts()
    obj = bpy.data.objects['Throw']
    reference, density, splits, pins = prepare_throw(obj)
    p = points(obj)
    pins = {i: 1. for i in range(len(p)) if p[i, 1] >= .120 and p[i, 0] >= 1.100 and .765 <= p[i, 2] <= .790}
    if not pins:
        raise ValueError('Throw outer rear corner has no retained stitches')
    splits.update(pins=len(pins), pin_policy='outer rear arm corner: x>=1.100 m, y>=0.120 m, z=0.765..0.790 m')
    assert_surface_clear(obj)
    assert_collision_clear(obj)
    initial_contacts(obj, contacts())
    mod, settings = cloth(obj, reference, 'wool', frames=2400, quality=30, pins=pins)
    tune(obj, mod, settings, 'throw')
    record['throw'] = dict(density=density, splits=splits, settings=settings,
                           collider_friction_percent=contact_settings)
    checkpoint(out, record, 'throw-prepared.blend')
    result = solve(obj, mod, out, 'throw', frames=2400, collapse_frames=600)
    record['throw']['simulation'] = result
    record['throw']['lip_curl'] = open_lips(obj, 9699)
    low, reduction = decimate(obj, 3200, protect=.002, keep_factor=4)
    low.name = 'Throw_GameContact'
    low['aged_export'] = False
    low.hide_render = True
    original = points(low)
    record['throw']['clearance'] = clearance(contacts()+[low], {low.name})
    record['throw']['dense_clearance'] = carry_clearance(obj, low, original)
    reduction['boundary_hausdorff_upper_m'] = boundary_hausdorff(obj, low)
    record['throw'].update(reduction=reduction, dense_metrics=surface_metrics(obj), game_metrics=surface_metrics(low))
    save_surface(obj, out/'throw-dense.npz')
    save_surface(low, out/'throw-game.npz')
    checkpoint(out, record, 'throw.blend')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass9')
    parser.add_argument('--stage', choices=['seats', 'backs', 'throw'], required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    args.out.mkdir(parents=True, exist_ok=True)
    controls = json.loads((args.out/'controls.json').read_text())
    if not controls['pass']:
        raise ValueError('Forty-frame controls must pass before production')
    if args.source:
        bpy.ops.wm.open_mainfile(filepath=str(args.source))
        record = json.loads(bpy.context.scene['sofa_decay_record'])
    else:
        record = initialize()
        record['method'] = 'pass 9: pass-8 releases with softened cloth, zero-target back vacuum and shared finishing deformation'
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
