import numpy as np,cv2,json
from pathlib import Path
from scipy import ndimage as nd
from scipy.optimize import linear_sum_assignment
from skimage.segmentation import watershed
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
z=np.load(OUT/'poly3-5.npz');h=z['height'];res=z['residual']
# Otsu establishes the raised field; its bridges persist, so use 10 mm cores
# to seed watershed. Only oversized connected components require two seeds.
threshold=.010
mask=np.uint8((res>threshold)&np.isfinite(h))
mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
mask=nd.binary_fill_holes(mask)
dt=cv2.distanceTransform(mask.astype('uint8'),cv2.DIST_L2,5)
nc,cc,stats,centres=cv2.connectedComponentsWithStats(mask.astype('uint8'))
seeds=np.zeros(h.shape,np.int32);n=0
for comp in range(1,nc):
 if stats[comp,4]<250:continue
 if stats[comp,4]<6000:
  points=[centres[comp][::-1]]
 else:
  candidates=np.argwhere((cc==comp)&(dt==nd.maximum_filter(dt,size=25)))
  candidates=sorted(candidates,key=lambda p:float(dt[tuple(p)]),reverse=True)
  points=[]
  for p in candidates:
   if all(np.linalg.norm(p-q)>40 for q in points):points.append(p)
   if len(points)==2:break
 for p in points:
  n+=1;seeds[tuple(np.round(p).astype(int))]=n
cores=watershed(-dt,seeds,mask=mask)
# Where higher residuals expose a real valley, use those separated cap cores
# instead of dividing a long spacebar by distance alone.
for comp in range(1,nc):
 if stats[comp,4]<6000:continue
 own=np.unique(cores[cc==comp]);own=own[own>0]
 if len(own)!=2:continue
 for level in [.011,.012,.013,.014]:
  high=np.uint8((cc==comp)&(res>level));high=cv2.morphologyEx(high,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
  hn,hl,hs,hc=cv2.connectedComponentsWithStats(high);keep=[i for i in range(1,hn) if hs[i,4]>400]
  if len(keep)!=2:continue
  marker=np.zeros(h.shape,np.int32)
  for old,new in zip(keep,own):marker[hl==old]=new
  grown=watershed(-res,marker,mask=(cc==comp));cores[cc==comp]=grown[cc==comp];break
mask=nd.binary_fill_holes(z['labels']>0)
l=watershed(-res,cores,mask=mask)
regions=[]
for i in range(1,n+1):
 yy,xx=np.where(l==i);regions.append({'label':i,'centre':[float(xx.mean()),float(yy.mean())],'bounds':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],'area':len(xx)})
median=np.median([r['area'] for r in regions]);regions=[r for r in regions if .3*median<=r['area']<=6*median]
keys=json.loads((OUT/'design.json').read_text());rect=np.array([k['rect'] for k in keys]);dc=np.stack(((rect[:,0]+rect[:,2])/2,-(rect[:,1]+rect[:,3])/2),axis=1)
dlo=np.array([rect[:,0].min(),-rect[:,3].max()]);dhi=np.array([rect[:,2].max(),-rect[:,1].min()]);dn=(dc-dlo)/(dhi-dlo)
gc=np.array([r['centre'] for r in regions]);gb=np.array([r['bounds'] for r in regions]);glo=gb[:,:2].min(0);ghi=gb[:,2:].max(0);gn=(gc-glo)/(ghi-glo)
size=np.median(np.sqrt(((gb[:,2]-gb[:,0])/(ghi[0]-glo[0]))*((gb[:,3]-gb[:,1])/(ghi[1]-glo[1]))))
for rotate in [False,True]:
 g=1-gn if rotate else gn;cost=np.linalg.norm(g[:,None,:]-dn[None,:,:],axis=2);a,b=linear_sum_assignment(cost);err=cost[a,b]/size
 print('rotate180',rotate,'count',len(regions),'mean',err.mean(),'max',err.max(),'size',size)
 print([(regions[i]['label'],keys[j]['name'],round(float(cost[i,j]/size),3)) for i,j in zip(a,b)])
 if rotate:
  for i,j in zip(a,b):regions[i]['design']=int(j);regions[i]['error']=float(cost[i,j]/size)
np.savez(OUT/'segmentation.npz',labels=l,height=h,base=z['base'],residual=res,threshold=z['threshold'],xs=z['xs'],ys=z['ys'])
report={'key_count':len(regions),'mean_match_error_key_size':float(err.mean()),'max_match_error_key_size':float(err.max()),'unmatched_design':[keys[j]['name'] for j in range(29) if j not in b],'unmatched_generated':[regions[i]['label'] for i in range(len(regions)) if i not in a],'rotation_z_degrees':180,'regions':regions}
(OUT/'matching.json').write_text(json.dumps(report,indent=2))
rng=np.random.default_rng(91);colors=rng.integers(55,235,(n+1,3),dtype=np.uint8);colors[0]=[18,20,23]
height=np.uint8(np.clip((np.nan_to_num(h,nan=.025)-.025)/.03*255,0,255));resid=np.uint8(np.clip(res/.022*255,0,255));lab=colors[l]
panels=[]
for arr,title in [(height,'Height map, 1 mm grid'),(resid,'Cubic lower-40% frame subtraction, Otsu residual'),(lab,f'Watershed: {len(regions)} retained keys')]:
 im=Image.fromarray(np.fliplr(arr).copy()).convert('RGB');d=ImageDraw.Draw(im)
 if arr is lab:
  for r in regions:
   x,y=r['centre'];d.text((800-x,y),str(r['design']+1),fill='white',stroke_fill='black',stroke_width=1)
 p=Image.new('RGB',(801,339),(30,32,35));p.paste(im,(0,30));ImageDraw.Draw(p).text((12,8),title,fill='white');panels.append(p)
sheet=Image.new('RGB',(801,1017))
for i,p in enumerate(panels):sheet.paste(p,(0,i*339))
sheet.save(OUT/'segmentation.png')
