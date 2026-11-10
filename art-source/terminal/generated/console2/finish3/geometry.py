import bpy, bmesh, json, math, time
import numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent; ROOT=O.parent
# Reuse the original component filtering and fit rather than fitting the decimated asset.
code=(ROOT/'fit/build.py').read_text(); code=code[:code.index('# Keep low triangle count')]
exec(compile(code,'fit/build.py','exec'))
body=obj; scene=bpy.context.scene
bm=bmesh.new();bm.from_mesh(body.data)
raw_faces=len(bm.faces); bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.y>-.03],context='VERTS')
# The discarded backdrop was the wall-side cap. Extend its cut rim back to the wall.
cut_rim={v for e in bm.edges if e.is_boundary for v in e.verts if v.co.y>-.04}
for v in cut_rim:v.co.y=0
bm.to_mesh(body.data);bm.free();body.data.update()
a=np.array([v.co[:] for v in body.data.vertices]);lo=a.min(0);hi=a.max(0);cx=(lo[0]+hi[0])/2;sx=1.1/(hi[0]-lo[0])
for v in body.data.vertices:v.co.x=(v.co.x-cx)*sx
body.data.update()
# Reconstruct the finish2 photo cross-section fit, retaining the fitted Y/Z coordinates.
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.film_transparent=True
scene.render.resolution_x=1024;scene.render.resolution_y=1280;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
def camera(name,loc,target,width):
 d=bpy.data.cameras.new(name);d.type='ORTHO';d.ortho_scale=width;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
def emitmat():
 m=bpy.data.materials.new('Mask');m.use_nodes=True;n=m.node_tree.nodes;n.clear();e=n.new('ShaderNodeEmission');e.inputs[0].default_value=(1,1,1,1);out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(e.outputs[0],out.inputs[0]);return m
body.data.materials.clear();body.data.materials.append(emitmat())
a=np.array([v.co[:] for v in body.data.vertices]);lo=a.min(0);hi=a.max(0);height=hi[2]-lo[2];cz=(hi[2]+lo[2])/2
cam=camera('FitMask',(0,-3,cz),(0,0,cz),height*1.08);scene.camera=cam
scene.render.filepath=str(O/'fit-mask.png');bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(str(O/'fit-mask.png'),check_existing=False);src=np.array(im.pixels[:]).reshape(1280,1024,4)[::-1,:,3]>.5
im=bpy.data.images.load(str(ROOT/'finish2/photo-silhouette.png'),check_existing=False);w,h=im.size;dst=np.array(im.pixels[:]).reshape(h,w,4)[::-1,:,0]>.5
sg=json.loads((ROOT/'finish2/screen-segmentation.json').read_text());px,py,pw,ph=sg['photo_bbox']
def bounds(mask):
 rows=np.flatnonzero(mask.any(1));left=np.array([np.flatnonzero(mask[y])[0] for y in rows]);right=np.array([np.flatnonzero(mask[y])[-1] for y in rows]);return rows,left,right
sr,sl,sright=bounds(src);tr,tl,tright=bounds(dst);my=int(sr[0]);mh=int(sr[-1]-sr[0]+1);meter=cam.data.ortho_scale/1280
maxdelta=0
for v in body.data.vertices:
 row=640-(v.co.z-cz)/meter
 l=(np.interp(row,sr,sl)-512)*meter;r=(np.interp(row,sr,sright)-512)*meter
 ty=py+(row-my)/(mh-1)*(ph-1);target_l=-.55+(np.interp(ty,tr,tl)-px)/(pw-1)*1.1;target_r=-.55+(np.interp(ty,tr,tright)-px)/(pw-1)*1.1
 t=np.clip((v.co.x-l)/(r-l),0,1);new=target_l+t*(target_r-target_l);maxdelta=max(maxdelta,abs(new-v.co.x));v.co.x=float(new)
