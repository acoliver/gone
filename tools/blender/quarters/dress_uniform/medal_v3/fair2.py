"""Fair fit1's measured controls, including slope-coupled joins and plain rear."""
from pathlib import Path
from collections import defaultdict
import json
import shutil
import numpy as np
from scipy.interpolate import splprep,splev
from scipy.sparse import coo_matrix,diags
from scipy.sparse.linalg import spsolve
SOURCE=Path(__file__).resolve().parent
OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2'
BEFORE=OUT.parent/'fit1'
OUT.mkdir(parents=True,exist_ok=True)
for name in ['sparse-cage.json','features.json','cage-samples.json','raw-arrays.json','raw-lowpass.npz','raw-blender-frame.ply','fit-report.json','camera-match.json']:
 shutil.copy2(BEFORE/name,OUT/name)
d=json.loads((BEFORE/'sparse-cage.json').read_text());old=json.loads((BEFORE/'fairing-targets.json').read_text());v=np.array(old['vertices'])*1000;original=v.copy();faces=d['faces'];count=d['front_face_count'];paths={p['name']:p['vertices'] for p in d['paths']};weights={tuple(sorted(e[:2])):e[2] for e in old['creases']}
# Smooth only the depth of the measured feature paths. X/Z positions, unequal
# spacings, and the independent generated sectors remain unchanged.
spacing={}
for name in ['star_outline','rim_step_0','rim_step_1']:
 ids=paths[name];p=v[ids];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.vstack([p,p[:1]]),axis=0)[:,[0,2]],axis=1))]
 from scipy.interpolate import UnivariateSpline
 # Periodically repeated samples avoid a privileged join in the closed curve.
 xx=np.r_[arc[:-1]-arc[-1],arc[:-1],arc[:-1]+arc[-1]];yy=np.tile(p[:,1],3)
 spline=UnivariateSpline(xx,yy,s=len(xx)*(.065 if name=='star_outline' else .10)**2)
 v[ids,1]=spline(arc[:-1]);spacing[name]={'segment_min_mm':float(np.diff(arc).min()),'segment_max_mm':float(np.diff(arc).max()),'max_depth_change_mm':float(abs(v[ids,1]-original[ids,1]).max())}
# Match each measured branch's terminal depth slope to its surrounding
# measured outline/rim neighbourhood before solving the adjacent surfaces.
from scipy.interpolate import CubicHermiteSpline
terminal_joins={}
boundary_ids=np.array(paths['star_outline']+paths['rim_step_0'])
for name,ids in paths.items():
 if not name.startswith(('star_ridge','star_valley')):continue
 q=v[ids].copy();s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0)[:,[0,2]],axis=1))];end=q[-1];dist=np.linalg.norm(v[boundary_ids][:,[0,2]]-end[[0,2]],axis=1);near=boundary_ids[dist<3.]
 xy=v[near][:,[0,2]]-end[[0,2]];gradient=np.linalg.lstsq(np.c_[xy,np.ones(len(xy))],v[near,1],rcond=None)[0][:2]
 direction=(q[-1]-q[-2])[[0,2]];direction/=np.linalg.norm(direction);slope=float(gradient@direction);start=max(1,int(np.searchsorted(s,s[-1]-2.8)));incoming=(q[start,1]-q[start-1,1])/(s[start]-s[start-1]);curve=CubicHermiteSpline([s[start],s[-1]],[q[start,1],end[1]],[incoming,slope]);v[np.array(ids[start:]),1]=curve(s[start:])
 terminal_joins[name]={'terminal_slope_before':float((q[-1,1]-q[-2,1])/(s[-1]-s[-2])),'terminal_slope_target':slope,'modified_length_mm':float(s[-1]-s[start]),'max_depth_change_mm':float(abs(v[ids,1]-q[:,1]).max())}
# A tapered crease terminates before the outline instead of forming a full
# crease T junction. Semi-sharp outlines become C1 at the subdivision limit.
outline=set(paths['star_outline']);rim0=set(paths['rim_step_0']);rim1=set(paths['rim_step_1'])
for e,w in list(weights.items()):
 if set(e)<=outline:weights[e]=.65
 elif set(e)<=rim0:weights[e]=0.
 elif set(e)<=rim1:weights[e]=.35
for name,ids in paths.items():
 if not name.startswith(('star_ridge','star_valley')):continue
 q=v[ids];s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
 for k,(a,b) in enumerate(zip(ids,ids[1:])):
  mid=(s[k]+s[k+1])/2
  def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
  weights[tuple(sorted((a,b)))]=float(smooth((mid-.7)/1.0)*smooth((s[-1]-mid-.5)/1.3))

