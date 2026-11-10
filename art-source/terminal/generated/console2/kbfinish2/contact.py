from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json
OUT=Path(__file__).resolve().parent
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
font=ImageFont.truetype(fontpath,24);small=ImageFont.truetype(fontpath,20);title=ImageFont.truetype(fontpath,34)
r=json.loads((OUT/'report.json').read_text())
sheet=Image.new('RGB',(2400,1120),(27,29,31));d=ImageDraw.Draw(sheet)
d.text((24,13),'Generated keyboard | olive steel, rubber and Nalesha legends',font=title,fill=(225,223,212))
items=[(OUT.parent/'outputs/keyboard-s520.png','Generated reference photo'),(OUT.parents[1]/'kbmodel/render-top.png','Our 29-key design'),(OUT/'top.png','Finished generated mesh | top'),(OUT/'operator.png','Operator view | 35 degrees above front'),(OUT/'side.png','Side view'),(OUT/'segmentation.png','Height residual and numbered watershed regions')]
for i,(path,label) in enumerate(items):
 col=i%3;row=i//3;x=col*800;y=65+row*485
 image=Image.open(path).convert('RGB');image=ImageOps.contain(image,(792,440),Image.Resampling.LANCZOS);sheet.paste(image,(x+(800-image.width)//2,y+38+(440-image.height)//2));d.text((x+16,y+5),label,font=font,fill=(217,218,209))
d.text((24,1044),f"29 regions | 29 stroke legends | 2048 albedo / ORM / normal | Cycles 64 + denoise | 1600 x 900 per view",font=small,fill=(215,216,207))
d.text((24,1078),f"Hungarian error: mean {r['mean_match_error_key_size']:.3f}, max {r['max_match_error_key_size']:.3f} key sizes. The u assignment is the spatial outlier; key geometry was retained.",font=small,fill=(207,192,155))
sheet.save(OUT/'contact.png')
print('contact.png',sheet.size)
