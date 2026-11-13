"""Assemble labelled matched-view sheets; no visual assessment."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont,ImageOps
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',19)
views=['front','three-quarter','edge','rear','star-close','ring-bar-close'];paths=[]
for kind in ['raw','high','low','low-normalmapped']:
 sheet=Image.new('RGB',(1200,860),(230,230,230));draw=ImageDraw.Draw(sheet)
 for i,view in enumerate(views):
  with Image.open(OUT/(kind+'-'+view+'.jpg')) as im:sheet.paste(im.convert('RGB').resize((400,400)),((i%3)*400,(i//3)*430+30))
  draw.text(((i%3)*400+8,(i//3)*430+6),kind+' | '+view,fill='black',font=font)
 path=OUT/(kind+'-six-views.jpg');sheet.save(path,quality=94);paths.append(str(path))
for names,filename in [(['input','raw','high','low'],'input-raw-high-low-three-quarter.jpg'),(['input','raw','high','low-normalmapped'],'input-raw-high-normalmapped-three-quarter.jpg')]:
 sheet=Image.new('RGB',(1400,390),(230,230,230));draw=ImageDraw.Draw(sheet)
 for i,kind in enumerate(names):
  p=SOURCE/'frozen-c01-seed1306201.png' if kind=='input' else OUT/(kind+'-three-quarter.jpg')
  with Image.open(p) as im:sheet.paste(ImageOps.contain(im.convert('RGB'),(350,350)),(i*350,40))
  draw.text((i*350+8,8),kind,fill='black',font=font)
 path=OUT/filename;sheet.save(path,quality=94);paths.append(str(path))
manifest=json.loads((OUT/'render-manifest.json').read_text());manifest['sheets']=paths;manifest['rotation_controls']=json.loads((OUT/'rotation-manifest-after.json').read_text());manifest['rotation_sheets']=[str(OUT/name) for name in ['five-rotation-bottom-crops-after.png','five-rotation-star-close-after.png']];manifest['visual_assessment']='Not performed.'
(OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2));print('SHEETS_COMPLETE',paths,flush=True)
