import bpy,sys,json
from pathlib import Path
root=Path('/Volumes/XS1000/acoliver/projects/gone/branch-3/tmp/issue91/panelmodel')
for p in sorted((root/'meshes').glob('*.glb')):
 bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=str(p)); vs=[v.co[:] for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]; lo=[min(v[i] for v in vs) for i in range(3)]; hi=[max(v[i] for v in vs) for i in range(3)]; print(p.name,'bounds',lo,hi,'dims',[hi[i]-lo[i] for i in range(3)],flush=True)
