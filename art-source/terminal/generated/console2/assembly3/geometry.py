import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'assembly/console-with-keyboard.blend'))
body=bpy.data.objects['ConsoleBody'];mesh=body.data
source=json.loads((O.parent/'assembly/report.json').read_text());a,b,c=source['deck']['plane_z_equals_ax_plus_by_plus_c'];front=source['deck']['front_y_m'];rear=source['deck']['rear_y_m'];depth=source['deck']['along_slope_depth_m'];extension=.035;tangent=np.array([0,1,b])/math.sqrt(1+b*b)
original_vertex_count=len(mesh.vertices);original_face_count=len(mesh.polygons)
band_rear=front+.025/math.sqrt(1+b*b)
lip_bottom=.478;falloff=.200

def influence(points):
 y=points[:,1];z=points[:,2]
 # The entire front lip is rigid. Only the front 25 mm of top moves.
 # Below it, front-face displacement is affine in source z, ending 200 mm down.
 lower_front=-.366-.48*np.minimum(z,lip_bottom)+.025
 lower_band=np.clip((lower_front-y)/.008,0,1)
 projected_y=(y+b*(z-a*points[:,0]-c))/(1+b*b)
 lip_band=np.clip((band_rear-projected_y)/(.008/math.sqrt(1+b*b)),0,1)
 t=np.clip((z-lip_bottom)/.010,0,1)
 front_band=(1-t)*lower_band+t*lip_band
 return np.clip((z-(lip_bottom-falloff))/falloff,0,1)*front_band
# Some source side triangles span over half a metre across the falloff. Split
# those coplanar faces locally before proportional editing so the deformation
# is sampled spatially, while their original shape and interpolated UVs stay put.
import sys
sys.path.insert(0,str(O))
from tessellate import local_tessellation
from lip_profile import measure_lip
local_tessellation(mesh,influence,rear)
before=np.array([v.co[:] for v in mesh.vertices]);uv_before=np.array([l.uv[:] for l in mesh.uv_layers.active.data]);faces=np.array([p.vertices[:] for p in mesh.polygons]);protected={name:{'matrix':[list(r) for r in bpy.data.objects[name].matrix_world],'vertices':[v.co[:] for v in bpy.data.objects[name].data.vertices] if bpy.data.objects[name].type=='MESH' else []} for name in ['DisplayPlane','ScreenSocket']}
np.save(O/'source-vertices.npy',before);np.save(O/'source-faces.npy',faces);np.save(O/'source-uv.npy',uv_before)
lip_before=measure_lip(before,faces,(a,b,c))
w=influence(before)
movement=-extension*w[:,None]*tangent[None,:];after=before+movement
for v,p in zip(mesh.vertices,after):v.co=p
mesh.update()
lip_after=measure_lip(np.array([v.co[:] for v in mesh.vertices]),faces,(a,b,c),-extension*tangent)
for old,new in zip(lip_before,lip_after):
 assert abs(old['normal_thickness_mm']-new['normal_thickness_mm'])<.002,(old,new)
 assert abs(old['front_face_angle_from_vertical_deg']-new['front_face_angle_from_vertical_deg'])<.002,(old,new)
assert np.allclose(movement[(before[:,1]<band_rear-.008)&(before[:,2]>=lip_bottom)],-extension*tangent,atol=1e-10)
low=(before[:,2]<lip_bottom-falloff)
assert np.array_equal(before[low],after[low])
front_face=(before[:,2]>.29)&(before[:,2]<.46)&(before[:,1]<-.366-.48*before[:,2]+.010)
linear_expected=(before[front_face,2]-(lip_bottom-falloff))/falloff
assert np.allclose(w[front_face],linear_expected,atol=1e-12)
moved=np.linalg.norm(movement,axis=1)>1e-10;affected=np.any(moved[faces],axis=1)
# Principal stretches of each triangle's local deformation, excluding no faces.
def bases(v):
 p=v[faces];e1=p[:,1]-p[:,0];e2=p[:,2]-p[:,0];length=np.linalg.norm(e1,axis=1);x=e1/length[:,None];xp=(x*e2).sum(1);yp=np.linalg.norm(e2-x*xp[:,None],axis=1);m=np.zeros((len(p),2,2));m[:,0,0]=length;m[:,0,1]=xp;m[:,1,1]=yp;return m
