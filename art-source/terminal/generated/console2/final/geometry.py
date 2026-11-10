import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;A=O.parent/'assembly3'
bpy.ops.wm.open_mainfile(filepath=str(A/'console-with-keyboard.blend'))
body=bpy.data.objects['ConsoleBody'];mesh=body.data
r=json.loads((A/'report.json').read_text());before=np.array([v.co[:] for v in mesh.vertices]);old_uv=np.array([l.uv[:] for l in mesh.uv_layers.active.data])
# Recover assembly3's rigid lip selection, excluding its lower-body falloff.
assembly_source=np.load(A/'source-vertices.npy');assembly_delta=np.array(r['deformation']['full_displacement_m']);lip_bottom=r['deformation']['linear_z_falloff_top_m']
rigid_lip=(assembly_source[:,2]>=lip_bottom-1e-7)&np.all(np.abs(before-assembly_source-assembly_delta)<1e-6,axis=1)
underside=[p for p in mesh.polygons if p.normal.z<-.2 and p.center.y<-.64 and rigid_lip[list(p.vertices)].all()]
assert underside
lip_ids=sorted({i for p in underside for i in p.vertices});lip_low=min(lip_ids,key=lambda i:before[i,2]);lip=before[lip_low]
cut=float(lip[2]-.010);deck=float(bpy.data.objects['KeyboardSocket'].location.z);delta=1-deck;s=(cut+delta)/cut
assert .40<cut<.49
# Insert a shared ring so triangles crossing the derivative change follow the exact map.
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=False,clear_outer=False)
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);bm.to_mesh(mesh);bm.free();mesh.update()
source=np.array([v.co[:] for v in mesh.vertices]);uv_before=np.array([l.uv[:] for l in mesh.uv_layers.active.data]);faces=np.array([p.vertices[:] for p in mesh.polygons]);affected=np.any(source[faces,2]<cut-1e-7,axis=1)
after=source.copy();after[:,2]=np.where(source[:,2]<cut,source[:,2]*s,source[:,2]+delta)
for v,p in zip(mesh.vertices,after):v.co=p
mesh.update()
for name in ['DisplayPlane','ScreenSocket','KeyboardSocket','KeyboardBase']:bpy.data.objects[name].location.z+=delta
bpy.context.view_layer.update()
# Reserve the untouched islands, then pack only stretched faces in free atlas space.
S=512;occupied=np.zeros((S,S),bool)
for p in mesh.polygons:
 if affected[p.index]:continue
 q=uv_before[p.loop_start:p.loop_start+3]*S;lo=np.maximum(0,np.floor(q.min(0)).astype(int));hi=np.minimum(S-1,np.ceil(q.max(0)).astype(int))
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5);points=np.stack((xx,yy),axis=-1);d=q[1]-q[0];e=q[2]-q[0];v=points-q[0];det=d[0]*e[1]-d[1]*e[0]
 if abs(det)<1e-12:continue
 u=(v[:,:,0]*e[1]-v[:,:,1]*e[0])/det;w=(d[0]*v[:,:,1]-d[1]*v[:,:,0])/det
 occupied[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=(u>=-.02)&(w>=-.02)&(u+w<=1.02)
for _ in range(4):
 padded=np.pad(occupied,1,constant_values=True);occupied=np.logical_or.reduce([padded[dy:dy+S,dx:dx+S] for dy in range(3) for dx in range(3)])
heights=np.zeros(S,int);best=(0,None)
for y in range(S):
 heights=np.where(~occupied[y],heights+1,0);stack=[]
 for x in range(S+1):
  h=int(heights[x]) if x<S else 0;left=x
  while stack and stack[-1][1]>h:
   oldleft,oldheight=stack.pop();width=x-oldleft;left=oldleft;width2=min(width,oldheight*2);height2=min(oldheight,width*2);area=width2*height2
   if min(width2,height2)>32 and area>best[0]:best=(area,(oldleft,y-height2+1,width2,height2))
  if not stack or stack[-1][1]<h:stack.append((left,h))
assert best[1] is not None
rx,ry,rw,rh=best[1]
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for v in mesh.vertices:v.select=False
for e in mesh.edges:e.select=False
for p in mesh.polygons:p.select=bool(affected[p.index])
bpy.context.tool_settings.mesh_select_mode=(False,False,True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012,area_weight=.25,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
uv=mesh.uv_layers.active;loops=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in mesh.polygons if affected[p.index]]);coords=np.array([uv.data[i].uv[:] for i in loops]);cmin=coords.min(0);extent=np.ptp(coords,axis=0);available=np.array([rw-2,rh-2])/S;factor=float(np.min(available/extent));offset=np.array([rx+1,ry+1])/S+(available-extent*factor)/2
for i,q in zip(loops,coords):uv.data[i].uv=offset+(q-cmin)*factor
fixed=np.concatenate([np.arange(p.loop_start,p.loop_start+p.loop_total) for p in mesh.polygons if not affected[p.index]])
uv_after=np.array([l.uv[:] for l in uv.data]);assert np.array_equal(uv_after[fixed],uv_before[fixed])
actual=np.array([v.co[:] for v in mesh.vertices]);assert np.allclose(actual,after,atol=1e-7,rtol=0);assert np.array_equal(actual[:len(before),:2],before[:,:2])
upper=source[:,2]>=cut;assert np.allclose(actual[upper]-source[upper],[0,0,delta],atol=1e-7,rtol=0)
bm=bmesh.new();bm.from_mesh(mesh);bad=sum(not e.is_manifold for e in bm.edges);bm.free();assert bad==0
screen=bpy.data.objects['DisplayPlane'];centre=sum((screen.matrix_world@v.co for v in screen.data.vertices),Vector())/len(screen.data.vertices)
r={'source':str(A/'console-with-keyboard.blend'),'standing':{'deck_source_z_m':deck,'deck_new_z_m':float(bpy.data.objects['KeyboardSocket'].location.z),'lip_underside_lowest_m':lip.tolist(),'lip_underside_faces':len(underside),'lip_measurement':'Lowest vertex of downward-facing front-lip triangles (normal.z < -0.2, centroid y < -0.64 m) whose vertices belong to assembly3 rigid lip: source z >= 0.478 m and displacement equals assembly3 full in-plane translation within 1 micrometre. Includes rounded ends; excludes the lower-body falloff.','z_cut_m':cut,'delta_m':delta,'lower_body_vertical_scale':s,'height_m':float(np.ptp(actual[:,2])),'screen_centre_m':list(centre),'dimensions_m':np.ptp(actual,axis=0).tolist(),'cut_new_z_m':cut+delta,'original_vertices':len(before),'final_vertices':len(actual),'final_triangles':len(mesh.polygons),'lower_reunwrapped_faces':int(affected.sum()),'upper_uv_loops_exactly_preserved':True,'upper_rigid_translation_verified':True,'xy_exactly_preserved':True,'nonmanifold_edges':bad,'lower_uv_slot_pixels_2048':[int(i*4) for i in best[1]],'bisect_note':'Interpolated UVs on split triangles above cut preserve their existing texture mapping; original fully upper faces retain exact loop values.'},'deck':json.loads((A/'report.json').read_text())['deck']}
r['deck']['plane_z_equals_ax_plus_by_plus_c'][2]+=delta
for p in r['deck']['ray_samples']:p[2]+=delta
np.save(O/'source-vertices.npy',source);np.save(O/'source-faces.npy',faces);np.save(O/'affected-faces.npy',affected);np.save(O/'source-uv.npy',uv_before)
(O/'geometry-report.json').write_text(json.dumps(r,indent=2));print('STANDING',json.dumps(r['standing']),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'deformed.blend'))
print('GEOMETRY_DONE',flush=True)
