import numpy as np, cv2, json, sys
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from PIL import Image,ImageDraw
from pathlib import Path
OUT=Path(__file__).resolve().parent
z=np.load(OUT/'height.npz');h=z['height'];xs=z['xs'];ys=z['ys'];valid=np.isfinite(h)
h=ndi.grey_closing(np.nan_to_num(h,nan=float(np.nanmin(h))),size=(3,3))
# Opening removes cap-scale raised islands while following the curved housing.
for rad in [7,11,16,21,26,32,40]:
 base=cv2.morphologyEx(h,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(rad*2+1,rad*2+1)))
 res=np.maximum(h-base,0);u=np.uint8(np.clip(res/np.percentile(res[valid],99.9)*255,0,255))
 t,mask=cv2.threshold(u,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
 mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8));mask[~valid]=0
 n,l,st,c=cv2.connectedComponentsWithStats(mask)
 areas=st[1:,4];a=areas[areas>50];med=np.median(a)
 keep=[i for i in range(1,n) if .3*med<=st[i,4]<=6*med and st[i,4]>100]
 print('radius',rad,'otsu mm',t/255*np.percentile(res[valid],99.9)*1000,'median',med,'count',len(keep),'areas',sorted(st[keep,4].tolist()),flush=True)
 np.savez(OUT/f'candidate{rad}.npz',height=h,base=base,residual=res,labels=l,keep=keep,threshold=t/255*np.percentile(res[valid],99.9),xs=xs,ys=ys)
 # Each view uses the same XY convention as a top camera: +Y toward image top.
 def rgb(a):return cv2.cvtColor(a,cv2.COLOR_GRAY2RGB)
 height=rgb(np.uint8(np.clip((h-np.nanmin(h))/(np.nanmax(h)-np.nanmin(h))*255,0,255)))
 residual=rgb(u);rng=np.random.default_rng(91);colors=rng.integers(55,245,(n,3),dtype=np.uint8);colors[0]=[18,20,23];lab=colors[l];lab[~np.isin(l,keep)]=[18,20,23]
 panels=[]
 for arr,title in [(height,'Height'),(residual,f'Residual radius {rad} mm'),(lab,f'{len(keep)} components')]:
  im=Image.fromarray(arr[::-1].copy());d=ImageDraw.Draw(im)
  if title.endswith('components'):
   for j,k in enumerate(keep):d.text((c[k,0],len(ys)-1-c[k,1]),str(j+1),fill='white',stroke_width=1,stroke_fill='black')
  panel=Image.new('RGB',(len(xs),len(ys)+30),(32,34,37));panel.paste(im,(0,30));ImageDraw.Draw(panel).text((10,8),title,fill='white');panels.append(panel)
 sheet=Image.new('RGB',(len(xs),3*(len(ys)+30)))
 for j,im in enumerate(panels):sheet.paste(im,(0,j*(len(ys)+30)))
 sheet.save(OUT/f'segmentation-r{rad}.png')
