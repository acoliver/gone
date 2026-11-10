"""Edit coarse visible face candidates into quiet paint, thin oxide and soft dust."""
import argparse
import json
import os
import subprocess

from PIL import Image

from materials import ROOT, SOURCE, SCRATCH, FACES

NAMES = ['left', 'right-inner', 'door-inner', 'back', 'top', 'bottom', 'frame', 'header',
         'door-outer', 'left-inner', 'right', 'ceiling']


def main(names):
    selection = json.loads((SOURCE / 'selection.json').read_text())
    for index, name in enumerate(NAMES):
        if names and name not in names:
            continue
        face = FACES[name]
        seeds = range(98300 + index*10, 98302 + index*10)
        outputs = [SOURCE / f'{name}-{seed}.png' for seed in seeds]
        if all(output.exists() for output in outputs):
            for output in outputs:
                json.loads(output.with_suffix('.metadata.json').read_text())
            continue
        original = selection[name]['chosen']
        input_path = SOURCE / f'{name}-refine-input.png'
        Image.open(SOURCE / original).convert('RGB').save(input_path)
        prompt = (
            'Edit this flat painted steel material image. Keep its exact muted grey paint and brown iron oxide palette. '
            'This is a material colour image, not a shaded object: flat even diffuse illumination, no relief lighting or shadows. '
            'Replace the coarse speckles and pebbled appearance within intact paint with quiet smooth old rolled-steel paint. '
            'Retain subtle slow pigment variation over large areas, not tiny noisy dots, gritty stone, rough plaster or gravel. '
            'Most of the broad field remains uninterrupted grey paint. Remove the broad orange smears and wide continuous perimeter bands. '
            'Keep small irregular chips and ragged broken corrosion at isolated edges, corners and fixture outlets. '
            'Edge chips are a few millimetres to two centimetres, not wide strips. Never draw a complete rectangular rust frame. '
            'A few thin dark reddish brown rusty trails, only two to five millimetres wide, descend vertically from fixtures. '
            'They have tapered ends and do not branch or spread into orange clouds. No broad rust washes. '
            'Sealed sterile dry oxygenated ship after 1000 years. No biological growth, moss, mould or saturated green. '
            'Do not draw an object, hardware, seam, border or perspective. ')
        if name in ('top', 'bottom'):
            prompt += (
                'This face is horizontal and upward-facing. Remove all downward runs. A fine soft warm grey settled dust veil '
                'rests over the quiet painted broad field. Dust is smooth, even and low contrast, not gritty or speckled. '
                'Keep only small broken oxide patches close to the edges. No cloudy stains, swirls, blobs or drifts. ')
        if name == 'ceiling':
            prompt += ('This face is the downward-facing interior ceiling. Remove all vertical runs '
                       'and all settled dust. Preserve quiet old paint with sparse broken edge oxide. ')
        prompt += f"The complete image covers {face['size'][0]} by {face['size'][1]} metres of steel. "
        prompt_path = SOURCE / f'{name}-refine-prompt.txt'
        prompt_path.write_text(prompt.rstrip() + '\n')
        reason = 'Matched neutral review found coarse colour variation and broad rust marks; relief-off controls changed broad-face high-frequency contrast by less than 0.5 percent.'
        for path in SOURCE.glob(name + '-[0-9]*.metadata.json'):
            metadata = json.loads(path.read_text())
            if metadata['seed'] < 98300:
                metadata['visual_rejection'] = reason
                path.write_text(json.dumps(metadata, indent=2) + '\n')
        for seed in range(98300 + index*10, 98302 + index*10):
            output = SOURCE / f'{name}-{seed}.png'
            if output.exists():
                if not output.with_suffix('.metadata.json').exists():
                    raise ValueError(f'incomplete generation: {output}')
                continue
            command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                       '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                       '--image-paths', str(input_path), '--prompt-file', str(prompt_path),
                       '--seed', str(seed), '--width', str(face['pixels'][0]),
                       '--height', str(face['pixels'][1]), '--output', str(output)]
            print('REFINE', name, seed, flush=True)
            with (SCRATCH / f'{name}-{seed}.log').open('w') as log:
                subprocess.run(command, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1',
                                        PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(SCRATCH)))
            if Image.open(output).size != tuple(face['pixels']):
                raise ValueError(f'wrong generated size: {output}')
            metadata = dict(face=name, seed=seed, model='black-forest-labs/FLUX.2-klein-4B', steps=4,
                            quantize=4, command=command, prompt=prompt, input=input_path.name,
                            input_generated_from=original, crop=face['crop'], reference=f'{name}-source.png')
            output.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
            print('REFINED', name, seed, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--face', action='append', choices=NAMES)
    main(parser.parse_args().face)
