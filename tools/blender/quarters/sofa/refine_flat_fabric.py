"""Generate flat aged wool and fine yarn from accepted clean fabric edits."""
import json
import os
from pathlib import Path
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'art-source/quarters/sofa'


def main():
    selected = json.loads((SOURCE / 'selected.json').read_text())
    crop = SOURCE / 'weave-yarn-reference.png'
    Image.open(SOURCE / 'upholstery-clean.png').crop((256, 256, 512, 512)).save(crop)
    edits = {
        'throw-aged': ('throw-clean.png', 'A continuous perfectly flat wool textile albedo scan, faded muted taupe-brown oatmeal yarns with subtle dry brown grime mottling. Preserve the fine yarn texture and flat even illumination of this reference. Homogeneous edge-to-edge fabric surface, diffuse reflectance only. The material is uniformly flat and uniformly scaled.'),
        'weave': (crop.name, 'A uniformly flat seamless fine plain-woven cotton upholstery textile scan. Eighty thin vertical oatmeal cotton yarns interlace with eighty thin horizontal oatmeal cotton yarns at right angles, with tiny equal-size tight alternating over-under intersections. Uniform yarn scale, uniform oatmeal beige, flat shadowless illumination. Entire square is filled with the same fine continuous weave.'),
    }
    for index, (name, (file, prompt)) in enumerate(edits.items()):
        prompt_file = SOURCE / (name + '-flat2-prompt.txt')
        prompt_file.write_text(prompt + '\n')
        output = SOURCE / (name + '-flat2.png')
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit', '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4', '--image-paths', str(SOURCE / file), '--prompt-file', str(prompt_file), '--seed', str(95630 + index), '--width', '768', '--height', '768', '--output', str(output)]
        if not output.exists():
            with (ROOT / 'tmp/mat/sofa' / (name + '-flat2.log')).open('w') as log:
                subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1'))
        (SOURCE / (name + '-flat2.json')).write_text(json.dumps(dict(command=command, prompt=prompt, input=file, seed=95630 + index, model='black-forest-labs/FLUX.2-klein-4B', quantize=4, steps=4, colour_reference='throw-aged-crop.png' if name == 'throw-aged' else 'upholstery-clean.png'), indent=2) + '\n')
        selected[name] = output.name
        print('FLAT', name, flush=True)
    selected['weave'] = 'upholstery-clean.png'
    (SOURCE / 'selected.json').write_text(json.dumps(selected, indent=2) + '\n')


if __name__ == '__main__':
    main()
