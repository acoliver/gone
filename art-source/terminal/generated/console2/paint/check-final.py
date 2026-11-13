import bpy,json
from pathlib import Path
p=Path('art-source/terminal/generated/console2/fit/console-painted.glb')
bpy.ops.import_scene.gltf(filepath=str(p))
for o in bpy.context.scene.objects:
 print(o.name,o.type, len(o.data.vertices) if o.type=='MESH' else '',len(o.data.polygons) if o.type=='MESH' else '', [list(row) for row in o.matrix_world])
