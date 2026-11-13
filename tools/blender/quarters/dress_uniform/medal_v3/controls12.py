"""Compose unrotated control crops and numerical image descriptors only."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
OUT=Path(__file__).resolve().parents[5]/'tmp/issue130-v3/fit1'
suffix=('aligned-' if '--aligned' in sys.argv else '')+('after' if '--after' in sys.argv else 'before')
manifest=json.loads((OUT/('rotation-manifest-'+suffix+'.json')).read_text())
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
crop=(325,565,575,750)
full=Image.new('RGB',(2250,980),(230,230,230));close=Image.new('RGB',(1500,540),(230,230,230))
rows=[]
for entry in manifest['images']:
 row=0 if entry['label']=='high' else 1;k=entry['k']
 with Image.open(OUT/entry['file']) as im:
  im=im.convert('RGB');box=im.crop(crop)
  # Keep the established notch filenames, now using the fixed-camera crops.
  ImageOps.pad(box,(420,420),color=(230,230,230)).save(OUT/('notch-'+suffix+'-'+entry['label']+'-'+format(entry['notch_degrees'],'.2f')+'.png'))
  full.paste(im.resize((450,450)),(k*450,row*490+40));close.paste(box.resize((300,222)),(k*300,row*270+40))
  rgb=np.array(box,dtype=float)/255;lum=rgb@np.array([.2126,.7152,.0722]);gradient=np.hypot(*np.gradient(lum))
  rows.append({**entry,'crop_mean_luminance':float(lum.mean()),'crop_p05_luminance':float(np.percentile(lum,5)),'crop_fraction_below_0_3':float((lum<.3).mean()),'crop_gradient_p95':float(np.percentile(gradient,95))})
 title=entry['label']+' | '+format(entry['notch_degrees'],'.2f')+' deg'
 ImageDraw.Draw(full).text((k*450+8,row*490+10),title,font=font,fill='black');ImageDraw.Draw(close).text((k*300+8,row*270+10),title,font=font,fill='black')
full.save(OUT/('five-rotation-star-close-'+suffix+'.png'));close.save(OUT/('five-rotation-bottom-crops-'+suffix+'.png'))
(OUT/('rotation-numeric-'+suffix+'.json')).write_text(json.dumps({'crop_pixels':crop,'method':'Fixed identical pixel crop, no image rotation. Numeric descriptors are not a visual verdict.','rows':rows,'visual_judgment':'Not performed.'},indent=2))
print(json.dumps(rows,indent=2))
