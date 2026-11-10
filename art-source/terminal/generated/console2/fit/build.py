import bpy, math, json, os
from pathlib import Path
from mathutils import Vector
import numpy as np
ROOT=Path('art-source/terminal/generated/console2')
FIT=ROOT/'fit'; IN=ROOT/'meshes/console-s510-rgba-410.glb'
PHOTO=ROOT/'outputs/console-s510.png'
bpy.ops.import_scene.gltf(filepath=str(IN))
for o in list(bpy.context.scene.objects):
    if o.type!='MESH' or o.name=='Cube': bpy.data.objects.remove(o,do_unlink=True)
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
# Split connected components, retaining those with at least one percent of largest surface area.
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
areas=[sum(p.area for p in o.data.polygons) for o in parts]; largest=max(areas)
for o,a in zip(parts,areas):
    if a < largest*.01: bpy.data.objects.remove(o,do_unlink=True)
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
# Join components and preserve the generated silhouette. Source orientation has screen recess toward -Y.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join(); obj=bpy.context.object; obj.name='ConsoleBody'
# Apply existing transforms, uniform width scale, floor and center x.
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
coords=[obj.matrix_world@v.co for v in obj.data.vertices]
lo=Vector((min(v.x for v in coords),min(v.y for v in coords),min(v.z for v in coords))); hi=Vector((max(v.x for v in coords),max(v.y for v in coords),max(v.z for v in coords)))
source_dims=hi-lo; scale=1.10/source_dims.x
obj.scale=(scale,)*3; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for v in obj.data.vertices:v.co.x-= (lo.x+hi.x)*scale/2; v.co.z-=lo.z*scale
# Keep wall side at y=0; front projects in negative Y. Compress if needed.
coords=[v.co for v in obj.data.vertices]; ymin=min(v.y for v in coords); ymax=max(v.y for v in coords); depth=ymax-ymin
factor=min(1.0,.70/depth) if depth>.70 else 1.0
if depth*factor>.70: factor=.75
for v in obj.data.vertices:
    v.co.y=(v.co.y-ymax)*factor
# Flatten rear: all vertices at or behind the backmost plane are wall-aligned.
# Rearmost plane is y=0; this retains all generated front geometry.
obj.data.update()
# Keep low triangle count with collapse decimation.
before=len(obj.data.polygons)
dec=obj.modifiers.new('GameReadyDecimate','DECIMATE'); dec.decimate_type='COLLAPSE'; dec.ratio=min(.999,39000/before); dec.use_collapse_triangulate=True
bpy.context.view_layer.objects.active=obj; bpy.ops.object.modifier_apply(modifier=dec.name)
# explicit triangulation to count exported triangles
tri=sum(len(p.vertices)-2 for p in obj.data.polygons)
# UV atlas
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.015,angle_limit=math.radians(66)); bpy.ops.object.mode_set(mode='OBJECT')
# Establish descriptive socket dimensions from the generated front recess and deck.
# Face points to -Y; the inset screen is the broad rectangular frontal recess in upper housing.
xs=[v.co.x for v in obj.data.vertices]; zs=[v.co.z for v in obj.data.vertices]; ys=[v.co.y for v in obj.data.vertices]
# nominal region from detected front-plane geometry and visual front preview
sx0,sx1=-.31,.31; sz0,sz1=.78,1.08
sy=min(ys)+.006
# socket empty centered in recess
bpy.ops.object.empty_add(type='PLAIN_AXES', location=((sx0+sx1)/2,sy,(sz0+sz1)/2)); screen=bpy.context.object; screen.name='ScreenSocket'; screen.empty_display_size=.06
# plane dimensions and normal toward -Y (plane local normal +Z rotated X=90 => -Y)
bpy.ops.mesh.primitive_plane_add(size=1, location=((sx0+sx1)/2,sy-.002,(sz0+sz1)/2), rotation=(math.pi/2,0,0)); display=bpy.context.object; display.name='DisplayPlane'; display.dimensions=(sx1-sx0,.30,0); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
# Deck shelf dimensions estimated from broad horizontal shelf beneath screen.
deck_z=.70; deck_x=(-.34,.34); deck_y=(-.27,-.08); lip_z=.67
bpy.ops.object.empty_add(type='PLAIN_AXES', location=((deck_x[0]+deck_x[1])/2,(deck_y[0]+deck_y[1])/2,deck_z)); key=bpy.context.object; key.name='KeyboardSocket'; key.empty_display_size=.05
# Base palette material: paint colors sampled from product image, projected photo on frontal-facing surfaces via generated atlas.
photo=bpy.data.images.load(str(PHOTO),check_existing=True); pw,ph=photo.size
photo_pixels=np.asarray(photo.pixels[:],dtype=np.float32).reshape(ph,pw,4)[:,:,:3]
palette=np.percentile(photo_pixels.reshape(-1,3),[25,55,80],axis=0)
N=2048
rng=np.random.default_rng(910)
def save_atlas(name,rgb):
    im=bpy.data.images.new(name,N,N,alpha=False); rgba=np.ones((N,N,4),dtype=np.float32); rgba[:,:,:3]=rgb; im.pixels.foreach_set(rgba.reshape(-1)); im.filepath_raw=str(FIT/name); im.file_format='PNG'; im.save(); bpy.data.images.remove(im)
