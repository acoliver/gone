from pathlib import Path
import bpy, math, json, sys
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'working.blend'))
s=bpy.context.scene
source=bpy.data.objects['SOURCE_720_generated_painted']
source.hide_render=True;source.hide_set(True)
asset=[o for o in s.objects if o.type=='MESH' and o!=source]
steel=bpy.data.materials['OliveSteel_Rebaked720_HatchScans']
nt=steel.node_tree;nodes=nt.nodes;links=nt.links
for n in list(nodes):nodes.remove(n)
out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
for file,socket,space in [('olive_weathered_albedo.png','Base Color','sRGB'),('olive_orm.png',None,'Non-Color'),('720_generated_normal.png',None,'Non-Color')]:
 t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/file));t.image.colorspace_settings.name=space;t.image.pack()
 if socket:links.new(t.outputs['Color'],bs.inputs[socket]);albedo=t
 elif file=='olive_orm.png':
  split=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],split.inputs['Color']);links.new(split.outputs['Green'],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic'])
 else:
  nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.14;links.new(t.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
bs.inputs['Coat Weight'].default_value=.06;bs.inputs['Specular IOR Level'].default_value=.32
bpy.ops.object.select_all(action='DESELECT')
for o in asset:o.select_set(True)
bpy.context.view_layer.objects.active=asset[0]
bpy.ops.export_scene.gltf(filepath=str(R/'fixture.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'fixture.blend'))
if '--export-only' in sys.argv:sys.exit(0)
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('DarkGreyRoom');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.12,.13,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
m=bpy.data.materials.new('PREVIEW_DarkGreyCeiling');m.diffuse_color=(.065,.070,.072,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.065,.070,.072,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.94
bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,.002));plane=bpy.context.object;plane.name='PREVIEW_ONLY_Ceiling';plane.data.materials.append(m)
for name,loc,power,size in [('SoftRoomFill',(-.9,-.6,-1.),18,2.),('MetalEdgeFill',(1,.4,-.35),12,1.)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,-.05))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('PlayerCamera');cam=bpy.data.objects.new('PlayerCamera',d);s.collection.objects.link(cam);s.camera=cam;d.type='PERSP';d.lens=55
views=[('below-2p5m',(0,-.025,-2.55)),('below-close',(0,-.20,-1.35)),('three-quarter',(1.05,-1.15,-1.85)),('end-left',(-1.15,-.33,-.37)),('end-right',(1.15,-.33,-.37)),('emissive-off',(0,-.20,-1.35)),('weather-disabled',(0,-.20,-1.35))]
gs=bpy.data.materials['RecessedFrostedGlass'].node_tree.nodes['Principled BSDF']
records=[]
for name,loc in views:
 gs.inputs['Emission Strength'].default_value=0 if name=='emissive-off' else 2.2
 if name=='weather-disabled':albedo.image=bpy.data.images.load(str(R/'olive_unweathered_control.png'))
 cam.location=loc;cam.rotation_euler=(Vector((0,0,-.05))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/f'{name}.png');bpy.ops.render.render(write_still=True)
 records.append({'name':name,'path':str(R/f'{name}.png'),'camera_blender_m':loc,'target_blender_m':[0,0,-.05],'emission':float(gs.inputs['Emission Strength'].default_value)})
(R/'render-settings.json').write_text(json.dumps({'engine':'Cycles CPU','samples':48,'size':[1200,900],'views':records},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'preview.blend'))
print('RENDERS_COMPLETE',flush=True)
