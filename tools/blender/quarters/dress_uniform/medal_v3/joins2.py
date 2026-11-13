"""Measure C1 join behaviour on the actual fitted triangle surfaces."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
import trimesh
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2';BEFORE=OUT.parent/'fit1'
def stats(x):
 x=np.asarray(x);return {'samples':int(x.size),'rms':float(np.sqrt(np.mean(x*x))),'p95_abs':float(np.percentile(abs(x),95)),'max_abs':float(abs(x).max())}
def boundary(d):
 t=np.array(d['triangles']);flag=np.array(d['field']);owners=defaultdict(list)
 for j,f in enumerate(t):
  for e in zip(f,np.roll(f,-1)):owners[tuple(sorted(map(int,e)))].append(j)
 return np.array([e for e,fs in owners.items() if len(fs)==2 and sum(flag[fs])==1])
report={}
for suffix,folder in [('before',BEFORE),('after',OUT)]:
 cage=json.loads((OUT/('controls-'+suffix+'.json')).read_text())['Body'];cv=np.array(cage['vertices'])*1000;paths={p['name']:p['vertices'] for p in json.loads((folder/'sparse-cage.json').read_text())['paths']};report[suffix]={}
 for kind in ['high','low']:
  d=next(d for d in json.loads((folder/(kind+'-arrays.json')).read_text()) if d['name'].startswith('Body'));v=np.array(d['vertices'])*1000;t=np.array(d['triangles']);surface=trimesh.Trimesh(v,t,process=False);edges=boundary(d);mid=v[edges].mean(1);records={}
  for name,ids in paths.items():
   if not name.startswith(('star_ridge','star_valley')):continue
   q=cv[ids];anchor=q[-1];i=np.linalg.norm(mid-anchor,axis=1).argmin();edge=edges[i];p=v[edge].mean(0);tangent=(v[edge[1]]-v[edge[0]])[[0,2]];tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
   if normal@(q[-1]-q[-2])[[0,2]]<0:normal=-normal
   offsets=np.array([-.12,-.06,-.03,-.01,.01,.03,.06,.12]);xz=p[[0,2]]+offsets[:,None]*normal;origins=np.c_[xz[:,0],np.full(len(xz),-20.),xz[:,1]];hits,index,_=surface.ray.intersects_location(origins,np.tile([0.,1.,0.],(len(xz),1)),multiple_hits=False);assert len(index)==len(xz)
   y=np.empty(len(xz));y[index]=hits[:,1];L=np.polyfit(offsets[1:4],y[1:4],1);R=np.polyfit(offsets[4:7],y[4:7],1)
   records[name]={'anchor_mm':p.tolist(),'offsets_mm':offsets.tolist(),'depths_mm':y.tolist(),'extrapolated_gap_mm':float(R[1]-L[1]),'left_depth_slope':float(L[0]),'right_depth_slope':float(R[0]),'slope_jump':float(R[0]-L[0])}
  report[suffix][kind]={'joins':records,'depth_slope_jump':stats([r['slope_jump'] for r in records.values()]),'extrapolated_gap_mm':stats([r['extrapolated_gap_mm'] for r in records.values()])}
(OUT/'join-comparison.json').write_text(json.dumps(report,indent=2));print('JOINS2_COMPLETE',json.dumps({s:{k:d['depth_slope_jump'] for k,d in data.items()} for s,data in report.items()}),flush=True)
