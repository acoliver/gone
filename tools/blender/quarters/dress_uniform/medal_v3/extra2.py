"""Outside-Blender dimensions, rear fairness, and suspension contact checks."""
from pathlib import Path
import json
import numpy as np
import trimesh
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2';BEFORE=OUT.parent/'fit1'
def stats(x):
 x=np.asarray(x);x=x[np.isfinite(x)];return {'samples':len(x),'rms':float(np.sqrt(np.mean(x*x))),'p95_abs':float(np.percentile(abs(x),95)),'max_abs':float(abs(x).max())}
report={'before':{},'after':{},'visual_assessment':'Not performed.'}
for suffix,folder in [('before',BEFORE),('after',OUT)]:
 report[suffix]={}
 for kind in ['high','low']:
  data=json.loads((folder/(kind+'-arrays.json')).read_text());meshes={d['name'].split('_')[0]:trimesh.Trimesh(np.array(d['vertices'])*1000,d['triangles'],process=False) for d in data};body=meshes['Body'];loop=meshes['Loop'];bar=meshes['Bar']
  dims={name:{'blender_xyz_extents_mm':mesh.extents.tolist(),'bounds_mm':mesh.bounds.tolist(),'connected_components':len(mesh.split(only_watertight=False))} for name,mesh in meshes.items()}
  x,z=np.meshgrid(np.arange(-13,13.01,.5),np.arange(-13,13.01,.5));mask=x*x+z*z<13.**2;points=np.c_[x[mask],np.full(mask.sum(),20.),z[mask]];hits,index,_=body.ray.intersects_location(points,np.tile([0.,-1.,0.],(len(points),1)),multiple_hits=False);assert len(index)==len(points);depth=np.full(mask.shape,np.nan);depth[mask]=np.empty(len(points));y=np.empty(len(points));y[index]=hits[:,1];depth[mask]=y;lap=(depth[2:,1:-1]+depth[:-2,1:-1]+depth[1:-1,2:]+depth[1:-1,:-2]-4*depth[1:-1,1:-1])/.5**2
  lower=mask&(z<-8);lower_y=depth[lower];rear={'grid_pitch_mm':.5,'rear_depth_range_mm':[float(y.min()),float(y.max())],'rear_depth_laplacian_per_mm':stats(lap),'lower_rear_depth_range_mm':[float(np.nanmin(lower_y)),float(np.nanmax(lower_y))]}
  # Sample actual surface triangles, then test nearest distance and containment.
  lp,_=trimesh.sample.sample_surface(loop,1800,seed=130);bp,_=trimesh.sample.sample_surface(bar,1800,seed=131)
  cap=lp[:,2]<loop.bounds[0,2]+1.;contact_points=lp[cap];_,dist,_=trimesh.proximity.closest_point(body,contact_points);bar_nearest=trimesh.proximity.closest_point(loop,bp)[1]
  overlap=body.contains(contact_points);bar_inside=loop.contains(bp)
  suspension={'loop_body_contact_min_mm':float(dist.min()),'loop_body_sampled_inside_points':int(overlap.sum()),'bar_loop_contact_min_mm':float(bar_nearest.min()),'bar_loop_sampled_inside_points':int(bar_inside.sum()),'bar_body_vertical_clearance_mm':float(bar.bounds[0,2]-body.bounds[1,2]),'sampling':'1800 deterministic actual surface samples per hardware part; body contact restricted to the existing bottom 1 mm loop band.'}
  report[suffix][kind]={'parts':dims,'rear':rear,'suspension':suspension}
(OUT/'extra-checks.json').write_text(json.dumps(report,indent=2))
for kind in ['high','low']:
 s=report['after'][kind]['suspension'];assert s['bar_body_vertical_clearance_mm']>0
 assert s['loop_body_contact_min_mm']<.2,(kind,s)
 assert s['bar_loop_sampled_inside_points']>0,(kind,s)
 assert report['after'][kind]['parts']['Bar']['connected_components']==1
(OUT/'extra-checks.json').write_text(json.dumps(report,indent=2));print('EXTRA2_COMPLETE',json.dumps({s:{k:d['suspension'] for k,d in data.items()} for s,data in report.items() if isinstance(data,dict)}),flush=True)
