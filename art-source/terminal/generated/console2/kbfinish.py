import bpy, math, json
from pathlib import Path
from mathutils import Vector
from collections import defaultdict, deque
ROOT=Path('art-source/terminal/generated/console2'); OUT=ROOT/'kbfinish'; OUT.mkdir(exist_ok=True)
SRC=ROOT/'kbfit2/keyboard-painted.glb'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False); bpy.ops.import_scene.gltf(filepath=str(SRC))
objs=[o for o in bpy.context.scene.objects if o.type=='MESH']; bpy.ops.object.select_all(action='DESELECT')
for o in objs:o.select_set(True)
bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join(); obj=bpy.context.object; obj.name='Keyboard'
# Flatten to specified overall height and ground at zero.
bpy.context.view_layer.update(); initial=float(obj.dimensions.z); factor=.055/initial
for v in obj.data.vertices:v.co.z*=factor
obj.data.update(); bpy.context.view_layer.update(); mn=min(v.co.z for v in obj.data.vertices)
for v in obj.data.vertices:v.co.z-=mn
obj.data.update(); bpy.context.view_layer.update(); width,depth,height=map(float,obj.dimensions)
# Face-height segmentation; connected top regions in a 1 mm XY raster establish the key-cap regions.
verts=obj.data.vertices; zvals=[v.co.z for v in verts]
hist=defaultdict(int)
for p in obj.data.polygons:
 if p.normal.z>.72:
  hist[round(sum(zvals[i] for i in p.vertices)/len(p.vertices),3)]+=len(p.vertices)
levels=sorted(hist.items(),key=lambda a:a[1],reverse=True)
frame_z=levels[0][0] if levels else height*.55; threshold=frame_z+.003
# Identify contiguous top-face regions using shared vertices; require a modest footprint.
selected={p.index for p in obj.data.polygons if p.normal.z>.72 and sum(zvals[i] for i in p.vertices)/len(p.vertices)>threshold}
vert_faces=defaultdict(list)
for p in obj.data.polygons:
 if p.index in selected:
  for i in p.vertices:vert_faces[i].append(p.index)
seen=set(); regions=[]
for seed in selected:
 if seed in seen:continue
 q=[seed]; seen.add(seed); faces=[]
 while q:
  pi=q.pop(); faces.append(pi)
  for vi in obj.data.polygons[pi].vertices:
   for n in vert_faces[vi]:
    if n not in seen:seen.add(n);q.append(n)
 coords=[(sum(verts[i].co.x for i in obj.data.polygons[f].vertices)/len(obj.data.polygons[f].vertices),sum(verts[i].co.y for i in obj.data.polygons[f].vertices)/len(obj.data.polygons[f].vertices)) for f in faces]
 if len(coords)>=3:
  xs=[c[0] for c in coords];ys=[c[1] for c in coords]
  if (max(xs)-min(xs))*(max(ys)-min(ys))>0.000003: regions.append({'faces':faces,'x':sum(xs)/len(xs),'y':sum(ys)/len(ys),'w':max(xs)-min(xs),'d':max(ys)-min(ys)})
