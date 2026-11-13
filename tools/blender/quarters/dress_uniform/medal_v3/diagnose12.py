"""Fixed-camera rotation controls and mesh-space shading diagnostics, no image judgment."""
from pathlib import Path
import json
import math
import sys
import bpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SOURCE=Path(__file__).resolve().parent
OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit1'
BEFORE=OUT
FOLDER=OUT
SUFFIX=('aligned-' if '--aligned' in sys.argv else '')+('after' if '--after' in sys.argv else 'before')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(FOLDER/'medal-fitted.blend'))
center=np.array(json.loads((OUT/'features.json').read_text())['star_center_mm'])
notches=json.loads((BEFORE/'local-measurements.json').read_text())['star']['high']['notches']
angles=np.array([n['angle_degrees'] for n in notches]);radii=np.array([n['radius_mm'] for n in notches])
image=bpy.data.images.load(str(FOLDER/'medal-low-normal.png'));image.colorspace_settings.name='Non-Color'
pixels=np.array(image.pixels[:],dtype=float).reshape(image.size[1],image.size[0],4)

def stats(x):
 x=np.asarray(x)
 if not x.size:return {'count':0}
 return {'count':int(x.size),'mean':float(x.mean()),'rms':float(np.sqrt(np.mean(x*x))),'p95':float(np.percentile(x,95)),'max':float(x.max()),'min':float(x.min())}

def angular(a,b):
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
 a=a/np.linalg.norm(a,axis=-1,keepdims=True);b=b/np.linalg.norm(b,axis=-1,keepdims=True)
 return np.degrees(np.arccos(np.clip(np.sum(a*b,axis=-1),-1,1)))

def selected(p,k):
 a=math.radians(angles[k]);axis=np.array([math.cos(a),math.sin(a)]);tangent=np.array([-axis[1],axis[0]])
 q=p[:,[0,2]]-center
 return (p[:,1]<0)&(abs(np.einsum('ij,j->i',q,axis)-radii[k])<1.5)&(abs(np.einsum('ij,j->i',q,tangent))<1.5)

def raster_normal_stats(uv_triangles,areas):
 values=[];weighted_sum=0.;represented_area=0.
 for uv,area in zip(uv_triangles,areas):
  p=uv*np.array(image.size);lower=np.maximum(np.ceil(p.min(0)-.5).astype(int),0);upper=np.minimum(np.floor(p.max(0)-.5).astype(int),np.array(image.size)-1)
  xx,yy=np.meshgrid(np.arange(lower[0],upper[0]+1),np.arange(lower[1],upper[1]+1))
  points=np.c_[xx.ravel()+.5,yy.ravel()+.5]
  bary=np.linalg.solve((p[1:]-p[0]).T,(points-p[0]).T).T
  inside=(bary[:,0]>=0)&(bary[:,1]>=0)&(bary.sum(1)<=1)
  if not inside.any():continue
  n=pixels[yy.ravel()[inside],xx.ravel()[inside],:3]*2-1;n/=np.linalg.norm(n,axis=1)[:,None]
  deviation=np.degrees(np.arccos(np.clip(n[:,2],-1,1)));values.extend(deviation.tolist());weighted_sum+=float(deviation.mean()*area);represented_area+=area
 return {'method':'All atlas texel centres inside each selected low UV triangle; physical triangle-area weighting, no padding texels. Triangles too small to contain a texel are excluded and represented area is reported.',
  'texel_deviation_degrees':stats(values),'area_weighted_mean_degrees':float(weighted_sum/represented_area),'represented_area_mm2':float(represented_area),'selected_area_mm2':float(np.sum(areas))}

