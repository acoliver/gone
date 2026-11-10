from pathlib import Path
import cv2, json, numpy as np
from PIL import Image, ImageDraw
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent
im=np.array(Image.open(ROOT/'outputs/console-s510.png').convert('RGB')); h,w=im.shape[:2]; f=im.astype(float)
# Olive foreground is chromatic; neutral light-grey backdrop and its shadows are not.
olive=((f[:,:,1]-f[:,:,2])>9)&((f[:,:,0]-f[:,:,2])>5)&((f[:,:,1]-f[:,:,0])>-4)
dark=(f.max(2)<65); upper=np.zeros((h,w),bool); upper[:int(h*.52)]=True
n,lab,stats,centroids=cv2.connectedComponentsWithStats((dark&upper).astype('uint8'),8)
candidates=[i for i in range(1,n) if stats[i,4]>1000 and stats[i,2]>stats[i,3]*.8]
i=max(candidates,key=lambda i:stats[i,4]); screen=lab==i
mask=(olive|screen).astype('uint8'); mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); contour=max(contours,key=cv2.contourArea); mask[:]=0; cv2.drawContours(mask,[contour],-1,1,-1)
px,py,pw,ph=cv2.boundingRect(contour)
mesh=np.array(Image.open(OUT/'mesh-silhouette.png').convert('RGBA'))[:,:,3]>127
ys,xs=np.nonzero(mesh); mx,my,mw,mh=int(xs.min()),int(ys.min()),int(xs.max()-xs.min()+1),int(ys.max()-ys.min()+1)
aligned=np.zeros((h,w),np.uint8); aligned[py:py+ph,px:px+pw]=cv2.resize(mesh[my:my+mh,mx:mx+mw].astype('uint8'),(pw,ph),interpolation=cv2.INTER_NEAREST)
iou=float(np.count_nonzero(aligned&mask)/np.count_nonzero(aligned|mask))
# Robust axis-aligned screen rectangle excludes softened corner pixels and black reflected foot shape.
sy,sx=np.nonzero(screen); xlo,xhi=np.percentile(sx,[1,99]); ylo,yhi=np.percentile(sy,[1,99])
# Recover straight edges using the long black runs in the middle half of each axis.
rows=[]; cols=[]
for y in range(int(ylo+(yhi-ylo)*.2),int(ylo+(yhi-ylo)*.8)):
 xx=np.flatnonzero(screen[y]); rows.append((xx.min(),xx.max()))
for x in range(int(xlo+(xhi-xlo)*.2),int(xlo+(xhi-xlo)*.8)):
 yy=np.flatnonzero(screen[:,x]); cols.append((yy.min(),yy.max()))
xlo,xhi=np.median(rows,axis=0); ylo,yhi=np.median(cols,axis=0)
proj=json.loads((OUT/'projection.json').read_text()); scale=proj['ortho_height']/proj['height']
def world_x(x):return proj['centre_x']+((mx+(x-px)/pw*mw)-proj['width']/2)*scale
def world_z(y):return proj['centre_z']+(proj['height']/2-(my+(y-py)/ph*mh))*scale
rect={'x':[world_x(xlo)+.008,world_x(xhi)-.008],'z':[world_z(yhi)+.008,world_z(ylo)-.008]}
info=json.loads((OUT/'mesh-info.json').read_text()); low,high=info['bounds']; centre=sum(rect['z'])/2
report={'photo_bbox':[px,py,pw,ph],'mesh_bbox':[mx,my,mw,mh],'silhouette_iou':iou,'screen_photo_pixels':[xlo,ylo,xhi,yhi],'inset_m':.008,'rectangle_m':rect,'screen_centre_height_fraction':(centre-low[2])/(high[2]-low[2])}
(OUT/'screen-segmentation.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
Image.fromarray(mask*255).save(OUT/'photo-silhouette.png'); Image.fromarray(aligned*255).save(OUT/'aligned-silhouette.png')
overlay=im.copy(); edge=cv2.morphologyEx(aligned,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))>0; overlay[edge]=[0,200,255]; cv2.rectangle(overlay,(int(xlo),int(ylo)),(int(xhi),int(yhi)),(255,80,30),3); Image.fromarray(overlay).save(OUT/'photo-detection.png')
assert iou>=.9, f'Silhouette alignment failed: {iou}'
assert (centre-low[2])/(high[2]-low[2])>=.65, 'Screen is not in the upper 35 percent'
