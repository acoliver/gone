"""Edit the existing generated-surface cages, not replacement primitives."""
from pathlib import Path
from collections import defaultdict
import json
import bpy,bmesh
import numpy as np
from mathutils.bvhtree import BVHTree
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2';BEFORE=OUT.parent/'fit1'
bpy.ops.wm.open_mainfile(filepath=str(BEFORE/'medal-fitted.blend'));bpy.context.preferences.filepaths.save_version=0
for o in list(bpy.data.objects):
 if o.name.endswith(('_High','_Low')) or o.name=='Body_RawGuide':bpy.data.objects.remove(o,do_unlink=True)
body=bpy.data.objects['Body_Cage'];m=body.data
if m.attributes.get('enamel_field7'):m.attributes.remove(m.attributes['enamel_field7'])
region=m.attributes.new('body_region2','INT','FACE');count=json.loads((OUT/'sparse-cage.json').read_text())['front_face_count']
for p in m.polygons:region.data[p.index].value=1 if p.index<count else 2 if len(p.vertices)==3 else 3
report={}
# Shrink the existing generated wire normally; leave its body contact cap fixed.
loop=bpy.data.objects['Loop_Cage'];m=loop.data;m.update();old=np.array([v.co[:] for v in m.vertices])*1000;normals=np.array([v.normal[:] for v in m.vertices]);fade=np.clip((old[:,2]-17.2)/2,0,1);offset=.22*fade
v=old-offset[:,None]*normals
# Its broad X cross-section is thicker than the measured Y/Z wire sections.
# Compress that existing section, preserving the generated centreline and hole.
v[:,0]*=1-.12*fade
neck=np.clip(1-(old[:,2]-old[:,2].min())/2.2,0,1);neck=neck*neck*(3-2*neck);v[:,2]-=.45*neck
for p,q in zip(m.vertices,v):p.co=q/1000
report['Loop']={'normal_inward_offset_mm':.22,'generated_lower_neck_extension_mm':.45,'neck_extension_fade_mm':2.2,'cross_section_x_scale_above_contact':.88,'contact_fade_z_mm':[17.2,19.2],'cage_extents_before_mm':np.ptp(old,axis=0).tolist(),'cage_extents_after_mm':np.ptp(v,axis=0).tolist(),'maximum_control_displacement_mm':float(np.linalg.norm(v-old,axis=1).max())}
# The generated bar cage has three disconnected rails. Retain the two rear
# rails, remove the duplicate left/front rail, and close their existing cut
# ends by extending those measured cage sections into an overlapping union.
bar=bpy.data.objects['Bar_Cage'];m=bar.data;old=np.array([p.co[:] for p in m.vertices])*1000
bm=bmesh.new();bm.from_mesh(m);bm.verts.ensure_lookup_table()
remove=[p for p in bm.verts if p.co.y<0];removed=len(remove);bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(m);bm.free();m.update()
v=np.array([p.co[:] for p in m.vertices])*1000;initial=v.copy();left=v[:,0]<0;right=~left
extensions={}
for label,mask in [('left',left),('right',right)]:
 q=v[mask];sign=1 if label=='left' else -1;cap=q[:,0].max() if sign==1 else q[:,0].min();distance=sign*(cap-q[:,0]);blend=np.clip(1-distance/1.5,0,1);extension=abs(cap)+.35
 v[mask,0]+=sign*extension*blend
 # Modest wire thinning around the measured rail's own mean cross-section.
 center=q[:,1:].mean(0);v[mask,1:]=center+.85*(q[:,1:]-center)
 extensions[label]={'cut_end_extension_mm':float(extension),'cut_end_before_x_mm':float(cap),'local_yz_scale':.85,'section_center_yz_mm':center.tolist()}
for p,q in zip(m.vertices,v):p.co=q/1000
# Union only the transformed generated cages. The voxel guide is a clean
# intermediate; its sparse cage samples this guide, never the raw lumps.
bpy.ops.object.select_all(action='DESELECT');bar.hide_set(False);bar.select_set(True);bpy.context.view_layer.objects.active=bar
bar.modifiers.clear()
for p in bar.data.vertices:p.co*=1000
sub=bar.modifiers.new('Generated_rail_limit','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
bar.data.remesh_voxel_size=.18;bar.data.use_remesh_preserve_volume=True;bpy.ops.object.voxel_remesh()
bm=bmesh.new();bm.from_mesh(bar.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),'Generated rail union is not manifold';bm.to_mesh(bar.data);bm.free()
guide=bar.data.copy();guide.calc_loop_triangles();tree=BVHTree.FromPolygons([p.co for p in guide.vertices],[t.vertices[:] for t in guide.loop_triangles],all_triangles=True)
bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=True,smooth_normals=True,mode='FACES',target_faces=180,seed=130)
assert len(bar.data.polygons)<500,'Sparse bar remeshing failed'
for p in bar.data.vertices:p.co=tree.find_nearest(p.co)[0]/1000
for p in bar.data.polygons:p.use_smooth=True
sub=bar.modifiers.new('Clean_surface_from_sparse_controls','SUBSURF');sub.levels=sub.render_levels=2
new=np.array([p.co[:] for p in bar.data.vertices])*1000
report['Bar']={'original_disconnected_rails':3,'removed_duplicate_front_rail_controls':removed,'rail_extensions':extensions,'voxel_union_resolution_mm':.18,'cage_extents_before_mm':np.ptp(old,axis=0).tolist(),'cage_extents_after_mm':np.ptp(new,axis=0).tolist(),'method':'Retain generated rear rails, thin existing Y/Z sections 15 percent and bridge their measured internal cut ends by overlap/voxel union; sparse guide sampling, no constructed bar profile.'}
fit=json.loads((OUT/'fit-report.json').read_text());fit['parts']['Loop']['thinning']=report['Loop'];fit['parts']['Bar']['thinning']=report['Bar'];fit['method']='Fit2 starts from fit1 generated-surface cages; slope-coupled sparse front fairing, tapering crease fans, heavily diffused boundary-faired rear, and consolidation/thinning of generated suspension.';fit['corrections']='Front feature depths fair along their original paths; outline and rim joins become semi-sharp C1 limit surfaces. Rear raw-depth attraction removed. Duplicate generated front bar rail removed; retained rear rail cut sections fused. No ideal surface, symmetry, donor mesh or dense raw projection.'
(OUT/'hardware-changes.json').write_text(json.dumps(report,indent=2));(OUT/'fit-report.json').write_text(json.dumps(fit,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-cage.blend'));print('EDIT_FIT2_COMPLETE',json.dumps(report),flush=True)
