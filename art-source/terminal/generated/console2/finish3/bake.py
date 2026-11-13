import bpy, math, json, time
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent; ROOT=O.parent; N=2048
bpy.ops.wm.open_mainfile(filepath=str(O/'source.blend'))
scene=bpy.context.scene; body=bpy.data.objects['ConsoleBody']; display=bpy.data.objects['DisplayPlane']; socket=bpy.data.objects['ScreenSocket']; key=bpy.data.objects['KeyboardSocket']
for ob in list(scene.objects):
 if ob.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(ob,do_unlink=True)
for ob in (body,display,socket,key):ob.hide_render=False
for polygon in body.data.polygons:polygon.use_smooth=True
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.cycles.seed=410
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.10,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
# Plane is explicitly in X/Z, with its normal facing -Y.
seg=json.loads((O/'screen-segmentation.json').read_text()); left,right=seg['rectangle_m']['x'];bottom,top=seg['rectangle_m']['z']
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
samples=[]
for z in np.linspace(bottom,top,5):
 for x in np.linspace(left,right,5):
  hit,n,face,d=bvh.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
  assert hit is not None, (x,z)
  samples.append([float(x),float(hit.y),float(z)])
plane_y=min(p[1] for p in samples)-.001
mesh=bpy.data.meshes.new('FittedDisplay');mesh.from_pydata([(-(right-left)/2,0,-(top-bottom)/2),((right-left)/2,0,-(top-bottom)/2),((right-left)/2,0,(top-bottom)/2),(-(right-left)/2,0,(top-bottom)/2)],[],[(0,1,2,3)]);mesh.update();display.data=mesh;display.parent=None;display.rotation_mode='XYZ';display.rotation_euler=(0,0,0);display.scale=(1,1,1);display.location=((left+right)/2,plane_y,(top+bottom)/2);socket.parent=None;socket.rotation_mode='XYZ';socket.rotation_euler=(0,0,0);socket.location=display.location
sm=bpy.data.materials.new('Black glossy display glass');sm.use_nodes=True; bs=sm.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.002,.003,.004,1);bs.inputs['Metallic'].default_value=.1;bs.inputs['Roughness'].default_value=.085;bs.inputs['IOR'].default_value=1.5;bs.inputs['Coat Weight'].default_value=.4;display.data.materials.append(sm)
scene.view_layers[0].update()
world_corners=np.array([display.matrix_world@v.co for v in display.data.vertices]);assert np.ptp(world_corners[:,1])<1e-6, 'Display is not axis aligned in X/Z'
assert np.max(np.abs(world_corners[:,1]-plane_y))<1e-6
# Sockets are in final world coordinates; preserve keyboard placement from input.
report={'screen_rectangle_m':{'x':[left,right],'z':[bottom,top],'y':plane_y,'width':right-left,'height':top-bottom},'screen_raycast_samples':samples,'frontmost_surface_y':min(p[1] for p in samples),'plane_offset_m':.001,'silhouette_iou':seg['silhouette_iou'],'screen_height_fraction':seg['screen_centre_height_fraction'],'resolution':2048}
def area(name,loc,power,color,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,-.35,.65))-o.location).to_track_quat('-Z','Y').to_euler();return o
def camera(name,loc,target,width):
 d=bpy.data.cameras.new(name);d.type='ORTHO';d.ortho_scale=width;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
lights=[area('Key',(-2,-3,3),240,(1,.94,.83),2),area('Fill',(2,-2,1.9),140,(.79,.86,1),2.4),area('Rim',(1,.7,2.3),230,(1,.87,.66),1.8)]
cams={
 'front':camera('Front',(0,-3,.6374),(0,-.35,.6374),2.65),
 'three-quarter':camera('ThreeQuarter',(-2,-3,1.65),(0,-.35,.64),2.78),
 'side':camera('Side',(-3,-.35,.65),(0,-.35,.65),2.65),
 'deck-joint':camera('DeckJoint',(-1.2,-2.8,1.04),(0,-.50,.605),1.28),
}
# Ground is only for renders, never included in export.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.name='StudioFloor';fm=bpy.data.materials.new('StudioFloor');fm.diffuse_color=(.035,.042,.05,1);fm.use_nodes=True;fb=fm.node_tree.nodes.get('Principled BSDF');fb.inputs['Base Color'].default_value=(.035,.042,.05,1);fb.inputs['Roughness'].default_value=.85;floor.data.materials.append(fm)
def render(name,cam):
 scene.camera=cam;scene.render.filepath=str(O/(name+'.png'));print('RENDER',name,flush=True);bpy.ops.render.render(write_still=True)

