import bpy,json,math,sys,shutil,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
from placement import place
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'finish4/console.blend'))
scene=bpy.context.scene;body=bpy.data.objects['ConsoleBody'];display=bpy.data.objects['DisplayPlane'];assets=[body,display,bpy.data.objects['ScreenSocket'],bpy.data.objects['KeyboardSocket']]
sockets={ob.name:[list(r) for r in ob.matrix_world] for ob in assets if ob.type=='EMPTY'}
geometry_before=[tuple(v.co) for v in body.data.vertices]
report={'source_console':'finish4/console.blend','source_keyboard':'kb3/keyboard.blend','textures':json.loads((O/'texture-report.json').read_text()),'sockets_before':sockets}
# Only asset objects survive from the source studio. The review studio is built separately below.
for ob in list(scene.objects):
 if ob not in assets:bpy.data.objects.remove(ob,do_unlink=True)
scene.use_nodes=False;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=10
scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.bake.margin=12;scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False;scene.render.bake.normal_space='TANGENT'
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
mat=bpy.data.materials.new('Assembly colour bake');mat.use_nodes=True;body.data.materials.clear();body.data.materials.append(mat);nt=mat.node_tree;nodes=nt.nodes;links=nt.links;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');links.new(em.outputs[0],out.inputs[0])
def tex(path,space):
 im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name=space;n=nodes.new('ShaderNodeTexImage');n.image=im;return n

def bake(name,space,source=None,kind='EMIT'):
 im=bpy.data.images.new(name,2048,2048,alpha=False);im.colorspace_settings.name=space;target=nodes.new('ShaderNodeTexImage');target.image=im
 for n in nodes:n.select=n==target
 nodes.active=target
 if source is not None:links.new(source,em.inputs[0]);links.new(em.outputs[0],out.inputs[0])
 print('BAKE_START',name,flush=True);bpy.ops.object.bake(type=kind);im.filepath_raw=str(O/(name+'.png'));im.file_format='PNG';im.save();im.pack();print('BAKE_DONE',name,flush=True);return im
albedo=bake('console-albedo','sRGB',tex(O/'paint-resolved.png','sRGB').outputs['Color'])
orm=bake('console-orm','Non-Color',tex(O/'orm-resolved.png','Non-Color').outputs['Color'])
p=nodes.new('ShaderNodeBsdfPrincipled');links.new(p.outputs[0],out.inputs[0]);geo=nodes.new('ShaderNodeNewGeometry');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1500;noise.inputs['Detail'].default_value=1;links.new(geo.outputs['Position'],noise.inputs['Vector']);grain=nodes.new('ShaderNodeBump');grain.inputs['Strength'].default_value=.10;grain.inputs['Distance'].default_value=.00014;links.new(noise.outputs['Fac'],grain.inputs['Height']);chip=tex(O/'chip-mask.png','Non-Color');bump=nodes.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.00018;links.new(chip.outputs['Color'],bump.inputs['Height']);links.new(grain.outputs['Normal'],bump.inputs['Normal']);links.new(bump.outputs['Normal'],p.inputs['Normal']);normal=bake('console-normal','Non-Color',kind='NORMAL')
final=bpy.data.materials.new('Console dusty yellow-green paint and sparse rust');final.use_nodes=True;fn=final.node_tree.nodes;fl=final.node_tree.links;fn.clear();p=fn.new('ShaderNodeBsdfPrincipled');out=fn.new('ShaderNodeOutputMaterial');fl.new(p.outputs[0],out.inputs[0]);p.inputs['Specular IOR Level'].default_value=.10
images={}
for name,im in [('albedo',albedo),('orm',orm),('normal',normal)]:
 n=fn.new('ShaderNodeTexImage');n.image=im;images[name]=n
