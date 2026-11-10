"""Refine shared face images once, before remapping any furniture atlas."""
import argparse
import json
import os
import subprocess

from steel_library import ROOT, LIBRARY, SCRATCH, wait_for_gpu

INSTRUCTIONS = {
    'top': ('Refine this flat horizontal painted-steel texture with clearly visible fine soft settled dust. '
            'A thin diffuse warm-grey powder veil covers the quiet central paint, with delicate fine particulate '
            'detail and soft irregular settling. It must read as dry matte dust, not fresh pale paint. '
            'Keep the existing sparse edge corrosion and most underlying grey-green paint. '
            'No blotchy patches, repeated marks, swirls, tracks, flakes, sand, grit piles or vertical rust runs.'),
    'broad': ('Refine this flat vertical grey-green painted-steel texture. Retain most broad central paint. '
              'Keep corrosion around the outside edges, corners and isolated old fixture scars near those edges. '
              'Give a few narrow tapered downward rust trails unequal widths and lengths, with subtle softly '
              'feathered oxide rims. Their placement must be irregular, never parallel repeated stripes. '
              'Keep the colour palette. No broad pale flaking, white patches, regular dots or new hardware.'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=tuple(INSTRUCTIONS), action='append')
    parser.add_argument('--label', default='finish2')
    parser.add_argument('--seed-offset', type=int, default=600000)
    args = parser.parse_args()
    path = LIBRARY / 'manifest.json'
    manifest = json.loads(path.read_text())
    for row in manifest['faces']:
        if row['kind'] not in (args.kind or INSTRUCTIONS) or row.get('refinement') == args.label:
            continue
        name = row['id']
        source = LIBRARY / f'{name}-{args.label}-input.png'
        if not source.exists(): source.write_bytes((LIBRARY / row['image']).read_bytes())
        output = LIBRARY / f'{name}-{args.label}-raw.png'
        prompt_path = LIBRARY / f'{name}-{args.label}-prompt.txt'
        prompt = (INSTRUCTIONS[row['kind']]+' Shadowless edge-to-edge texture only, orthographic flat material, '
                  'no object silhouette, frame, lighting gradient, cast shadows or biological growth. '
                  '1000 years of dry sterile oxygenated ship aging.\n')
        prompt_path.write_text(prompt)
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                   '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                   '--image-paths', str(source), '--prompt-file', str(prompt_path),
                   '--seed', str(row['seed']+args.seed_offset), '--width', str(row['pixels'][0]),
                   '--height', str(row['pixels'][1]), '--output', str(output)]
        if not output.exists():
            wait_for_gpu()
            print('REFINE', name, flush=True)
            with (SCRATCH / f'{name}-{args.label}.log').open('w') as log:
                subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', TMPDIR=str(SCRATCH)))
        output.with_suffix('.metadata.json').write_text(json.dumps(dict(
            command=command, prompt=prompt, input=source.name, parent_raw=row['raw'],
            model='FLUX.2-klein-4B', seed=row['seed']+args.seed_offset, quantize=4, steps=4,
            pixels=row['pixels']), indent=2)+'\n')
        row['parent_raw'], row['raw'] = row['raw'], output.name
        row['refinement'] = args.label
        row.pop('treatment', None)
        row['passed'] = False
        if row['kind'] == 'top': row['neutral_paint_target'] = [.56, .58, .54]
        path.write_text(json.dumps(manifest, indent=2)+'\n')
        print('REFINED', name, flush=True)


if __name__ == '__main__':
    main()
