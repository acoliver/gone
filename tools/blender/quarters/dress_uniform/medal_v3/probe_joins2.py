"""Measure projected orientation while selecting clean outline crease support."""
from pathlib import Path
import json
import bpy
import numpy as np
SOURCE=Path(__file__).resolve().parent;OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'medal-cage.blend'));o=bpy.data.objects['Body_Cage'];m=o.data;target=json.loads((OUT/'fairing-targets.json').read_text());d=json.loads((OUT/'sparse-cage.json').read_text());outline=set(next(p['vertices'] for p in d['paths'] if p['name']=='star_outline'));w={tuple(sorted(e[:2])):e[2] for e in target['creases']}
for p,q in zip(m.vertices,target['vertices']):p.co=q
o.modifiers[0].levels=3
report={}
for weight in [.65,.85,1.]:
 for e in m.edges:m.attributes['crease_edge'].data[e.index].value=weight if set(e.vertices)<=outline else w.get(tuple(sorted(e.vertices)),0.)
 bpy.context.view_layer.update();mesh=bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()));mesh.calc_loop_triangles();v=np.array([p.co[:] for p in mesh.vertices])*1000;t=np.array([p.vertices[:] for p in mesh.loop_triangles]);region=mesh.attributes['body_region2'];front=np.array([region.data[p.polygon_index].value==1 for p in mesh.loop_triangles]);n=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]);report[str(weight)]={'reversed_front_triangles':int((front&(n[:,1]>=0)).sum()),'front_triangles':int(front.sum()),'reversed_positions_mm':v[t[front&(n[:,1]>=0)]].mean(1).tolist()};bpy.data.meshes.remove(mesh)
(OUT/'outline-orientation-probe.json').write_text(json.dumps(report,indent=2));print('OUTLINE_PROBE',json.dumps({k:{n:v for n,v in row.items() if n!='reversed_positions_mm'} for k,row in report.items()}),flush=True)
