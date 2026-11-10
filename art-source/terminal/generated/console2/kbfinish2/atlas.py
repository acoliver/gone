import numpy as np,cv2,json,sys
from scipy import ndimage as nd
from PIL import Image,ImageDraw
from pathlib import Path
OUT=Path(__file__).resolve().parent;N=2048
sys.path.insert(0,str(OUT.parents[1]/'terminal'))
import build_deliverables as layout
import build_icons as icons
geo=np.load(OUT/'atlas_geometry.npz');positions=geo['positions'];uvs=geo['uvs'];normals=geo['normals']
pos=np.zeros((N,N,3),np.float32);normal=np.zeros_like(pos);covered=np.zeros((N,N),bool)
for pp,uu,nn in zip(positions,uvs,normals):
 q=uu*np.array([N,-N])+np.array([-.5,N-.5]);xmin,ymin=np.maximum(np.ceil(q.min(0)).astype(int),0);xmax,ymax=np.minimum(np.floor(q.max(0)).astype(int),N-1)
 if xmax<xmin or ymax<ymin:continue
 a,b,c=q;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
 if abs(den)<1e-7:continue
 yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1];w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w2=1-w0-w1;inside=(w0>=-1e-5)&(w1>=-1e-5)&(w2>=-1e-5)
 y=yy[inside];x=xx[inside];w=np.stack((w0[inside],w1[inside],w2[inside]),axis=1);pos[y,x]=w@pp;normal[y,x]=w@nn;covered[y,x]=True
print('rasterized texels',covered.sum(),flush=True)
z=np.load(OUT/'segmentation.npz');labels=z['labels'];height=z['height'];base=z['base'];threshold=float(z['threshold']);xs=z['xs'];ys=z['ys'];report=json.loads((OUT/'matching.json').read_text());keys=json.loads((OUT/'design.json').read_text())
gx=(pos[:,:,0]-xs[0])/(xs[-1]-xs[0])*800;gy=(pos[:,:,1]-ys[0])/(ys[-1]-ys[0])*308;coords=np.stack((gy,gx));ids=nd.map_coordinates(labels,coords,order=0,mode='nearest');surface=nd.map_coordinates(np.nan_to_num(height,nan=0),coords,order=1,mode='nearest');frame=nd.map_coordinates(base,coords,order=1,mode='nearest')
valid_ids=[r['label'] for r in report['regions']];ids=np.where(np.isin(ids,valid_ids),ids,0)
key=covered&(ids>0)&(pos[:,:,2]-frame>threshold*.87)&(abs(pos[:,:,2]-surface)<.0035)&(normal[:,:,2]>.35)
# Include molded sidewalls and recessed membrane in rubber, keeping the broad deck olive.
field_distance=nd.distance_transform_edt(labels==0);gapdist=nd.map_coordinates(field_distance,coords,order=1,mode='nearest')
rubber=covered&~key&(gapdist<9)&(pos[:,:,2]>frame-.0045)
steel=covered&~key&~rubber
rng=np.random.default_rng(91091);grain=rng.normal(0,1,(N,N)).astype(np.float32);x,y,zz=pos.transpose(2,0,1)
coarse=(np.sin(x*111+y*97+zz*41)+np.sin(x*217-y*87)+np.sin(x*67+y*263))/3
micro=(np.sin(x*3901+y*2017)+np.sin(x*2813-y*4327))/2
ao=np.array(Image.open(OUT/'keyboard_ao.png').convert('RGB'))[:,:,0]/255.;point=np.array(Image.open(OUT/'keyboard_pointiness.png').convert('RGB'))[:,:,0]/255.
print('AO covered',np.percentile(ao[covered],[0,25,50,75,100]),'curvature steel',np.percentile(point[steel],[0,25,50,75,90,95,100]),flush=True)
albedo=np.full((N,N,3),[84,90,58],np.float32);albedo+=coarse[:,:,None]*4+grain[:,:,None]*1.3
albedo[key]=np.array([42,44,46])+coarse[key,None]*1.8+grain[key,None]*.85
albedo[rubber]=np.array([13,15,15])+coarse[rubber,None]*1.3+grain[rubber,None]*.7
# Convex edge curvature and exposed AO determine paint losses and grime.
edge=np.clip((point-.505)/.055,0,1);chips=steel&(edge>.18)&(grain*.30+micro*.24+edge>.75)
chipcolor=np.zeros_like(albedo)+[128,125,108];chipcolor+=coarse[:,:,None]*9;albedo[chips]=chipcolor[chips]
rust=chips&(coarse<-.23);albedo[rust]=[105,76,47]
grime=np.clip((1-ao)*.19+np.maximum(-coarse,0)*.06,0,.22);albedo*=1-grime[:,:,None]
rough=np.full((N,N),.60,np.float32);rough[key]=.8;rough[rubber]=.88;rough[chips]=.48;rough+=coarse*.035+grain*.008;rough+=grime*.25
metal=np.full((N,N),.18,np.float32);metal[key|rubber]=0;metal[chips]=.78;metal[rust]=.35
# Find a real cap-interior rectangle rather than painting across the watershed boundary.
def maxrect(mask):
 heights=np.zeros(mask.shape[1],int);best=(0,(0,0,1,1))
 for row in range(mask.shape[0]):
  heights=np.where(mask[row],heights+1,0);stack=[]
  for col in range(len(heights)+1):
   hh=heights[col] if col<len(heights) else 0;start=col
   while stack and stack[-1][1]>hh:
    left,hh0=stack.pop();area=hh0*(col-left)
    if area>best[0]:best=(area,(left,row-hh0+1,col,row+1))
    start=left
   if not stack or stack[-1][1]<hh:stack.append((start,hh))
 return best[1]
