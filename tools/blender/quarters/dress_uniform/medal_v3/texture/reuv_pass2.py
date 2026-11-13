"""Detach residual intrinsic-chart conflicts, retaining every geometry sample."""
import json
import sys
from pathlib import Path
import bpy

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[5]
OUT=ROOT/'tmp/issue130-v3/tex2/geom'
sys.path.insert(0,str(SOURCE.parent))
from atlas import isolate_overlapping_triangles
from export4 import export

bpy.ops.wm.open_mainfile(filepath=str(OUT/'medal-fitted.blend'))
bpy.context.preferences.filepaths.save_version=0
objects=[bpy.data.objects[p+'_Low'] for p in ['Body','Loop','Bar']]
for obj in objects:
    for collection in obj.users_collection:
        collection.hide_viewport=False
    obj.hide_set(False)
conflicts=isolate_overlapping_triangles(objects)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
bpy.ops.uv.pack_islands(rotate=True,scale=True,merge_overlap=False,margin_method='FRACTION',margin=.008,shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
export(objects,OUT/'medal-low.glb')
payload=json.loads((OUT/'low-arrays.json').read_text())
for part,obj in zip(payload,objects):
    mesh=obj.data;mesh.calc_loop_triangles()
    assert part['vertices']==[list(v.co) for v in mesh.vertices]
    assert part['triangles']==[list(t.vertices) for t in mesh.loop_triangles]
    part['triangle_uv']=[[mesh.uv_layers.active.data[i].uv[:] for i in t.loops] for t in mesh.loop_triangles]
(OUT/'low-arrays.json').write_text(json.dumps(payload,separators=(',',':')))
(OUT/'uv-repair.json').write_text(json.dumps({'detached_conflicting_triangles':conflicts,'method':'Existing atlas.isolate_overlapping_triangles then concave island packing at .008 padding; vertex positions and triangle identities unchanged.'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'medal-fitted.blend'))
print('UV_REPAIR_COMPLETE',conflicts,flush=True)