# Save untouched Hunyuan material for the controlled before/after comparison.
original=body.data.materials[0];base_image=next(n.image for n in original.node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
base_image.colorspace_settings.name='sRGB'
m=bpy.data.materials.new('WornPaintBake');m.use_nodes=True;body.data.materials[0]=m;nt=m.node_tree;nt.nodes.clear();nodes=nt.nodes;links=nt.links
out=nodes.new('ShaderNodeOutputMaterial');principled=nodes.new('ShaderNodeBsdfPrincipled');links.new(principled.outputs[0],out.inputs['Surface'])
def node(kind):return nodes.new(kind)
def link(a,b):links.new(a,b)
def mathnode(op,a,b=None):
 n=node('ShaderNodeMath');n.operation=op
 for i,v in enumerate((a,b)):
  if v is not None:
   if hasattr(v,'node'):link(v,n.inputs[i])
   else:n.inputs[i].default_value=v
 return n.outputs[0]
def ramp(src,lo,hi):
 n=node('ShaderNodeValToRGB');n.color_ramp.elements[0].position=float(lo);n.color_ramp.elements[1].position=float(hi);link(src,n.inputs[0]);return n.outputs['Color']
def mix(a,b,factor,blend='MIX'):
 n=node('ShaderNodeMixRGB');n.blend_type=blend
 for v,s in ((factor,n.inputs[0]),(a,n.inputs[1]),(b,n.inputs[2])):
  if hasattr(v,'node'):link(v,s)
  elif isinstance(v,(int,float)):s.default_value=v
  else:s.default_value=v
 return n.outputs[0]
def texture(image,noncolor=False):
 n=node('ShaderNodeTexImage');n.image=image
 if noncolor:image.colorspace_settings.name='Non-Color'
 return n
uv=node('ShaderNodeTexCoord');base=texture(base_image);link(uv.outputs['UV'],base.inputs['Vector']);link(base.outputs['Color'],principled.inputs['Base Color']);principled.inputs['Roughness'].default_value=.62
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
scene.render.bake.margin=12;scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False;scene.render.bake.normal_space='TANGENT'
scene.cycles.samples=16
# Other surfaces must not affect self-AO.
floor.hide_render=True;display.hide_render=True
emission=node('ShaderNodeEmission')
def image(name,noncolor=True):
 im=bpy.data.images.new(name,N,N,alpha=False,float_buffer=name=='surface-position');im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB';return im
def bake(name,kind='EMIT',signal=None,noncolor=True):
 im=image(name,noncolor);target=texture(im);nodes.active=target
 for n in nodes:n.select=n==target
 if signal is not None:link(signal,emission.inputs[0]);link(emission.outputs[0],out.inputs[0])
 else:link(principled.outputs[0],out.inputs[0])
 print('BAKE_START',name,kind,flush=True);t=time.time();bpy.ops.object.bake(type=kind);im.filepath_raw=str(O/(name+'.png'));im.file_format='PNG';im.save();print('BAKE_END',name,time.time()-t,flush=True)
 return im
ao=bake('console-ao','AO');geo=node('ShaderNodeNewGeometry');raw=bake('pointiness-raw',signal=geo.outputs['Pointiness']);ar=np.array(raw.pixels[:],np.float32).reshape(N,N,4)[:,:,0];valid=ar[(ar>.05)&(ar<.99)];q=np.percentile(valid,[50,85,95,99,99.7]);report['pointiness_quantiles']=q.tolist();lo=max(.50005,float(q[0])+.0001);hi=max(lo+.0015,float(q[2]));print('POINTINESS_THRESHOLDS',lo,hi,flush=True)
edge_signal=ramp(geo.outputs['Pointiness'],lo,hi);edge=bake('convex-edge-mask',signal=edge_signal)
exec((O/'edge_bake.py').read_text())
aotex=texture(ao,True);edgetex=texture(edge,True)
# Detail is object-space box projected, one tile per 0.6 metres.
scale=node('ShaderNodeVectorMath');scale.operation='SCALE';link(uv.outputs['Object'],scale.inputs[0]);scale.inputs['Scale'].default_value=1/.6
wear=texture(bpy.data.images.load(str(O/'wear-detail.png')));wear.projection='BOX';wear.projection_blend=.2;link(scale.outputs['Vector'],wear.inputs['Vector'])
noise=node('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=110;noise.inputs['Detail'].default_value=3.5;noise.inputs['Roughness'].default_value=.72;link(uv.outputs['Object'],noise.inputs['Vector'])
chip=mathnode('MULTIPLY',edgetex.outputs['Color'],ramp(noise.outputs['Fac'],.28,.55));chip=ramp(chip,.065,.42)
steel=ramp(mathnode('MULTIPLY',edgetex.outputs['Color'],ramp(noise.outputs['Fac'],.43,.67)),.32,.66)
paint=mix(base.outputs['Color'],wear.outputs['Color'],.35,'MULTIPLY')
# Reuse the finish2 layers without its texture-only joint camouflage.
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
# Long fine broken scuffs follow object coordinates across UV seams.
stretch=node('ShaderNodeVectorMath');stretch.operation='MULTIPLY';link(uv.outputs['Object'],stretch.inputs[0]);stretch.inputs[1].default_value=(35,440,140)
scuffnoise=node('ShaderNodeTexNoise');scuffnoise.inputs['Scale'].default_value=1;scuffnoise.inputs['Detail'].default_value=2;link(stretch.outputs[0],scuffnoise.inputs['Vector'])
scuff=mathnode('MULTIPLY',ramp(scuffnoise.outputs['Fac'],.64,.73),ramp(noise.outputs['Fac'],.45,.63))
chip=mathnode('MAXIMUM',chip,scuff)
paint=mix(paint,tuple(linear(np.array([103,108,73])/255))+(1,),mathnode('MULTIPLY',scuff,.40))
mottle=node('ShaderNodeTexNoise');mottle.inputs['Scale'].default_value=11;mottle.inputs['Detail'].default_value=4;link(uv.outputs['Object'],mottle.inputs['Vector']);mottletint=mix((.45,.50,.35,1),(1.3,1.3,1.1,1),mottle.outputs['Fac']);paint=mix(paint,mottletint,1.,'MULTIPLY')
calibration=node('ShaderNodeMixRGB');calibration.blend_type='MULTIPLY';calibration.inputs[0].default_value=1.;link(paint,calibration.inputs[1]);calibration.inputs[2].default_value=(1,1,1,1);paint=calibration.outputs[0]
under=tuple(linear(np.array([48,50,46])/255))+(1,);bare=tuple(linear(np.array([110,108,104])/255))+(1,)
colour=mix(paint,under,chip);colour=mix(colour,bare,steel)
grime=mathnode('POWER',mathnode('SUBTRACT',1.,aotex.outputs['Color']),1.05)
position=node('ShaderNodeSeparateXYZ');link(uv.outputs['Object'],position.inputs[0]);lower=mathnode('SUBTRACT',1.,ramp(position.outputs['Z'],.03,.43));grime=mathnode('MAXIMUM',grime,mathnode('MULTIPLY',lower,.38));colour=mix(colour,(.008,.011,.004,1),mathnode('MULTIPLY',grime,.78))
# Five small anchored patches, rather than uniform rust speckles.
rust=0.;patches=[]
for x,z,radius in [(-.13,.045,.026),(.13,.06,.023),(-.25,.26,.030),(.12,.19,.022),(-.40,.505,.026),(.40,.515,.024),(-.40,.635,.021)]:
 hit,n,face,d=bvh.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
 assert hit is not None,(x,z)
 pos=hit+n*.001;dist=node('ShaderNodeVectorMath');dist.operation='DISTANCE';link(uv.outputs['Object'],dist.inputs[0]);dist.inputs[1].default_value=pos
 amount=mathnode('SUBTRACT',1.,mathnode('DIVIDE',dist.outputs['Value'],radius));amount=mathnode('MAXIMUM',amount,0.);amount=mathnode('MULTIPLY',amount,ramp(noise.outputs['Fac'],.32,.6));rust=mathnode('MAXIMUM',rust,amount) if hasattr(rust,'node') else amount;patches.append({'centre':list(pos),'radius_m':radius})
rusthalo=ramp(rust,.015,.15);colour=mix(colour,under,rusthalo);rust=ramp(rust,.12,.5);rustcol=mix((.045,.012,.003,1),(.14,.038,.008,1),noise.outputs['Fac']);colour=mix(colour,rustcol,rust)
rough=mix((.62,.62,.62,1),(.4,.4,.4,1),chip);rough=mix(rough,(.4,.4,.4,1),steel);rough=mix(rough,(.75,.75,.75,1),grime);rough=mix(rough,(.75,.75,.75,1),rust)
metal=mathnode('MAXIMUM',mathnode('MULTIPLY',chip,.3),steel);metal=mathnode('MULTIPLY',metal,mathnode('SUBTRACT',1.,rust))
# Normal combines sub-millimetre paint grain and the edges of chipped paint.
bump=node('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.00065;link(wear.outputs['Color'],bump.inputs['Height'])
chipbump=node('ShaderNodeBump');chipbump.invert=True;chipbump.inputs['Strength'].default_value=.35;chipbump.inputs['Distance'].default_value=.0008;link(chip,chipbump.inputs['Height']);link(bump.outputs['Normal'],chipbump.inputs['Normal']);link(chipbump.outputs['Normal'],principled.inputs['Normal']);link(colour,principled.inputs['Base Color']);link(rough,principled.inputs['Roughness']);link(metal,principled.inputs['Metallic'])
paintmasksignal=mathnode('SUBTRACT',1.,mathnode('MAXIMUM',mathnode('MAXIMUM',chip,steel),rust))
paintmask=bake('paint-mask',signal=paintmasksignal)
coverage=bake('uv-coverage',signal=mathnode('ADD',1.,0.))
pm=np.array(paintmask.pixels[:],np.float32).reshape(N,N,4)[:,:,0];cv=np.array(coverage.pixels[:],np.float32).reshape(N,N,4)[:,:,0];av=np.array(ao.pixels[:],np.float32).reshape(N,N,4)[:,:,0]
paint_texels=(pm>.95)&(cv>.99)&(av>.9)
assert np.count_nonzero(paint_texels)>10000
calibrations=[]
for iteration in range(3):
 albedo=bake('console-albedo',signal=colour,noncolor=False)
 pixels=np.array(albedo.pixels[:],np.float32).reshape(N,N,4)[:,:,:3];median=np.median(pixels[paint_texels],axis=0);calibrations.append((median*255).tolist())
 if np.max(np.abs(median*255-np.array([74,80,50])))<=1.5:break
 if iteration<2:
  old=np.array(calibration.inputs[2].default_value[:3]);ratio=linear(np.array([74,80,50])/255)/np.maximum(linear(median),.001);calibration.inputs[2].default_value=tuple(old*ratio)+(1,)
report['paint_albedo_median_srgb_255']=(median*255).tolist();report['paint_texels_measured']=int(np.count_nonzero(paint_texels));report['paint_mask_definition']='UV-covered texels with paint mask >0.95 and self-AO >0.90, excluding chips, steel, rust and deep crevices';report['albedo_calibration_medians_srgb_255']=calibrations
combine=node('ShaderNodeCombineColor');combine.mode='RGB';link(aotex.outputs['Color'],combine.inputs['Red']);link(rough,combine.inputs['Green']);link(metal,combine.inputs['Blue']);orm=bake('console-orm',signal=combine.outputs['Color']);normal=bake('console-normal','NORMAL')
report['rust_patches']=patches;report['bakes']={'ao_samples':16,'edge_mask':'14 mm object-space distance band at actual convex mesh edges; noise-broken chips and steel','tile_m':.6,'box_blend':.2,'base_detail_multiply':.35,'scuffs':'Anisotropic noise, broken by object-space high-frequency noise','lower_area_grime':.38,'roughness':{'paint':.62,'chips':.4,'grime':.75},'normal':'Cycles tangent-space bake of detail and chip bump nodes'}
# Material for glTF: one albedo, one shared ORM, one tangent normal.
final=bpy.data.materials.new('Console worn olive paint');final.use_nodes=True;fn=final.node_tree.nodes;fl=final.node_tree.links;fn.clear();p=fn.new('ShaderNodeBsdfPrincipled');o=fn.new('ShaderNodeOutputMaterial');fl.new(p.outputs[0],o.inputs[0])
def texfinal(im):
 n=fn.new('ShaderNodeTexImage');n.image=im;im.pack();return n
at=texfinal(albedo);fl.new(at.outputs['Color'],p.inputs['Base Color']);ot=texfinal(orm);sep=fn.new('ShaderNodeSeparateColor');sep.mode='RGB';fl.new(ot.outputs['Color'],sep.inputs[0]);fl.new(sep.outputs['Green'],p.inputs['Roughness']);fl.new(sep.outputs['Blue'],p.inputs['Metallic']);normaltex=texfinal(normal);nm=fn.new('ShaderNodeNormalMap');fl.new(normaltex.outputs[0],nm.inputs['Color']);fl.new(nm.outputs[0],p.inputs['Normal'])
# The exporter recognises this named occlusion input and shares the packed ORM image.
group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat');gi=fn.new('ShaderNodeGroup');gi.node_tree=group;fl.new(sep.outputs['Red'],gi.inputs['Occlusion'])
body.data.materials[0]=final;floor.hide_render=False;display.hide_render=False;scene.cycles.samples=64
for name,cam in cams.items():render(name,cam)
for l in lights:l.data.color=(1,.018,.006);l.data.energy={'Key':38,'Fill':12,'Rim':20}[l.name]
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.008
render('red',cams['three-quarter'])
# Restore studio settings in the editable scene.
for l,power,color in zip(lights,[240,140,230],[(1,.94,.83),(.79,.86,1),(1,.87,.66)]):l.data.energy=power;l.data.color=color
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
bpy.ops.object.select_all(action='DESELECT')
for ob in (body,display,socket,key):ob.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(O/'console.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO',export_yup=True)
# Coordinates for the diagnostic outline on the final front render.
from bpy_extras.object_utils import world_to_camera_view
scene.camera=cams['front'];scene.view_layers[0].update();corners=[]
for x,z in [(left,bottom),(right,bottom),(right,top),(left,top)]:
 v=world_to_camera_view(scene,cams['front'],Vector((x,plane_y,z)));corners.append([v.x*1600,(1-v.y)*900])
report['front_render_screen_corners_px']=corners;report['triangles']=sum(len(p.vertices)-2 for p in body.data.polygons);report['dimensions_m']=list(body.dimensions);report['objects']=[ob.name for ob in (body,display,socket,key)];report['geometry']=json.loads((O/'geometry-report.json').read_text());report['keyboard_deck']=json.loads((O/'deck-report.json').read_text());report['incomplete']=[]
(O/'report.json').write_text(json.dumps(report,indent=2));scene.camera=cams['three-quarter'];bpy.ops.wm.save_as_mainfile(filepath=str(O/'console.blend'));print('FINISHED',json.dumps(report),flush=True)
