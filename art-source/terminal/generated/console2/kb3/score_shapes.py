import json,numpy as np,cv2,sys
from scipy import ndimage as nd
from scipy.optimize import linear_sum_assignment
from pathlib import Path
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
r=np.array(json.loads((OUT/'reference.json').read_text())['rects']);dc=(r[:,:2]+r[:,2:])/2;dn=(dc-r[:,:2].min(0))/(r[:,2:].max(0)-r[:,:2].min(0));dn[:,1]=1-dn[:,1];pitch=float(np.median(np.sqrt(np.prod((r[:,2:]-r[:,:2])/(r[:,2:].max(0)-r[:,:2].min(0)),axis=1))))
results=[]
for seed in [410,411]:
 D=OUT/f'mesh-{seed}'
 if not (D/'height.npz').exists():continue
 z=np.load(D/'height.npz');h=z['height'];valid=np.isfinite(h);v=np.nan_to_num(h,nan=float(np.nanmin(h)));v=nd.grey_closing(v,size=(3,3));opts=[]
 bases=[]
 for rad in [21,29,37,45,57]:
  base=cv2.morphologyEx(v,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(rad*2+1,rad*2+1)));bases.append((f'opening{rad}',base))
 # Iterative lower-envelope polynomial follows a curved deck without subtracting caps.
 yy,xx=np.mgrid[-1:1:complex(h.shape[0]),-1:1:complex(h.shape[1])];A=np.stack([xx**i*yy**j for i in range(4) for j in range(4-i)],axis=2);fit=valid.copy()
 for _ in range(5):
  co=np.linalg.lstsq(A[fit],v[fit],rcond=None)[0];base=A@co;res=v-base;fit=valid&(res<np.percentile(res[valid],45))
 bases.append(('polynomial3',base.astype(np.float32)))
 for kind,base in bases:
  residual=v-base
  for threshold in np.arange(.0025,.0181,.0005):
   mask=np.uint8((residual>threshold)&valid);mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));mask=nd.binary_fill_holes(mask).astype('uint8');n,l,s,c=cv2.connectedComponentsWithStats(mask)
   keep=[i for i in range(1,n) if 180<s[i,4]<h.size*.10 and s[i,2]>10 and s[i,3]>10 and s[i,4]/(s[i,2]*s[i,3])>.40]
   if not keep:continue
   gb=s[keep,:4];gn=(c[keep]-gb[:,:2].min(0))/((gb[:,:2]+gb[:,2:]).max(0)-gb[:,:2].min(0));cost=np.linalg.norm(gn[:,None]-dn[None,:],axis=2);a,b=linear_sum_assignment(cost);err=cost[a,b];matched=int((err<pitch*.6).sum());rank=(-matched,abs(len(keep)-29),float(err.mean()))
   opts.append((rank,kind,float(threshold),l,s,c,keep,a,b,err,base,residual))
 # Shallow valleys between tall keys can sit above the global deck threshold.
 # Local upper-envelope cores isolate those plateaus without design-seeded markers.
 smooth=nd.gaussian_filter(np.nan_to_num(h,nan=.025),1.1)
 for size in [21,31,41,51,65]:
  upper=nd.maximum_filter(smooth,size=size)
  for diff in [.0003,.0005,.0007,.001,.0013,.0016,.002]:
   mask=np.uint8(valid&(smooth>.047)&(smooth>upper-diff));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));mask=nd.binary_fill_holes(mask).astype('uint8');n,l,s,c=cv2.connectedComponentsWithStats(mask)
   keep=[i for i in range(1,n) if 350<s[i,4]<h.size*.10 and s[i,2]>14 and s[i,3]>14 and s[i,4]/(s[i,2]*s[i,3])>.40]
   if not keep:continue
   gb=s[keep,:4];gn=(c[keep]-gb[:,:2].min(0))/((gb[:,:2]+gb[:,2:]).max(0)-gb[:,:2].min(0));cost=np.linalg.norm(gn[:,None]-dn[None,:],axis=2);a,b=linear_sum_assignment(cost);err=cost[a,b];matched=int((err<pitch*.6).sum());rank=(-matched,abs(len(keep)-29),float(err.mean()));base=np.full(h.shape,.045,np.float32)
   opts.append((rank,f'upper-envelope{size}-drop{diff}',.002,l,s,c,keep,a,b,err,base,v-base))
 best=min(opts,key=lambda x:x[0]);rank,kind,threshold,l,s,c,keep,a,b,err,base,residual=best
 labels=np.where(np.isin(l,keep),l,0);regions=[{'label':int(keep[i]),'design':int(j),'centre':c[keep[i]].tolist(),'bounds':[int(s[keep[i],0]),int(s[keep[i],1]),int(s[keep[i],0]+s[keep[i],2]),int(s[keep[i],1]+s[keep[i],3])],'area':int(s[keep[i],4]),'error':float(err[k]/pitch)} for k,(i,j) in enumerate(zip(a,b))]
 report={'seed':seed,'key_count':len(keep),'matched_count':-rank[0],'mean_error_normalized':float(err.mean()),'max_error_normalized':float(err.max()),'mean_match_error_key_size':float(err.mean()/pitch),'max_match_error_key_size':float(err.max()/pitch),'method':kind,'threshold':threshold,'rotation_z_degrees':0,'unmatched_design':[int(j+1) for j in range(29) if j not in b],'unmatched_generated':len(keep)-len(a),'regions':regions}
 (D/'matching.json').write_text(json.dumps(report,indent=2));np.savez_compressed(D/'segmentation.npz',labels=labels,height=h,base=base,residual=residual,threshold=threshold,xs=z['xs'],ys=z['ys'])
 rng=np.random.default_rng(91);col=rng.integers(70,235,(n+max(keep)+1,3),dtype=np.uint8);col[0]=[24,27,30];im=Image.fromarray(col[labels][::-1].copy());draw=ImageDraw.Draw(im)
 for r0 in regions:x,y=r0['centre'];draw.text((x,h.shape[0]-1-y),str(r0['design']+1),fill='white',stroke_width=1,stroke_fill='black')
 im.save(D/'segmentation.png');report['candidates']=[{'method':o[1],'threshold':o[2],'count':len(o[6]),'matched':-o[0][0],'mean':o[0][2]} for o in opts];(D/'scores.json').write_text(json.dumps(report,indent=2));results.append(report);print(json.dumps({k:v for k,v in report.items() if k not in ['regions','candidates']}),flush=True)
best=min(results,key=lambda r:(-r['matched_count'],abs(r['key_count']-29),r['mean_error_normalized']));(OUT/'chosen-shape.json').write_text(json.dumps({k:v for k,v in best.items() if k!='candidates'},indent=2));(OUT/'shape-scores.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ['regions','candidates']} for r in results],indent=2));print('CHOSEN SHAPE',best['seed'],flush=True)
