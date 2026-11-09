"""Sequential offline FLUX.2-klein edits from the sofa's saved concept crops."""
import json
import os
from pathlib import Path
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'art-source/quarters/sofa'
SCRATCH = ROOT / 'tmp/mat/sofa'
REFERENCES = {
    'upholstery-clean': ('hero.png', [490, 590, 610, 625], 'Fine woven upholstery cloth, recoloured warm pale oatmeal beige as directed for the remembered sofa. Preserve the reference fine yarn texture. Clean new fabric.'),
    'upholstery-aged': ('aged-target.png', [275, 380, 410, 475], 'Faded dusty oatmeal upholstery fabric, warm grey taupe with uneven dry brown grime and broad subtle mottling. Brittle fine woven yarns, dry mineral dust.'),
    'throw-clean': ('hero.png', [785, 545, 895, 690], 'New warm beige oatmeal wool blanket fabric, soft irregular interwoven yarns.'),
    'throw-aged': ('aged-target.png', [805, 555, 895, 690], 'Old faded dusty taupe wool blanket fabric with dry brown grime, muted mauve-brown and warm grey yarns.'),
    'foam': ('aged-target.png', [160, 790, 365, 860], 'Continuous crumbly tan-brown oxidised polyurethane foam crust. Fine friable ochre-brown granules and tiny broken pores; dry material only, filling all gaps with the same material.'),
    'weave': ('hero.png', [490, 590, 610, 625], 'Seamlessly tileable macro scan of fine plain-woven oatmeal upholstery yarns, alternating warp and weft, homogeneous fine weave at equal scale across the whole image.'),
}


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    records = {}
    for index, (name, (file, box, description)) in enumerate(REFERENCES.items()):
        crop = SOURCE / (name + '-crop.png')
        Image.open(ROOT / 'docs/art/quarters/sheets/sofa' / file).convert('RGB').crop(box).save(crop)
        prompt = (description + ' Orthographic flat material scan, shadowless even diffuse illumination, edge-to-edge continuous surface. Remove the object shape, folds, cast shadows, floor, hardware, borders and perspective. No green; only warm neutral, tan and brown colours. No biological growth, lettering or objects. Seamless repeating texture.')
        prompt_file = SOURCE / (name + '-prompt.txt')
        prompt_file.write_text(prompt + '\n')
        output = SOURCE / (name + '.png')
        command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                   '--model', 'flux2-klein-4b', '--quantize', '4', '--steps', '4',
                   '--image-paths', str(crop), '--prompt-file', str(prompt_file),
                   '--seed', str(95600 + index), '--width', '768', '--height', '768', '--output', str(output)]
        metadata = dict(model='black-forest-labs/FLUX.2-klein-4B', seed=95600 + index,
                        quantize=4, steps=4, source='docs/art/quarters/sheets/sofa/' + file,
                        crop_xyxy=box, prompt=prompt, command=command)
        if not output.exists():
            print('GENERATE', name, flush=True)
            with (SCRATCH / (name + '-flux.log')).open('w') as log:
                subprocess.run(command, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, HF_HOME='/Volumes/XS1000/hf-cache', HF_HUB_OFFLINE='1', TMPDIR=str(SCRATCH)))
        (SOURCE / (name + '.json')).write_text(json.dumps(metadata, indent=2) + '\n')
        records[name] = metadata
    print('GENERATED', len(records), flush=True)


if __name__ == '__main__':
    main()
