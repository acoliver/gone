"""Reach the fitted rear without projecting the star's inner wall onto its field."""
from pathlib import Path
import json
import sys
import bpy
import numpy as np

SOURCE=Path(__file__).resolve().parent;sys.path.insert(0,str(SOURCE))
from glb_normals import preserve_normals
OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.bake.use_selected_to_active=True;scene.render.bake.normal_space='TANGENT'
scene.render.bake.cage_extrusion=.0006;scene.render.bake.max_ray_distance=.0012
scene.render.bake.margin=8;scene.render.bake.use_clear=False
assets={}
for kind in ['high','low']:
 bpy.ops.import_scene.gltf(filepath=str(OUT/('medal-'+kind+'.glb')))
 assets[kind]={o.name.split('_')[0]:o for o in bpy.context.selected_objects if o.type=='MESH'}
base=bpy.data.images.load(str(OUT/'medal-low-normal.png'));base.colorspace_settings.name='Non-Color'
w,h=base.size;old=np.array(base.pixels[:],dtype=np.float32).reshape(h,w,4)
wide=bpy.data.images.new('Fit12_Rear_Reach',width=w,height=h,alpha=False);wide.generated_color=(.5,.5,1,1);wide.colorspace_settings.name='Non-Color'
for part,low in assets['low'].items():
 material=bpy.data.materials.new('Fit12_'+part+'_Bake');material.use_nodes=True
 tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=wide if part=='Body' else base;material.node_tree.nodes.active=tex
 low.data.materials.clear();low.data.materials.append(material)
 for face in low.data.polygons:face.use_smooth=True
 if part=='Body':
  bpy.ops.object.select_all(action='DESELECT');low.select_set(True);assets['high'][part].select_set(True);bpy.context.view_layer.objects.active=low
  bpy.ops.object.bake(type='NORMAL');tex.image=base
 nm=material.node_tree.nodes.new('ShaderNodeNormalMap');nm.space='TANGENT'
 material.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);material.node_tree.links.new(nm.outputs['Normal'],material.node_tree.nodes['Principled BSDF'].inputs['Normal'])
mask=np.zeros((h,w),bool);other_core=np.zeros((h,w),bool);triangles=0
for part,obj in assets['low'].items():
 mesh=obj.data;mesh.calc_loop_triangles();uv=np.array([x.uv[:] for x in mesh.uv_layers.active.data])
 for tri in mesh.loop_triangles:
  rear=part=='Body' and tri.normal.y>.25 and np.mean([mesh.vertices[i].co.y for i in tri.vertices])>0
  target=mask if rear else other_core;triangles+=int(rear)
  p=uv[list(tri.loops)]*np.array([w,h]);lower=np.maximum(np.ceil(p.min(0)-.5).astype(int),0);upper=np.minimum(np.floor(p.max(0)-.5).astype(int),[w-1,h-1])
  xx,yy=np.meshgrid(np.arange(lower[0],upper[0]+1),np.arange(lower[1],upper[1]+1));points=np.c_[xx.ravel()+.5,yy.ravel()+.5]
  b=np.linalg.solve((p[1:]-p[0]).T,(points-p[0]).T).T;inside=(b[:,0]>=0)&(b[:,1]>=0)&(b.sum(1)<=1)
  target[yy.ravel()[inside],xx.ravel()[inside]]=True
# Keep padding with its own rear charts. Existing chart margins separate these
# charts from the front; the non-rear atlas remains byte-identical.
core=mask.copy()
for axis in [0,1]:
 source=mask.copy()
 for shift in range(1,9):
  if axis==0:mask[shift:,:]|=source[:-shift,:];mask[:-shift,:]|=source[shift:,:]
  else:mask[:,shift:]|=source[:,:-shift];mask[:,:-shift]|=source[:,shift:]
mask&=~other_core
new=np.array(wide.pixels[:],dtype=np.float32).reshape(h,w,4);combined=old.copy();combined[mask]=new[mask]
assert np.array_equal(old[~mask],combined[~mask]) and np.array_equal(old[other_core],combined[other_core])
changed_pixels=int(np.any(np.rint(old*255).astype(np.uint8)!=np.rint(combined*255).astype(np.uint8),axis=2).sum())
if '--require-identical' in sys.argv:assert changed_pixels==0,changed_pixels
base.pixels.foreach_set(combined.ravel());base.filepath_raw=str(OUT/'medal-low-normal.png');base.file_format='PNG';base.save()
bpy.ops.object.select_all(action='DESELECT')
for low in assets['low'].values():low.select_set(True)
bpy.context.view_layer.objects.active=assets['low']['Body']
bpy.ops.export_scene.gltf(filepath=str(OUT/'medal-low-normalmapped.glb'),use_selection=True,export_format='GLB',export_yup=True,export_normals=True,export_texcoords=True,export_tangents=True,export_materials='EXPORT')
changes=preserve_normals(OUT/'medal-low.glb',OUT/'medal-low-normalmapped.glb');(OUT/'normal-export-roundtrip.json').write_text(json.dumps(changes,indent=2))
report={'cause':'Rear reduction can exceed the front-safe reach; retain the established separate rear-only bake without changing front/hardware core texels.',
 'method':'Additional selected-to-active rear bake, merged only into rear UV triangles and their 8-pixel padding; retain the existing front-safe normal bake and hardware texels.',
 'rear_triangles':triangles,'rear_core_texels':int(core.sum()),'rear_including_padding_texels':int(mask.sum()),'outside_mask_pixels_unchanged':True,'changed_quantized_pixels_this_run':changed_pixels,'rear_cage_extrusion_m':.0006,'rear_max_ray_distance_m':.0012,'visual_assessment':'Not performed.'}
metadata=json.loads((OUT/'normal-bake.json').read_text());metadata[0]['rear_only_pass']=report;(OUT/'normal-bake.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(report,indent=2),flush=True);print('REAR12_BAKED',flush=True)
