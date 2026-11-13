"""Render diagnostic rasters and summarize per-finding mesh measurements."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial import cKDTree
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2';BEFORE=OUT.parent/'fit1'
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
def stats(x):
 x=np.asarray(x);x=x[np.isfinite(x)]
 return {'samples':len(x),'rms':float(np.sqrt(np.mean(x*x))),'p95_abs':float(np.percentile(abs(x),95)),'max_abs':float(abs(x).max())} if len(x) else {'samples':0}
boxes={'front_top':('front',[360,230,540,380]),'front_left':('front',[215,350,385,525]),'front_right':('front',[515,350,685,525]),'front_lower':('front',[325,550,575,730]),'rear_lower':('rear',[265,665,635,850]),'notch_338_93':('star-close',[550,390,755,590])}
report={'before':{},'after':{},'visual_assessment':'Not performed.'}
for suffix,folder in [('before',BEFORE),('after',OUT)]:
 projection=json.loads((OUT/('projection-'+suffix+'.json')).read_text());cage=json.loads((OUT/('controls-'+suffix+'.json')).read_text())['Body'];cv=np.array(cage['vertices'])*1000
 target=np.array(json.loads((folder/'fairing-targets.json').read_text())['vertices'])*1000;ft=np.array(json.loads((folder/'field-flatness.json').read_text())['field_triangles']);flat=target.copy();flat[:,1]=0;membrane=trimesh.Trimesh(flat,ft,process=False)
 regions={}
 for view,item in projection['views'].items():
  s=np.array(item['rows']);px=s[:,:2].astype(int);angle=np.degrees(np.arccos(np.clip(np.sum(s[:,5:8]*s[:,8:11],axis=1),-1,1)));depth=np.full(len(s),np.nan)
  reference_mesh=membrane;reference_vertices=target;reference_flat=flat;reference_tri=ft
  if view=='rear':
   source=json.loads((OUT/'sparse-cage.json').read_text());reference_vertices=np.array(json.loads((OUT/'fairing-targets.json').read_text())['vertices'])*1000;reference_tri=np.array([f for f in source['faces'][source['front_face_count']:] if len(f)==3]);reference_flat=reference_vertices.copy();reference_flat[:,1]=0;reference_mesh=trimesh.Trimesh(reference_flat,reference_tri,process=False)
  points=s[:,2:5].copy();points[:,1]=0
  chunks=[trimesh.proximity.closest_point(reference_mesh,points[i:i+300]) for i in range(0,len(points),300)];co=np.concatenate([x[0] for x in chunks]);dist=np.concatenate([x[1] for x in chunks]);face=np.concatenate([x[2] for x in chunks]);bary=trimesh.triangles.points_to_barycentric(reference_flat[reference_tri[face]],co);ref=np.einsum('ij,ij->i',bary,reference_vertices[reference_tri[face],1]);inside=dist<1e-5;depth[inside]=s[inside,3]-ref[inside]
  for kind,values,limit in [('normal-difference',angle,30.),('mapped-normal-error',s[:,14],30.),('depth',depth,.15)]:
   rgb=np.full((900,900,3),220,dtype=np.uint8)
   if kind=='depth':
    q=np.clip(values/limit,-1,1);colors=np.c_[255-190*np.maximum(-q,0),255-190*abs(q),255-190*np.maximum(q,0)]
   else:
    q=np.clip(values/limit,0,1);colors=np.c_[255*q,220*np.minimum(q*2,2-2*q),255*(1-q)]
   colors[~np.isfinite(values)]=[150,150,150]
   # Three-pixel sampling is drawn as noninterpolated cells.
   im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
   for (x,y),color in zip(px,colors):draw.rectangle((int(x),int(y),int(x+2),int(y+2)),fill=tuple(np.uint8(np.clip(color,0,255))))
   canvas=Image.new('RGB',(900,940),(230,230,230));canvas.paste(im,(0,40));ImageDraw.Draw(canvas).text((8,10),f'{suffix} | {view} | {kind} | scale {limit}',font=font,fill='black');canvas.save(OUT/(f'diagnostic-{view}-{kind}-{suffix}.png'))
  # Project editable sparse wire and crease graph through this exact camera.
  inv=np.linalg.inv(np.array(item['camera_matrix']));q=np.c_[cv,np.ones(len(cv))]@inv.T;scale=item['scale_mm'];cp=np.c_[(q[:,0]/scale+.5)*900,(.5-q[:,1]/scale)*900]
  with Image.open(folder/('high-'+view+'.jpg')) as im:im=im.convert('RGB')
  draw=ImageDraw.Draw(im);edge_weights={tuple(sorted(e[:2])):e[2] for e in cage['creases']}
  edges={tuple(sorted(e)) for f in cage['faces'] for e in zip(f,f[1:]+f[:1])}
  for e in edges:
   if (cv[list(e),1].mean()>0)==(view!='rear'):continue
   xy=cp[list(e)];w=edge_weights.get(e,0);draw.line([tuple(a) for a in xy],fill=(255,65,20) if w>0 else (75,160,180),width=2 if w>0 else 1)
  im.save(OUT/(f'diagnostic-{view}-wire-{suffix}.png'))
  for name,(which,box) in boxes.items():
   if which!=view:continue
   mask=(s[:,0]>=box[0])&(s[:,0]<box[2])&(s[:,1]>=box[1])&(s[:,1]<box[3])
   regions[name]={'pixels':box,'camera_projected_bounds_mm':[s[mask,2:5].min(0).tolist(),s[mask,2:5].max(0).tolist()],'high_corner_vs_geometric_normal_degrees':stats(angle[mask]),'mapped_low_vs_visible_high_degrees':stats(s[mask,14]),'depth_vs_boundary_reference_mm':stats(depth[mask])}
 # Slope changes along and across exact exported source-bounded contours.
 paths={p['name']:p['vertices'] for p in json.loads((folder/'sparse-cage.json').read_text())['paths']};ids=paths['star_outline'];q=cv[ids];segments=np.roll(q,-1,axis=0)-q;length=np.linalg.norm(segments[:,[0,2]],axis=1);slopes=segments[:,1]/length
 outline={'spacing_mm':stats(length),'depth_slope_jump':stats(slopes-np.roll(slopes,1))}
 # The low-only line's geometric/UV support, independent of render judgment.
 triangles=projection['notch_338_93_triangles'];regions['notch_uv_support']={'aspect_ratio':stats([x['aspect'] for x in triangles]),'uv_area_texels':stats([x['uv_area_texels'] for x in triangles]),'triangles_with_less_than_8_texels':sum(x['uv_area_texels']<8 for x in triangles)}
 report[suffix]={'regions':regions,'outline':outline}
(OUT/'finding-diagnostics.json').write_text(json.dumps(report,indent=2));print('MAPS2_COMPLETE',flush=True)
