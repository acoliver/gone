"""Sample sparse controls and feature curves from the frozen generated surface."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.interpolate import LinearNDInterpolator, splprep, splev
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
from scipy.signal import find_peaks

SOURCE=Path(__file__).resolve().parent;ROOT=SOURCE.parents[4];OUT=ROOT/'tmp/issue130-v3/fit1'
OUT.mkdir(parents=True,exist_ok=True)
metrics=json.loads((SOURCE/'frozen-c01-hyseed0-star.json').read_text())
hdata=np.load(SOURCE/'frozen-c01-hyseed0-height.npz')
m=trimesh.load(SOURCE/'frozen-c01-hyseed0.glb',force='mesh');v=np.asarray(m.vertices)
origin=np.r_[metrics['normalization']['raw_body_center_xy'][0],0.,metrics['normalization']['raw_body_center_xy'][1]]
scale=metrics['normalization']['mm_per_raw_unit']/1000
v=np.c_[v[:,0],-v[:,2],v[:,1]];v=(v-origin)*scale*1000
raw=trimesh.Trimesh(v/1000,m.faces,process=False)
center=np.array(metrics['star_center_body_mm']);body=(v[:,2]<(0.455-origin[2])*scale*1000)
front=body&(raw.vertex_normals[:,1]<-.12)&(v[:,1]<0);rear=body&(raw.vertex_normals[:,1]>.12)&(v[:,1]>0)
front_interp=LinearNDInterpolator(v[front][:,[0,2]],v[front,1]);rear_interp=LinearNDInterpolator(v[rear][:,[0,2]],v[rear,1])

def sampled(interp,xy):
 y=np.asarray(interp(xy)).reshape(-1);assert np.isfinite(y).all(),('Sparse surface interpolation miss',xy[~np.isfinite(y)].tolist())
 return np.c_[xy[:,0],y,xy[:,1]]

def spline(points,closed,spacing=.8,smooth=.06):
 points=np.asarray(points);tck,_=splprep(points.T,s=len(points)*smooth**2,per=closed,k=3)
 dense=np.array(splev(np.linspace(0,1,4000,endpoint=not closed),tck)).T
 chain=np.vstack([dense,dense[:1]]) if closed else dense
 arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(chain,axis=0),axis=1))]
 count=max(4,int(np.ceil(arc[-1]/spacing)))
 ss=np.linspace(0,arc[-1],count,endpoint=not closed)
 return np.c_[[np.interp(ss,arc,chain[:,k]) for k in range(3)]].T

# Equal-angle searches locate independent source samples, not profile radii.
angles=np.linspace(0,2*np.pi,120,endpoint=False);axes=np.c_[np.cos(angles),np.sin(angles)]
rad=np.linalg.norm(v[:,[0,2]]-center,axis=1);theta=np.arctan2(v[:,2]-center[1],v[:,0]-center[0])
outer=[]
for angle in angles:
 delta=np.abs(np.angle(np.exp(1j*(theta-angle))))
 ids=np.flatnonzero(body&(delta<np.pi/100));j=ids[np.argmax(rad[ids])];outer.append(v[j])
outer=np.array(outer)
# Filter only angular scan noise. Preserve every generated asymmetry.
outer=np.stack([gaussian_filter1d(outer[:,i],1.4,mode='wrap') for i in range(3)],axis=1)
outer_r=np.linalg.norm(outer[:,[0,2]]-center,axis=1)
side=[]
for offset,interp in [(.9,front_interp),(.27,front_interp),(0,None),(.27,rear_interp),(.9,rear_interp)]:
 if interp is None:side.append(outer.copy());continue
 p=sampled(interp,center+(outer_r-offset)[:,None]*axes)
 p[:,1]=gaussian_filter1d(p[:,1],1.4,mode='wrap');side.append(p)
# The nominal input ray contour supplies every measured star outline sample.
a=np.radians(hdata['angles_degrees']);r=hdata['outline_radius_mm'];outline=spline(sampled(front_interp,center+r[:,None]*np.c_[np.cos(a),np.sin(a)]),True,.65,.045)
features=[{'name':'star_outline','closed':True,'points_mm':outline.tolist()}]
rad_outline=np.linalg.norm(outline[:,[0,2]]-center,axis=1)
outline_angles=np.unwrap(np.arctan2(outline[:,2]-center[1],outline[:,0]-center[0]));outline_angles=np.mod(outline_angles,2*np.pi)
peaks=find_peaks(np.tile(r,3),prominence=1.)[0];peaks=peaks[(peaks>=len(r))&(peaks<2*len(r))]-len(r);assert len(peaks)==5
notches=[]
for x,y in zip(peaks,np.roll(peaks,-1)):
 ids=np.arange(x,y+1 if y>x else y+len(r)+1)%len(r);notches.append(int(ids[r[ids].argmin()]))
h=-hdata['height_mm'];h=gaussian_filter1d(gaussian_filter1d(h,3,axis=0),2,axis=1,mode='wrap');rr=hdata['radii_mm']
central=sampled(front_interp,center[None,:])[0]
for kind,ends,sign in [('ridge',peaks,-1),('valley',notches,1)]:
 for n,end in enumerate(ends):
  raw_samples=[];previous=int(end)
  for radius in np.linspace(r[end],.35,70):
   ri=int(abs(rr-radius).argmin());angular=gaussian_filter1d(-h[ri],3,mode='wrap',order=2)
   candidates=np.arange(end-36,end+37)%len(a);offset=np.minimum(abs(candidates-previous),len(a)-abs(candidates-previous))
   j=int(candidates[np.argmax(sign*angular[candidates]-offset**2*2e-5)]);previous=j
   xy=center+radius*np.array([np.cos(a[j]),np.sin(a[j])]);raw_samples.append(sampled(front_interp,xy[None,:])[0])
  raw_samples=np.vstack([central,np.array(raw_samples)[::-1]])
  q=spline(raw_samples,False,.8,.08);u=np.linspace(0,1,len(q))
  endpoint=outline[np.linalg.norm(outline[:,[0,2]]-raw_samples[-1,[0,2]],axis=1).argmin()]
  q+=(1-u[:,None])**4*(central-q[0])+u[:,None]**6*(endpoint-q[-1]);q[0]=central;q[-1]=endpoint
  features.append({'name':'star_'+kind+'_'+str(n),'closed':False,'points_mm':q.tolist(),'raw_samples_mm':raw_samples.tolist()})
# Locate each rim's rising foot and crest on the raw ray, outside the star.
# Wide star tips meet the rim; the available residual annulus is retained.
rim_r=[[],[]]
for j,angle in enumerate(angles):
 ai=int(round(angle/(2*np.pi)*len(a)))%len(a);lo=max(10.1,r[ai]+.3);hi=outer_r[j]-.9
 assert hi-lo>.2,(j,lo,hi)
 rs=np.arange(lo,hi,.035);xy=center+rs[:,None]*axes[j];yy=-np.asarray(front_interp(xy));assert np.isfinite(yy).all()
 yy=gaussian_filter1d(yy,2);g=np.gradient(yy,rs);crest=int(np.argmax(yy));foot=int(np.argmax(g[:max(2,crest)]))
 first=float(rs[foot]);second=float(rs[crest]);second=max(second,first+.14)
 if second>=hi-.06:second=hi-.06;first=min(first,second-.14)
 rim_r[0].append(first);rim_r[1].append(second)
for k in range(2):rim_r[k]=gaussian_filter1d(rim_r[k],1.2,mode='wrap')
# Keep the measured outline and rim graphs disjoint at contacts.
raw_at_angles=np.interp(angles,a,r,period=2*np.pi)
rim_r[0]=np.maximum(rim_r[0],raw_at_angles+.22)
rim_r[1]=np.maximum(rim_r[1],rim_r[0]+.14)
assert np.all(rim_r[1]<outer_r-.93)
from shapely.geometry import Polygon
star_domain=Polygon(outline[:,[0,2]])
previous=star_domain
for i,rs in enumerate(rim_r):
 search=Polygon(center+rs[:,None]*axes).union(previous.buffer(.4 if i==0 else .24)).buffer(0)
 boundary=search.exterior
 count=int(np.ceil(boundary.length/.65))
 xy=np.array([boundary.interpolate(s).coords[0] for s in np.linspace(0,boundary.length,count,endpoint=False)])
 p=sampled(front_interp,xy);p[:,1]=gaussian_filter1d(p[:,1],1,mode='wrap')
 features.append({'name':'rim_step_'+str(i),'closed':True,'points_mm':p.tolist(),'contact_correction':'At fused star/rim contacts, move the search outward to the source surface outside the preceding measured curve; heights still sample the raw mesh. This prevents crossing controls, rather than retaining conflicting rim labels.'})
 previous=Polygon(xy)
 assert previous.contains(star_domain),('Rim graph crosses star',i)
features.extend([{'name':'outer_silhouette','closed':True,'points_mm':side[2].tolist()},{'name':'rear_transition','closed':True,'points_mm':side[4].tolist()}])
front_free=[];rear_free=[]
from shapely.geometry import Polygon,Point
front_domain=Polygon(side[0][:,[0,2]]);rear_domain=Polygon(side[4][:,[0,2]])
feature_xy=np.vstack([np.array(f['points_mm'])[:,[0,2]] for f in features[:13]])
for z in np.arange(v[:,2].min(),v[body,2].max(),1.3):
 for x in np.arange(-16,16,1.3):
  p=np.array([x,z]);pt=Point(p)
  if front_domain.buffer(-.38).contains(pt) and cKDTree(feature_xy).query(p)[0]>.4:front_free.append(sampled(front_interp,p[None,:])[0].tolist())
  if rear_domain.buffer(-.45).contains(pt):rear_free.append(sampled(rear_interp,p[None,:])[0].tolist())
raw.export(OUT/'raw-blender-frame.ply')
(OUT/'raw-arrays.json').write_text(json.dumps([{'name':'Raw_Frozen_Uniform32mm','vertices':(v/1000).tolist(),'triangles':m.faces.tolist()}],separators=(',',':')))
lowpass=raw.copy();trimesh.smoothing.filter_taubin(lowpass,lamb=.5,nu=.53,iterations=240)
np.savez_compressed(OUT/'raw-lowpass.npz',vertices=lowpass.vertices,faces=m.faces)
report={'chosen':'c01-hyseed0','uniform_scale':scale,'raw_origin':origin.tolist(),'raw_body_width_mm':32.,'raw_triangles':len(m.faces),'budget':10500,'parts':{},'split_body_raw_z':.455,'split_bar_raw_x':.13,'split_bar_lower_raw_z':.80,
 'corrections':'Separate fused body/loop at source height .455; loop/bar lateral junctions at source X +/- .13 above .80. Sparse source sampling, spline fairing, harmonic inter-feature depth; no symmetry, donor repair, analytic star, lathe, or dense raw projection. Suspension receives sparse fitted cages; no invented hardware.',
 'method':'Detected raw contour, five signed-angular-curvature ridges and five valleys sharing the measured deepest central patch. Even arclength controls. Measured source rim-rise/crest and five independent outer/rear transition loops. Constrained front triangulation plus side quad bands; boundary-only enamel solve. Rounded inner convergence.'}
(OUT/'fit-report.json').write_text(json.dumps(report,indent=2))
(OUT/'features.json').write_text(json.dumps({'features':features,'star_center_mm':center.tolist(),'central_point_mm':central.tolist(),'tip_angles_degrees':np.degrees(a[peaks]).tolist(),'notch_angles_degrees':np.degrees(a[notches]).tolist(),'source_metrics':metrics},indent=2))
(OUT/'cage-samples.json').write_text(json.dumps({'side_mm':np.array(side).tolist(),'front_free_mm':front_free,'rear_free_mm':rear_free},separators=(',',':')))
print('PREPARED',len(front_free),len(rear_free),len(outline),flush=True)
