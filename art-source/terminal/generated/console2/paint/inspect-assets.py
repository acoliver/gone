import bpy, json
from pathlib import Path
root=Path('art-source/terminal/generated/console2')
for filename in ('fit/console-a.glb','paint/console-body-fit.glb','paint/console-painted-normalized.glb'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/filename))
    vals=[]
    for o in bpy.context.scene.objects:
        if o.type=='MESH':
            vs=[o.matrix_world @ v.co for v in o.data.vertices]
            vals.append({'name':o.name,'verts':len(vs),'faces':len(o.data.polygons),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)],'matrix':[list(row) for row in o.matrix_world]})
    print(filename,json.dumps(vals),flush=True)
