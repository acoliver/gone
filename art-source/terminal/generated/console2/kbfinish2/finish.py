import bpy,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'uv.blend'))
ob=bpy.data.objects['Keyboard']
for item in list(bpy.data.objects):
 if item!=ob:bpy.data.objects.remove(item,do_unlink=True)
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
mat=bpy.data.materials.new('Keyboard | olive steel, charcoal rubber, worn script');mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.6
images={}
for name,space in [('albedo','sRGB'),('orm','Non-Color'),('normal','Non-Color')]:
 im=bpy.data.images.load(str(OUT/f'keyboard_{name}.png'),check_existing=False);im.colorspace_settings.name=space;im.pack();node=nt.nodes.new('ShaderNodeTexImage');node.name='Keyboard '+name;node.label=name.upper()+' 2048';node.image=im;images[name]=node
nt.links.new(images['albedo'].outputs['Color'],bs.inputs['Base Color'])
sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(images['orm'].outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=1;nt.links.new(images['normal'].outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');ao=nt.nodes.new('ShaderNodeGroup');ao.node_tree=group;nt.links.new(sep.outputs['Red'],ao.inputs['Occlusion'])
ob.data.materials.clear();ob.data.materials.append(mat)
for p in ob.data.polygons:p.material_index=0;p.use_smooth=True
# Correct the main-bank orientation so it reads from the specified -Y operator side.
ob.rotation_euler.z=math.pi;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
coords=np.array([v.co[:] for v in ob.data.vertices]);low=coords.min(0);high=coords.max(0)
base=bpy.data.objects.new('KeyboardBase',None);bpy.context.collection.objects.link(base);base.location=((low[0]+high[0])/2,(low[1]+high[1])/2,low[2]);base.empty_display_type='PLAIN_AXES';base.empty_display_size=.04
worldmatrix=ob.matrix_world.copy();ob.parent=base;ob.matrix_world=worldmatrix
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);base.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.gltf(filepath=str(OUT/'keyboard.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_materials='EXPORT')
report=json.loads((OUT/'report.json').read_text());report.update({'dimensions_m':(high-low).tolist(),'vertices':len(ob.data.vertices),'triangles':len(ob.data.polygons),'material_count':len(ob.data.materials),'base_location_m':list(base.location),'render_engine':'Cycles','samples':64,'denoise':True,'render_resolution':[1600,900],'operator_elevation_degrees':35})
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
# Neutral studio, without geometry or lighting included in the GLB.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=10
# Prefer Metal when Blender exposes an available local device, otherwise CPU is explicit.
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
 prefs.compute_device_type='METAL';prefs.get_devices();devices=[d for d in prefs.devices if d.type=='METAL']
 if devices:
  for device in prefs.devices:device.use=(device.type=='METAL')
  scene.cycles.device='GPU';print('Rendering on Metal',[(d.name,d.type) for d in devices],flush=True)
except TypeError:
 print('Metal not available in this Blender build; using CPU',flush=True)
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.5,.5,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0015));ground=bpy.context.object;ground.name='Studio ground';gm=bpy.data.materials.new('Neutral studio ground');gm.use_nodes=True;gp=gm.node_tree.nodes.get('Principled BSDF');gp.inputs['Base Color'].default_value=(.075,.075,.075,1);gp.inputs['Roughness'].default_value=.9;ground.data.materials.append(gm)
for name,loc,power,size in [('Key',(-.45,-.5,.95),95,1.0),('Fill',(.55,.25,.75),65,.9),('Rim',(-.15,.6,.55),40,.6)]:
 ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(Vector((0,0,.02))-lo.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.shape='DISK';ld.size=size;ld.color=(1,1,1)
def camera(name,loc,orthoscale,target=(0,0,.025)):
 d=bpy.data.cameras.new(name);c=bpy.data.objects.new(name,d);scene.collection.objects.link(c);c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=orthoscale;d.lens=55;d.clip_start=.005;d.clip_end=200;return c
views=[('top',(0,0,1.2),.9),('operator',(0,-.9,.025+.9*math.tan(math.radians(35))),.9),('side',(.95,-.18,.15),.55)]
for name,loc,scale in views:
 scene.camera=camera(name,loc,scale);scene.render.filepath=str(OUT/f'{name}.png');print('RENDER',name,flush=True);bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'keyboard.blend'))
print('DONE',json.dumps({k:report[k] for k in ['dimensions_m','key_count','legend_count','mean_match_error_key_size','max_match_error_key_size']}),flush=True)
