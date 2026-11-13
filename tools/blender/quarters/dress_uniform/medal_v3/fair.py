"""Solve feature-bounded sparse relief and one boundary-only enamel membrane."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from shapely.geometry import Polygon,Point
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
d=json.loads((OUT/'sparse-cage.json').read_text());features=json.loads((OUT/'features.json').read_text())
v=np.array(d['vertices'])*1000;original=v.copy();faces=d['faces'];front_count=d['front_face_count'];tri=np.array(faces[:front_count]);weights={tuple(sorted(e[:2])):e[2] for e in d['creases']}
curves={f['name']:np.array(f['points_mm']) for f in features['features']}
star=Polygon(curves['star_outline'][:,[0,2]]);rim=Polygon(curves['rim_step_0'][:,[0,2]])
flags=np.zeros(len(faces),int)
for i,t in enumerate(tri):
 p=Point(v[t][:,[0,2]].mean(0));flags[i]=int(rim.contains(p) and not star.contains(p))
# Field ownership is exact because both boundaries are embedded CDT edges.
owners=defaultdict(list)
for i,f in enumerate(faces):
 for e in zip(f,f[1:]+f[:1]):owners[tuple(sorted(e))].append(i)
internal={e for e,fs in owners.items() if len(fs)==2 and all(flags[fs])}
for e in internal:weights.pop(e,None)
field_faces=np.flatnonzero(flags);field_tri=tri[field_faces]

# Finite-element Dirichlet solve. No raw targets enter the enamel objective.
def solve(ts,pinned=None):
 ids=np.unique(ts);inv={i:j for j,i in enumerate(ids)};local=np.array([[inv[i] for i in t] for t in ts]);xy=v[ids][:,[0,2]];rows=[];cols=[];values=[];counts=defaultdict(int);mass=np.zeros(len(ids))
 for t in local:
  p=xy[t];a,b=p[1]-p[0],p[2]-p[0];twice=a[0]*b[1]-a[1]*b[0];area=abs(twice)/2;assert area>1e-9,area
  for e in zip(t,np.roll(t,-1)):counts[tuple(sorted(e))]+=1
  gradient=np.array([[p[1,1]-p[2,1],p[2,0]-p[1,0]],[p[2,1]-p[0,1],p[0,0]-p[2,0]],[p[0,1]-p[1,1],p[1,0]-p[0,0]]])/twice
  stiffness=area*gradient@gradient.T
  for a in range(3):
   mass[t[a]]+=area/3
   for b in range(3):rows.append(t[a]);cols.append(t[b]);values.append(stiffness[a,b])
 K=coo_matrix((values,(rows,cols)),shape=(len(ids),len(ids))).tocsr()
 boundary={i for e,n in counts.items() if n==1 for i in e}
 if pinned:boundary|={inv[i] for i in pinned if i in inv}
 boundary=np.array(sorted(boundary));free=np.setdiff1d(np.arange(len(ids)),boundary);y=v[ids,1].copy();solved=y.copy()
 solved[free]=spsolve(K[free][:,free],-K[free][:,boundary]@y[boundary]);v[ids,1]=solved
 residual=(K@solved)[free]/mass[free]
 return {'vertices':ids.tolist(),'boundary_vertices':ids[boundary].tolist(),'free_vertices':ids[free].tolist(),'laplacian_rms_per_mm':float(np.sqrt(np.mean(residual**2))),'laplacian_max_abs_per_mm':float(abs(residual).max())}
# Relief free controls fair generously between measured branches; every curve
# control and outer-front band remains fixed.
pins={i for e,w in weights.items() if w>0 for i in e}
for path in d['paths']:
 if path['name'].startswith('star_'):pins.update(path['vertices'])
relief=solve(tri,pins)
field=solve(field_tri)
# Rear has no relief constraints; retain broad generated curvature with a
# sparse thin-plate fairing rather than a boundary-only flattening.
rear_tri=[]
for f in faces[front_count:]:
 if len(f)==3:rear_tri.append(f)
adj=defaultdict(set)
for t in rear_tri:
 for a,b in zip(t,np.roll(t,-1)):adj[a].add(b);adj[b].add(a)
rear_pins={i for path in d['paths'] if path['name']=='rear_transition' for i in path['vertices']}
for k in range(180):
 new=v.copy()
 for i,ns in adj.items():
  if i not in rear_pins:new[i,1]+=.25*(v[list(ns),1].mean()-v[i,1])+.015*(original[i,1]-v[i,1])
 v=new
field_components=[];remaining=set(field_faces.tolist())
while remaining:
 seed=remaining.pop();group={seed};queue=[seed]
 while queue:
  i=queue.pop();f=faces[i]
  for e in zip(f,f[1:]+f[:1]):
   for j in owners[tuple(sorted(e))]:
    if j in remaining:remaining.remove(j);group.add(j);queue.append(j)
 field_components.append(len(group))
assert len(field_components)==1,field_components
report={'method':'One connected enamel annulus bounded by measured star outline and inner rim; boundary-only finite-element harmonic depth solve, zero guide fidelity. Relief free controls harmonic with every detected curve pinned. Rear sparse-depth fairing retains low-frequency generated curvature.','field_face_ids':field_faces.tolist(),'field_triangles':field_tri.tolist(),'field_vertices':field['vertices'],'field_boundary_vertices':field['boundary_vertices'],'field_free_vertices':field['free_vertices'],'field_components':field_components,'field_laplacian_rms_per_mm':field['laplacian_rms_per_mm'],'field_laplacian_max_per_mm':field['laplacian_max_abs_per_mm'],'guidance_fidelity_per_mm2':0,'field_interior_crease_edges':0,'max_control_shift_mm':float(np.linalg.norm(v-original,axis=1).max()),'relief':relief}
(OUT/'fairing-targets.json').write_text(json.dumps({'vertices':(v/1000).tolist(),'creases':[[*e,w] for e,w in weights.items()],'field':flags.tolist()},separators=(',',':')))
(OUT/'field-flatness.json').write_text(json.dumps(report,indent=2));print('FAIR_COMPLETE',len(field_faces),'field faces',report['max_control_shift_mm'],'mm maximum control shift',flush=True)
