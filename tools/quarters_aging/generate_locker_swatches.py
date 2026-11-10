"""Generate the locker's saved FLUX edit inputs sequentially, with cached weights."""
import json
import os
from pathlib import Path
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'art-source/quarters/locker'
SCRATCH = ROOT / 'tmp/mat/locker/pass3'
CLASSES = {
    'panel': ('docs/art/quarters/concept-now.png', [445, 338, 535, 411], 95030,
              'Preserve mostly surviving grey-green paint with scattered reddish-brown rust blisters and a few peeling paint islands. About fifteen percent is exposed rust; most of the broad surface remains painted.'),
    'loss': ('docs/art/corridors/hatch-concept-rusted.png', [784, 132, 872, 241], 95130,
             'Preserve the extensive dark reddish-brown rust, flaking orange corrosion and scattered small broken grey-green paint islands from the reference. Most of the surface is exposed rust.'),
    'dust': ('docs/art/quarters/concept-now.png', [464, 266, 561, 306], 95230,
             'Preserve the settled warm grey-brown dust over old grey-green paint and reddish-brown rust. Dust is a soft continuous deposited layer with small sheltered exposed patches, not speckled noise. No directional illumination or cast shadows.'),
}


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for name, (concept, box, first_seed, description) in CLASSES.items():
        crop = SOURCE / f'{name}-crop.png'
        Image.open(ROOT / concept).convert('RGB').crop(box).save(crop)
        prompt = ('Remove every hinge, handle, latch, rivet, bolt, seam, panel edge and shadow from this image. '
                  'Replace all hardware, edges and shadows with a continuous rusted, peeling painted steel surface matching the surrounding surface. '
                  + description + ' Fill the entire image edge to edge with only this continuous flat material surface, lit flat and evenly, without shadows, seams, borders or hardware. No frame, no bevel, no perspective, no objects.')
        prompt_file = SOURCE / f'{name}-prompt.txt'
        prompt_file.write_text(prompt + '\n')
        for seed in range(first_seed, first_seed + 3):
            output = SOURCE / f'{name}-{seed}.png'
            command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                       '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                       '--image-paths', str(crop), '--prompt-file', str(prompt_file),
                       '--seed', str(seed), '--width', '768', '--height', '768', '--output', str(output)]
            metadata = dict(model='black-forest-labs/FLUX.2-klein-4B', quantize=4, steps=4,
                            seed=seed, size=[768, 768], source_concept=concept,
                            concept_crop_xyxy=box, prompt=prompt, command=command,
                            source_crop=crop.name, candidate=output.name)
            if output.exists():
                raise FileExistsError(output)
            print('GENERATE', name, seed, flush=True)
            with (SCRATCH / f'{name}-{seed}.log').open('w') as log:
                subprocess.run(command, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1',
                                        PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(SCRATCH)))
            with Image.open(output) as image:
                assert image.size == (768, 768)
            (SOURCE / f'{name}-{seed}.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print('GENERATED 9/9', flush=True)


if __name__ == '__main__':
    main()
