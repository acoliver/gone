from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
root=Path(__file__).resolve().parent
sheet=Image.open(root.parent/'room2/design-sheet-v3.png').convert('RGB')
w,h=sheet.size
sheet=sheet.crop((0,0,w//2,h))
refs=[('Design sheet',sheet),('Front',Image.open(root/'renders/panel-front.png').convert('RGB')),('3/4',Image.open(root/'renders/panel-threequarter.png').convert('RGB')),('Side',Image.open(root/'renders/panel-side.png').convert('RGB')),('Board',Image.open(root/'renders/panel-board-v2-perceived.png').convert('RGB'))]
W,H=1800,1200; canvas=Image.new('RGB',(W,H),(226,226,222)); draw=ImageDraw.Draw(canvas)
margin=28; gap=20; left_w=600; right_w=W-left_w-3*margin

def fit(im,bw,bh):
 im=ImageOps.contain(im,(bw,bh),Image.Resampling.LANCZOS)
 frame=Image.new('RGB',(bw,bh),(42,44,43)); frame.paste(im,((bw-im.width)//2,(bh-im.height)//2)); return frame
canvas.paste(fit(refs[0][1],left_w,H-2*margin),(margin,margin)); draw.text((margin+12,margin+10),'APPROVED DESIGN SHEET',fill='white')
cell_w=(right_w-gap)//2; cell_h=(H-2*margin-gap)//2
for index,(title,image) in enumerate(refs[1:]):
 col=index%2; row=index//2; x=2*margin+left_w+col*(cell_w+gap); y=margin+row*(cell_h+gap)
 canvas.paste(fit(image,cell_w,cell_h),(x,y)); draw.text((x+12,y+10),title,fill='white')
canvas.save(root/'contact.png',quality=95)
