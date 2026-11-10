import bpy, bmesh, math, json, time, subprocess
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent;OLD=O.parent/'finish3';N=2048
bpy.ops.wm.open_mainfile(filepath=str(OLD/'console.blend'))
scene=bpy.context.scene;body=bpy.data.objects['ConsoleBody'];display=bpy.data.objects['DisplayPlane']
assets=[body,display,bpy.data.objects['ScreenSocket'],bpy.data.objects['KeyboardSocket']]
sockets={o.name:[list(row) for row in o.matrix_world] for o in assets if o.type=='EMPTY'}
report={'source':'finish3/console.blend','sockets_before':sockets,'resolution':N}
def bvh():return BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
before=bvh()
# Fill the recessed front profile by extending the head face into the sloped deck.
# This deformation preserves the closed mesh and its existing UV atlas.
changed=[]
for v in body.data.vertices:
 x,y,z=v.co
 if .600<z<.710 and y<-.43:
  sample_x=max(-.42,min(.42,x))
  reference=before.ray_cast(Vector((sample_x,-2,.680)),Vector((0,1,0)))[0]
  front=before.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))[0]
  if front is None:continue
  target=reference.y+.13*(z-.680)
  radius=.006
  h=max(radius-abs(front.y-target),0)/radius
  filled=min(front.y,target)-h*h*radius*.25
  upper=max(0,min(1,(.710-z)/.015));upper=upper*upper*(3-2*upper)
  lateral=max(0,min(1,(.485-abs(x))/.06));lateral=lateral*lateral*(3-2*lateral)
  depth=max(0,min(1,1-(y-front.y)/.045));depth=depth*depth*(3-2*depth)
  new=y+(filled-front.y)*upper*lateral*depth
  if new<y-1e-7:v.co.y=new;changed.append([int(v.index),float(y-new)])
# Remove the measured raised scan strip on the right deck, retaining its intended slope.
body.data.update();right_smoothed=[]
for v in body.data.vertices:
 x,y,z=v.co
 if x>.405 and -.682<y<-.519 and .545<z<.642 and v.normal.z>.45:
  target=.00025930161*x+.4948926607*y+.8868393254
  if z<=target:continue
  weight=max(0,min(1,(x-.405)/.035));weight=weight*weight*(3-2*weight)
  weight*=max(0,min(1,(y+.682)/.012))*max(0,min(1,(-.519-y)/.008))
  delta=(z-target)*weight;v.co.z-=delta;right_smoothed.append(float(delta))
body.data.update();bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
report['right_deck_smoothing']={'vertices':len(right_smoothed),'max_removed_height_mm':max(right_smoothed)*1000}
for p in body.data.polygons:p.use_smooth=True
bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update()
report['geometry_fill']={'moved_vertices':len(changed),'maximum_outward_fill_mm':max(a[1] for a in changed)*1000,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'triangles':len(body.data.polygons)}
assert report['geometry_fill']['nonmanifold_edges']==0
features=[];angles=[]
for e in bm.edges:
 if len(e.link_faces)!=2:continue
 f,g=e.link_faces;angle=math.acos(max(-1,min(1,f.normal.dot(g.normal))))
 if angle<math.radians(8):continue
 if (g.calc_center_median()-f.calc_center_median()).dot(f.normal)>=0:continue
 a=np.array(e.verts[0].co);b=np.array(e.verts[1].co);count=max(2,int(math.ceil(np.linalg.norm(b-a)/.001))+1)
 features.extend(a[None,:]+np.linspace(0,1,count)[:,None]*(b-a)[None,:]);angles.extend([angle]*count)
bm.free();np.save(O/'convex-features.npy',np.array(features,np.float32));print('FEATURES',len(features),flush=True)
after=bvh();profiles=[]
for x in np.round(np.arange(-.4,.401,.05),4):
 row={'x':float(x),'front':[],'above_front':[]}
 for z in np.linspace(.60,.78,181):
  h,n,f,d=after.ray_cast(Vector((x,-2,z)),Vector((0,1,0)));row['front'].append([float(z),float(h.y)])
  h,n,f,d=after.ray_cast(Vector((x,-2,z+1.2)),Vector((0,1,-.8)).normalized())
  if h:row['above_front'].append(list(h))
 profiles.append(row)
report['junction_after_profiles']=profiles
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
for o in scene.objects:
 if o.type=='MESH':o.hide_render=False
scene.cycles.samples=64
for name,loc,power in [('Key',(-2,-3,1.6),180),('Fill',(2,-2,1.2),110),('Rim',(1,.7,1.3),45)]:
 light=bpy.data.objects[name];light.location=loc;light.data.energy=power;light.rotation_euler=(Vector((0,-.35,.65))-light.location).to_track_quat('-Z','Y').to_euler()
report['roof_diagnosis']={'finish3_roof_texel_srgb_255':[77,83,52],'pale_texels_found':0,'cause':'Top-heavy studio lighting and dielectric highlights, not missing roof paint. All faces used the baked olive material.','correction':'Shared world-space olive paint on every surface; specular IOR level 0.10; lower studio light elevations and weaker rim.'}
cams={name:bpy.data.objects[obj] for name,obj in [('front','Front'),('three-quarter','ThreeQuarter'),('side','Side'),('deck-joint','DeckJoint')]}
cams['three-quarter'].location=(-2,-3,2.15);cams['three-quarter'].data.ortho_scale=3.10;cams['three-quarter'].rotation_euler=(Vector((0,-.35,.68))-cams['three-quarter'].location).to_track_quat('-Z','Y').to_euler()
cams['deck-joint'].location=(-.95,-2.8,1.28);cams['deck-joint'].rotation_euler=(Vector((0,-.52,.64))-cams['deck-joint'].location).to_track_quat('-Z','Y').to_euler();cams['deck-joint'].data.ortho_scale=1.34
# Albedo-only view uses emission, so lighting and normals cannot hide colour seams.
cdata=bpy.data.cameras.new('AlbedoShelf');cdata.type='ORTHO';cdata.ortho_scale=1.33;cam=bpy.data.objects.new('AlbedoShelf',cdata);scene.collection.objects.link(cam);cam.location=(-.82,-2.5,1.62);cam.rotation_euler=(Vector((0,-.55,.605))-cam.location).to_track_quat('-Z','Y').to_euler();cams['albedo-shelf']=cam
report['sockets_after']={o.name:[list(row) for row in o.matrix_world] for o in assets if o.type=='EMPTY'};assert report['sockets_before']==report['sockets_after'];report['socket_max_displacement_m']=0
bpy.ops.object.select_all(action='DESELECT')
for o in assets:o.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(O/'console.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_yup=True)
scene.camera=cams['three-quarter'];bpy.ops.wm.save_as_mainfile(filepath=str(O/'console.blend'))
(O/'report.json').write_text(json.dumps(report,indent=2));print('ASSETS_SAVED',flush=True)
for name,cam in cams.items():
 scene.camera=cam
 if name=='albedo-shelf':
  em=fn.new('ShaderNodeEmission');fl.new(at.outputs['Color'],em.inputs[0]);fl.new(em.outputs[0],out.inputs[0]);scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
 scene.render.filepath=str(O/(name+'.png'));print('RENDER_START',name,flush=True);bpy.ops.render.render(write_still=True);print('RENDER_END',name,flush=True)
print('FINISH4_DONE',flush=True)
