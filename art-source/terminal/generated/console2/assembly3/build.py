import bpy,json,math,sys,shutil,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from placement import place
bpy.ops.wm.open_mainfile(filepath=str(O/'baked.blend'))
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=10;scene.cycles.device='CPU'
body=bpy.data.objects['ConsoleBody'];display=bpy.data.objects['DisplayPlane'];assets=[body,display,bpy.data.objects['ScreenSocket'],bpy.data.objects['KeyboardSocket']]
key=bpy.data.objects['Keyboard'];base=bpy.data.objects['KeyboardBase']
for ob in list(scene.objects):
 if ob not in assets+[key,base]:bpy.data.objects.remove(ob,do_unlink=True)
for ob in assets+[key,base]:ob.hide_render=False
scene.use_nodes=False
report=json.loads((O/'geometry-report.json').read_text());report['textures']=json.loads((O/'texture-report.json').read_text());key,base=place(O,report)
# The standalone keyboard remains byte-identical in local coordinates.
shutil.copyfile(O.parent/'kb3/keyboard.glb',O/'keyboard.glb')
for name,data in report['protected_objects_before'].items():
 ob=bpy.data.objects[name];assert data['matrix']==[list(r) for r in ob.matrix_world]
 if data['vertices']:assert data['vertices']==[list(v.co) for v in ob.data.vertices]
report['keyboard_local_geometry_unchanged']=True
report['keyboard_socket']={'location_m':list(bpy.data.objects['KeyboardSocket'].location),'matrix':[list(r) for r in bpy.data.objects['KeyboardSocket'].matrix_world]}
def export(path,obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 bpy.ops.export_scene.gltf(filepath=str(O/path),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_yup=True)
export('console.glb',assets);export('console-with-keyboard.glb',assets+[base,key])
scene.cycles.device='CPU'
scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.seed=492;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.5,.5,1);world.node_tree.nodes['Background'].inputs[1].default_value=.16;scene.world=world
# The back mount and feet meet the wall and steel floor at their reference planes.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,1));wall=bpy.context.object;wall.name='Review rust wall';wall.rotation_euler=(math.pi/2,0,0);wm=bpy.data.materials.new('Matte rust-wall backdrop');wm.use_nodes=True;wn=wm.node_tree.nodes;wl=wm.node_tree.links;ws=wn.get('Principled BSDF');ws.inputs['Roughness'].default_value=.93;noise=wn.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;noise.inputs['Detail'].default_value=3;tc=wn.new('ShaderNodeTexCoord');wl.new(tc.outputs['Object'],noise.inputs['Vector']);ramp=wn.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.035,.016,.009,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.16,.064,.031,1);wl.new(noise.outputs['Fac'],ramp.inputs[0]);wl.new(ramp.outputs['Color'],ws.inputs['Base Color']);ws.inputs['Metallic'].default_value=.42;wall.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));ground=bpy.context.object;ground.name='Review dark steel floor';gm=bpy.data.materials.new('Dark worn steel floor');gm.use_nodes=True;gn=gm.node_tree.nodes;gl=gm.node_tree.links;gs=gn['Principled BSDF'];gs.inputs['Metallic'].default_value=.75;gs.inputs['Roughness'].default_value=.78
noise=gn.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7;noise.inputs['Detail'].default_value=3;tc=gn.new('ShaderNodeTexCoord');gl.new(tc.outputs['Object'],noise.inputs['Vector']);ramp=gn.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.010,.014,.018,1);ramp.color_ramp.elements[1].color=(.034,.040,.045,1);gl.new(noise.outputs['Fac'],ramp.inputs[0]);gl.new(ramp.outputs['Color'],gs.inputs['Base Color']);grain=gn.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=220;gl.new(tc.outputs['Object'],grain.inputs['Vector']);bump=gn.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.0003;gl.new(grain.outputs['Fac'],bump.inputs['Height']);gl.new(bump.outputs['Normal'],gs.inputs['Normal']);ground.data.materials.append(gm)
for name,loc,power,size in [('Key',(-2,-3,2.4),200,2.5),('Fill',(2,-2,1.8),130,2.3),('Top',(0,-.4,3),55,1.8)]:
 ld=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,-.4,.7))-ob.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size;ld.color=(1,1,1)
centre=Vector((0,(report['deck']['front_y_m']+report['deck']['rear_y_m'])/2,0));a,b,c=report['deck']['plane_z_equals_ax_plus_by_plus_c'];centre.z=b*centre.y+c
views=[('three-quarter',(-1.85,-2.8,1.85),(0,-.36,.67),2.60),('side',(2.7,-.35,.94),(0,-.35,.68),2.50),('operator',report['keyboard']['operator_eye_m'],tuple(centre),None),('keyboard-closeup',(-.58,-1.42,1.13),(0,-.641,.59),1.18)]
cams={}
for name,loc,target,ortho in views:
 cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);scene.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.clip_start=.005;cd.clip_end=300
 if ortho is not None:cd.type='ORTHO';cd.ortho_scale=ortho
 else:cd.type='PERSP';cd.lens=18;cd.sensor_width=36
 cams[name]=cam
scene.camera=cams['three-quarter'];bpy.context.view_layer.update();report['render']={'engine':'CYCLES','device':'CPU','device_note':'Metal command buffer was discarded during GPU recovery; rendered all views on CPU.','samples':64,'denoising':True,'resolution':[1600,900],'neutral_light_rgb':[1,1,1],'wall_y_m':0,'floor_z_m':0,'views':[v[0] for v in views]};report['render']['floor_material']='Dark worn steel, metallic 0.75';report['render']['wall_material']='Rusty steel, metallic 0.42';(O/'report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'console-with-keyboard.blend'));print('ASSETS_SAVED',flush=True)
for name,cam in cams.items():
 scene.camera=cam;scene.render.filepath=str(O/(name+'.png'));print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
print('ASSEMBLY_DONE',flush=True)
