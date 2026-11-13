"""Measure topology-owned star contours and the boundary-only enamel surface."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
import trimesh
from scipy.signal import find_peaks
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import contains_xy
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
center=np.array(json.loads((OUT/'features.json').read_text())['star_center_mm'])

def stats(x):
 x=np.asarray(x);return {'samples':int(x.size),'rms_mm':float(np.sqrt(np.mean(x*x))),'max_abs_mm':float(abs(x).max()),'p95_abs_mm':float(np.percentile(abs(x),95))}

def cycle(d):
 v=np.array(d['vertices'])*1000;tri=np.array(d['triangles']);field=np.array(d['field']);owners=defaultdict(list)
 for fi,t in enumerate(tri):
  for e in zip(t,np.roll(t,-1)):owners[tuple(sorted(map(int,e)))].append(fi)
 adj=defaultdict(list)
 for (a,b),fs in owners.items():
  if len(fs)==2 and sum(field[fs])==1:adj[a].append(b);adj[b].append(a)
 assert all(len(ns)==2 for ns in adj.values()),'Field boundaries must be cycles'
 remaining=set(adj);cycles=[]
 while remaining:
  ids=[min(remaining)];previous=None
  while True:
   nxt=next(i for i in adj[ids[-1]] if i!=previous);previous=ids[-1]
   if nxt==ids[0]:break
   assert nxt not in ids;ids.append(nxt)
  cycles.append(ids);remaining-=set(ids)
 assert len(cycles)==2,len(cycles)
 ids=min(cycles,key=lambda ids:Polygon(v[ids][:,[0,2]]).area)
 q=v[ids];r=np.linalg.norm(q[:,[0,2]]-center,axis=1);n=len(q)
 peaks=find_peaks(np.tile(r,3),prominence=1.)[0];peaks=peaks[(peaks>=n)&(peaks<2*n)]-n
 def point(j):return {'radius_mm':float(r[j]),'angle_degrees':float(np.degrees(np.arctan2(q[j,2]-center[1],q[j,0]-center[0]))%360),'position_mm':q[j].tolist()}
 notches=[]
 for a,b in zip(peaks,np.roll(peaks,-1)):
  segment=np.arange(a,b+1) if a<b else np.r_[np.arange(a,n),np.arange(b+1)];j=int(segment[r[segment].argmin()]);item=point(j)
  s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q[segment][:,[0,2]],axis=0),axis=1))];pos=s[np.flatnonzero(segment==j)[0]]
  L=np.array([np.interp(max(0,pos-.65),s,q[segment,h]) for h in [0,2]])-q[j,[0,2]]
  R=np.array([np.interp(min(s[-1],pos+.65),s,q[segment,h]) for h in [0,2]])-q[j,[0,2]]
  item['included_angle_degrees']=float(np.degrees(np.arccos(np.clip(L@R/(np.linalg.norm(L)*np.linalg.norm(R)),-1,1))));notches.append(item)
 notches=sorted(notches,key=lambda x:x['angle_degrees']);radii=np.array([x['radius_mm'] for x in notches]);included=np.array([x['included_angle_degrees'] for x in notches])
 return {'peaks':len(peaks),'prominence_mm':1.,'tips':sorted([point(int(j)) for j in peaks],key=lambda x:x['angle_degrees']),'notches':notches,'notch_radius_spread_mm':float(np.ptp(radii)),'notch_radius_std_mm':float(radii.std()),'notch_included_angle_spread_degrees':float(np.ptp(included))}

report={'star':{},'field':{},'visual_assessment':'Not performed.'}
cage=np.array(json.loads((OUT/'fairing-targets.json').read_text())['vertices'])*1000
field_tri=np.array(json.loads((OUT/'field-flatness.json').read_text())['field_triangles']);flat=cage.copy();flat[:,1]=0;membrane=trimesh.Trimesh(flat,field_tri,process=False)
for kind in ['high','low']:
 d=next(x for x in json.loads((OUT/(kind+'-arrays.json')).read_text()) if x['name'].startswith('Body'));v=np.array(d['vertices'])*1000;t=np.array(d['triangles']);field=np.array(d['field'],bool);surface=trimesh.Trimesh(v,t,process=False)
 report['star'][kind]=cycle(d);assert report['star'][kind]['peaks']==5,report['star'][kind]
 domain=unary_union([Polygon(p[:,[0,2]]) for p in v[t[field]]]).buffer(-.4)
 xx,zz=np.meshgrid(np.arange(-16,16.01,.25),np.arange(-16,17.01,.25));mask=contains_xy(domain,xx,zz);points=np.c_[xx[mask],np.full(mask.sum(),-20),zz[mask]]
 hit,index,_=surface.ray.intersects_location(points,np.tile([0.,1.,0.],(len(points),1)),multiple_hits=False);assert len(index)==len(points)
 y=np.empty(len(points));y[index]=hit[:,1];grid=np.full(mask.shape,np.nan);grid[mask]=y
 lap=(grid[2:,1:-1]+grid[:-2,1:-1]+grid[1:-1,2:]+grid[1:-1,:-2]-4*grid[1:-1,1:-1])/.25**2
 A=np.c_[points[:,0],points[:,2],np.ones(len(points))];coef=np.linalg.lstsq(A,y,rcond=None)[0]
 planar=points.copy();planar[:,1]=0;chunks=[trimesh.proximity.closest_point(membrane,planar[i:i+400]) for i in range(0,len(planar),400)];co=np.concatenate([x[0] for x in chunks]);distance=np.concatenate([x[1] for x in chunks]);face=np.concatenate([x[2] for x in chunks]);assert distance.max()<1e-5,float(distance.max())
 bary=trimesh.triangles.points_to_barycentric(flat[field_tri[face]],co);reference=np.einsum('ij,ij->i',bary,cage[field_tri[face],1]);owners=defaultdict(list)
 for i,tri in enumerate(t):
  for e in zip(tri,np.roll(tri,-1)):owners[tuple(sorted(map(int,e)))].append(i)
 interior={e for e,fs in owners.items() if len(fs)==2 and all(field[fs])};sharp=sum(tuple(sorted(e)) in interior for e in d['sharp_edges']);assert sharp==0
 normal=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]])
 reversed_field=int((normal[field,1]>=0).sum());assert reversed_field==0,reversed_field
 report['field'][kind]={'plane_residual_mm':stats(y-A@coef),'depth_laplacian_per_mm':stats(lap[np.isfinite(lap)]),'residual_to_boundary_membrane_mm':stats(reference-y),'boundary_exclusion_mm':.4,'grid_pitch_mm':.25,'interior_sharp_edges':sharp,'reversed_field_triangles':reversed_field}
(OUT/'local-measurements.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
