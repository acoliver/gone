import bpy, json
from pathlib import Path
from mathutils import Vector
import numpy as np
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'fit/console-painted.glb'))
body=bpy.data.objects['ConsoleBody']; scene=bpy.context.scene
bpy.context.view_layer.objects.active=body
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
verts=np.array([body.matrix_world@v.co for v in body.data.vertices]); lo=verts.min(0); hi=verts.max(0)
matdata=[]
for m in body.data.materials:
 print('MATERIAL',m.name,flush=True)
 for n in m.node_tree.nodes:
  print(n.name,n.type, 'image='+str(n.image.name if n.type=='TEX_IMAGE' and n.image else None),flush=True)
  if n.type=='TEX_IMAGE' and n.image:
   n.image.filepath_raw=str(OUT/'hunyuan-albedo.png'); n.image.file_format='PNG'; n.image.save()
 matdata.append({'name':m.name,'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]})
meta={'bounds':[lo.tolist(),hi.tolist()],'dimensions':(hi-lo).tolist(),'materials':matdata,'objects':[{ 'name':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'dimensions':list(o.dimensions)} for o in scene.objects]}
(OUT/'mesh-info.json').write_text(json.dumps(meta,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source.blend'))
for o in scene.objects:
 if o!=body:o.hide_render=True
m=bpy.data.materials.new('Silhouette'); m.use_nodes=True; nt=m.node_tree; nt.nodes.clear(); e=nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value=(1,1,1,1); out=nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0],out.inputs[0]); body.data.materials.clear(); body.data.materials.append(m)
d=bpy.data.cameras.new('FrontSilhouette'); d.type='ORTHO'; d.ortho_scale=float(hi[2]-lo[2])*1.08
cam=bpy.data.objects.new('FrontSilhouette',d); scene.collection.objects.link(cam); cam.location=((lo[0]+hi[0])/2,-3,(lo[2]+hi[2])/2); cam.rotation_euler=(Vector(((lo[0]+hi[0])/2,0,(lo[2]+hi[2])/2))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.resolution_x=1024; scene.render.resolution_y=1280; scene.render.resolution_percentage=100; scene.render.film_transparent=True; scene.render.image_settings.color_mode='RGBA'; scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(OUT/'mesh-silhouette.png'); bpy.ops.render.render(write_still=True)
(OUT/'projection.json').write_text(json.dumps({'centre_x':float((lo[0]+hi[0])/2),'centre_z':float((lo[2]+hi[2])/2),'ortho_height':d.ortho_scale,'width':1024,'height':1280}))
