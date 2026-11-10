"""Fracture the fitted arm crest with two bridges, then release wool without pins."""
import argparse
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bake_down import decimate
from cloth_metrics import save_surface, surface_metrics
from cloth_stage import calibrated_config, configure
from common import assert_collision_clear, assert_surface_clear, collision, midsurface, surface_tree
from densify import densify
from sofa_full_decay import ROOT, checkpoint, freeze_simulation
from sofa_decay_policy import ORDER
from split_contacts import exclude_split_contacts
from tear_paths import split_polyline


def crest_split(obj):
    tree = surface_tree(obj)
    inverse = obj.matrix_world.inverted()
    records = []
    # Three split runs leave two short bridges and retain the rear corner.
    intervals = [(-.414, -.260), (-.242, -.085), (-.066, .085)]
    reference = []
    for y in np.linspace(-.44, .14, 150):
        p, _, _, _ = tree.find_nearest(Vector((1.095, y, .802)))
        reference.append(p)
    full = sum((a-b).length for a, b in zip(reference, reference[1:]))
    for lo, hi in intervals:
        points = []
        for y in np.linspace(lo, hi, max(3, int((hi-lo)/.004))):
            p, _, _, _ = tree.find_nearest(Vector((1.095, y, .802)))
            points.append(tuple(inverse@p))
        records.append(split_polyline(obj, points))
    share = sum(r['split_length_m'] for r in records)/full
    return {'method': 'zero-area crest splits; two retained 18/19 mm bridges plus end corners',
            'reference_crest_length_m': full, 'runs': records, 'split_share': share,
            'pins': 0, 'G18_pass': .6 <= share <= .9}


def install_contacts():
    names = {'Frame', 'Feet', 'Rivets', 'DecayFloor'}
    names.update(n+suffix for n in ORDER for suffix in ['_GameContact', '_Residue'])
    missing = names-set(bpy.context.scene.objects.keys())
    if missing:
        raise ValueError(f'Throw needs all settled mechanical contacts: {sorted(missing)}')
    floor = bpy.data.objects['DecayFloor']
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.)
    for vertex in bm.verts:
        vertex.co.x *= 8
        vertex.co.y *= 8
        vertex.co.z = vertex.co.z*.1-.05
    bm.to_mesh(floor.data)
    bm.free()
    floor['aged_export'] = False
    floor.hide_render = True
    contacts = {}
    for obj in bpy.context.scene.objects:
        for mod in list(obj.modifiers):
            if mod.type == 'COLLISION':
                obj.modifiers.remove(mod)
        if obj.name in names:
            collision(obj, .001)
            obj.collision.cloth_friction = 8 if obj.name == 'DecayFloor' else 5
            contacts[obj.name] = float(obj.collision.cloth_friction)
    return contacts


def run(source, out, frames=480):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    record = json.loads(bpy.context.scene['sofa_decay_record'])
    bpy.context.scene.frame_set(1)
    contacts = install_contacts()
    obj = bpy.data.objects['Throw']
    obj.modifiers.clear()
    midsurface(obj)
    reference = len(obj.data.vertices)
    density = densify(obj, levels=2)
    from sofa_contact_mesh import resolve_elements
    density['contact_resolution'] = resolve_elements(obj)
    splits = crest_split(obj)
    exclude_split_contacts(obj)
    assert_surface_clear(obj)
    assert_collision_clear(obj)
    config = calibrated_config('wool', .006, .022222222, frames)
    config.update(stiffness=200, bending=.9, shrink_min=0., quality=16, time_scale=.6,
                  self_collision=True, self_distance=.001, distance=.0015, collision_quality=6)
    mod = configure(obj, config, reference)
    actual_self_distance = float(mod.collision_settings.self_distance_min)
    checkpoint(out, record, 'throw-prepared.blend')
    simulation = freeze_simulation(obj, mod, frames, trace_path=out/'throw-contact-trace.json')
    save_surface(obj, out/'throw-dense.npz')
    low, reduction = decimate(obj, 3200)
    low.name = 'Throw_GameContact'
    low['aged_export'] = False
    low.hide_render = True
    save_surface(low, out/'throw-game.npz')
    record['throw'] = {'density': density, 'splits': splits, 'settings': config,
                       'collider_friction_percent': contacts,
                       'contact_trace': str(out/'throw-contact-trace.json'),
                       'actual_self_distance_m': actual_self_distance,
                       'simulation': simulation, 'reduction': reduction,
                       'dense_metrics': surface_metrics(obj), 'game_metrics': surface_metrics(low)}
    checkpoint(out, record, 'throw.blend')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'tmp/age/pass6/cushions.blend')
    p.add_argument('--out', type=Path, default=ROOT/'tmp/age/pass6')
    p.add_argument('--frames', type=int, default=480)
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    run(a.source, a.out, a.frames)
