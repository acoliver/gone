"""Evaluate faired cages, reduce by visibility, unwrap and export isolated fits."""
from pathlib import Path
from collections import defaultdict
import json,sys
import bpy,bmesh
import numpy as np
SOURCE=Path(__file__).resolve().parent;ROOT=SOURCE.parents[4];OUT=ROOT/'tmp/issue130-v3/fit1';sys.path.insert(0,str(SOURCE))
from reduce_low import reduce_body
from export4 import export
from unwrap8 import unwrap
bpy.ops.wm.open_mainfile(filepath=str(OUT/'medal-cage.blend'));bpy.context.preferences.filepaths.save_version=0
fit=json.loads((OUT/'fit-report.json').read_text());target=json.loads((OUT/'fairing-targets.json').read_text())
# Keep the exact source-plane body split beside the separately fitted cage.
bm=bmesh.new();bm.from_mesh(bpy.data.objects['Raw_Frozen_Uniform32mm'].data)
cut_height=(fit['split_body_raw_z']-fit['raw_origin'][2])*fit['uniform_scale']
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-9,plane_co=(0,0,cut_height),plane_no=(0,0,1),clear_outer=True)
filled=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces'];bmesh.ops.triangulate(bm,faces=filled);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges)
mesh=bpy.data.meshes.new('Body_RawGuide');bm.to_mesh(mesh);bm.free();guide=bpy.data.objects.new('Body_RawGuide',mesh);bpy.context.scene.collection.objects.link(guide)
cage=bpy.data.objects['Body_Cage'];weights={tuple(sorted(e[:2])):e[2] for e in target['creases']}
for p,co in zip(cage.data.vertices,target['vertices']):p.co=co
paths=json.loads((OUT/'sparse-cage.json').read_text())['paths']
rear_ids=next(p['vertices'] for p in paths if p['name']=='rear_transition')
rear_edges={tuple(sorted(e)) for e in zip(rear_ids,rear_ids[1:]+rear_ids[:1])}
for e in cage.data.edges:
 key=tuple(sorted(e.vertices));w=weights.get(key,0.)
 cage.data.attributes['crease_edge'].data[e.index].value=.3 if key in rear_edges else w
attr=cage.data.attributes.new('enamel_field7','INT','FACE')
for p,flag in zip(cage.data.polygons,target['field']):attr.data[p.index].value=int(flag)
cage.data.update()
fit['parts']['Body']={'vertices':len(cage.data.vertices),'faces':len(cage.data.polygons),'quads':sum(len(p.vertices)==4 for p in cage.data.polygons),'method':'Sparse measured front constrained triangulation, side quad bands and sparse generated rear; no dense remesher. Feature controls pinned, enamel single-cell boundary membrane, rounded central crease starts.'}

def evaluated(o,name,level):
 sub=o.modifiers[0];sub.levels=sub.render_levels=level;bpy.context.view_layer.update()
 mesh=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()));obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj

def triangulate(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),o.name;bm.to_mesh(o.data);bm.free();o.data.update()

highs=[];lows=[]
for name in ['Body','Loop','Bar']:
 c=bpy.data.objects[name+'_Cage'];high=evaluated(c,name+'_High',3);low=evaluated(c,name+'_Low',2);c.modifiers[0].levels=c.modifiers[0].render_levels=2
 highs.append(high);lows.append(low)
 for o in [high,low]:
  cr=o.data.attributes.get('crease_edge')
  for e in o.data.edges:e.use_edge_sharp=bool(cr and cr.data[e.index].value>=.99)
  for p in o.data.polygons:p.use_smooth=True
  o.data.update()
# Hardware's curvature and holes are protected with a sparse angle-derived
# edge graph before using the same visibility-weighted reduction as the body.
from projection import project
def projected_edges(mesh):
 mesh.calc_loop_triangles();protected=set()
 vertices=np.array([p.co[:] for p in mesh.vertices]);triangles=np.array([t.vertices[:] for t in mesh.loop_triangles])
 for camera in ['studio','game']:
  xy=project(vertices,camera);q=xy[triangles];a=q[:,1]-q[:,0];b=q[:,2]-q[:,0];orientation=a[:,0]*b[:,1]-a[:,1]*b[:,0]
  owners=defaultdict(list)
  for i,t in enumerate(triangles):
   for edge in zip(t,np.roll(t,-1)):owners[tuple(sorted(map(int,edge)))].append(i)
  for edge,fs in owners.items():
   if len(fs)==2 and orientation[fs[0]]*orientation[fs[1]]<0:protected.add(edge)
 return protected