body.data.update();body.name='ConsoleBody'
reference=body.copy();reference.data=body.data.copy();scene.collection.objects.link(reference);reference.name='RawFittedReference';reference.hide_render=True
bpy.context.view_layer.objects.active=body
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
def topology(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);edges=sum(not e.is_manifold for e in bm.edges);boundary=sum(e.is_boundary for e in bm.edges);wire=sum(e.is_wire for e in bm.edges)
 unseen=set(bm.verts);components=[]
 while unseen:
  start=unseen.pop();stack=[start];component=[start]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    other=e.other_vert(v)
    if other in unseen:unseen.remove(other);stack.append(other);component.append(other)
  components.append(len(component))
 bm.free();return {'vertices':len(ob.data.vertices),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'nonmanifold_edges':edges,'boundary_edges':boundary,'wire_edges':wire,'components':len(components)}
report={'source':'meshes/console-s510-rgba-410.glb','raw_fitted':topology(reference),'uniform_scale':scale,'depth_y_factor':factor,'backdrop_cut_y_m':-.03,'back_wall_y_m':0,'removed_backdrop_faces':raw_faces-len(body.data.polygons),'photo_fit_maximum_x_displacement_m':maxdelta,'voxel_size_m':.005,'smooth_factor':.5,'smooth_iterations':5}
# Reconstruct clean side/underside panels from the fitted raw silhouette and front ray depths.
# A remesh of the thin torn scan alone seals its skin but retains deep closed creases.
from mathutils.bvhtree import BVHTree
raw=np.array([v.co[:] for v in body.data.vertices]);bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
zgrid=np.linspace(raw[:,2].min(),raw[:,2].max(),320);lefts=[];rights=[];fronts=[]
for z in zgrid:
 row=raw[np.abs(raw[:,2]-z)<.003]
 lefts.append(float(row[:,0].min()) if len(row) else np.nan);rights.append(float(row[:,0].max()) if len(row) else np.nan);fronts.append(float(row[:,1].min()) if len(row) else np.nan)
lefts=np.array(lefts);rights=np.array(rights);fronts=np.array(fronts)
for values in (lefts,rights,fronts):
 valid=np.isfinite(values);values[:]=np.interp(zgrid,zgrid[valid],values[valid])
newleft=lefts.copy();newright=rights.copy()
for z0,z1 in [(.025,.465),(.555,.625),(.700,1.245)]:
 region=(zgrid>=z0)&(zgrid<=z1)
 for original,new in [(lefts,newleft),(rights,newright)]:
  coefficients=np.polyfit(zgrid[region],original[region],1);fit=np.polyval(coefficients,zgrid[region]);weights=np.minimum(1.,np.minimum((zgrid[region]-z0)/.012,(z1-zgrid[region])/.012));new[region]=original[region]*(1-weights)+fit*weights
# Suppress single-row scan notches while retaining the head, deck and pedestal corners.
for values in (newleft,newright,fronts):
 values[1:-1]=values[:-2]*.2+values[1:-1]*.6+values[2:]*.2
vertices=[];faces=[];columns=65;stride=columns+2
for row,z in enumerate(zgrid):
 l,r=newleft[row],newright[row];oldl,oldr=lefts[row],rights[row];front=fronts[row]
 for col,t in enumerate(np.linspace(0,1,columns)):
  x=l+t*(r-l);samplex=oldl+t*(oldr-oldl);hit,n,f,d=bvh.ray_cast(Vector((samplex,-2,z)),Vector((0,1,0)));y=front if hit is None else min(front+.035,max(front,hit.y))
  if t<.06 or t>.94:y=front
  vertices.append((float(x),float(y),float(z)))
 vertices.extend([(float(l),0,float(z)),(float(r),0,float(z))])
 if row:
  a=(row-1)*stride;b=row*stride
  for col in range(columns-1):faces.append((a+col,a+col+1,b+col+1,b+col))
  faces.extend([(a+columns,b+columns,b,a),(a+columns-1,b+columns-1,b+columns+1,a+columns+1),(a+columns+1,b+columns+1,b+columns,a+columns)])
