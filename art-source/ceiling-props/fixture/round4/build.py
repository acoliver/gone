from pathlib import Path
import bpy,bmesh,math,json,numpy as np
R=Path(__file__).resolve().parent
PREV=R.parent/'round3'
bpy.ops.wm.open_mainfile(filepath=str(PREV/'fixture.blend'))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=4
s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
source=bpy.data.objects['SOURCE_720_generated_painted'];source.hide_render=True;source.hide_set(True)
body=bpy.data.objects['Seed720_CleanedGeneratedBeam'];grille=bpy.data.objects['GeneratedUnderside_ArmouredGrille'];glass=bpy.data.objects['RecessedGlass_13mm']
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
 active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def cube(name,loc,dims,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  m=o.modifiers.new('Physical end chamfer','BEVEL');m.width=bevel;m.segments=1;apply(o,m)
 return o
# Retain recessed channel, rounded generated body lip and louvre bevels.
# Move the selected bar laterally, strongest at its centre, rather than only
# lifting it. Its adjacent aperture becomes visibly narrow and skewed.
for v in grille.data.vertices:
 if abs(v.co.x+.14)<.0175:
  v.co.x+=.013*max(0,1-abs(v.co.y)/.047)
grille.data.update()
# Remove terminal source protrusions at the actual body, not with cover shoes.
bm=bmesh.new();bm.from_mesh(body.data)
for x,normal in [(-.510,(-1,0,0)),(.510,(1,0,0))]:
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(x,0,0),plane_no=normal,clear_outer=True,clear_inner=False)
 boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
# Retain rails, baffles and side studs; replace old terminal hardware.
o=bpy.data.objects['RaisedRails_Rivets_GravityFasteners'];active(o)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
parts=[]
for o in list(bpy.context.selected_objects):
 co=np.array([(o.matrix_world@v.co)[:] for v in o.data.vertices]);lo=co.min(0);hi=co.max(0);centre=(lo+hi)/2
 if abs(centre[0])>.53:
  bpy.data.objects.remove(o,do_unlink=True);continue
 if len(o.data.polygons)>8 and hi[2]<-.098:
  m=o.modifiers.new('Rail bolt budget','DECIMATE');m.ratio=.48;apply(o,m)
 parts.append(o)
for sign in [-1,1]:
 # Caps are entirely inside the specified silhouette, with a continuous
 # chamfered lower edge. The top flange occupies the mounting envelope.
 cap=cube('FlushBevelledEndPlate',(sign*.530,0,-.052),(.040,.218,.096),.0015)
 # Bolt heads sit behind the end plane, so recess their seats instead of
 # burying the entire heads in the solid plate or extending the silhouette.
 for y in [-.077,.077]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.0045,depth=.006,end_fill_type='NGON',location=(sign*.550,y,-.013),rotation=(0,math.pi/2,0))
  cutter=bpy.context.object;m=cap.modifiers.new('Recessed flange bolt seat','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(cap,m);bpy.data.objects.remove(cutter,do_unlink=True)
 parts.append(cap)
 parts.append(cube('CeilingMountFlange',(sign*.529,0,-.002),(.042,.220,.004),0))
 for y in [-.077,.077]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.0033,depth=.0012,end_fill_type='NGON',location=(sign*.5486,y,-.013),rotation=(0,math.pi/2,0))
  parts.append(bpy.context.object);parts[-1].name='InsetEndFlangeBolt'
active(parts[0])
for o in parts:o.select_set(True)
bpy.ops.object.join();hardware=bpy.context.object;hardware.name='RaisedRails_Rivets_GravityFasteners'
asset=[body,grille,hardware,glass]
for o in [body,grille,hardware]:
 bm=bmesh.new();bm.from_mesh(o.data)
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(38)
 bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=True
 m=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=60;apply(o,m)
# Atlas positions and normals are baked by Blender for physical weather masks.
for o,prefix,size in [(body,'body',1024),(grille,'grille',1024),(hardware,'hardware',1024)]:
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(50),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
 mat=bpy.data.materials.new(prefix+'_FieldBake');mat.use_nodes=True;o.data.materials.clear();o.data.materials.append(mat)
 for p in o.data.polygons:p.material_index=0
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');geo=nodes.new('ShaderNodeNewGeometry');vec=nodes.new('ShaderNodeVectorMath');links.new(em.outputs[0],out.inputs['Surface']);links.new(vec.outputs[0],em.inputs['Color'])
 im=bpy.data.images.new(prefix+'_field',width=size,height=size,float_buffer=True,alpha=False);im.colorspace_settings.name='Non-Color';target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
 for kind in ['position','normals']:
  if kind=='position':vec.operation='ADD';vec.inputs[1].default_value=(.55,.11,.1);links.new(geo.outputs['Position'],vec.inputs[0])
  else:vec.operation='MULTIPLY_ADD';vec.inputs[1].default_value=(.5,.5,.5);vec.inputs[2].default_value=(.5,.5,.5);links.new(geo.outputs['Normal'],vec.inputs[0])
  bpy.ops.object.bake(type='EMIT');a=np.empty(size*size*4,dtype=np.float32);im.pixels.foreach_get(a);np.save(R/(prefix+'_'+kind+'.npy'),a.reshape(size,size,4))
for o in asset:o['source_round']='round3/fixture.blend';o['authored_axes']='Blender +Z up, -Y front; export_yup=True'
counts={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in asset}
assert sum(counts.values())<=3000,counts
b=json.loads((PREV/'build-stats.json').read_text());b.update({'objects':counts,'source_round':str(PREV/'fixture.blend'),'skewed_louvre_centre_x_m':-.14,'maximum_lateral_bend_m':.013,'terminal_cut_x_m':[-.510,.510],'end_plate_dimensions_m':[.040,.218,.096],'end_plate_chamfer_m':.0015,'flange_dimensions_m':[.042,.220,.004],'method':'Round-3 channel and rounded lower lip retained; lateral louvre bend; source terminals trimmed and replaced by flush bevelled caps and inset bolted ceiling flanges'})
(R/'build-stats.json').write_text(json.dumps(b,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(R/'working.blend'));print('BUILD_COMPLETE',counts,flush=True)
