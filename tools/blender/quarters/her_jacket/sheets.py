"""Label the concept and fixed-camera new/aged clothing captures."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[4]
FONT=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',23)


def make(prop):
    out=ROOT/'docs/art/quarters/sheets'/prop
    if prop=='her_dresses':
        detail=Image.new('RGB',(1000,1000))
        for i,name in enumerate(('shoulder','heap')):
            detail.paste(Image.open(out/f'aged-{name}.png').convert('RGB').crop((0,250,1000,750)),(0,i*500))
        detail.save(out/'aged-detail.png')
        for state in ('remembered','aged','aged-control'):
            pair=Image.new('RGB',(1000,1000),(241,241,238))
            for i,tag in enumerate(('rose','blue')):
                filename=f'aged-{tag}-control.png' if state=='aged-control' else f'{state}-{tag}-broadside.png'
                image=Image.open(out/filename).convert('RGB').crop((250,0,750,1000))
                pair.paste(image,(i*500,0))
            pair.save(out/('aged-no-fibres-control.png' if state=='aged-control' else f'{state}-hero.png'))
    names=[('hero.png','A: generated design guide'),
           ('remembered-hero.png','B: remembered, exported mesh'),
           ('aged-hero.png','C: aged 1000 years, exported mesh')]
    if prop=='her_jacket':
        names += [('remembered-front.png','Remembered: chair seat side'),('aged-front.png','Aged: chair seat side'),
                  ('aged-no-fibres-control.png','Aged: fibres disabled control')]
    else:
        names += [('remembered-context.png','Remembered: wardrobe and real tunic'),
                  ('aged-context.png','Aged: wardrobe and real tunic'),
                  ('aged-detail.png','Aged: shoulders / floor fibres, isolated')]
    canvas=Image.new('RGB',(1950,1400),(241,241,238));draw=ImageDraw.Draw(canvas)
    for i,(filename,label) in enumerate(names):
        image=Image.open(out/filename).convert('RGB')
        image=ImageOps.contain(image,(650,650),Image.Resampling.LANCZOS)
        x=(i%3)*650;y=(i//3)*700
        canvas.paste(image,(x+(650-image.width)//2,y+42))
        draw.text((x+12,y+10),label,font=FONT,fill=(25,25,25))
    canvas.save(out/'comparison.png')
    on=np.asarray(Image.open(out/'aged-hero.png').convert('RGB'),dtype=float)/255
    off=np.asarray(Image.open(out/'aged-no-fibres-control.png').convert('RGB'),dtype=float)/255
    def linear(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
    difference=np.abs(linear(on)-linear(off))
    report={'comparison':'matched CPU Cycles lit fibre deposits and fringe ON/OFF; includes their shadows',
            'mean_absolute_linear_rgb_difference':float(difference.mean()),
            'pixel_fraction_difference_over_001':float(np.mean(difference.max(2)>.01))}
    (out/'fibre-visibility.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prop',choices=['her_jacket','her_dresses'])
    make(p.parse_args().prop)
