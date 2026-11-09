"""Fit baked cloth contacts using exact overlaps of exported triangle planes."""
import argparse
import json
from pathlib import Path
import subprocess

from verify import HERE, ROOT, load, support_gap

BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'


def headboard_shift(part, headboard, gap=.001):
    # Blender back +Y becomes glTF -Z.
    return float(part.bounds[0, 2] - headboard.bounds[1, 2] - gap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', choices=('remembered', 'aged'), default='remembered')
    args = parser.parse_args()
    suffix = '_aged' if args.state == 'aged' else ''
    _, meshes = load(ROOT / f'assets/props/quarters/bed_soft{suffix}.glb')
    _, bed = load(ROOT / 'assets/props/quarters/bed.glb')
    shifts = {}
    for name in ('Pillow_L', 'Pillow_R', 'Quilt'):
        back = 0 if name == 'Quilt' else headboard_shift(meshes[name], bed['Headboard'])
        meshes[name].apply_translation([0, 0, -back])
        shifts[name] = {'back_m': back, 'up_m': .001 - support_gap(meshes[name], meshes['Mattress'])}
    path = ROOT / f'tmp/bed_soft2/{args.state}-contact-shifts.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(shifts, indent=2) + '\n')
    print(shifts, flush=True)
    subprocess.run([BLENDER, '--background', '--factory-startup', '--threads', '4', '--python-exit-code', '1',
                    '--python', str(HERE / 'build.py'), '--', '--state', args.state, '--fit-contacts', str(path)], check=True)


if __name__ == '__main__':
    main()