legends=[];total_ink=np.zeros((N,N),np.float32)
for r in report['regions']:
 lab=r['label'];k=keys[r['design']];cap=key&(ids==lab)
 cap[int(N*.43):]=False
 yy,xx=np.where(cap)
 if not len(xx):raise RuntimeError(f'No planar key-top texels for {lab}')
 x0,x1=xx.min(),xx.max()+1;y0,y1=yy.min(),yy.max()+1
 small=nd.binary_fill_holes(cap[y0:y1,x0:x1]);a,b,c,d=maxrect(small)
 box=(x0+a,y0+b,x0+c,y0+d);w=box[2]-box[0];hh=box[3]-box[1]
 # Fifteen percent margin includes stroke radius, preserving the original glyph aspect.
 inset=max(2,min(w,hh)*.15);inner=(box[0]+inset,box[1]+inset,box[2]-inset,box[3]-inset)
 mark=Image.new('L',(N,N));draw=ImageDraw.Draw(mark);stroke=max(2,round(min(w,hh)*.055))
 if k['paths']:
  layout.fit_paths(draw,k['paths'],inner,color=255,width=stroke,pad=stroke/2)
 elif k['name']=='help':icons.help_variant(draw,inner,'squared',255,stroke)
 else:
  # Rasterize the exact source icon, then fit its occupied pixels to the same margin.
  tile=Image.new('L',(512,512));layout.icon(ImageDraw.Draw(tile),(0,0,512,512),k['name'],color=255);bounds=tile.getbbox();tile=tile.crop(bounds);scale=min((inner[2]-inner[0])/tile.width,(inner[3]-inner[1])/tile.height);tile=tile.resize((max(1,round(tile.width*scale)),max(1,round(tile.height*scale))),Image.Resampling.LANCZOS);mark.paste(tile,(round((box[0]+box[2]-tile.width)/2),round((box[1]+box[3]-tile.height)/2)))
 ink=np.array(mark,dtype=np.float32)/255*cap
 wear=np.clip(.96+.07*coarse+.035*grain,0,1);wear[grain<-1.85]*=.2;alpha=ink*.60*wear
 albedo=albedo*(1-alpha[:,:,None])+np.array([150,146,128])[None,None,:]*alpha[:,:,None]
 rough=rough*(1-alpha)+.79*alpha;total_ink=np.maximum(total_ink,alpha)
 count=int(np.count_nonzero(ink>.05));legends.append({'design_index':r['design']+1,'name':k['name'] or 'carrier','key_region':lab,'painted_texels':count,'interior_rect_px':list(map(int,box))})
 print('legend',k['name'] or 'carrier',count,'texels',box,flush=True)
 if count<5:raise RuntimeError(f'Empty legend {k}')
orm=np.stack((np.clip(ao,.18,1),np.clip(rough,0,1),np.clip(metal,0,1)),axis=2)*255
# Dilate only into unused UV space, never across a neighboring occupied island.
distance,nearest=nd.distance_transform_edt(~covered,return_indices=True);pad=(~covered)&(distance<=8)
for data,name in [(albedo,'albedo'),(orm,'orm')]:
 data[pad]=data[tuple(nearest[:,pad])];Image.fromarray(np.uint8(np.clip(data,0,255))).save(OUT/f'keyboard_{name}.png')
Image.fromarray(np.uint8(total_ink*255)).save(OUT/'legend_mask.png')
np.savez_compressed(OUT/'atlas_masks.npz',covered=covered,key=key,rubber=rubber,steel=steel,chips=chips)
report.update({'atlas_size':[2048,2048],'legend_count':len(legends),'legends':legends,'covered_texels':int(covered.sum()),'key_texels':int(key.sum()),'rubber_gap_texels':int(rubber.sum()),'painted_steel_texels':int(steel.sum()),'chipped_steel_texels':int(chips.sum()),'input_winding_repaired':True,'uv_method':'Smart UV Project 0.02 island margin, housing lower atlas, planar key tops upper atlas','material_maps':['keyboard_albedo.png','keyboard_orm.png','keyboard_normal.png'],'limitations':['The u legend is a spatial outlier, 1.722 key sizes from its normalized design centre. The generated mesh has four caps in the vowel bank and five small control-bank caps; the 29-way Hungarian assignment puts u on the extra small cap. No key geometry was rebuilt.']})
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Atlas complete. Steel chips:',chips.sum(),flush=True)
