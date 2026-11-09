from pathlib import Path
import sys,json,math,statistics
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent
config=json.loads((R/'fit-config.json').read_text())
chosen=json.loads((R/'chosen.json').read_text())
metrics=chosen.get('directional_metrics',{})
if metrics:
 def strip_score(metric):
  counts=metric['counts']
  return max((min(n,12)-.5*abs(n-12) for n in counts),default=-6)+.2*metric['recess_count_median']
 best_surface=max(metrics,key=lambda k:strip_score(metrics[k]))
 if strip_score(metrics[best_surface])>strip_score(metrics[config['grille_surface']])+1:config['grille_surface']=best_surface
out=Path(config.get('output_dir',str(R/'final')));out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=config['source'])
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
if len(objects)>1:bpy.ops.object.join()
obj=bpy.context.object;obj.name='GeneratedBeamFixture'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
source_faces=len(obj.data.polygons)
rotation={'bottom':0,'front':math.pi/2,'back':-math.pi/2,'top':math.pi}[config['grille_surface']]
obj.data.transform(Matrix.Rotation(rotation,4,'X'))
# Remove disconnected scan specks, preserving generated fixture geometry.
bm=bmesh.new();bm.from_mesh(obj.data)
# glTF flat normals and UV seams duplicate vertices; weld before classifying islands.
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00002)
unseen=set(bm.verts);islands=[]
while unseen:
 start=unseen.pop();stack=[start];island=[start]
 while stack:
  v=stack.pop()
  for edge in v.link_edges:
   other=edge.other_vert(v)
   if other in unseen:unseen.remove(other);stack.append(other);island.append(other)
 islands.append(island)
largest=max(len(x) for x in islands);removed=[v for island in islands if len(island)<max(12,largest*.002) for v in island]
if removed:bmesh.ops.delete(bm,geom=removed,context='VERTS')
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=0.000001)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
# Place the top flush on Z=0 in Blender native coordinates.
vs=[v.co.copy() for v in obj.data.vertices];lo=Vector(tuple(min(v[i] for v in vs) for i in range(3)));hi=Vector(tuple(max(v[i] for v in vs) for i in range(3)));ext=hi-lo
length,width,height=1.10,.22,.10
for v in obj.data.vertices:
 v.co.x=(v.co.x-(lo.x+hi.x)/2)*length/ext.x
 v.co.y=(v.co.y-(lo.y+hi.y)/2)*width/ext.y
 v.co.z=(v.co.z-hi.z)*height/ext.z