stretch=np.linalg.svd(bases(after)@np.linalg.inv(bases(before)),compute_uv=False);maximum=float(stretch.max())
# Re-unwrap the affected faces into unused atlas space. Untouched UV loops
# retain their exact coordinates. A raster of those fixed triangles reserves
# padding before the affected-only projected charts are packed into a free slot.
S=512;occupied=np.zeros((S,S),bool)
for triangle in uv_before.reshape(-1,3,2)[~affected]:
 q=triangle*S;lo=np.maximum(0,np.floor(q.min(0)).astype(int));hi=np.minimum(S-1,np.ceil(q.max(0)).astype(int))
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
 points=np.stack((xx,yy),axis=-1);d=q[1]-q[0];e=q[2]-q[0];r=points-q[0];det=d[0]*e[1]-d[1]*e[0]
 u=(r[:,:,0]*e[1]-r[:,:,1]*e[0])/det;v=(d[0]*r[:,:,1]-d[1]*r[:,:,0])/det
 occupied[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=(u>=-.02)&(v>=-.02)&(u+v<=1.02)
for _ in range(4):
 padded=np.pad(occupied,1,constant_values=True);occupied=np.logical_or.reduce([padded[dy:dy+S,dx:dx+S] for dy in range(3) for dx in range(3)])
heights=np.zeros(S,int);best=(0,None)
for y in range(S):
 heights=np.where(~occupied[y],heights+1,0);stack=[]
 for x in range(S+1):
  h=int(heights[x]) if x<S else 0;left=x
  while stack and stack[-1][1]>h:
   oldleft,oldheight=stack.pop();width=x-oldleft;left=oldleft
   # Keep the slot's aspect moderate so selected charts retain useful density.
   width2=min(width,oldheight*2);height2=min(oldheight,width*2)
   area=width2*height2
   if min(width2,height2)>32 and area>best[0]:best=(area,(oldleft,y-height2+1,width2,height2))
  if not stack or stack[-1][1]<h:stack.append((left,h))
assert best[1] is not None,'No atlas slot for local unwrap'
rx,ry,rw,rh=best[1];print('UV_FREE_SLOT',best,flush=True)
bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();bm.select_mode={'FACE'};layer=bm.loops.layers.uv.active
for f in bm.faces:f.select_set(False)
for e in bm.edges:e.select_set(False)
for v in bm.verts:v.select_set(False)
for f in bm.faces:
 if affected[f.index]:f.select_set(True)
 for l in f.loops:l[layer].pin_uv=False
bm.select_flush_mode();bm.to_mesh(mesh);bm.free();bpy.context.tool_settings.mesh_select_mode=(False,False,True)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
pinned=0
if affected.any():
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012,area_weight=.25,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
 uv=mesh.uv_layers.active
 selectedloops=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in mesh.polygons if affected[p.index]])
 coords=np.array([uv.data[i].uv[:] for i in selectedloops]);cmin=coords.min(0);extent=np.ptp(coords,axis=0)
 available=np.array([rw-2,rh-2])/S;factor=float(np.min(available/extent));offset=np.array([rx+1,ry+1])/S+(available-extent*factor)/2
 for i,q in zip(selectedloops,coords):uv.data[i].uv=offset+(q-cmin)*factor
uv_after=np.array([l.uv[:] for l in mesh.uv_layers.active.data]);unchangedloops=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in mesh.polygons if not affected[p.index]])
assert np.array_equal(uv_before[unchangedloops],uv_after[unchangedloops]),'Unchanged face UVs moved'
assert uv_after.min()>0 and uv_after.max()<1
np.save(O/'unwrapped-uv.npy',uv_after)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh)
nonmanifold=sum(not e.is_manifold for e in bm.edges);boundary=sum(e.is_boundary for e in bm.edges);bm.free();assert nonmanifold==boundary==0
for name,data in protected.items():
 ob=bpy.data.objects[name];assert data['matrix']==[list(r) for r in ob.matrix_world]
 if data['vertices']:assert data['vertices']==[v.co[:] for v in ob.data.vertices]