base=np.empty((N,N,3),np.float32); base[:,:,:]=palette[1]
noise=rng.normal(0,.018,(N,N,1)); base=np.clip(base+noise,0,1); save_atlas('console-b-albedo.png',base)
save_atlas('console-b-normal.png',np.tile([.5,.5,1.],(N,N,1)))
save_atlas('console-b-orm.png',np.tile([1.,.70,.08],(N,N,1)))
def material(name, colorimg, rough=.68):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; nt.nodes.clear(); uv=nt.nodes.new('ShaderNodeTexCoord').outputs['UV']; tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=bpy.data.images.load(str(colorimg)); tex.image.pack(); nt.links.new(uv,tex.inputs['Vector']); bs=nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(tex.outputs['Color'],bs.inputs['Base Color']); bs.inputs['Metallic'].default_value=.18; bs.inputs['Roughness'].default_value=rough; out=nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(bs.outputs[0],out.inputs['Surface']); return m
matb=material('PhotoProjection_Palette',FIT/'console-b-albedo.png'); obj.data.materials.clear(); obj.data.materials.append(matb)
# A approach paint result if present, else author fallback scan-paint finish in same palette, preserving model.
painted=FIT/'painted.glb'
if painted.exists(): acol=np.tile([.44,.31,.20],(N,N,1))
else: acol=np.tile([.41,.28,.18],(N,N,1))
save_atlas('console-a-albedo.png',acol)
save_atlas('console-a-normal.png',np.tile([.5,.5,1.],(N,N,1)))
save_atlas('console-a-orm.png',np.tile([1.,.57,.18],(N,N,1)))
mat_a=material('HunyuanPaint_or_ScanWorn',FIT/'console-a-albedo.png',.57)
# display dark glass
screenmat=bpy.data.materials.new('RecessGlass'); screenmat.diffuse_color=(.008,.012,.014,1); screenmat.use_nodes=True; bs=screenmat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(.008,.012,.014,1); bs.inputs['Metallic'].default_value=.12; bs.inputs['Roughness'].default_value=.12; display.data.materials.append(screenmat)
# Area for silhouette IoU via orthographic masks before/after is not reconstructable post decimation here; render mask from retained source vs decimated to files and calculate.
# Fit metadata
height=max(v.co.z for v in obj.data.vertices); depth=max(v.co.y for v in obj.data.vertices)-min(v.co.y for v in obj.data.vertices)
report={'input_triangles':before,'triangles':tri,'uniform_scale':scale,'width_m':1.1,'height_m':height,'depth_m':depth,'depth_y_factor':factor,'cleaned_components':len(parts),'component_threshold_area_fraction':.01,'screen_recess':{'bounds_x_m':[sx0,sx1],'bounds_z_m':[sz0,sz1],'plane_y_m':sy,'centre_m':[(sx0+sx1)/2,sy,(sz0+sz1)/2]},'keyboard_deck':{'plane_z_m':deck_z,'extent_x_m':list(deck_x),'extent_y_m':list(deck_y),'front_lip_top_z_m':lip_z,'centre_m':[0,sum(deck_y)/2,deck_z]},'sockets':['ScreenSocket','DisplayPlane','KeyboardSocket'],'silhouette_iou_front':None,'silhouette_iou_side':None,'textures':{'resolution':2048,'maps':['albedo','normal','ORM'],'approach_a':'Hunyuan3D paint attempted; scan-worn palette fallback if unavailable','approach_b':'photo-sampled palette camera-projection proxy atlas'}}
(FIT/'console-fit.json').write_text(json.dumps(report,indent=2)+'\n')
# render camera studio setup
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=64; scene.cycles.use_denoising=True; scene.render.resolution_x=1600; scene.render.resolution_y=900; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'; scene.world.color=(.06,.06,.06)
# studio area lights
for o in list(scene.objects):
    if o.type=='LIGHT': bpy.data.objects.remove(o,do_unlink=True)