bpy.context.view_layer.objects.active=obj
smooth=obj.modifiers.new('SmallScanFairing','SMOOTH');smooth.factor=.22;smooth.iterations=2;bpy.ops.object.modifier_apply(modifier=smooth.name)
tri=obj.modifiers.new('TriangulateGeneratedSurface','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
dec=obj.modifiers.new('GameBudget','DECIMATE');dec.ratio=min(1,2780/max(1,len(obj.data.polygons)));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
# Restore the exact envelope after fairing, without replacing the generated form.
vs=[v.co.copy() for v in obj.data.vertices];lo=Vector(tuple(min(v[i] for v in vs) for i in range(3)));hi=Vector(tuple(max(v[i] for v in vs) for i in range(3)))
for v in obj.data.vertices:
 v.co.x=(v.co.x-(lo.x+hi.x)/2)*length/(hi.x-lo.x);v.co.y=(v.co.y-(lo.y+hi.y)/2)*width/(hi.y-lo.y);v.co.z=(v.co.z-hi.z)*height/(hi.z-lo.z)
obj.data.update()
# Use the installed painter's baked albedo when available.
painted=config['paint_success']
if painted:
 steel=obj.data.materials[0];steel.name='WeatheredOliveSteel'
 shader=steel.node_tree.nodes.get('Principled BSDF')
 shader.inputs['Metallic'].default_value=.35;shader.inputs['Roughness'].default_value=.70
else:
 obj.data.materials.clear();steel=bpy.data.materials.new('WeatheredOliveSteel_ConceptProjection');steel.use_nodes=True;obj.data.materials.append(steel)
 nodes=steel.node_tree.nodes;shader=nodes.get('Principled BSDF');shader.inputs['Metallic'].default_value=.35;shader.inputs['Roughness'].default_value=.70
 tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(config['reference']);tex.image.pack();obj.data.materials[0].node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
 uv=obj.data.uv_layers.new(name='ConceptProjection')
 box=config['reference_bbox']
 for poly in obj.data.polygons:
  for li in poly.loop_indices:
   v=obj.data.vertices[obj.data.loops[li].vertex_index].co
   u=box[0]/1024+(v.x/length+.5)*(box[2]-box[0])/1024
   vv=1-box[3]/1024+((v.z/height+1)*.6+.2)*(box[3]-box[1])/1024
   uv.data[li].uv=(u,vv)
shader.inputs['Coat Weight'].default_value=.04

def material(name,color,metallic,roughness,emission=None):
 m=bpy.data.materials.new(name);m.use_nodes=True;s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=(*color,1);s.inputs['Metallic'].default_value=metallic;s.inputs['Roughness'].default_value=roughness
 if emission:s.inputs['Emission Color'].default_value=(*emission,1);s.inputs['Emission Strength'].default_value=1.1
 return m
steelidx=0
grille=material('DarkArmouredGrille',(.025,.032,.022),.72,.62);grilleidx=len(obj.data.materials);obj.data.materials.append(grille)
glass=material('RecessedEmissiveFrostedGlass',(.32,.34,.30),0,.35,(.70,.67,.59));glassidx=len(obj.data.materials);obj.data.materials.append(glass)
verts=[v.co.copy() for v in obj.data.vertices];faces=[tuple(p.vertices) for p in obj.data.polygons];bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True)
import numpy as np
# Locate the narrow generated grille band; it need not occupy the broad face's centre.
bands=[]
for yi in range(33):
 y=(yi/32-.5)*width*.86;line=[]
 for xi in range(300):
  x=(xi/299-.5)*length*.84;hit,n,idx,d=bvh.ray_cast(Vector((x,y,-.2)),Vector((0,0,1)),.4);line.append(hit.z if hit else float('nan'))
 z=np.array(line);valid=np.isfinite(z)
 if valid.sum()<len(z)*.9:continue
 z=np.interp(np.arange(len(z)),np.flatnonzero(valid),z[valid]);smooth=np.convolve(np.pad(z,(2,2),mode='edge'),np.ones(5)/5,mode='valid');peaks=[]
 for i in range(10,len(smooth)-10):
  if smooth[i]>smooth[i-1] and smooth[i]>=smooth[i+1]:
   prominence=min(smooth[i]-min(smooth[i-10:i]),smooth[i]-min(smooth[i+1:i+11]))
   if prominence>.0012 and (not peaks or i-peaks[-1]>10):peaks.append(i)
 cv=float(np.std(np.diff(peaks))/np.mean(np.diff(peaks))) if len(peaks)>2 else 1
 score=min(len(peaks),12)-.35*abs(len(peaks)-12)-2*cv
 bands.append({'y':y,'count':len(peaks),'spacing_cv':cv,'score':score,'profile':z.tolist()})
if not bands:raise RuntimeError('No complete generated underside band')
band=max(bands,key=lambda b:b['score']);grille_y=band['y'];grille_half_width=width*.145
heights=[]
for yi in range(7):
 y=grille_y+(yi/6-.5)*grille_half_width*1.2
 for xi in range(180):
  x=(xi/179-.5)*length*.84
  hit,n,idx,d=bvh.ray_cast(Vector((x,y,-.2)),Vector((0,0,1)),.4)
  if hit:heights.append(hit.z)
