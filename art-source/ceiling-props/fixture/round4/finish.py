from pathlib import Path
import bpy,math,json,sys
from mathutils import Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'working.blend'));bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene
source=bpy.data.objects['SOURCE_720_generated_painted'];source.hide_render=True;source.hide_set(True)
asset=[o for o in s.objects if o.type=='MESH' and o!=source]
for name in ['DarkArmouredSteel','RecessedFrostedGlass']:
 if name in bpy.data.materials:bpy.data.materials[name].name='ROUND3_'+name
weather=[]
for prefix,name in [('body','Seed720_CleanedGeneratedBeam'),('grille','GeneratedUnderside_ArmouredGrille'),('hardware','RaisedRails_Rivets_GravityFasteners')]:
 o=bpy.data.objects[name];mat=bpy.data.materials.new({'body':'OliveSteel_StructuredWeather','grille':'DarkArmouredSteel','hardware':'RaisedRailSteel'}[prefix]);mat.use_nodes=True;o.data.materials.clear();o.data.materials.append(mat)
 for p in o.data.polygons:p.material_index=0
 nt=mat.node_tree;nodes=nt.nodes;links=nt.links;bs=nodes.get('Principled BSDF');textures={}
 for kind in ['albedo','orm','control','control_orm','no_rust','no_streak']:
  im=bpy.data.images.load(str(R/(prefix+'_'+kind+'.png')));im.colorspace_settings.name='Non-Color' if 'orm' in kind else 'sRGB';im.pack();textures[kind]=im
 albedo=nodes.new('ShaderNodeTexImage');albedo.image=textures['albedo'];links.new(albedo.outputs['Color'],bs.inputs['Base Color'])
 orm=nodes.new('ShaderNodeTexImage');orm.image=textures['orm'];split=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],split.inputs['Color']);links.new(split.outputs['Green'],bs.inputs['Roughness']);links.new(split.outputs['Blue'],bs.inputs['Metallic']);bs.inputs['Specular IOR Level'].default_value=.32
 weather.append((albedo,orm,textures))
glass=bpy.data.objects['RecessedGlass_13mm'];gm=bpy.data.materials.new('RecessedFrostedGlass');gm.use_nodes=True;glass.data.materials.clear();glass.data.materials.append(gm)
for p in glass.data.polygons:p.material_index=0
bs=gm.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.045,.05,.04,1);bs.inputs['Roughness'].default_value=.83;bs.inputs['Emission Strength'].default_value=2.0
tex=gm.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'glass_emission.png'));tex.image.pack();gm.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color'])
bpy.ops.object.select_all(action='DESELECT')
for o in asset:o.hide_render=False;o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=asset[0]
bpy.ops.export_scene.gltf(filepath=str(R/'fixture.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'fixture.blend'))
if '--export-only' in sys.argv:sys.exit(0)
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.seed=0;s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('DarkGreyRoom');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.12,.13,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
m=bpy.data.materials.new('PREVIEW_DarkGreyCeiling');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.065,.070,.072,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.94
bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,.002));plane=bpy.context.object;plane.name='PREVIEW_ONLY_Ceiling';plane.data.materials.append(m)
for name,loc,power,size in [('SoftRoomFill',(-.9,-.6,-1.),18,2.),('MetalEdgeFill',(1,.4,-.35),12,1.)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,-.05))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('PlayerCamera');cam=bpy.data.objects.new('PlayerCamera',d);s.collection.objects.link(cam);s.camera=cam;d.type='PERSP';d.lens=55
views=[('below-2p5m',(0,-.025,-2.55)),('below-close',(0,-.20,-1.35)),('three-quarter',(1.05,-1.15,-1.85)),('grazing',(1.05,-1.15,-.48)),('end-left',(-1.15,-.33,-.37)),('end-right',(1.15,-.33,-.37)),('emissive-off',(0,-.20,-1.35)),('weather-disabled',(0,-.20,-1.35)),('grazing-weather-disabled',(1.05,-1.15,-.48)),('below-2p5m-weather-disabled',(0,-.025,-2.55)),('rust-disabled',(0,-.20,-1.35)),('grazing-rust-disabled',(1.05,-1.15,-.48)),('grazing-streak-disabled',(1.05,-1.15,-.48))]
records=[]
for name,loc in views:
 bs.inputs['Emission Strength'].default_value=0 if name=='emissive-off' else 2.0;disable='weather-disabled' in name
 for albedo,orm,textures in weather:
  kind='control' if disable else ('no_rust' if 'rust-disabled' in name else ('no_streak' if 'streak-disabled' in name else 'albedo'))
  albedo.image=textures[kind];orm.image=textures['control_orm' if disable else 'orm']
 cam.location=loc;cam.rotation_euler=(Vector((0,0,-.05))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/(name+'.png'));bpy.ops.render.render(write_still=True)
 if '--probe-only' in sys.argv:sys.exit(0)
 records.append({'name':name,'path':str(R/(name+'.png')),'camera_blender_m':loc,'target_blender_m':[0,0,-.05],'emission':float(bs.inputs['Emission Strength'].default_value),'all_metal_weather_disabled':disable,'angle_below_ceiling_deg':math.degrees(math.atan2(abs(loc[2]+.05),math.hypot(loc[0],loc[1])))})
for albedo,orm,textures in weather:albedo.image=textures['albedo'];orm.image=textures['orm']
bs.inputs['Emission Strength'].default_value=2
bpy.ops.wm.save_as_mainfile(filepath=str(R/'preview.blend'))
# Unlit feature masks use the exact cameras and geometry for measurements on
# the lit render pairs. They are not beauty renders or exported materials.
def maskmat(prefix=None):
 mat=bpy.data.materials.new('MEASURE_'+str(prefix));mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');nt.links.new(em.outputs[0],out.inputs['Surface']);em.inputs['Color'].default_value=(0,0,0,1)
 if prefix:
  t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/(prefix+'_zones.png')));t.image.colorspace_settings.name='Non-Color';nt.links.new(t.outputs['Color'],em.inputs['Color'])
 return mat
for prefix,o in zip(['body','grille','hardware'],[bpy.data.objects['Seed720_CleanedGeneratedBeam'],bpy.data.objects['GeneratedUnderside_ArmouredGrille'],bpy.data.objects['RaisedRails_Rivets_GravityFasteners']]):o.data.materials.clear();o.data.materials.append(maskmat(prefix))
black=maskmat()
for o in [plane,glass]:o.data.materials.clear();o.data.materials.append(black)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.cycles.samples=8;s.cycles.use_denoising=False
for name,loc in [('zones-close',(0,-.20,-1.35)),('zones-grazing',(1.05,-1.15,-.48)),('zones-2p5m',(0,-.025,-2.55))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,-.05))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/(name+'.png'));bpy.ops.render.render(write_still=True)
(R/'render-settings.json').write_text(json.dumps({'engine':'Cycles CPU','samples':48,'seed':0,'size':[1200,900],'white_secondary_fill_watts':[18,12],'views':records},indent=2));print('RENDERS_COMPLETE',flush=True)
