"""Build the second geometry-aging pass from the unchanged fitted prop sources."""
import argparse
import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import export, save

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prop', choices=['sofa', 'dress_uniform'], required=True)
    parser.add_argument('--trial', default='pass2-a')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    folder = ROOT / 'tools/blender/quarters' / args.prop
    stem = 'sofa' if args.prop == 'sofa' else 'tunic'
    params = json.loads((folder / 'aging.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / f'{stem}-working.blend'))
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and obj.name not in params['parts']:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in params['parts']:
        obj = bpy.data.objects[name]
        obj.hide_set(False)
        obj.hide_render = False
        obj.modifiers.clear()
        obj['aged_export'] = True
    if args.prop == 'sofa':
        from sofa_pass2 import build
    else:
        from tunic_pass2 import build
    record = {'trial': args.trial, 'seed': params['seed'], 'prop': args.prop, 'construction': build(params['seed'])}
    record['section_repairs'] = {obj.name: int(obj.get('pruned_impossible_fibres', 0)) for obj in bpy.context.scene.objects if obj.type == 'MESH'}
    out = ROOT / 'tmp/age/pass2' / args.trial
    out.mkdir(parents=True, exist_ok=True)
    save(out / f'{stem}-aged.blend', record)
    export(out / f'{args.prop}_aged.glb')
    (out / f'{args.prop}-trial.json').write_text(json.dumps(record, indent=2) + '\n')
    if args.publish:
        save(folder / f'{stem}-aged.blend', record)
        export(ROOT / params['asset'])
        (folder / f'{stem}-aged.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
