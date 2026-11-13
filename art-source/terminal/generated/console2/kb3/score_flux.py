from pathlib import Path
import numpy as np,cv2,json
from scipy import ndimage as nd
from scipy.optimize import linear_sum_assignment
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
ref=json.loads((OUT/'reference.json').read_text());rect=np.array(ref['rects']);dc=(rect[:,:2]+rect[:,2:])/2;dlo=rect[:,:2].min(0);dhi=rect[:,2:].max(0);dn=(dc-dlo)/(dhi-dlo)
def match(cc,stats,centres,keep):
 gb=stats[keep,:4];lo=gb[:,:2].min(0);hi=(gb[:,:2]+gb[:,2:]).max(0);gn=(centres[keep]-lo)/(hi-lo)
 cost=np.linalg.norm(gn[:,None]-dn[None,:],axis=2);a,b=linear_sum_assignment(cost);err=cost[a,b]
 return a,b,err
reports=[]
for seed in range(530,534):
 path=OUT/f'flux-{seed}.png'
 if not path.exists():continue
 rgb=np.array(Image.open(path).convert('RGB'));grey=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);options=[]
 # Neutral dark-cap bands remove black connecting boots; opening removes narrow bridges.
 for kernel in [3,5,7,9]:
  for lower in range(30,76,3):
   for upper in range(max(lower+9,65),126,5):
    mask=np.uint8((grey>lower)&(grey<upper)&((rgb.max(2).astype(float)-rgb.min(2))<15));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((kernel,kernel),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8));mask=nd.binary_fill_holes(mask).astype('uint8')
    nc,cc,stats,centres=cv2.connectedComponentsWithStats(mask)
    keep=[i for i in range(1,nc) if 100<stats[i,4]<20000 and stats[i,2]>9 and stats[i,3]>9 and stats[i,4]/(stats[i,2]*stats[i,3])>.45]
    if not keep:continue
    a,b,err=match(cc,stats,centres,keep)
    options.append((abs(len(keep)-29),float(err.mean()),float(err.max()),[lower,upper,kernel],cc,stats,centres,keep,a,b))
 opt=min(options,key=lambda o:(o[0],o[1]));delta,mean,maxerr,threshold,cc,stats,centres,keep,a,b=opt
 # A match more than half a median key pitch away is not the requested key.
 pitch=np.median(np.sqrt(np.prod((rect[:,2:]-rect[:,:2])/(dhi-dlo),axis=1)));errors=np.linalg.norm(((centres[keep] - stats[keep,:2].min(0))/((stats[keep,:2]+stats[keep,2:4]).max(0)-stats[keep,:2].min(0)))[a]-dn[b],axis=1)
 accepted=errors<pitch*.6
 record={'seed':seed,'detected_count':len(keep),'matched_count':int(accepted.sum()),'mean_error_normalized':mean,'max_error_normalized':maxerr,'mean_error_key_size':mean/pitch,'max_error_key_size':maxerr/pitch,'threshold_luminance':threshold,'regions':[{'label':int(keep[i]),'design':int(j),'centre':centres[keep[i]].tolist(),'bounds':stats[keep[i],:4].tolist(),'error':float(errors[n])} for n,(i,j) in enumerate(zip(a,b))],'threshold_counts':[{ 'threshold':o[3],'count':len(o[7]),'mean':o[1]} for o in options]}
 reports.append(record);im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
 for r in record['regions']:
  x,y=r['centre'];draw.text((x,y),str(r['design']+1),fill='white',stroke_width=1,stroke_fill='red')
 im.save(OUT/f'flux-{seed}-segmented.png');np.savez_compressed(OUT/f'flux-{seed}-segmentation.npz',labels=cc,keep=keep)
 print(json.dumps({k:v for k,v in record.items() if k not in ['regions','threshold_counts']}),flush=True)
(OUT/'flux-scores.json').write_text(json.dumps(reports,indent=2))
if len(reports)==4:
 best=min(reports,key=lambda r:(r['matched_count']!=29,abs(r['detected_count']-29),r['mean_error_normalized']));(OUT/'chosen-flux.json').write_text(json.dumps(best,indent=2));rgb=np.array(Image.open(OUT/f"flux-{best['seed']}.png").convert('RGB'))
 # Border-connected neutral light background, with antialiasing on the silhouette.
 delta=np.linalg.norm(rgb.astype(float)-np.median(np.r_[rgb[0],rgb[-1],rgb[:,0],rgb[:,-1]],axis=0),axis=2);fg=(delta>28)&(rgb.mean(2)<205);fg=cv2.morphologyEx(fg.astype('uint8'),cv2.MORPH_CLOSE,np.ones((5,5),np.uint8));n,c,s,_=cv2.connectedComponentsWithStats(fg);fg=nd.binary_fill_holes(c==(1+np.argmax(s[1:,4])));alpha=np.uint8(fg)*255
 rgba=np.dstack((rgb,alpha));Image.fromarray(rgba).save(OUT/'reference-rgba.png');print('CHOSEN',best['seed'],'cutout',np.count_nonzero(alpha),flush=True)