def stiffness(tri):
 ids=np.unique(tri);index={int(i):j for j,i in enumerate(ids)};ts=np.array([[index[int(i)] for i in t] for t in tri]);xy=v[ids][:,[0,2]];rr=[];cc=[];vv=[];mass=np.zeros(len(ids))
 for t in ts:
  p=xy[t];a,b=p[1:]-p[0];twice=float(a[0]*b[1]-a[1]*b[0]);area=abs(twice)/2
  g=np.array([[p[1,1]-p[2,1],p[2,0]-p[1,0]],[p[2,1]-p[0,1],p[0,0]-p[2,0]],[p[0,1]-p[1,1],p[1,0]-p[0,0]]])/twice
  local=area*g@g.T
  for j in range(3):
   mass[t[j]]+=area/3
   for k in range(3):rr.append(t[j]);cc.append(t[k]);vv.append(local[j,k])
 return ids,coo_matrix((vv,(rr,cc)),shape=(len(ids),len(ids))).tocsr(),mass

def bending(tri,pins,prior=None,fidelity=0.):
 ids,K,mass=stiffness(tri);Q=K.T@diags(1/mass)@K;lookup={int(i):j for j,i in enumerate(ids)};fixed=np.array(sorted(lookup[i] for i in pins if i in lookup));free=np.setdiff1d(np.arange(len(ids)),fixed);y=v[ids,1].copy();rhs=-Q[free][:,fixed]@y[fixed]
 if prior is not None:
  Q=Q+diags(mass*fidelity);rhs+=mass[free]*fidelity*prior[ids[free]]
 y[free]=spsolve(Q[free][:,free],rhs);v[ids,1]=y
 return {'free_controls':len(free),'fixed_controls':len(fixed),'bending_energy':float(y@(K.T@diags(1/mass)@K)@y)}
tri=np.array(faces[:count]);pins={i for name,ids in paths.items() if name!='rear_transition' for i in ids}
# One global minimum-bending solve couples field and rim slopes through each
# measured curve, rather than solving independent C0 membranes at contacts.
front=bending(tri,pins)
rear=np.array([f for f in faces[count:] if len(f)==3]);ids,K,mass=stiffness(rear);rear_pins=set(paths['rear_transition']);fixed=np.array([j for j,i in enumerate(ids) if i in rear_pins]);free=np.setdiff1d(np.arange(len(ids)),fixed)
# Heavily diffuse sparse generated rear depths before a boundary-constrained
# bending solve. No raw attraction remains to reintroduce the lower patches.
y=original[ids,1].copy();A=diags(mass)+K*16.
for k in range(8):y=spsolve(A,mass*y)
prior=original[:,1].copy();prior[ids]=y
rear_report=bending(rear,rear_pins,prior,.001)
flags=np.array(old['field']);field_tri=tri[np.flatnonzero(flags[:count])];field_ids,field_K,field_mass=stiffness(field_tri)
owners=defaultdict(int)
for t in field_tri:
 for a,b in zip(t,np.roll(t,-1)):owners[tuple(sorted((int(a),int(b))))]+=1
boundary={i for e,n in owners.items() if n==1 for i in e};free=[j for j,i in enumerate(field_ids) if i not in boundary];residual=(field_K@v[field_ids,1])[free]/field_mass[free]
report=json.loads((BEFORE/'field-flatness.json').read_text());report.update({'method':'Global sparse minimum-bending front depth with measured feature depths pinned, semi-sharp outline and terminating fan creases; field/rim joins share the same bending solve. Rear boundary-constrained bending with strongly diffused generated sparse-depth prior. No dense raw projection.','field_laplacian_rms_per_mm':float(np.sqrt(np.mean(residual**2))),'field_laplacian_max_per_mm':float(abs(residual).max()),'max_control_shift_mm':float(np.linalg.norm(v-original,axis=1).max()),'front_bending':front,'rear_bending':rear_report,'feature_depth_smoothing':spacing})
(OUT/'fairing-targets.json').write_text(json.dumps({'vertices':(v/1000).tolist(),'creases':[[*e,w] for e,w in weights.items()],'field':old['field']},separators=(',',':')))
(OUT/'field-flatness.json').write_text(json.dumps(report,indent=2))
(OUT/'fair2-changes.json').write_text(json.dumps({'feature_depth_smoothing':spacing,'terminal_joins':terminal_joins,'maximum_body_control_shift_mm':float(np.linalg.norm(v-original,axis=1).max()),'rear_max_depth_shift_mm':float(abs(v[ids,1]-original[ids,1]).max()),'front_bending':front,'rear_bending':rear_report,'rear_lowpass_diffusion_mm2':128.},indent=2))
print('FAIR2_COMPLETE',json.dumps(json.loads((OUT/'fair2-changes.json').read_text())),flush=True)