faces.append(tuple(list(range(columns))+[columns+1,columns]));a=(len(zgrid)-1)*stride;faces.append(tuple([a+columns,a+columns+1]+[a+c for c in reversed(range(columns))]))
clean=bpy.data.meshes.new('Clean fitted console shell');clean.from_pydata(vertices,[],faces);clean.update();body.data=clean
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.materials.append(emitmat())
report['local_repairs']=['Closed side and underside panels reconstructed from the raw fitted silhouette, retaining the ray-sampled front depth and screen recess.','Side-panel outline straightened with 12 mm feathering; single-row scan notches filtered before voxel rebuilding.','Deck-to-body joint is a continuous solid shell with no retained scan sliver.']
rem=body.modifiers.new('Watertight 5 mm voxel rebuild','REMESH');rem.mode='VOXEL';rem.voxel_size=.005;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
report['after_voxel']=topology(body)
sm=body.modifiers.new('Remove voxel stepping','SMOOTH');sm.factor=.5;sm.iterations=5;bpy.ops.object.modifier_apply(modifier=sm.name)
# Keep the back exactly wall aligned and floor exactly grounded after smoothing.
a=np.array([v.co[:] for v in body.data.vertices]);lo=a.min(0);hi=a.max(0)
for v in body.data.vertices:
 v.co.x*=1.1/(hi[0]-lo[0]);v.co.x-=(hi[0]+lo[0])*.5*1.1/(hi[0]-lo[0]);v.co.z-=lo[2]
 if v.co.y>-.012:v.co.y=0
body.data.update()
dec=body.modifiers.new('Collapse to 48000 triangles','DECIMATE');dec.decimate_type='COLLAPSE';dec.ratio=min(1,47998/sum(len(p.vertices)-2 for p in body.data.polygons));dec.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=dec.name)
report['final_geometry']=topology(body);assert report['final_geometry']['triangles']<=48000;assert report['final_geometry']['nonmanifold_edges']==0,report
# Front and side masks share identical cameras and framing with their raw fitted references.
scene.render.resolution_x=1600;scene.render.resolution_y=1600
maskcams={'front':camera('FrontIoU',(0,-3,.6374),(0,0,.6374),1.42),'side':camera('SideIoU',(-3,-.35,.6374),(0,-.35,.6374),1.42)}
ious={}
for name,c in maskcams.items():
 scene.camera=c;masks=[]
 for ob,label in [(reference,'raw'),(body,'rebuilt')]:
  body.hide_render=ob!=body;reference.hide_render=ob!=reference;scene.render.filepath=str(O/f'silhouette-{name}-{label}.png');bpy.ops.render.render(write_still=True)
  im=bpy.data.images.load(scene.render.filepath,check_existing=False);masks.append(np.array(im.pixels[:]).reshape(1600,1600,4)[:,:,3]>.5)
 ious[name]=float(np.count_nonzero(masks[0]&masks[1])/np.count_nonzero(masks[0]|masks[1]))
report['silhouette_iou']=ious;print('GEOMETRY',json.dumps(report),flush=True)
(O/'geometry-report.json').write_text(json.dumps(report,indent=2))
assert min(ious.values())>=.97,ious
bpy.data.objects.remove(reference,do_unlink=True);body.hide_render=False
# Required smart UV atlas is retained through repaint by transferring the generated atlas.
bpy.context.view_layer.objects.active=body;bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
body.data.materials.clear();m=bpy.data.materials.new('Neutral grey clay');m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.18,.18,.18,1);p.inputs['Roughness'].default_value=.72;body.data.materials.append(m)
for poly in body.data.polygons:poly.use_smooth=True
bpy.ops.export_scene.gltf(filepath=str(O/'console-unpainted.glb'),export_format='GLB',use_selection=True,export_apply=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'geometry.blend'))
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.film_transparent=False;scene.render.image_settings.color_mode='RGB';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.10,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
def area(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,-.35,.65))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-2,-3,3),280,2);area('Fill',(2,-2,1.9),160,2.4);area('Underside fill',(-1,-2,-.2),90,1.4)
claycams={'three-quarter':camera('ClayThreeQuarter',(-2,-3,1.65),(0,-.35,.64),2.78),'side':camera('ClaySide',(-3,-.35,.65),(0,-.35,.65),2.65),'underside':camera('ClayUnderside',(-1.3,-2.6,.24),(-.20,-.47,.59),1.35)}
for name,c in claycams.items():scene.camera=c;scene.render.filepath=str(O/f'clay-{name}.png');bpy.ops.render.render(write_still=True)
print('CLAY_COMPLETE',flush=True)
