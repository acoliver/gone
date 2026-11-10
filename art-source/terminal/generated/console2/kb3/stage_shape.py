import bpy,numpy as np,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent;seed=int(sys.argv[sys.argv.index('--')+1]);D=OUT/f'mesh-{seed}';D.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(OUT/f'shape-{seed}.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Keyboard';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
m=ob.data
if m.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');m.calc_loop_triangles()
v=np.array([v.co[:] for v in m.vertices]);f=np.array([t.vertices[:] for t in m.loop_triangles]);tri=v[f];ar=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2;mean=(tri.mean(1)*ar[:,None]).sum(0)/ar.sum();d=tri-mean;cov=np.einsum('tvi,tvj,t->ij',d,d,ar)/(3*ar.sum());evals,evecs=np.linalg.eigh(cov)
# Level the key-facing surface. Whole-body PCA confuses depth with thickness
# when Hunyuan inflates the unseen back of this thin object.
front=np.array([0,-1,0]);tn=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);tn/=np.maximum(np.linalg.norm(tn,axis=1,keepdims=True),1e-15);visible=(tn@front)>.9
t=tri[visible];a=ar[visible];surface_mean=(t.mean(1)*a[:,None]).sum(0)/a.sum();d=t-surface_mean;surface_cov=np.einsum('tvi,tvj,t->ij',d,d,a)/(3*a.sum());surface_evals,surface_evecs=np.linalg.eigh(surface_cov);normal=surface_evecs[:,0];normal*=1 if normal@front>0 else -1
x=surface_evecs[:,2];x*=1 if x[0]>0 else -1;y=np.cross(normal,x);R=np.stack((x,y,normal));vlevel=v@R.T
lo=vlevel.min(0);hi=vlevel.max(0);sc=np.array([.8/(hi[0]-lo[0]),.8/(hi[0]-lo[0]),.055/(hi[2]-lo[2])]);shift=np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
def fitted(v):return (v@R.T-shift)*sc
vf=fitted(v);low=vf.min(0);high=vf.max(0);xs=np.linspace(low[0],high[0],1025);ys=np.linspace(low[1],high[1],round((high[1]-low[1])/.8*1024)+1)
def height(v,faces):
 bvh=BVHTree.FromPolygons([Vector(p) for p in v],faces,all_triangles=True);h=np.full((len(ys),len(xs)),np.nan,np.float32)
 for j,y in enumerate(ys):
  for i,x in enumerate(xs):
   hit=bvh.ray_cast(Vector((x,y,.2)),Vector((0,0,-1)))
   if hit[0] is not None:h[j,i]=hit[0].z
 return h
print('RAW',seed,len(f),low,high,flush=True);rawh=height(vf,f.tolist());rawfaces=len(f)
mod=ob.modifiers.new('Decimation to 29000 triangles','DECIMATE');mod.ratio=min(1.,29000/len(f));mod.use_collapse_triangulate=True;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name);m=ob.data;m.calc_loop_triangles();f=np.array([t.vertices[:] for t in m.loop_triangles]);v=np.array([v.co[:] for v in m.vertices])
bpy.ops.export_scene.gltf(filepath=str(D/'paint-input.glb'),export_format='GLB',use_selection=True,export_apply=True)
vf=fitted(v);h=height(vf,f.tolist());a=np.isfinite(rawh);b=np.isfinite(h);iou=float((a&b).sum()/(a|b).sum());assert iou>=.97,(seed,iou)
# Set exact requested dimensions after decimation while preserving XY aspect.
lo=vf.min(0);hi=vf.max(0);vf[:,:2]-=(lo[:2]+hi[:2])/2;vf[:,:2]*=.8/(hi[0]-lo[0]);vf[:,2]=(vf[:,2]-lo[2])*.055/(hi[2]-lo[2]);xs=np.linspace(vf[:,0].min(),vf[:,0].max(),1025);ys=np.linspace(vf[:,1].min(),vf[:,1].max(),h.shape[0]);h=height(vf,f.tolist())
for vertex,co in zip(m.vertices,vf):vertex.co=co
m.update();bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(D/'source.blend'));np.savez_compressed(D/'height.npz',height=h,xs=xs,ys=ys)
info={'seed':seed,'eigenvalues':evals.tolist(),'front_surface_eigenvalues':surface_evals.tolist(),'raw_to_levelled':R.tolist(),'dimensions_m':np.ptp(vf,axis=0).tolist(),'triangles':len(f),'raw_triangles':rawfaces,'silhouette_iou':iou,'iou_grid':[len(xs),len(ys)],'front_direction_blender':[0,-1,0],'operator_direction_final':[0,-1,0]};(D/'stage.json').write_text(json.dumps(info,indent=2));print('STAGED',json.dumps(info),flush=True)