assert np.array_equal(after[before[:,2]>=.625],before[before[:,2]>=.625])
assert np.array_equal(after[(before[:,1]>=rear)&(before[:,2]>=lip_bottom)],before[(before[:,1]>=rear)&(before[:,2]>=lip_bottom)])
front2=front-extension*tangent[1];tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons]);samples=[]
for y in np.linspace(front2+.012,rear-.010,5):
 for x in np.linspace(-.39,.39,5):
  h,n,f,d=tree.ray_cast(Vector((float(x),float(y),.9)),Vector((0,0,-1)));assert h is not None;samples.append(list(h))
p=np.array(samples);A=np.c_[p[:,:2],np.ones(25)];fit=np.linalg.lstsq(A,p[:,2],rcond=None)[0];res=p[:,2]-A@fit;flat=float(np.ptp(res)*1000);assert flat<=1.5,flat
# Measure the rear transitions across the new keyboard width independently.
rears=[]
normal=Vector((-fit[0],-fit[1],1)).normalized()
for x in np.linspace(-.36,.36,13):
 end=None
 for y in np.linspace(-.60,-.51,901):
  h,n,f,d=tree.ray_cast(Vector((float(x),float(y),.9)),Vector((0,0,-1)))
  if h is None or abs(h.z-(fit[0]*x+fit[1]*y+fit[2]))>.0006 or n.dot(normal)<.98:break
  end=float(y)
 rears.append(end)
report={'source':'assembly/console-with-keyboard.blend','deformation':{'method':'Rigid front lip and front 25 mm top band, in-plane 35 mm translation; front-face falloff linear in source z over 200 mm, local linear side blend; no radial or cubic falloff','front_band_along_slope_m':.025,'linear_z_falloff_height_m':falloff,'linear_z_falloff_top_m':lip_bottom,'linear_z_falloff_bottom_m':lip_bottom-falloff,'below_falloff_unchanged':True,'front_face_linear_z_verified_vertices':int(front_face.sum()),'extension_along_slope_m':extension,'full_displacement_m':(-extension*tangent).tolist(),'source_vertices':original_vertex_count,'source_triangles':original_face_count,'vertices_after_local_tessellation':len(before),'triangles_after_local_tessellation':len(faces),'moved_vertices':int(moved.sum()),'affected_faces':int(affected.sum()),'max_triangle_principal_stretch_factor':maximum,'stretch_p50_p95_p99':np.percentile(stretch[affected,0],[50,95,99]).tolist(),'locally_reunwrapped_faces':int(affected.sum()),'local_uv_slot_pixels_2048':[int(v*4) for v in best[1]],'untouched_face_uvs_unchanged':True,'nonmanifold_edges':nonmanifold,'boundary_edges':boundary,'head_vertices_unchanged':True,'behind_deck_above_lip_vertices_unchanged':True},'lip_profile':{'measurement':'Thickness normal to the deck at source y=-0.680 m; front-face least-squares angle from vertical at source z=0.510..0.528 m. After samples translated by the exact in-plane extension.','before':lip_before,'after':lip_after,'profile_preserved':True},'protected_objects_before':protected,'protected_objects_unchanged':True,'deck':{'plane_z_equals_ax_plus_by_plus_c':fit.tolist(),'ray_samples':samples,'flatness_peak_to_peak_mm':flat,'front_y_m':float(front2),'rear_y_m':rear,'rear_boundary_samples_y_m':rears,'along_slope_depth_m':float((rear-front2)*math.sqrt(1+fit[1]**2)),'slope_degrees':math.degrees(math.atan(math.hypot(*fit[:2])))}}
(O/'geometry-report.json').write_text(json.dumps(report,indent=2));np.save(O/'affected-faces.npy',affected);print('GEOMETRY_REPORT',json.dumps({k:v for k,v in report.items() if k!='protected_objects_before'}),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'deformed.blend'))
