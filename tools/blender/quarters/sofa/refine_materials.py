"""Flatten the rejected throw, foam and weave edits without changing their source."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'art-source/quarters/sofa'
EDITS = {
    'throw-aged': ('upholstery-aged.png', 'Two flat material references. Preserve the muted taupe-brown dusty wool colour of the first reference, using the second reference as the example of even flat material coverage. Remove the dark left border, curved crease and every long line. Continuous homogeneous fine wool yarn texture with soft irregular brown fading, very low contrast. Flat diffuse albedo scan.'),
    'foam': ('upholstery-aged.png', 'Flatten the first reference into a diffuse albedo scan of dry fine-grained tan-brown oxidised polyurethane crust, with the second reference showing the required flat illumination. Make the granules very fine and shallow. Remove raised clumps, dark holes, cast shadows, highlights, large lumps and directional shading. Warm dull tan-brown material filling the entire square.'),
    'weave': ('upholstery-clean.png', 'Convert the second reference into a perfectly homogeneous fine plain-woven oatmeal upholstery material scan. The first reference shows yarn intersections only; remove its horizontal band, block pattern and stripes. Equal thread scale and equal brightness everywhere, fine warp and weft, continuous edge-to-edge material, seamlessly tileable.'),
}


def main():
    selected = {name: name + '.png' for name in ['upholstery-clean', 'upholstery-aged', 'throw-clean', 'throw-aged', 'foam', 'weave']}
    for index, (name, (flat, description)) in enumerate(EDITS.items()):
        prompt = description + ' Shadowless orthographic material only, no geometry, seams, borders, floor, objects or green. No biological growth.'
        prompt_path = SOURCE / (name + '-flat-prompt.txt')
        prompt_path.write_text(prompt + '\n')
        output = SOURCE / (name + '-flat.png')
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit', '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4', '--image-paths', str(SOURCE / (name + '.png')), str(SOURCE / flat), '--prompt-file', str(prompt_path), '--seed', str(95620 + index), '--width', '768', '--height', '768', '--output', str(output)]
        if not output.exists():
            with (ROOT / 'tmp/mat/sofa' / (name + '-refine.log')).open('w') as log:
                subprocess.run(command, check=True, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1'))
        (SOURCE / (name + '-flat.json')).write_text(json.dumps(dict(command=command, prompt=prompt, inputs=[name + '.png', flat], seed=95620 + index, model='black-forest-labs/FLUX.2-klein-4B', steps=4, quantize=4), indent=2) + '\n')
        selected[name] = output.name
        print('REFINED', name, flush=True)
    (SOURCE / 'selected.json').write_text(json.dumps(selected, indent=2) + '\n')


if __name__ == '__main__':
    main()