report={'sector_definition':'Front notch, tangent +/-1.5 mm, radial +/-1.5 mm from measured notch; areas and densities differ with retained generated-fit topology.','notch_angles_degrees':angles.tolist(),'meshes':{},'projection':{},'visual_assessment':'Not performed.'}
for kind in ['Cage','High','Low']:
 mesh=bpy.data.objects['Body_'+kind].data;mesh.calc_loop_triangles()
 v=np.array([p.co[:] for p in mesh.vertices])*1000
 tri=np.array([p.vertices[:] for p in mesh.loop_triangles]);loops=np.array([p.loops[:] for p in mesh.loop_triangles])
 fn=np.array([p.normal[:] for p in mesh.loop_triangles]);cn=np.array([p.vector[:] for p in mesh.corner_normals])
 centroid=v[tri].mean(1);area=np.linalg.norm(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]),axis=1)/2
 edges=np.array([e.vertices[:] for e in mesh.edges]);em=v[edges].mean(1)
 sharp=np.array([e.use_edge_sharp for e in mesh.edges]);crease=mesh.attributes.get('crease_edge')
 weights=np.array([x.value for x in crease.data]) if crease else np.zeros(len(edges))
 adjacency={}
 for p in mesh.polygons:
  for edge in p.edge_keys:adjacency.setdefault(tuple(sorted(edge)),[]).append(p.index)
 split=[]
 for e in mesh.edges:
  faces=adjacency[tuple(sorted(e.vertices))]
  if len(faces)!=2:continue
  aa=[]
  for vi in e.vertices:
   nn=[]
   for fi in faces:
    p=mesh.polygons[fi];li=next(i for i in p.loop_indices if mesh.loops[i].vertex_index==vi);nn.append(cn[li])
   aa.append(float(angular(nn[0],nn[1])))
  if max(aa)>.01:split.append((e.index,max(aa)))
 split_ids={x[0] for x in split}
 rows=[]
 for k in range(5):
  mask=selected(centroid,k);vmask=selected(v,k);emask=selected(em,k)
  polys={mesh.loop_triangles[i].polygon_index for i in np.flatnonzero(mask)}
  deviation=angular(cn[loops[mask]],fn[mask,None,:]).reshape(-1)
  row={'angle_degrees':float(angles[k]),'triangles':int(mask.sum()),'vertices':int(vmask.sum()),'area_mm2':float(area[mask].sum()),'vertices_per_mm2':float(vmask.sum()/area[mask].sum()),
   'smooth_polygons':sum(mesh.polygons[i].use_smooth for i in polys),'flat_polygons':sum(not mesh.polygons[i].use_smooth for i in polys),
   'sharp_edges':int((sharp&emask).sum()),'nonzero_crease_edges':int(((weights>0)&emask).sum()),'crease_weights':stats(weights[emask&(weights>0)]),
   'split_edges':int(sum(emask[i] for i in split_ids)),'has_custom_normals':mesh.has_custom_normals,'corner_vs_face_degrees':stats(deviation)}
  worst=int(np.flatnonzero(mask)[deviation.reshape(-1,3).max(1).argmax()])
  row['worst_normal_triangle']={'index':worst,'coordinates_mm':v[tri[worst]].tolist(),'area_mm2':float(area[worst]),'face_normal':fn[worst].tolist(),'corner_normals':cn[loops[worst]].tolist(),'field':int(mesh.attributes['enamel_field7'].data[mesh.loop_triangles[worst].polygon_index].value)}
  if kind=='Low':
   uv=np.array([d.uv[:] for d in mesh.uv_layers.active.data]);sample_uv=uv[loops[mask]].mean(1)
   ix=np.clip((sample_uv[:,0]*image.size[0]).astype(int),0,image.size[0]-1);iy=np.clip((sample_uv[:,1]*image.size[1]).astype(int),0,image.size[1]-1)
   n=pixels[iy,ix,:3]*2-1;n/=np.linalg.norm(n,axis=1)[:,None]
   dev=np.degrees(np.arccos(np.clip(n[:,2],-1,1)))
   row['baked_normal_deviation_degrees']=stats(dev);row['baked_normal_area_weighted_mean_degrees']=float(np.average(dev,weights=area[mask]))
   row['baked_normal_raster']=raster_normal_stats(uv[loops[mask]],area[mask])
  rows.append(row)
 field=mesh.attributes['enamel_field7'];interior=np.array([len(adjacency[tuple(sorted(e.vertices))])==2 and all(field.data[i].value for i in adjacency[tuple(sorted(e.vertices))]) for e in mesh.edges])
 field_flags={'sharp_edges':int((sharp&interior).sum()),'crease_edges':int(((weights>0)&interior).sum()),'split_edges':int(sum(interior[i] for i in split_ids))}
 assert all(n==0 for n in field_flags.values()),(kind,field_flags)
 report['meshes'][kind]={'subdivision_modifiers':[{'type':m.type,'levels':m.levels,'render_levels':m.render_levels} for m in bpy.data.objects['Body_'+kind].modifiers if m.type=='SUBSURF'],'field_interior_flags':field_flags,'sectors':rows}
