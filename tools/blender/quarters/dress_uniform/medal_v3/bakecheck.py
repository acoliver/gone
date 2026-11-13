"""Numerically check bake reach and tangent normals without judging images."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
assets={}
for kind,filename in [('high','medal-high.glb'),('low','medal-low-normalmapped.glb')]:
 bpy.ops.import_scene.gltf(filepath=str(OUT/filename));assets[kind]={o.name.split('_')[0]:o for o in bpy.context.selected_objects if o.type=='MESH'}
image=bpy.data.images.load(str(OUT/'medal-low-normal.png'));image.colorspace_settings.name='Non-Color';w,h=image.size;pixels=np.array(image.pixels[:]).reshape(h,w,4)

def stats(x):
 x=np.asarray(x);return {'samples':int(x.size),'rms':float(np.sqrt(np.mean(x*x))),'p95':float(np.percentile(x,95)),'max':float(x.max())} if x.size else {'samples':0}

def barycentric(p,t):
 a=t[1]-t[0];b=t[2]-t[0];d=p-t[0];u=np.linalg.solve([[a@a,a@b],[a@b,b@b]],[a@d,b@d]);return np.r_[1-u.sum(),u]

def sample(uv):
 p=uv*np.array([w,h])-.5;x,y=np.floor(p).astype(int);u,v=p-[x,y];x0,x1=np.clip([x,x+1],0,w-1);y0,y1=np.clip([y,y+1],0,h-1)
 c=(1-u)*(1-v)*pixels[y0,x0,:3]+u*(1-v)*pixels[y0,x1,:3]+(1-u)*v*pixels[y1,x0,:3]+u*v*pixels[y1,x1,:3];return c*2-1
report={'sampling':'Each low triangle centroid and three interior barycentric quarter-points. Rays follow interpolated actual exported low corner normals; normal map sampled bilinearly in linear non-colour space and transformed by exported low Mikk tangents. Reach check is a geometric diagnostic, not a per-texel Cycles pass audit.','parts':{},'visual_assessment':'Not performed.'}
for part in assets['low']:
 lo=assets['low'][part].data;hi=assets['high'][part].data;lo.calc_loop_triangles();hi.calc_loop_triangles();lo.calc_tangents()
 lv=np.array([p.co[:] for p in lo.vertices])*1000;hv=np.array([p.co[:] for p in hi.vertices])*1000;ht=np.array([t.vertices[:] for t in hi.loop_triangles]);hl=np.array([t.loops[:] for t in hi.loop_triangles]);hcn=np.array([p.vector[:] for p in hi.corner_normals]);cn=np.array([p.vector[:] for p in lo.corner_normals]);uv=np.array([p.uv[:] for p in lo.uv_layers.active.data]);tangent=np.array([p.tangent[:] for p in lo.loops]);sign=np.array([p.bitangent_sign for p in lo.loops]);tree=BVHTree.FromPolygons([Vector(p) for p in hv],ht.tolist(),all_triangles=True)
 rows={name:{'misses':0,'samples':0,'nearest_distance_mm':[],'mapped_normal_error_degrees':[],'black_core_samples':0} for name in ['front','rear','side']}
 for triangle in lo.loop_triangles:
  ids=list(triangle.vertices);ls=list(triangle.loops);rear=part=='Body' and triangle.normal.y>.25 and lv[ids,1].mean()>0
  region='rear' if rear else 'front' if triangle.normal.y<-.25 else 'side';row=rows[region]
  extrusion,reach=(.6,1.2) if rear else (.1,.25) if part=='Body' else (.5,1.)
  for weights in [np.array([1/3]*3),np.array([.5,.25,.25]),np.array([.25,.5,.25]),np.array([.25,.25,.5])]:
   p=weights@lv[ids];normal=weights@cn[ls];normal/=np.linalg.norm(normal);row['samples']+=1
   hit=tree.ray_cast(Vector(p+normal*extrusion),Vector(-normal),reach)[0]
   row['misses']+=int(hit is None)
   co,nn,j,distance=tree.find_nearest(Vector(p));row['nearest_distance_mm'].append(float(distance));weights_high=barycentric(np.array(co),hv[ht[j]]);reference=weights_high@hcn[hl[j]];reference/=np.linalg.norm(reference)
   texnormal=sample(weights@uv[ls]);row['black_core_samples']+=int(np.all(texnormal<-.98))
   t=weights@tangent[ls];t-=normal*(normal@t);t/=np.linalg.norm(t);b=np.cross(normal,t)*np.sign(weights@sign[ls]);mapped=texnormal[0]*t+texnormal[1]*b+texnormal[2]*normal;mapped/=np.linalg.norm(mapped)
   row['mapped_normal_error_degrees'].append(float(np.degrees(np.arccos(np.clip(mapped@reference,-1,1)))))
 for row in rows.values():
  row['nearest_distance_mm']=stats(row['nearest_distance_mm']);row['mapped_normal_error_degrees']=stats(row['mapped_normal_error_degrees'])
 report['parts'][part]=rows
(OUT/'bake-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
