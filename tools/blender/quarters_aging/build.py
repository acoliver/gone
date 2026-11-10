"""Derive and bake an aged prop, or byte-reproducibly export its baked source."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import collision, export, save
from foam_collapse import collapse, seat_on_support
from cloth_decay import decay
from debris import scatter

ROOT = Path(__file__).resolve().parents[3]


def run(source, params, output, stages=frozenset({'foam', 'cloth', 'debris'})):
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    names = params['parts']
    # Remove hidden construction patterns so they cannot collide with the aged cloth.
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and obj.name not in names:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in names:
        obj = bpy.data.objects[name]
        obj.hide_set(False)
        obj.hide_render = False
        obj.modifiers.clear()
        obj['aged_export'] = True
    for name in params['colliders']:
        collision(bpy.data.objects[name])
    # Floor participates in cloth settling, but has no exported geometry.
    floor = -params['debris']['drop_height_m'] if 'drop_height_m' in params['debris'] else params['floor_z_m']
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, floor))
    ground = bpy.context.object
    ground.name = 'AgingFloorCollider'
    ground.hide_render = True
    collision(ground)
    record = {'trial': params['trial'], 'seed': params['seed'], 'parameters': params, 'foam': {}, 'cloth': {}}
    if 'foam' in stages:
        for index, name in enumerate(params.get('foam', {}).get('names', [])):
            record['foam'][name] = collapse(bpy.data.objects[name], params['foam'], params['seed'] + index * 101)
            collision(bpy.data.objects[name], .0005)
    if 'cloth' in stages:
        for index, (name, config) in enumerate(params.get('cloth', {}).items()):
            details = [bpy.data.objects[n] for n in config.get('protected_details', [])]
            record['cloth'][name] = decay(bpy.data.objects[name], config, params['seed'] + 1000 + index, details)
    if 'debris' in stages:
        record['debris'] = scatter(bpy.data.objects[params['debris']['source']], params['debris'], params['seed'] + 2000)
    if 'foam' in stages and params.get('foam'):
        record['support_fit'] = {name: seat_on_support(bpy.data.objects[name], params['foam']) for name in params['foam']['names']}
    bpy.data.objects.remove(ground, do_unlink=True)
    baked = output.with_suffix('.blend')
    save(baked, record)
    export(ROOT / params['asset'])
    output.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--params', type=Path)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reexport', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.reexport:
        bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
        export(args.output)
    else:
        run(args.source, json.loads(args.params.read_text()), args.output)


if __name__ == '__main__':
    main()
