"""Fit baked pillow undersides using exact overlaps of exported triangle planes."""
import argparse
import json
from pathlib import Path
import subprocess

from verify import HERE, ROOT, load, support_gap

BLENDER = '/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', choices=('remembered', 'aged'), default='remembered')
    args = parser.parse_args()
    suffix = '_aged' if args.state == 'aged' else ''
    _, meshes = load(ROOT / f'assets/props/quarters/bed_soft{suffix}.glb')
    shifts = {name: .001 - support_gap(meshes[name], meshes['Mattress']) for name in ('Pillow_L', 'Pillow_R')}
    path = ROOT / f'tmp/bed_soft/{args.state}-contact-shifts.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(shifts, indent=2) + '\n')
    print(shifts, flush=True)
    subprocess.run([BLENDER, '--background', '--factory-startup', '--threads', '4', '--python-exit-code', '1',
                    '--python', str(HERE / 'build.py'), '--', '--state', args.state, '--fit-contacts', str(path)], check=True)


if __name__ == '__main__':
    main()