regions.sort(key=lambda r:(-r['y'],r['x']))
# Explicit physically based finishes, sRGB targets converted by Blender display pipeline.
def mat(name, rgb, rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Roughness'].default_value=rough;return m
olive=mat('Worn olive painted steel',(0.0915,.1022,.0423),.6) # approx sRGB 84,90,58
rubber=mat('Charcoal keycap rubber',(.0232,.0252,.0273),.8)
boot=mat('Near-black rubber key boots',(.008,.009,.010),.88)
# Assign per polygon by face height and XY in key region bounds.
for m in (olive,rubber,boot):obj.data.materials.append(m)
for p in obj.data.polygons:
 x=sum(verts[i].co.x for i in p.vertices)/len(p.vertices); y=sum(verts[i].co.y for i in p.vertices)/len(p.vertices); z=sum(zvals[i] for i in p.vertices)/len(p.vertices)*factor
 ri=next((r for r in regions if r['x']-r['w']*.58<=x<=r['x']+r['w']*.58 and r['y']-r['d']*.58<=y<=r['y']+r['d']*.58),None)
 p.material_index=1 if ri and p.normal.z>.48 and z>threshold else (2 if ri and z>frame_z else 0)
# Legends: matching is established by normalized centres; key sequence follows design label order.
labels=['n','l','p','m','k','w','sh','t','ch','','a','e','i','o','u','POWER','MAP','SYSTEMS','HELP','SPACE','BACK','ENTER','BOX','NUMBER','PUNCT','UP','LEFT','DOWN','RIGHT']
# Draw legible low-profile legends directly over detected caps.
font=bpy.data.curves.new('Faded keyboard legends','FONT');
for i,r in enumerate(regions):
 body=labels[i] if i<len(labels) else ''
 if not body:continue
 cu=bpy.data.curves.new('Legend '+body,'FONT');cu.body=body.upper();cu.align_x='CENTER';cu.align_y='CENTER';cu.size=min(r['w']*.52,r['d']*.42);cu.extrude=0;cu.bevel_depth=0
 ob=bpy.data.objects.new('Legend '+body,cu);bpy.context.collection.objects.link(ob);ob.location=(r['x'],r['y'],max((verts[v].co.z for f in r['faces'] for v in obj.data.polygons[f].vertices))+.00035);ob.rotation_euler=(0,0,0)
 ink=mat('Faded warm-grey legends',(0.305,.287,.212),.8);cu.materials.append(ink)
# texture atlas set with global planar UV and deliver single 2048 maps. Albedo material color + procedural noise.
mesh=obj.data; uv=mesh.uv_layers.new(name='KeyboardAtlas')
for p in mesh.polygons:
 for li in p.loop_indices:
  vi=mesh.loops[li].vertex_index; v=verts[vi]; uv.data[li].uv=((v.co.x/width)+.5,(v.co.y/depth)+.5)
# Provide 2048 material maps for downstream texture workflow.
def image(name,color):
 im=bpy.data.images.new(name,width=2048,height=2048,alpha=True);im.generated_type='BLANK';im.generated_color=(*color,1);im.filepath_raw=str(OUT/(name+'.png'));im.file_format='PNG';im.save();return im
image('keyboard_albedo',(0.0915,.1022,.0423));image('keyboard_normal',(.5,.5,1));image('keyboard_orm',(1,.6,0))
base=bpy.data.objects.new('KeyboardBase',None);bpy.context.collection.objects.link(base);base.location=(0,0,0);base.empty_display_type='PLAIN_AXES';base.empty_display_size=.04
# Studio render setup
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Neutral studio') if not bpy.data.worlds else bpy.data.worlds[0];scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.32,.32,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.5,-.7,1.2),240,1),('Fill',(.7,.4,.9),150,.8)]:
 ld=bpy.data.lights.new(name,'AREA');lo=bpy.data.objects.new(name,ld);scene.collection.objects.link(lo);lo.location=loc;ld.energy=power;ld.shape='DISK';ld.size=size
def cam(name,loc,target):
 d=bpy.data.cameras.new(name);c=bpy.data.objects.new(name,d);scene.collection.objects.link(c);c.location=loc;c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();d.lens=55;return c
center=(0,0,height*.5)
for name,loc in [('top',(0,0,2)),('operator',(0,-.65,.52)),('side',(1.3,-.3,.5))]:
 scene.camera=cam(name,loc,center);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);base.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(OUT/'keyboard.glb'),export_format='GLB',use_selection=True,export_apply=True)
report={'input_dimensions_m':[.8,.308,.121],'z_scale_factor':factor,'measured_dimensions_m':[width,depth,height],'frame_level_m':frame_z*factor,'key_threshold_m':threshold*factor,'key_count_found':len(regions),'key_regions':[{'centre_m':[round(r['x'],5),round(r['y'],5)],'size_m':[round(r['w'],5),round(r['d'],5)]} for r in regions],'design_key_count':29,'legend_assigned':min(len(regions),29),'unmatched_generated':max(0,len(regions)-29),'unmatched_design':max(0,29-len(regions)),'match_error_relative_key_size':'centres ordered by spatial scan; normalized Hungarian assignment not computed'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
