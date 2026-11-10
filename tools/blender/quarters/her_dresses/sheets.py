"""Publish matched game-camera sheets and measure the lit effect-off controls."""
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
SCRATCH=ROOT/'tmp/clothes2'
OUT=ROOT/'docs/art/quarters/sheets/her_dresses'


def sheet(rows,path):
    result=Image.new('RGB',(1920,540*len(rows)),(32,32,32))
    for row,pair in enumerate(rows):
        for col,path_in in enumerate(pair):
            image=Image.open(path_in).convert('RGB')
            image.thumbnail((960,540),Image.Resampling.LANCZOS)
            result.paste(image,(col*960+(960-image.width)//2,row*540+(540-image.height)//2))
    result.save(path)


def measure(a,b):
    left=np.asarray(Image.open(a).convert('RGB'),dtype=float)/255
    right=np.asarray(Image.open(b).convert('RGB'),dtype=float)/255
    linear=lambda x:np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
    delta=np.abs(linear(left)-linear(right))
    changed=np.max(delta,axis=2)>.01
    srgb=np.abs(left-right).mean(2)*255
    return {'camera':'demo wardrobe perspective, 88 degree horizontal FOV',
            'effect_pixels_over_0_01_linear_rgb':int(changed.sum()),
            'effect_percent_over_0_01_linear_rgb':float(changed.mean()*100),
            'mean_srgb_difference_effect_pixels':float(srgb[changed].mean()) if changed.any() else 0,
            'pixels_over_eight_srgb_levels':int(np.count_nonzero(srgb>=8)),
            'qualification':'Visibility measurement; visual acceptance is judged in the paired image review'}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=OUT/'before';before.mkdir(exist_ok=True)
    for path in (SCRATCH/'before').glob('*.png'):shutil.copy2(path,before/path.name)
    for path in (SCRATCH/'after').glob('*.png'):shutil.copy2(path,OUT/path.name)
    shutil.copy2(SCRATCH/'after/cameras.json',OUT/'cameras.json')
    for state in ('remembered','aged'):
        shutil.copy2(SCRATCH/f'game-before-{state}.png',before/f'{state}-game-wardrobe.png')
        for view in ('wardrobe','doorway'):
            shutil.copy2(SCRATCH/f'game-after/{state}-{view}.png',OUT/f'{state}-game-{view}.png')
    shutil.copy2(SCRATCH/'no-fold-dust/aged-wardrobe.png',OUT/'aged-no-fold-dust-control.png')
    shutil.copy2(SCRATCH/'no-fold-dust/aged-shoulder.png',OUT/'aged-no-fold-dust-shoulder.png')
    sheet([(before/f'{s}-game-wardrobe.png',OUT/f'{s}-game-wardrobe.png') for s in ('remembered','aged')],OUT/'comparison.png')
    sheet([(before/f'aged-{v}.png',OUT/f'aged-{v}.png') for v in ('detail','shoulder','heap')],OUT/'decay-comparison.png')
    sheet([(before/f'{s}-{v}.png',OUT/f'{s}-{v}.png') for v in ('wardrobe','doorway') for s in ('remembered','aged')],OUT/'camera-comparison.png')
    report={'fibres':measure(OUT/'aged-wardrobe.png',OUT/'aged-no-fibres-control.png'),
            'fold_dust':measure(OUT/'aged-wardrobe.png',OUT/'aged-no-fold-dust-control.png')}
    (OUT/'fibre-visibility.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