(OUT/('sector-diagnostics-'+SUFFIX+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
if '--measure-only' in sys.argv:sys.exit(0)

scene=bpy.context.scene
for col in bpy.data.collections:col.hide_render=False;col.hide_viewport=False
for o in bpy.data.objects:o.hide_render=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.seed=13012;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_x=scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.32,.32,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
clay=bpy.data.materials.new('RotationControlClay');clay.use_nodes=True
bs=clay.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.45,.45,.45,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.73
normalclay=clay.copy();tex=normalclay.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
nm=normalclay.node_tree.nodes.new('ShaderNodeNormalMap');normalclay.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);normalclay.node_tree.links.new(nm.outputs['Normal'],normalclay.node_tree.nodes['Principled BSDF'].inputs['Normal'])
for name,pos,power,size in [('Key',(-3,-4,6),650,4),('Fill',(4,-2,2),300,5),('Rear',(0,4,5),500,3)]:
 data=bpy.data.lights.new('Control'+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 o=bpy.data.objects.new('Control'+name,data);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,.5))-o.location).to_track_quat('-Z','Y').to_euler();o.hide_render=False
cd=bpy.data.cameras.new('FixedControl');cd.type='ORTHO';cd.clip_start=.01;cd.clip_end=100;cd.ortho_scale=2.3
cam=bpy.data.objects.new('FixedControl',cd);scene.collection.objects.link(cam)
# Face-on control removes perspective/tilt as well as image rotation confounds.
cam.location=(center[0]*.1,-9,center[1]*.1);cam.rotation_euler=(Vector((cam.location.x,0,cam.location.z))-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
manifest={'camera_position':list(cam.location),'camera_rotation':list(cam.rotation_euler),'ortho_scale':cd.ortho_scale,'rotation_axis':'Medal face normal, Blender Y','rotation_center_mm':[float(center[0]),0,float(center[1])],
 'method':'Identical fixed face-on camera and lights. Whole medal rotated offset+k*72 degrees. Each same bottom crop is extracted without image rotation. Generated notches are not exactly 72 degrees apart.','images':[]}
order=[3,4,0,1,2];offset=angles[3]+90
for label,filename in [('high','medal-high.glb'),('low-normalmapped','medal-low.glb')]:
 bpy.ops.import_scene.gltf(filepath=str(FOLDER/filename));objects=[o for o in bpy.context.selected_objects if o.type=='MESH']
 for obj in objects:
  for p in obj.data.vertices:p.co*=100
  obj.data.materials.clear();obj.data.materials.append(clay if label=='high' else normalclay)
  for f in obj.data.polygons:f.use_smooth=True
 for k,ni in enumerate(order):
  theta=angles[ni]+90 if '--aligned' in sys.argv else offset+k*72
  c=Vector((center[0]*.1,0,center[1]*.1));transform=Matrix.Translation(c)@Matrix.Rotation(math.radians(theta),4,'Y')@Matrix.Translation(-c)
  for obj in objects:obj.matrix_world=transform;obj.hide_render=False
  name=f'rotation-{SUFFIX}-{label}-{k}.png';scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
  manifest['images'].append({'file':name,'label':label,'k':k,'rotation_degrees':float(theta),'notch_degrees':float(angles[ni]),'notch_at_bottom_degrees':float((angles[ni]-theta)%360)})
 for obj in objects:obj.hide_render=True
if '--aligned' in sys.argv:
 manifest['method']='Additional exact-angle control: rotate each measured notch to 270 degrees. Same fixed camera and lights as the required 72-degree sequence; this removes the residual angular offsets caused by the generated star asymmetry.'
(OUT/('rotation-manifest-'+SUFFIX+'.json')).write_text(json.dumps(manifest,indent=2))
print('CONTROL12_COMPLETE',SUFFIX,flush=True)
