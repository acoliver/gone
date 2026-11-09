from pathlib import Path
import math,sys,json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
mesh_path,out=sys.argv[sys.argv.index('--')+1:]
out=Path(out);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=mesh_path)
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
# Resolve generated yaw before measuring aspect or casting lengthwise grille rays.
import numpy as np
from mathutils import Matrix
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
xy=np.array([[p.x,p.y] for p in points]);values,basis=np.linalg.eigh(np.cov(xy.T));axis=basis[:,-1]
if axis[0]<0:axis=-axis
yaw=math.atan2(axis[1],axis[0]);rotation=Matrix.Rotation(-yaw,4,'Z')
for o in objects:o.matrix_world=rotation@o.matrix_world
bpy.context.view_layer.update()
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(hi+lo)/2;ext=hi-lo;span=max(ext)
source=Path(mesh_path);raw=source.with_name('raw-mesh.glb')
if not raw.exists():
 import shutil
 shutil.copy2(source,raw)
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 bpy.ops.export_scene.gltf(filepath=str(source),export_format='GLB',use_selection=True,export_yup=True,export_materials='EXPORT')
(out/'alignment.json').write_text(json.dumps({'yaw_rotation_degrees':math.degrees(-yaw),'raw_mesh':str(raw),'aligned_mesh':str(source),'oriented_extents_blender':list(ext),'operation':'rigid rotation only; no deformation or rescaling'}))
verts=[];faces=[]
for o in objects:
 off=len(verts);verts.extend(o.matrix_world@v.co for v in o.data.vertices)
 o.data.calc_loop_triangles();faces.extend(tuple(off+i for i in t.vertices) for t in o.data.loop_triangles)
bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True)
xs=[lo.x+ext.x*(.08+.84*i/239) for i in range(240)]
ys=[center.y+ext.y*.38*(i/8-.5)*2 for i in range(9)]
depth=[]
for y in ys:
 line=[]
 for x in xs:
  hit,normal,idx,distance=bvh.ray_cast(Vector((x,y,lo.z-span*.1)),Vector((0,0,1)),span*2)
  line.append(float(hit.z) if hit else None)
 depth.append(line)
profiles={'bottom':depth}
for name,normal_axis,sign in [('front',1,-1),('back',1,1),('top',2,1)]:
 cross_axis=3-normal_axis
 lines=[]
 for j in range(9):
  cross=center[cross_axis]+ext[cross_axis]*.38*(j/8-.5)*2
  line=[]
  for x in xs:
   origin=center.copy();origin.x=x;origin[cross_axis]=cross;origin[normal_axis]=(lo[normal_axis]-span*.1) if sign<0 else (hi[normal_axis]+span*.1)
   direction=Vector((0,0,0));direction[normal_axis]=-sign
   hit,normal,idx,distance=bvh.ray_cast(origin,direction,span*2)
   line.append(float(-sign*hit[normal_axis]) if hit else None)
  lines.append(line)
 profiles[name]=lines
(out/'underside-profile.json').write_text(json.dumps({'x':xs,'y':ys,'z':depth,'profiles':profiles,'bounds_blender':[list(lo),list(hi)],'extents_blender':list(ext)}))
# Conditioning front depicts the underside; display that generated face down for ceiling clay views.
display=Matrix.Rotation(math.pi/2,4,'X')
for o in objects:o.matrix_world=display@o.matrix_world
bpy.context.view_layer.update()
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(hi+lo)/2;ext=hi-lo;span=max(ext)
(out/'display.json').write_text(json.dumps({'rotation_about_blender_x_degrees':90,'reason':'conditioning front is the intended underside; display only, source file unchanged'}))
mat=bpy.data.materials.new('GeneratedClay');mat.diffuse_color=(.32,.36,.38,1);mat.use_nodes=True;sh=mat.node_tree.nodes['Principled BSDF'];sh.inputs['Base Color'].default_value=(.32,.36,.38,1);sh.inputs['Roughness'].default_value=.7
for o in objects:
 o.data.materials.clear();o.data.materials.append(mat)
 for p in o.data.polygons:p.material_index=0;p.use_smooth=True
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=6
s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.22,.22,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
s.view_settings.view_transform='AgX'
for name,rel,power in [('Key',(-1,-2,-3),1000),('Fill',(2,-1,2),800),('Rim',(0,3,-1),500)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power*span*span/4;d.shape='DISK';d.size=span*1.6;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=center+Vector(rel)*span/2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=ext.length*1.15
for name,rel in [('front',(0,-4,-.5)),('three-quarter',(2,-3,-2)),('side',(-4,0,-.2)),('back',(0,4,-.5)),('below',(0,-.01,-4))]:
 cam.location=center+Vector(rel)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 if name=='below':cam.rotation_euler=(0,math.pi,0)
 s.render.filepath=str(out/f'{name}.png');bpy.ops.render.render(write_still=True)
