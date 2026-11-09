from pathlib import Path
import bpy, bmesh, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

R=Path(__file__).resolve().parent
PREV=R.parent/'round2'
bpy.ops.wm.open_mainfile(filepath=str(PREV/'fixture.blend'))
s=bpy.context.scene
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1
s.render.threads_mode='FIXED';s.render.threads=4
s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
s.render.bake.use_pass_direct=False;s.render.bake.use_pass_indirect=False
s.render.bake.use_pass_color=True
bpy.context.preferences.filepaths.save_version=0

def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def apply(o,m):
 active(o);bpy.ops.object.modifier_apply(modifier=m.name)

def cube(name,loc,dims):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 return o

def bevel(o,width,segments=1,angle=.52):
 m=o.modifiers.new('Small physical edge chamfer','BEVEL');m.width=width;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=angle
 apply(o,m)

def topology(o,label):
 bm=bmesh.new();bm.from_mesh(o.data)
 print('TOPOLOGY',label,len(bm.verts),len(bm.faces),sum(not e.is_manifold for e in bm.edges),'UNIQUE_Z',np.unique(np.round([v.co.z for v in bm.verts],7)).tolist(), 'SHAPE_KEYS',o.data.shape_keys,flush=True);bm.free()

def smooth(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 for e in bm.edges:e.smooth=len(e.link_faces)==2 and e.calc_face_angle(0)<math.radians(38)
 bm.to_mesh(o.data);bm.free()
 for p in o.data.polygons:p.use_smooth=True
 m=o.modifiers.new('Area weighted shading','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=60;apply(o,m)

source=bpy.data.objects['SOURCE_720_generated_painted'];source.hide_render=True;source.hide_set(True)
body=bpy.data.objects['Seed720_CleanedGeneratedBeam']
grille=bpy.data.objects['GeneratedUnderside_ArmouredGrille']
glass=bpy.data.objects['RecessedGlass_13mm']
# The body is the retained round-2 seed-720 mesh. Widen its existing pocket,
# leaving 10 mm shadow channels outside the raised rail shoulders.
cutter=cube('Temporary recessed channel cutter',(0,0,-.126),(1.014,.116,.100))
m=body.modifiers.new('Wider stepped grille receiving channel','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
apply(body,m);bpy.data.objects.remove(cutter,do_unlink=True)
# A two-segment bevel fairs the lower lip without changing the mounting envelope.
bevel(body,.00085,2,.45)
m=body.modifiers.new('Dissolve bevel coplanar diagonals','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(.5);apply(body,m)
# Keep the body envelope fixed after the bevel's tiny corner truncations.
coords=np.array([v.co[:] for v in body.data.vertices]);lo=coords.min(0);hi=coords.max(0)
for v in body.data.vertices:
 v.co.x=(v.co.x-(lo[0]+hi[0])/2)*1.1/(hi[0]-lo[0]);v.co.y=(v.co.y-(lo[1]+hi[1])/2)*.22/(hi[1]-lo[1]);v.co.z=(v.co.z-hi[2])*.1/(hi[2]-lo[2])
body.data.update()
# Dismiss triangulation before chamfering the retained perforated generated skin.
topology(grille,'round2 input')
m=grille.modifiers.new('Dissolve redundant flat diagonals','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=math.radians(.1);apply(grille,m)
topology(grille,'dissolved')
for v in grille.data.vertices:v.co.z=-.0995+(v.co.z+.100)*(.0095/.004)
grille.data.update()
# Give the two selected transverse louvres centre-span dents. The aperture XY
# positions do not move; the dent is a vertical deformation, not another slot.
bm=bmesh.new();bm.from_mesh(grille.data)
for y in [-.020,0,.020]:
 geom=[f for f in bm.faces if -.181<f.calc_center_median().x<-.099 or .239<f.calc_center_median().x<.322]
 edges=list({e for f in geom for e in f.edges});verts=list({v for e in edges for v in e.verts})
 bmesh.ops.bisect_plane(bm,geom=verts+edges+geom,dist=1e-7,plane_co=(0,y,0),plane_no=(0,1,0),clear_inner=False,clear_outer=False)
for v in bm.verts:
 for xc,amount in [(-.14,.0014),(.28,.0019)]:
  if abs(v.co.x-xc)<.0171:
   v.co.z+=amount*max(0,1-abs(v.co.y)/.033)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(grille.data);bm.free()
topology(grille,'bent')
# Chamfer only long exposed louvre edges. The short rounded slot ends retain
# their original 2 mm corner radius and do not spend triangles on hidden bevels.
bm=bmesh.new();bm.from_mesh(grille.data)
edges=[]
for e in bm.edges:
 d=e.verts[1].co-e.verts[0].co
 if abs(d.y)>.009 and abs(d.x)<.00001 and abs(e.verts[0].co.x)<.475 and max(abs(v.co.y) for v in e.verts)<.0341 and len(e.link_faces)==2 and e.calc_face_angle(0)>.6:
  edges.append(e)
bmesh.ops.bevel(bm,geom=edges,offset=.00065,segments=1,affect='EDGES',clamp_overlap=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(grille.data);bm.free()
topology(grille,'bevelled')
rails=[o for o in s.objects if o.name.startswith('RivetedEdgeRail')]
for o in rails:
 # A fresh chamfered rail gives a raised shoulder, rather than a flat strip.
 y=.044 if o.location.y>0 else -.044
 bpy.data.objects.remove(o,do_unlink=True)
 o=cube('RaisedChamferedRail',(0,y,-.0949),(.985,.008,.0078));bevel(o,.00085,1)
for o in list(s.objects):
 if o.name.startswith('RailRivet'):
  o.location.z=-.0991
# Recover spare triangles from fastener backs, without changing their size.
for o in list(s.objects):
 if o.name.startswith('RailRivet') or o.name.startswith('EndCapFastener'):
  m=o.modifiers.new('Fastener topology budget','DECIMATE');m.ratio=.56;apply(o,m)
# Add four side fasteners at actual generated side intersections. Their tails
# follow Blender -Z gravity, not the underside's transverse coordinate.
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons])
side_studs=[]
for x in [-.32,.32]:
 for sign in [-1,1]:
  hit,normal,_,_=bvh.ray_cast(Vector((x,sign*.3,-.045)),Vector((0,-sign,0)),.4)
  assert hit is not None
  bpy.ops.mesh.primitive_uv_sphere_add(segments=6,ring_count=3,radius=1,location=hit+normal*.00015)
  o=bpy.context.object;o.name='SideGravityFastener';o.scale=(.0024,.00075,.0024)
  active(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  side_studs.append({'x':float(hit.x),'y':float(hit.y),'z':float(hit.z)})
# Closed dark inner walls make the outer shadow channel non-emissive even at
# grazing angles; the diffuser is exposed through the fourteen apertures only.
for y in [-.0465,.0465]:cube('InnerChannelLightBaffle',(0,y,-.0835),(.990,.001,.015))
for x in [-.491,.491]:cube('InnerEndLightBaffle',(x,0,-.0835),(.001,.094,.015))
# The inherited source has a tapered centreline sliver at its left terminal.
# Full-depth end shoes close that sliver and join the hidden end baffles.
for x in [-.484,.484]:cube('ClosedGrilleEndShoe',(x,0,-.0948),(.022,.094,.0098))
metalparts=[o for o in s.objects if o.type=='MESH' and o not in [source,body,grille,glass]]
active(metalparts[0])
for o in metalparts:o.select_set(True)
bpy.ops.object.join();hardware=bpy.context.object;hardware.name='RaisedRails_Rivets_GravityFasteners'
for o in [body,grille,hardware]:smooth(o)
asset=[body,grille,hardware,glass]
# Bake positions and normals into fresh atlases so the material weather follows
# the modified recess, louvre side faces and rail chamfers in exported glTF.
for o,prefix,size in [(body,'body',1024),(grille,'grille',1024),(hardware,'hardware',1024)]:
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(50),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
 material=bpy.data.materials.new(prefix+'_FieldBake');material.use_nodes=True
 o.data.materials.clear();o.data.materials.append(material)
 for p in o.data.polygons:p.material_index=0
 nodes=material.node_tree.nodes;links=material.node_tree.links
 nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');geo=nodes.new('ShaderNodeNewGeometry');vec=nodes.new('ShaderNodeVectorMath')
 links.new(em.outputs[0],out.inputs['Surface']);links.new(vec.outputs[0],em.inputs['Color'])
 im=bpy.data.images.new(prefix+'_field',width=size,height=size,float_buffer=True,alpha=False);im.colorspace_settings.name='Non-Color'
 target=nodes.new('ShaderNodeTexImage');target.image=im;nodes.active=target
 for kind in ['position','normals']:
  if kind=='position':
   vec.operation='ADD';vec.inputs[1].default_value=(.55,.11,.1);links.new(geo.outputs['Position'],vec.inputs[0])
  else:
   vec.operation='MULTIPLY_ADD';vec.inputs[1].default_value=(.5,.5,.5);vec.inputs[2].default_value=(.5,.5,.5);links.new(geo.outputs['Normal'],vec.inputs[0])
  bpy.ops.object.bake(type='EMIT')
  a=np.empty(size*size*4,dtype=np.float32);im.pixels.foreach_get(a);np.save(R/(prefix+'_'+kind+'.npy'),a.reshape(size,size,4))
# Keep the same recessed 3 mm glass slab; assign a length/crosswise UV directly.
for poly in glass.data.polygons:
 for li in poly.loop_indices:
  co=glass.data.vertices[glass.data.loops[li].vertex_index].co+glass.location
  glass.data.uv_layers.active.data[li].uv=((co.x+.485)/.970,(co.y+.042)/.084)
for o in asset:
 o['source_round']='round2/fixture.blend';o['source_seed']=720;o['authored_axes']='Blender +Z up, -Y front; export_yup=True'
counts={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in asset}
print('TRIANGLE_BUDGET',json.dumps(counts),sum(counts.values()),flush=True)
assert sum(counts.values())<=3000,counts
(R/'build-stats.json').write_text(json.dumps({'objects':counts,'source_seed':720,'source_round':str(PREV/'fixture.blend'),'louvre_thickness_m':.0095,'louvre_edge_bevel_m':.00065,'bent_louvre_centres_x_m':[-.14,.28],'dent_depths_m':[.0014,.0019],'body_bevel_m':.00085,'body_bevel_segments':2,'channel_dimensions_m':[1.014,.116,.024],'side_shadow_gap_m':.010,'rail_dimensions_m':[.985,.008,.0078],'rail_chamfer_m':.00085,'side_fasteners':side_studs,'method':'Retained round-2 seed-720 body and perforated generated lower skin; wider body pocket, thick dented/chamfered louvres, raised rails, faired lower lip'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'working.blend'))
print('BUILD_COMPLETE',flush=True)