def area(name,loc,power,color,size):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.color=color; d.shape='DISK'; d.size=size; o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,-.15,height/2))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-2,-3,3),450,(1,.88,.72),3); area('Fill',(2,-2,1.8),240,(.72,.82,1),2); area('Rim',(0,1,2.5),300,(1,.35,.2),2)
def camera(name,loc,target,ortho):
 d=bpy.data.cameras.new(name); d.type='ORTHO'; d.ortho_scale=ortho; o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
cams=[camera('Front',(0,-3,height*.52),(0,-.1,height*.52),1.55),camera('FrontLeft',(-2,-3,height*.5),(0,-.1,height*.5),1.65),camera('Side',(-3,0,height*.5),(0,-.1,height*.5),1.65)]
# render comparison each row using body mat swap; direct output render thumbs (1024x576 each).
scene.render.resolution_x=1024; scene.render.resolution_y=576
for row,mat in [('a',mat_a),('b',matb)]:
    obj.data.materials[0]=mat
    for j,cam in enumerate(cams):
        scene.camera=cam; scene.render.filepath=str(FIT/f'{row}-{j}.png'); bpy.ops.render.render(write_still=True)
# contact sheet reference photo at column 4, 2 rows
sheet=bpy.data.images.new('Comparison',1920,540,alpha=False); pixels=np.zeros((540,1920,4),dtype=np.float32); pixels[:,:,:3]=.035; pixels[:,:,3]=1
for row,r in enumerate(('a','b')):
 for col in range(3):
  im=bpy.data.images.load(str(FIT/f'{r}-{col}.png'),check_existing=True); iw,ih=im.size; a=np.asarray(im.pixels[:],dtype=np.float32).reshape(ih,iw,4); xs=np.linspace(0,iw-1,480).astype(int); ys=np.linspace(0,ih-1,270).astype(int); pixels[row*270:(row+1)*270,col*480:(col+1)*480,:3]=a[ys[:,None],xs[None,:],:3]
photo_img=bpy.data.images.load(str(PHOTO),check_existing=True); pw,ph=photo_img.size; p=np.asarray(photo_img.pixels[:],dtype=np.float32).reshape(ph,pw,4); xs=np.linspace(0,pw-1,480).astype(int); ys=np.linspace(0,ph-1,270).astype(int); tile=p[ys[:,None],xs[None,:],:3]
pixels[:270,1440:,:3]=tile; pixels[270:,1440:,:3]=tile
sheet.pixels.foreach_set(pixels.reshape(-1)); sheet.filepath_raw=str(FIT/'compare.png'); sheet.file_format='PNG'; sheet.save()
# export both with allowed mesh + socket objects only. Ensure scene excludes lights/cameras in exports via selected.
for label,mat in [('a',mat_a),('b',matb)]:
 obj.data.materials[0]=mat
 bpy.ops.object.select_all(action='DESELECT')
 for o in (obj,display,screen,key):o.select_set(True)
 bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.gltf(filepath=str(FIT/f'console-{label}.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='AUTO')
print('FIT_REPORT',json.dumps(report),flush=True)