fl.new(images['albedo'].outputs['Color'],p.inputs['Base Color']);sep=fn.new('ShaderNodeSeparateColor');fl.new(images['orm'].outputs[0],sep.inputs[0]);fl.new(sep.outputs['Green'],p.inputs['Roughness']);fl.new(sep.outputs['Blue'],p.inputs['Metallic']);nm=fn.new('ShaderNodeNormalMap');fl.new(images['normal'].outputs[0],nm.inputs['Color']);fl.new(nm.outputs[0],p.inputs['Normal']);group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');gn=fn.new('ShaderNodeGroup');gn.node_tree=group;fl.new(sep.outputs['Red'],gn.inputs['Occlusion']);body.data.materials[0]=final
assert geometry_before==[tuple(v.co) for v in body.data.vertices],'Console geometry changed'
def export(path,obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 bpy.ops.export_scene.gltf(filepath=str(O/path),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_yup=True)
export('console.glb',assets)
# The separate keyboard is byte-identical to its source local-space export.
shutil.copyfile(O.parent/'kb3/keyboard.glb',O/'keyboard.glb')
key,base=place(O,report)
report['sockets_after']={ob.name:[list(r) for r in ob.matrix_world] for ob in assets if ob.type=='EMPTY'};assert sockets==report['sockets_after'],'Socket transforms changed';report['socket_max_displacement_m']=0;report['console_geometry_unchanged']=True;report['keyboard_geometry_unchanged']=True
export('console-with-keyboard.glb',assets+[base,key])
scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.seed=492;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.5,.5,1);world.node_tree.nodes['Background'].inputs[1].default_value=.16;scene.world=world
# Wall is just behind y=0, leaving the mount face flush and avoiding coplanar surfaces.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,.012,1));wall=bpy.context.object;wall.name='Review rust wall';wall.rotation_euler=(math.pi/2,0,0);wm=bpy.data.materials.new('Matte rust-wall backdrop');wm.use_nodes=True;wn=wm.node_tree.nodes;wl=wm.node_tree.links;ws=wn.get('Principled BSDF');ws.inputs['Roughness'].default_value=.93;noise=wn.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;noise.inputs['Detail'].default_value=3;tc=wn.new('ShaderNodeTexCoord');wl.new(tc.outputs['Object'],noise.inputs['Vector']);ramp=wn.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=(.035,.016,.009,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.16,.064,.031,1);wl.new(noise.outputs['Fac'],ramp.inputs[0]);wl.new(ramp.outputs['Color'],ws.inputs['Base Color']);wall.data.materials.append(wm)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.045));ground=bpy.context.object;ground.name='Review studio floor';gm=bpy.data.materials.new('Neutral floor');gm.use_nodes=True;gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.065,.065,.065,1);gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85;ground.data.materials.append(gm)
for name,loc,power,size in [('Key',(-2,-3,2.4),200,2.5),('Fill',(2,-2,1.8),130,2.3),('Top',(0,-.4,3),55,1.8)]:
 ld=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,-.4,.7))-ob.location).to_track_quat('-Z','Y').to_euler();ld.energy=power;ld.size=size;ld.color=(1,1,1)
centre=Vector((0,(report['deck']['front_y_m']+report['deck']['rear_y_m'])/2,0));a,b,c=report['deck']['plane_z_equals_ax_plus_by_plus_c'];centre.z=b*centre.y+c
views=[('three-quarter',(-1.85,-2.8,1.85),(0,-.36,.67),2.60),('side',(2.7,-.35,.94),(0,-.35,.68),2.50),('operator',report['keyboard']['operator_eye_m'],tuple(centre),None),('keyboard-closeup',(-.48,-1.27,1.12),(0,-.605,.61),.94)]
cams={}
for name,loc,target,ortho in views:
 cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);scene.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.clip_start=.005;cd.clip_end=300
 if ortho is not None:cd.type='ORTHO';cd.ortho_scale=ortho
 else:cd.type='PERSP';cd.lens=18;cd.sensor_width=36
 cams[name]=cam
scene.camera=cams['three-quarter'];report['render']={'engine':'CYCLES','samples':64,'denoising':True,'resolution':[1600,900],'neutral_light_rgb':[1,1,1],'wall_y_m':.012,'views':[v[0] for v in views]};(O/'report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'console-with-keyboard.blend'));print('ASSETS_SAVED',flush=True)
for name,cam in cams.items():
 scene.camera=cam;scene.render.filepath=str(O/(name+'.png'));print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
print('ASSEMBLY_DONE',flush=True)
