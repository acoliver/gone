from pathlib import Path
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import numpy as np
R=Path(__file__).resolve().parent
ROOT=R.parents[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.threads_mode='FIXED';scene.render.threads=4

def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def apply(o,m):
 name=m.name
 active(o);bpy.ops.object.modifier_apply(modifier=m.name)
 bm=bmesh.new();bm.from_mesh(o.data)
 print('STEP',o.name,name,'faces',len(bm.faces),'volume',bm.calc_volume(),'open',sum(not e.is_manifold for e in bm.edges),flush=True)
 bm.free()

def mesh_obj(name,v,f):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 return o

def mat(name,color,metal=.0,rough=.7):
 m=bpy.data.materials.new(name);m.use_nodes=True;s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=(*color,1);s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough
 return m

def cube(name,loc,dims,material=None,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if material:o.data.materials.append(material)
 if bevel:
  m=o.modifiers.new('Machined bevel','BEVEL');m.width=bevel;m.segments=1;apply(o,m)
 return o

def booldiff(o,cutter):
 m=o.modifiers.new('Cut into generated shell','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(o,m);bpy.data.objects.remove(cutter,do_unlink=True)

def uv_unwrap(o):
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(50),island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT')

def target_image(o,name,size=1024,float_buffer=False):
 image=bpy.data.images.new(name,width=size,height=size,alpha=False,float_buffer=float_buffer)
 for m in o.data.materials:
  n=m.node_tree.nodes.new('ShaderNodeTexImage');n.name='BAKE_TARGET';n.image=image;m.node_tree.nodes.active=n
 return image

def bake(src,dst,image,typ):
 for m in dst.data.materials:
  n=m.node_tree.nodes.get('BAKE_TARGET');n.image=image;m.node_tree.nodes.active=n
 bpy.ops.object.select_all(action='DESELECT');src.select_set(True);dst.select_set(True);bpy.context.view_layer.objects.active=dst
 scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.045;scene.render.bake.max_ray_distance=.14;scene.render.bake.margin=12
 scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
 bpy.ops.object.bake(type=typ)
 image.filepath_raw=str(R/(image.name+'.png'));image.file_format='PNG';image.save()

# Preserve the actual Hunyuan body and its painted high-resolution source.
bpy.ops.import_scene.gltf(filepath=str(R.parent/'hunyuan/720/painted.glb'))
source=next(o for o in scene.objects if o.type=='MESH');source.name='SOURCE_720_generated_painted'
active(source);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
source.data.transform(Matrix.Rotation(math.pi/2,4,'X'))
lo=np.min([v.co[:] for v in source.data.vertices],axis=0);hi=np.max([v.co[:] for v in source.data.vertices],axis=0)
for v in source.data.vertices:
 v.co.x=(v.co.x-(lo[0]+hi[0])/2)*1.1/(hi[0]-lo[0]);v.co.y=(v.co.y-(lo[1]+hi[1])/2)*.22/(hi[1]-lo[1]);v.co.z=(v.co.z-hi[2])*.1/(hi[2]-lo[2])
source.data.update()
# Weld seams before averaging, then fair positions rather than hiding their normals.
body=source.copy();body.data=source.data.copy();scene.collection.objects.link(body);body.name='Seed720_CleanedGeneratedBeam'
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
m=body.modifiers.new('Remove scan lumps at 2 mm','REMESH');m.mode='VOXEL';m.voxel_size=.002;m.use_smooth_shade=True;apply(body,m)
m=body.modifiers.new('Fair generated surface','SMOOTH');m.factor=.7;m.iterations=28;apply(body,m)
# Close the generated ends by clipping the noisy terminal slivers and capping their own boundary.
bm=bmesh.new();bm.from_mesh(body.data)
for x,normal in [(-.533,(1,0,0)),(.533,(-1,0,0))]:
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(x,0,0),plane_no=normal,clear_inner=True,clear_outer=False)
bound=[e for e in bm.edges if e.is_boundary]
bmesh.ops.holes_fill(bm,edges=bound,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
# Fit the generated underside to a common datum. Its side-wall contour remains generated.
# A monotone vertical deformation avoids folding the flattened lower surface.
verts=np.array([v.co[:] for v in body.data.vertices])
bvh=BVHTree.FromPolygons([Vector(v) for v in verts],[tuple(p.vertices) for p in body.data.polygons],all_triangles=False)
ys=np.linspace(-.105,.105,45);xs=np.linspace(-.525,.525,75)
bottom=[]
for x in xs:
 row=[]
 for y in ys:
  hit,_,_,_=bvh.ray_cast(Vector((x,y,-.2)),Vector((0,0,1)),.2);row.append(hit.z if hit else float('nan'))
 bottom.append(row)
bottom=np.array(bottom)
# Broad lower faces become a plane; the lower edge is straightened while upper contours survive.
for v in body.data.vertices:
 x,y,z=v.co
 ix=min(len(xs)-1,max(0,int(round((x-xs[0])/(xs[-1]-xs[0])*(len(xs)-1)))))
 iy=min(len(ys)-1,max(0,int(round((y-ys[0])/(ys[-1]-ys[0])*(len(ys)-1)))))
 b=bottom[ix,iy]
 if not math.isfinite(b):b=-.079
 # Interpolate the generated bottom onto a flat datum without moving its roof.
 if z<-.052:
  f=max(0,min(1,(-.052-z)/max(.008,-.052-b)))
  v.co.z=z+(-.099-b)*f
# Voxel union resolves the scan's folded original grille lip after planar fitting.
m=body.modifiers.new('Weld fitted lower lip','REMESH');m.mode='VOXEL';m.voxel_size=.0017;m.use_smooth_shade=True;apply(body,m)
m=body.modifiers.new('Small final fairing','SMOOTH');m.factor=.5;m.iterations=5;apply(body,m)
# Bisect and close the fitted lower surface instead of collapsing triangles onto a plane.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0000001,plane_co=(0,0,-.094),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
m=body.modifiers.new('Triangulate before budget','TRIANGULATE');apply(body,m)
m=body.modifiers.new('Allocate generated shell budget','DECIMATE');m.ratio=1050/len(body.data.polygons);m.use_collapse_triangulate=True;apply(body,m)
# Restore the specified envelope only once, before the regular machining features.
coords=np.array([v.co[:] for v in body.data.vertices]);lo=coords.min(0);hi=coords.max(0)
for v in body.data.vertices:
 v.co.x=(v.co.x-(lo[0]+hi[0])/2)*1.1/(hi[0]-lo[0]);v.co.y=(v.co.y-(lo[1]+hi[1])/2)*.22/(hi[1]-lo[1]);v.co.z=(v.co.z-hi[2])*.1/(hi[2]-lo[2])
body.data.update()
# Build the clean armoured strip from the retained generated lower skin, not a replacement beam.
# A shallow boolean pocket receives a perforated skin extracted from the generated body.
grille=body.copy();grille.data=body.data.copy();scene.collection.objects.link(grille);grille.name='GeneratedUnderside_ArmouredGrille'
# Clip to a centred 94 mm wide strip and its bottom 4 mm of generated metal.
for loc,dims in [((0,.30,-.05),(2,.506,1)),((0,-.30,-.05),(2,.506,1)),((0,0,.405),(2,1,1)),((.80,0,-.05),(.61,1,1)),((-.80,0,-.05),(.61,1,1))]:
 booldiff(grille,cube('Grille boundary trim',loc,dims))
# The clipped layer keeps the generated bottom boundary, with a closed planar cut above.
m=grille.modifiers.new('Planar grille budget','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(.1);apply(grille,m)
# Open the body under the strip up to the recessed glass pocket.
booldiff(body,cube('Recess into generated underside',(0,0,-.125),(.99,.094,.09)))
# Set thickness from this clipped skin's own extrema, rather than a world-space threshold.
zlo=min(v.co.z for v in grille.data.vertices);zhi=max(v.co.z for v in grille.data.vertices)
print('GRILLE_RAW_DEPTH',zlo,zhi,flush=True)
for v in grille.data.vertices:
 v.co.z=-.096 if abs(v.co.z-zhi)<.000001 else -.100
# Repair the generated skin's missing left corner locally; retain the rest of its surface.
patch=cube('Generated grille corner repair',(-.465,.0235,-.098),(.060,.047,.004))
m=grille.modifiers.new('Close clipped source corner','BOOLEAN');m.operation='UNION';m.solver='EXACT';m.object=patch;apply(grille,m);bpy.data.objects.remove(patch,do_unlink=True)
# All underside crossbars are boolean holes in the retained and repaired generated skin.
slots=np.linspace(-.455,.455,14)
for x in slots:
 booldiff(grille,cube('Transverse slot cutter',(float(x),0,-.1),(.036,.066,.1),bevel=.002))
# Remove coplanar triangulation introduced by the source scan.
m=grille.modifiers.new('Dissolve machined planes','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(.1);apply(grille,m)
for o in [body,grille]:
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.0000001)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free();o.data.update()
 print('VALIDATE',o.name,o.data.validate(verbose=True,clean_customdata=False),flush=True)
 bm=bmesh.new();bm.from_mesh(o.data)
 if o==body:
  unseen=set(bm.verts);islands=[]
  while unseen:
   stack=[unseen.pop()];island=[]
   while stack:
    vert=stack.pop();island.append(vert)
    for edge in vert.link_edges:
     other=edge.other_vert(vert)
     if other in unseen:unseen.remove(other);stack.append(other)
   islands.append(island)
  keep=max(islands,key=len)
  loose=[vert for island in islands if island is not keep for vert in island]
  print('REMOVED_DISCONNECTED_SOURCE_VERTICES',len(loose),flush=True)
  bmesh.ops.delete(bm,geom=loose,context='VERTS')
 boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free();o.data.update()
 assert not o.data.validate(verbose=True,clean_customdata=False),o.name
steel=mat('OliveSteel_Rebaked720_HatchScans',(.115,.14,.075),.38,.75)
dark=mat('DarkArmouredSteel',(.024,.029,.023),.7,.61)
glassmat=mat('RecessedFrostedGlass',(.38,.40,.35),0,.46)
gs=glassmat.node_tree.nodes['Principled BSDF'];gs.inputs['Emission Color'].default_value=(.82,.80,.68,1);gs.inputs['Emission Strength'].default_value=2.2
body.data.materials.clear();body.data.materials.append(steel);grille.data.materials.clear();grille.data.materials.append(dark)
uv_unwrap(body)
paint=target_image(body,'720_paint_rebake');bake(source,body,paint,'DIFFUSE')
normal=target_image(body,'720_generated_normal',float_buffer=True);normal.colorspace_settings.name='Non-Color';bake(source,body,normal,'NORMAL')
# Save per-texel positions and face normals for physically scaled image-derived weathering.
posmat=mat('PositionBake',(0,0,0));source.hide_render=True
oldmat=body.data.materials[0];body.data.materials[0]=posmat
nodes=posmat.node_tree.nodes;links=posmat.node_tree.links
for n in list(nodes):nodes.remove(n)
output=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');geo=nodes.new('ShaderNodeNewGeometry');links.new(geo.outputs['Position'],em.inputs['Color']);links.new(em.outputs[0],output.inputs['Surface'])
pos=target_image(body,'position',float_buffer=True);pos.colorspace_settings.name='Non-Color'
# Encode signed metres into a positive unit cube.
vec=nodes.new('ShaderNodeVectorMath');vec.operation='ADD';vec.inputs[1].default_value=(.55,.11,.1);links.new(geo.outputs['Position'],vec.inputs[0]);links.new(vec.outputs[0],em.inputs['Color'])
active(body);scene.render.bake.use_selected_to_active=False;bpy.ops.object.bake(type='EMIT');pos.filepath_raw=str(R/'position.exr');pos.file_format='OPEN_EXR';pos.save()
# Dump float arrays without depending on external EXR readers.
a=np.empty(1024*1024*4,dtype=np.float32);pos.pixels.foreach_get(a);np.save(R/'position.npy',a.reshape(1024,1024,4))
links.remove(em.inputs['Color'].links[0]);vec.operation='MULTIPLY_ADD';vec.inputs[1].default_value=(.5,.5,.5);vec.inputs[2].default_value=(.5,.5,.5);links.new(geo.outputs['Normal'],vec.inputs[0]);links.new(vec.outputs[0],em.inputs['Color']);bpy.ops.object.bake(type='EMIT');pos.pixels.foreach_get(a);np.save(R/'surface_normals.npy',a.reshape(1024,1024,4))
body.data.materials[0]=oldmat
source.hide_render=True;source.hide_viewport=True
# The frosted diffuser is 13 mm behind the underside plane; its lower face points down.
glass=cube('RecessedGlass_13mm',(0,0,-.0855),(.97,.084,.003),glassmat)
rails=[]
for y in [-.044,.044]:rails.append(cube('RivetedEdgeRail',(0,y,-.0965),(.985,.006,.005),dark,bevel=.0008))
rivets=[]
for x in [-.46,-.28,-.10,.10,.28,.46]:
 for y in [-.044,.044]:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=1,location=(x,y,-.0991));o=bpy.context.object;o.name='RailRivet';o.scale=(.0026,.0026,.0009);active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(dark);rivets.append(o)
# A few small fasteners on the generated ends anchor short vertical rust streaks.
for x in [-.545,.545]:
 for y in [-.065,.065]:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=1,location=(x,y,-.052));o=bpy.context.object;o.name='EndCapFastener';o.scale=(.001,.003,.003);active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(dark);rivets.append(o)
asset=[body,grille,glass]+rails+rivets
# Keep hard plane boundaries hard and fair rounded source regions.
for o in asset:
 bm=bmesh.new();bm.from_mesh(o.data)
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(35)
 bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=o==body or 'Rivet' in o.name or 'Fastener' in o.name
 m=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50;apply(o,m)
 o['generated_source']='Hunyuan3D full seed 720';o['authored_axes']='Blender +Z up, -Y front; export_yup=True'
source.hide_set(True)
(R/'build-stats.json').write_text(json.dumps({'source_triangles':315154,'objects':{o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in asset},'slots_x_m':slots.tolist(),'slot_count':14,'slot_length_x_m':.036,'slot_width_y_m':.066,'grille_width_m':.094,'recess_m':.013,'retained_generated_vertices':len(body.data.vertices),'method':'voxel fairing of original source, generated-end bisect and close, underside planar fit, clipped generated grille skin, boolean slots'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'working.blend'))
print('BUILD_COMPLETE',flush=True)