for o,goal in zip(lows[1:],[2300,900]):
 mesh=o.data;mesh.calc_loop_triangles()
 cr=mesh.attributes.get('crease_edge') or mesh.attributes.new('crease_edge','FLOAT','EDGE')
 protected=projected_edges(mesh)
 if o.name.startswith('Loop'):
  silhouette_vertices={i for edge in protected for i in edge}
  protected|={tuple(sorted(e.vertices)) for e in mesh.edges if any(i in silhouette_vertices for i in e.vertices)}
 for e in mesh.edges:
  if tuple(sorted(e.vertices)) in protected:cr.data[e.index].value=.0001
 stats=reduce_body(o,goal);fit['parts'][o.name.split('_')[0]]['low_reduction']=stats
remaining=10500-sum(len(o.data.polygons) for o in lows[1:])
# Side support bands shape the clean subdivision but are not detected feature
# curves. Let geometric error reduce them; keep the silhouette and measured
# rear transition, rim steps, outline and relief edges immutable.
for value in lows[0].data.attributes['crease_edge'].data:
 if abs(value.value-.35)<1e-5:value.value=0.
body_mesh=lows[0].data;body_mesh.calc_loop_triangles()
contour_vertices={i for edge in projected_edges(body_mesh) for i in edge}
importance=np.array([300. if any(i in contour_vertices for i in t.vertices) else 1. for t in body_mesh.loop_triangles])
fit['parts']['Body']['low_reduction']=reduce_body(lows[0],remaining,importance)
fit['parts']['Body']['low_reduction']['projected_contour_face_weight']=300
fit['parts']['Body']['low_reduction']['projected_contour_weighted_input_triangles']=int((importance>1).sum())
for o in highs:triangulate(o)
for o in lows:triangulate(o)
# Continuous normal fans along the whole full-crease graph. Field interiors
# have neither crease weights nor sharp flags, regardless of depth or radius.
for o in highs+lows:
 m=o.data;field=m.attributes.get('enamel_field7');cr=m.attributes.get('crease_edge')
 owners=defaultdict(list)
 for p in m.polygons:
  for e in p.edge_keys:owners[tuple(sorted(e))].append(p.index)
 for e in m.edges:
  fs=owners[tuple(sorted(e.vertices))]
  if field and all(field.data[i].value for i in fs):e.use_edge_sharp=False
  elif field and any(field.data[i].value for i in fs):e.use_edge_sharp=True
  elif cr:e.use_edge_sharp=cr.data[e.index].value>=.99
fit['low_uv']=unwrap(lows)
# The bake source UVs need no contiguous charts. Isolate high triangles to
# guarantee finite disjoint exported coordinates without dense chart folds.
count=sum(len(o.data.polygons) for o in highs);side=int(np.ceil(np.sqrt(count)));tile=0
for o in highs:
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
 for p in o.data.polygons:
  x,y=tile%side/side,tile//side/side
  for li,co in zip(p.loop_indices,[(x+.1/side,y+.1/side),(x+.9/side,y+.1/side),(x+.1/side,y+.9/side)]):uv.data[li].uv=co
  tile+=1
export([bpy.data.objects['Raw_Frozen_Uniform32mm']],OUT/'raw-oriented.glb')
for label,objects in [('high',highs),('low',lows)]:
 export(objects,OUT/('medal-'+label+'.glb'));payload=[]
 for o in objects:
  m=o.data;m.calc_loop_triangles();d={'name':o.name,'vertices':[p.co[:] for p in m.vertices],'triangles':[list(t.vertices) for t in m.loop_triangles]}
  if m.attributes.get('enamel_field7'):d['field']=[m.attributes['enamel_field7'].data[t.polygon_index].value for t in m.loop_triangles];d['sharp_edges']=[list(e.vertices) for e in m.edges if e.use_edge_sharp]
  if label=='low':d['triangle_uv']=[[m.uv_layers.active.data[i].uv[:] for i in t.loops] for t in m.loop_triangles]
  payload.append(d);fit['parts'][o.name.split('_')[0]][label+'_triangles']=len(m.loop_triangles)
 (OUT/(label+'-arrays.json')).write_text(json.dumps(payload,separators=(',',':')));fit[label+'_triangles']=sum(len(o.data.loop_triangles) for o in objects)
assert fit['low_triangles']<=10500
for o in bpy.data.objects:
 o.hide_render=o not in lows
fit['visual_assessment']='Not performed.'
(OUT/'fit-report.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-fitted.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'medal-fitted.blend'))
print('BUILD_COMPLETE',fit['high_triangles'],fit['low_triangles'],flush=True)
