from pathlib import Path
import json,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
O=Path(__file__).resolve().parent
before=np.load(O/'source-vertices.npy');after=np.load(O/'deformed-vertices.npy');faces=np.load(O/'source-faces.npy');r=json.loads((O/'geometry-report.json').read_text())
# Equal-scale orthographic projection of the actual whole-body mesh, clipped
# to the lower body. It retains side detail rather than idealizing a section.
W,H=1000,1000;scale=1050;padx=100;floor=825
font=lambda n:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',n)
sheet=Image.new('RGB',(2000,1080),'#171c1e');d=ImageDraw.Draw(sheet)
for i,(name,verts,color) in enumerate([('Original assembly',before,'#d4d9c5'),('Assembly3: +35 mm along slope',after,'#bdd69e')]):
 mask=Image.new('L',(W,H));md=ImageDraw.Draw(mask)
 coords=np.c_[padx+(verts[:,1]+.79)*scale,floor-verts[:,2]*scale]
 for face in faces:md.polygon([tuple(q) for q in coords[face]],fill=255)
 # The lower-body view ends below the head, at z=0.625 m.
 md.rectangle((0,0,W,floor-.625*scale),fill=0)
 inner=mask.filter(ImageFilter.MinFilter(3));edge=np.asarray(mask,dtype=np.int16)-np.asarray(inner,dtype=np.int16)
 fill=Image.new('RGB',(W,H),'#343c37');panel=Image.new('RGB',(W,H),'#171c1e');panel.paste(fill,(0,0),mask)
 panel.paste(Image.new('RGB',(W,H),color),(0,0),Image.fromarray(np.uint8(edge>0)*255))
 pd=ImageDraw.Draw(panel);pd.text((35,25),name,font=font(28),fill='#eef0df')
 pd.line((60,floor,940,floor),fill='#6d777b',width=2)
 pd.text((60,865),'Operator / front',font=font(22),fill='#d2d8cd');pd.text((800,865),'Wall',font=font(22),fill='#d2d8cd')
 pd.text((60,100),'Lower-body outline, same orthographic scale',font=font(21),fill='#d2d8cd')
 depth=147.05164686194586 if i==0 else r['deck']['along_slope_depth_m']*1000
 pd.text((60,135),f'Usable along-slope deck: {depth:.3f} mm',font=font(21),fill='#d2d8cd')
 if i==1:
  pd.text((60,925),'Rigid lip; 200 mm linear-z front-face falloff',font=font(22),fill='#d2d8cd')
  pd.text((60,960),'No new lower-front profile reversals at five sections',font=font(21),fill='#d2d8cd')
 sheet.paste(panel,(i*W,0))
d.text((30,1030),'Outline projected from mesh triangles. Floor and wall reference planes are unchanged.',font=font(23),fill='#d2d8cd')
sheet.save(O/'side-profile-comparison.png')
print('SIDE_PROFILE_COMPARISON_DONE',flush=True)
