from pathlib import Path
import bpy, bmesh, math, json, numpy as np
R=Path(__file__).resolve().parent
P=R.parent/'round4'; P3=R.parent/'round3'
bpy.ops.wm.open_mainfile(filepath=str(P/'fixture.blend'))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1
s.render.threads_mode='FIXED';s.render.threads=4
s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
source=bpy.data.objects['SOURCE_720_generated_painted'];source.hide_render=True;source.hide_set(True)
body=bpy.data.objects['Seed720_CleanedGeneratedBeam'];grille=bpy.data.objects['GeneratedUnderside_ArmouredGrille'];glass=bpy.data.objects['RecessedGlass_13mm']
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def apply(o,m):
 active(o);bpy.ops.object.modifier_apply(modifier=m.name)

def bevel(o,w,segments):
 m=o.modifiers.new('Soft manufactured cap edges','BEVEL');m.width=w;m.segments=segments;apply(o,m)

def cube(name,loc,dims):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o

with bpy.data.libraries.load(str(P3/'fixture.blend'),link=False) as (src,dst):
 dst.objects=['GeneratedUnderside_ArmouredGrille']
g3=dst.objects[0];grille.data=g3.data.copy();bpy.data.objects.remove(g3,do_unlink=True)
# Retain one shallow centre-span dent; remove the second inherited dent.
for v in grille.data.vertices:
 if abs(v.co.x-.28)<.0171:v.co.z-=.0019*max(0,1-abs(v.co.y)/.033)
 if abs(v.co.x+.14)<.0171:v.co.x+=.0012*max(0,1-abs(v.co.y)/.033)
grille.data.update()
old=bpy.data.objects['RaisedRails_Rivets_GravityFasteners'];active(old)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
parts=[]
for o in list(bpy.context.selected_objects):
 co=np.array([(o.matrix_world@v.co)[:] for v in o.data.vertices]);centre=(co.min(0)+co.max(0))/2
 if abs(centre[0])>.505:bpy.data.objects.remove(o,do_unlink=True)
 else:parts.append(o)
for sign in [-1,1]:
 cap=cube('TaperedRoundedEndCap',(sign*.530,0,-.052),(.040,.216,.096))
 for v in cap.data.vertices:
  lower=(.048-v.co.z)/.096
  v.co.x-=sign*.008*lower
  v.co.y*=1-.075*lower
 bevel(cap,.004,2)
 for y in [-.077,.077]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.0045,depth=.012,end_fill_type='NGON',location=(sign*.549,y,-.013),rotation=(0,math.pi/2,0))
  cutter=bpy.context.object;m=cap.modifiers.new('Inset flange bolt seat','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(cap,m);bpy.data.objects.remove(cutter,do_unlink=True)
 parts.append(cap)
 flange=cube('BevelledCeilingFlange',(sign*.527,0,-.002),(.046,.220,.004));bevel(flange,.0012,1);parts.append(flange)
 for y in [-.077,.077]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.0033,depth=.0012,end_fill_type='NGON',location=(sign*.5480,y,-.013),rotation=(0,math.pi/2,0))
  bolt=bpy.context.object;bolt.name='InsetCeilingFlangeBolt';parts.append(bolt)
active(parts[0])
for o in parts:o.select_set(True)
bpy.ops.object.join();hardware=bpy.context.object;hardware.name='RaisedRails_Rivets_GravityFasteners'
asset=[body,grille,hardware,glass]
for o in [body,grille,hardware]:
 bm=bmesh.new();bm.from_mesh(o.data)
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(38)
 bm.to_mesh(o.data);bm.free()
 for poly in o.data.polygons:poly.use_smooth=True
 m=o.modifiers.new('Weighted normals at chamfers','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=60;apply(o,m)
for o,prefix in [(body,'body'),(grille,'grille'),(hardware,'hardware')]:
 # Sample true mesh edges with sharp dihedral angles, in world coordinates.
 bm=bmesh.new();bm.from_mesh(o.data);edges=[]
 for e in bm.edges:
  if len(e.link_faces)!=2 or e.calc_face_angle(0)>math.radians(30):
   a=o.matrix_world@e.verts[0].co;b=o.matrix_world@e.verts[1].co;length=(b-a).length
   for t in np.linspace(0,1,max(2,int(length/.0007)+1)):edges.append(tuple(a.lerp(b,float(t))))
 bm.free();np.save(R/(prefix+'_sharp_edges.npy'),np.array(edges,dtype=np.float32))
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(50),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
 mat=bpy.data.materials.new(prefix+'_FieldBake');mat.use_nodes=True;o.data.materials.clear();o.data.materials.append(mat)
 for poly in o.data.polygons:poly.material_index=0
 nt=mat.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');geo=nt.nodes.new('ShaderNodeNewGeometry');vec=nt.nodes.new('ShaderNodeVectorMath');nt.links.new(em.outputs[0],out.inputs['Surface']);nt.links.new(vec.outputs[0],em.inputs['Color'])
 im=bpy.data.images.new(prefix+'_field',width=1024,height=1024,float_buffer=True,alpha=False);im.colorspace_settings.name='Non-Color';target=nt.nodes.new('ShaderNodeTexImage');target.image=im;nt.nodes.active=target
 for kind in ['position','normals']:
  if kind=='position':vec.operation='ADD';vec.inputs[1].default_value=(.55,.11,.1);nt.links.new(geo.outputs['Position'],vec.inputs[0])
  else:vec.operation='MULTIPLY_ADD';vec.inputs[1].default_value=(.5,.5,.5);vec.inputs[2].default_value=(.5,.5,.5);nt.links.new(geo.outputs['Normal'],vec.inputs[0])
  bpy.ops.object.bake(type='EMIT');a=np.empty(1024*1024*4,dtype=np.float32);im.pixels.foreach_get(a);np.save(R/(prefix+'_'+kind+'.npy'),a.reshape(1024,1024,4))
for o in asset:o['source_round']='round4/fixture.blend; grille round3';o['authored_axes']='Blender +Z up, -Y front; export_yup=True'
counts={o.name:sum(len(poly.vertices)-2 for poly in o.data.polygons) for o in asset}
assert sum(counts.values())<=3000,counts
stats=json.loads((P/'build-stats.json').read_text());stats.update({'objects':counts,'source_round':str(P/'fixture.blend'),'bent_louvre_centres_x_m':[-.14],'dent_depths_m':[.0014],'maximum_lateral_bend_m':.0012,'end_plate_chamfer_m':.004,'end_plate_chamfer_segments':2,'end_cap_lower_x_taper_m':.008,'end_cap_lower_width_taper_fraction':.075,'flange_dimensions_m':[.046,.220,.004],'flange_chamfer_m':.0012,'method':'Round4 sealed body and recessed channel; round3 grille with one shallow dent and 1.2 mm lateral bend; tapered 4 mm double-bevel end caps with inset end bolts and bevelled ceiling flanges'})
(R/'build-stats.json').write_text(json.dumps(stats,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(R/'working.blend'));print('BUILD_COMPLETE',counts,flush=True)
