"""Run four cached FLUX.2-klein edits per locker face, sequentially."""
import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter

from locker_faces import ROOT, SOURCE, SCRATCH, FACES, image_size, manifest, scores


def prepare():
    SOURCE.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SOURCE/'face-layout.json').write_text(json.dumps(manifest(),indent=2)+'\n')
    for name, face in FACES.items():
        source = face.get('concept', 'docs/art/quarters/concept-now.png')
        crop = Image.open(ROOT/source).convert('RGB').crop(face['crop'])
        crop.save(SOURCE/f'{name}-source.png')
        input_image=crop.resize(image_size(face),Image.Resampling.LANCZOS)
        if name=='door':
            overlay=Image.new('RGB',input_image.size,'black');draw=ImageDraw.Draw(overlay)
            w,h=input_image.size
            for y in (.075,.110,.145): draw.line((w*.20,h*y,w*.80,h*y),fill=(150,145,135),width=2)
            draw.ellipse((w*.85,h*.54,w*.91,h*.58),outline=(150,145,135),width=2)
            input_image=Image.blend(input_image,overlay.filter(ImageFilter.GaussianBlur(1)),.055)
        input_image.save(SOURCE/f'{name}-input.png')
        prompt = ('Edit the reference into a flat, evenly lit, shadowless, edge-to-edge aged painted steel material image. '
                  'Preserve the reference grey-green paint, reddish-brown rust, irregular paint-loss layout and ragged organic borders. '
                  'Remove hardware, seams, objects and cast shadows only; fill each removed hardware area with its neighbouring material. '
                  'Keep all existing paint-loss edges and corrosion variation. Do not draw a panel, frame, border or perspective. '
                  'Broken edge and corner regions have the most rust. The broad field retains quiet painted areas among differing sizes of irregular corrosion patches. '
                  'Rust has natural variations of dark oxide and orange pigment. A few narrow rusty runs travel downward with irregular gently wandering paths and tapered ends. '
                  'No long straight rust stripe, geometric cutout, stamped motif or repeated shape. ')
        if name == 'door':
            prompt += ('This image represents the full upright locker door. Include delicate downward rusty runs below the vent positions at 15, 13 and 10 percent from the top, across the middle 60 percent of the width, and below the handle position at 88 percent from the left and 65 percent from the top. Do not draw vents or a handle. ')
        if name == 'top':
            prompt += ('This is a horizontal upward-facing top. Preserve old paint and rust under a fine soft settled warm grey dust veil. Dust is even, powdery, low contrast, with no cloud patches, swirls, drifts or mottled blobs. No vertical runoff. ')
        if name == 'hardware':
            prompt = ('Remove all hardware, objects, seams, borders, perspective and shadows. Preserve the extensive dark reddish-brown rust and orange corrosion of this heavily rusted reference crop. Fill the entire image edge to edge with only this continuous flat heavily corroded steel surface, lit flat and evenly, without shadows or borders. Fine irregular pits and dark cavities intermix with orange oxide and small grey metal flecks. No shapes or repeated motifs. ')
        (SOURCE/f'{name}-prompt.txt').write_text(prompt.rstrip()+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--face',choices=list(FACES))
    parser.add_argument('--seed-offset',type=int,default=0)
    parser.add_argument('--extra-prompt',default='')
    args=parser.parse_args()
    prepare()
    for index,(name,face) in enumerate(FACES.items()):
        if args.face and name!=args.face: continue
        prompt_file=SOURCE/f'{name}-prompt.txt'
        if args.extra_prompt:
            prompt_file=SOURCE/f'{name}-extra-{args.seed_offset}-prompt.txt'
            prompt_file.write_text((SOURCE/f'{name}-prompt.txt').read_text()+args.extra_prompt+'\n')
        for seed in range(95500+index*10+args.seed_offset,95504+index*10+args.seed_offset):
            output = SOURCE/f'{name}-{seed}.png'
            if output.exists():
                if not output.with_suffix('.metadata.json').exists():
                    raise ValueError(f'incomplete generation: {output}')
                continue
            width,height = image_size(face)
            command = ['/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit',
                       '--model','flux2-klein-4b','--quantize','4','--steps','4',
                       '--image-paths',str(SOURCE/f'{name}-input.png'),
                       '--prompt-file',str(prompt_file),
                       '--seed',str(seed),'--width',str(width),'--height',str(height),'--output',str(output)]
            print('GENERATE',name,seed,flush=True)
            with (SCRATCH/f'{name}-{seed}.log').open('w') as log:
                subprocess.run(command,cwd=ROOT,check=True,stdout=log,stderr=subprocess.STDOUT,
                               env=dict(os.environ,HF_HOME='/Volumes/XS1000/hf-cache',HF_HUB_OFFLINE='1',
                                        PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(SCRATCH)))
            image=Image.open(output)
            if image.size != (width,height):
                raise ValueError(f'wrong generated dimensions: {image.size}')
            row=dict(face=name,seed=seed,model='black-forest-labs/FLUX.2-klein-4B',quantize=4,steps=4,
                     concept=face.get('concept','docs/art/quarters/concept-now.png'),crop=face['crop'],
                     input=f'{name}-input.png',source=f'{name}-source.png',size=[width,height],
                     prompt=prompt_file.read_text(),command=command,
                     scores=scores(image,Image.open(SOURCE/f'{name}-source.png'),face))
            output.with_suffix('.metadata.json').write_text(json.dumps(row,indent=2)+'\n')
            print('SCORES',name,seed,row['scores'],flush=True)
    print('GENERATION COMPLETE',flush=True)


if __name__ == '__main__':
    main()
