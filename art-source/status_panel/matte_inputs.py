from pathlib import Path
from rembg import remove, new_session
from PIL import Image
import numpy as np, json
root=Path(__file__).resolve().parent
session=new_session()
rows=[]
for p in sorted((root/'inputs').glob('front-s[0-9]*.png')):
 if '-rgba' in p.stem: continue
 rgba=remove(Image.open(p).convert('RGBA'),session=session)
 out=p.with_name(p.stem+'-rgba.png'); rgba.save(out)
 alpha=np.asarray(rgba.getchannel('A'))>127
 ys,xs=np.where(alpha)
 y0,y1=ys.min(),ys.max()+1; x0,x1=xs.min(),xs.max()+1
 widths=[]
 for y in range(y0,y1):
  xx=np.where(alpha[y])[0]; widths.append(int(xx.max()-xx.min()+1) if len(xx) else 0)
 h=len(widths)
 # Screen-opening estimate from central connected black region; product input crops only the full silhouette here.
 rows.append({'input':p.name,'matte':out.name,'bbox_xyxy':[int(x0),int(y0),int(x1),int(y1)],'outer_ratio':round((x1-x0)/(y1-y0),4),'foreground_fraction':round(float(alpha.mean()),5)})
(root/'input-measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
