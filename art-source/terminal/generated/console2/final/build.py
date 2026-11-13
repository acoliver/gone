import bpy,json,math,shutil,numpy as np
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'baked.blend'));scene=bpy.context.scene
report=json.loads((O/'fit-report.json').read_text());report['textures']=json.loads((O/'texture-report.json').read_text());body=bpy.data.objects['ConsoleBody'];display=bpy.data.objects['DisplayPlane'];assets=[body,display,bpy.data.objects['ScreenSocket'],bpy.data.objects['KeyboardSocket']];base=bpy.data.objects['KeyboardBase'];key=bpy.data.objects['Keyboard']
for ob in list(scene.objects):
 if ob not in assets+[base,key]:bpy.data.objects.remove(ob,do_unlink=True)
for ob in assets+[base,key]:ob.hide_render=False
scene.use_nodes=False
shutil.copyfile(O.parent/'assembly3/keyboard.glb',O/'keyboard.glb')
def export(name,obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.export_scene.gltf(filepath=str(O/name),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_yup=True)
export('console.glb',assets);export('console-with-keyboard.glb',assets+[base,key])
scene.render.threads_mode='FIXED';scene.render.threads=10
exec(compile((O/'stage.py').read_text(),str(O/'stage.py'),'exec'))
height=report['standing']['height_m'];front=report['deck']['front_y_m'];eye=report['keyboard']['operator_eye_m']
# All product cameras fit the full standing housing, the operator camera shows its working area.
views=[('front',(0,-3.5,height/2),(0,-.36,height/2),3.40),('three-quarter',(-2.4,-3.6,1.65),(0,-.35,height/2),3.70),('side',(3.5,-1.3,1.50),(0,-.35,height/2),3.40),('operator',eye,(0,-.57,1.28),None)]
cams={}
for name,loc,target,ortho in views:
 cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);scene.collection.objects.link(cam);cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.clip_start=.005;cd.clip_end=300
 if ortho is not None:cd.type='ORTHO';cd.ortho_scale=ortho
 else:cd.type='PERSP';cd.lens=18;cd.sensor_width=36
 cams[name]=cam
# Light targets remain physically above and in front of the now raised deck.
for name,loc,target in [('Key',(-2,-3,3),(0,-.4,1)),('Fill',(2,-2,2.3),(0,-.4,1)),('Top',(0,-.4,3.3),(0,-.4,1))]:
 ob=bpy.data.objects[name];ob.location=loc;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
scene.camera=cams['three-quarter'];bpy.context.view_layer.update();frames={}
for name,cam in cams.items():
 frames[name]={}
 for ob in [body,key,display]:
  p=np.array([list(world_to_camera_view(scene,cam,ob.matrix_world@v.co)) for v in ob.data.vertices]);frames[name][ob.name]={'min':p.min(0).tolist(),'max':p.max(0).tolist()}
for name in ['front','three-quarter','side']:
 for ob in ['ConsoleBody','Keyboard','DisplayPlane']:
  q=frames[name][ob];assert min(q['min'][:2])>=0 and max(q['max'][:2])<=1,(name,ob,q)
for ob in ['Keyboard','DisplayPlane']:
 q=frames['operator'][ob];assert min(q['min'][:2])>=0 and max(q['max'][:2])<=1,(ob,q)
report['render']={'engine':'CYCLES','samples':64,'denoising':True,'resolution':[1600,900],'wall_y_m':0,'floor_z_m':0,'views':[v[0] for v in views],'frames':frames}
(O/'report.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'console-with-keyboard.blend'));print('EXPORTS_DONE',flush=True)
for name,cam in cams.items():
 scene.camera=cam;scene.render.filepath=str(O/(name+'.png'));print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_DONE',name,flush=True)
# Emission-only close-up around the shared stretch ring, with no AO, lights or normals.
mat=bpy.data.materials.new('Seam check albedo only');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'console-albedo.png'));links.new(tex.outputs['Color'],em.inputs[0]);links.new(em.outputs[0],out.inputs[0]);body.data.materials[0]=mat
for ob in scene.objects:
 if ob.type=='MESH' and ob!=body:ob.hide_render=True
cut=report['standing']['cut_new_z_m'];cd=bpy.data.cameras.new('albedo-cut');cam=bpy.data.objects.new('albedo-cut',cd);scene.collection.objects.link(cam);cam.location=(-.70,-1.6,cut+.055);cam.rotation_euler=(Vector((0,-.60,cut))-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=1.35;scene.camera=cam;scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.render.filepath=str(O/'albedo-z-cut.png');bpy.ops.render.render(write_still=True)
print('BUILD_DONE',flush=True)