heights.sort();q10=heights[int(len(heights)*.1)];q90=heights[int(len(heights)*.9)];threshold=q10+max(.001,.40*(q90-q10))
counts={};areas={}
for p in obj.data.polygons:
 c=p.center
 p.material_index=steelidx
 if abs(c.x)<length*.47 and abs(c.y-grille_y)<grille_half_width and c.z<-.025:
  p.material_index=grilleidx
  if p.normal.z<-.38 and c.z>threshold:p.material_index=glassidx
 p.use_smooth=True
 counts[p.material_index]=counts.get(p.material_index,0)+1;areas[p.material_index]=areas.get(p.material_index,0)+p.area
if counts.get(glassidx,0)==0:raise RuntimeError('No generated recessed surface available for glass; cannot invent a substitute')
# Sample the exported design's actual visible glass islands rather than counting material slots.
slot_lines=[]
for yi in range(9):
 y=grille_y+(yi/8-.5)*grille_half_width*1.2;mask=[]
 for xi in range(360):
  x=(xi/359-.5)*length*.9;hit,n,idx,d=bvh.ray_cast(Vector((x,y,-.2)),Vector((0,0,1)),.4)
  mask.append(idx is not None and obj.data.polygons[idx].material_index==glassidx)
 runs=[];start=None
 for i,yes in enumerate(mask+[False]):
  if yes and start is None:start=i
  if not yes and start is not None:
   if i-start>=3:runs.append([start,i])
   start=None
 slot_lines.append({'y':y,'runs':runs,'count':len(runs)})
obj['generated_source']=config['source'];obj['hunyuan_seed']=config['seed'];obj['grille_surface_before_rotation']=config['grille_surface'];obj['top_mount_plane']='Blender Z=0; glTF Y=0';obj['front']='Blender -Y; glTF +Z'
# The fixture alone is exported. The ceiling below is a preview prop only.
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(out/'fixture.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_extras=True)
triangles=sum(len(p.vertices)-2 for p in obj.data.polygons)
assert triangles<=3000,triangles
stats={'seed':config['seed'],'source':config['source'],'source_faces':source_faces,'removed_floater_vertices':len(removed),'grille_surface_before_rotation':config['grille_surface'],'rotation_about_blender_x_degrees':math.degrees(rotation),'dimensions_blender':[length,width,height],'dimensions_gltf':[length,height,width],'triangles':triangles,'glass_faces':counts.get(glassidx,0),'grille_faces':counts.get(grilleidx,0),'steel_faces':counts.get(0,0),'glass_area_m2':areas.get(glassidx,0),'recess_threshold_m':threshold,'sample_depth_quantiles_m':[q10,q90],'generated_grille_band':band,'grille_center_y_blender_m':grille_y,'grille_width_m':grille_half_width*2,'visible_glass_slot_lines':slot_lines,'visible_glass_slot_count_median':statistics.median(r['count'] for r in slot_lines),'paint_success':painted,'materials':[m.name for m in obj.data.materials]}
(out/'stats.json').write_text(json.dumps(stats,indent=2))
# Save source before preview scene construction.
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fixture.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=6;s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
s.world=bpy.data.worlds.new('DarkGreyRoom');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.12,.13,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
ceiling=material('PreviewDarkGreyCeiling',(.065,.070,.072),0,.94)
bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,.002));plane=bpy.context.object;plane.name='PREVIEW_ONLY_CEILING';plane.data.materials.append(ceiling)
for name,loc,power,size in [('SoftRoomFill',(-.9,-.6,-1.0),18,2.0),('MetalEdgeFill',(1,.4,-.35),12,1.0)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,-.05))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('PlayerCamera');cam=bpy.data.objects.new('PlayerCamera',d);s.collection.objects.link(cam);s.camera=cam;d.type='PERSP';d.lens=55
for name,loc in [('below-2p5m',(0,-.025,-2.55)),('three-quarter',(1.05,-1.15,-1.85)),('below-close',(0,-.20,-1.35))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,-.05))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/f'{name}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'preview.blend'))
print('FINAL',json.dumps(stats),flush=True)
