import bpy,bmesh,math,json,subprocess,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;N=2048
bpy.ops.wm.open_mainfile(filepath=str(O/'deformed.blend'))
scene=bpy.context.scene;body=bpy.data.objects['ConsoleBody']
scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=10
bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update()
features=[];angles=[]
for e in bm.edges:
 if len(e.link_faces)!=2:continue
 f,g=e.link_faces;angle=math.acos(max(-1,min(1,f.normal.dot(g.normal))))
 if angle<math.radians(8):continue
 if (g.calc_center_median()-f.calc_center_median()).dot(f.normal)>=0:continue
 a=np.array(e.verts[0].co);b=np.array(e.verts[1].co);count=max(2,int(math.ceil(np.linalg.norm(b-a)/.001))+1)
 features.extend(a[None,:]+np.linspace(0,1,count)[:,None]*(b-a)[None,:]);angles.extend([angle]*count)
bm.free();np.save(O/'convex-features.npy',np.array(features,np.float32));print('FEATURES',len(features),flush=True)
# Rendering and bake setup follows finish3.
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.seed=410
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
scene.render.bake.margin=12;scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False;scene.render.bake.normal_space='TANGENT'
for o in scene.objects:
 if o.type=='MESH' and o!=body:o.hide_render=True
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
m=bpy.data.materials.new('Finish4 object-space paint bake');m.use_nodes=True;body.data.materials.clear();body.data.materials.append(m)
nt=m.node_tree;nodes=nt.nodes;links=nt.links;nodes.clear()
out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');links.new(em.outputs[0],out.inputs[0])
geo=nodes.new('ShaderNodeNewGeometry');uv=nodes.new('ShaderNodeTexCoord')
def bake(name,signal=None,kind='EMIT',floating=False):
 im=bpy.data.images.new(name,N,N,alpha=False,float_buffer=floating);im.colorspace_settings.name='Non-Color'
 target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
 for n in nodes:n.select=n==target
 if signal is not None:links.new(signal,em.inputs[0]);links.new(em.outputs[0],out.inputs[0])
 print('BAKE_START',name,flush=True);bpy.ops.object.bake(type=kind);print('BAKE_END',name,flush=True)
 if floating:np.save(O/(name+'.npy'),np.array(im.pixels[:],np.float32).reshape(N,N,4))
 else:im.filepath_raw=str(O/(name+'.png'));im.file_format='PNG';im.save()
 return im
# Position encoding keeps every axis positive in the float bake.
add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';links.new(geo.outputs['Position'],add.inputs[0]);add.inputs[1].default_value=(.6,.8,.01)
scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';links.new(add.outputs[0],scale.inputs[0]);scale.inputs['Scale'].default_value=1/1.6
bake('surface-position',scale.outputs[0],floating=True)
normaladd=nodes.new('ShaderNodeVectorMath');normaladd.operation='ADD';links.new(geo.outputs['True Normal'],normaladd.inputs[0]);normaladd.inputs[1].default_value=(1,1,1)
normalmul=nodes.new('ShaderNodeVectorMath');normalmul.operation='SCALE';links.new(normaladd.outputs[0],normalmul.inputs[0]);normalmul.inputs['Scale'].default_value=.5
bake('surface-normal',normalmul.outputs[0],floating=True)
value=nodes.new('ShaderNodeValue');value.outputs[0].default_value=1;bake('uv-coverage',value.outputs[0]);ao=bake('console-ao',kind='AO')
subprocess.run(['/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python',str(O/'textures.py')],check=True)
# Bake the emitted, UV-resolved object-space layers into the delivery maps.
def tex(path,noncolor=True):
 im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
 n=nodes.new('ShaderNodeTexImage');n.image=im;return n
albedosource=tex(O/'paint-resolved.png',False)
albedo=bpy.data.images.new('console-albedo',N,N,alpha=False);albedo.colorspace_settings.name='sRGB'
target=nodes.new('ShaderNodeTexImage');target.image=albedo;nodes.active=target;links.new(albedosource.outputs['Color'],em.inputs[0]);links.new(em.outputs[0],out.inputs[0]);print('BAKE_START albedo',flush=True);bpy.ops.object.bake(type='EMIT');albedo.filepath_raw=str(O/'console-albedo.png');albedo.file_format='PNG';albedo.save()
ormsource=tex(O/'orm-resolved.png');orm=bake('console-orm',ormsource.outputs['Color'])
# Surface grain is generated in world metres, independent of UV islands.
p=nodes.new('ShaderNodeBsdfPrincipled');links.new(p.outputs[0],out.inputs[0]);noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1500;noise.inputs['Detail'].default_value=1;links.new(geo.outputs['Position'],noise.inputs['Vector'])
grain=nodes.new('ShaderNodeBump');grain.inputs['Strength'].default_value=.10;grain.inputs['Distance'].default_value=.00014;links.new(noise.outputs['Fac'],grain.inputs['Height'])
chiptex=tex(O/'chip-mask.png');bump=nodes.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.00018;links.new(chiptex.outputs['Color'],bump.inputs['Height']);links.new(grain.outputs['Normal'],bump.inputs['Normal']);links.new(bump.outputs['Normal'],p.inputs['Normal']);normal=bake('console-normal',kind='NORMAL')
final=bpy.data.materials.new('Console worn olive paint finish4');final.use_nodes=True;fn=final.node_tree.nodes;fl=final.node_tree.links;fn.clear();p=fn.new('ShaderNodeBsdfPrincipled');out=fn.new('ShaderNodeOutputMaterial');fl.new(p.outputs[0],out.inputs[0])
def finaltex(im):
 n=fn.new('ShaderNodeTexImage');n.image=im;im.pack();return n
at=finaltex(albedo);fl.new(at.outputs['Color'],p.inputs['Base Color']);ot=finaltex(orm);sep=fn.new('ShaderNodeSeparateColor');sep.mode='RGB';fl.new(ot.outputs['Color'],sep.inputs[0]);fl.new(sep.outputs['Green'],p.inputs['Roughness']);fl.new(sep.outputs['Blue'],p.inputs['Metallic']);nm=fn.new('ShaderNodeNormalMap');tn=finaltex(normal);fl.new(tn.outputs[0],nm.inputs['Color']);fl.new(nm.outputs[0],p.inputs['Normal']);p.inputs['Specular IOR Level'].default_value=.10
group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');gn=fn.new('ShaderNodeGroup');gn.node_tree=group;fl.new(sep.outputs['Red'],gn.inputs['Occlusion']);body.data.materials[0]=final

bpy.ops.wm.save_as_mainfile(filepath=str(O/'baked.blend'))
print('BAKES_DONE',flush=True)
