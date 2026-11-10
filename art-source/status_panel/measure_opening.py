from pathlib import Path
import cv2, numpy as np, json
root=Path(__file__).resolve().parent
rows=[]
for path in sorted((root/'inputs').glob('front-s[0-9]*.png')):
 if '-rgba' in path.stem: continue
 rgb=cv2.imread(str(path))[:,:,::-1]
 h,w=rgb.shape[:2]
 # Screen is dark, large, centrally located, and inside foreground matte.
 grey=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
 roi=grey[int(.12*h):int(.88*h),int(.08*w):int(.92*w)]
 mask=(roi<35).astype('uint8')*255
 count, labels, stats, centroids=cv2.connectedComponentsWithStats(mask,8)
 comps=[]
 for i in range(1,count):
  x,y,cw,ch,area=stats[i]
  ratio=cw/max(ch,1)
  if area>1000 and ratio>1.7:
   comps.append({'bbox':[int(x+int(.08*w)),int(y+int(.12*h)),int(x+cw+int(.08*w)),int(y+ch+int(.12*h))],'ratio':round(ratio,4),'area':int(area)})
 rows.append({'image':path.name,'candidates':sorted(comps,key=lambda x:-x['area'])[:5]})
(root/'opening-measurements.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
