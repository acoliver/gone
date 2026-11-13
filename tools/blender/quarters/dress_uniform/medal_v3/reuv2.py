"""Update only fitted-low UVs and preserve all existing positions and normals."""
from pathlib import Path
import sys,json
import bpy
SOURCE=Path(__file__).resolve().parent;sys.path.insert(0,str(SOURCE));OUT=SOURCE.parents[4]/'tmp/issue130-v3/fit2'
from unwrap2 import unwrap
from export4 import export
bpy.ops.wm.open_mainfile(filepath=str(OUT/'medal-fitted.blend'));bpy.context.preferences.filepaths.save_version=0
objects=[bpy.data.objects[p+'_Low'] for p in ['Body','Loop','Bar']];fit=json.loads((OUT/'fit-report.json').read_text());fit['low_uv']=unwrap(objects);export(objects,OUT/'medal-low.glb')
payload=json.loads((OUT/'low-arrays.json').read_text())
for d,o in zip(payload,objects):
 m=o.data;m.calc_loop_triangles();assert len(m.loop_triangles)==len(d['triangles']);d['triangle_uv']=[[m.uv_layers.active.data[i].uv[:] for i in t.loops] for t in m.loop_triangles]
(OUT/'low-arrays.json').write_text(json.dumps(payload,separators=(',',':')));(OUT/'fit-report.json').write_text(json.dumps(fit,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-fitted.blend'));print('REUV2_COMPLETE',flush=True)
