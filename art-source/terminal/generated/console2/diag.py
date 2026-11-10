import bpy
from collections import Counter
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath='art-source/terminal/generated/console2/kbfit2/keyboard-painted.glb');o=next(x for x in bpy.context.scene.objects if x.type=='MESH');print('bounds',o.dimensions);print('normals',Counter(round(p.normal.z,1) for p in o.data.polygons));print('z',min(v.co.z for v in o.data.vertices),max(v.co.z for v in o.data.vertices));print('faces',len(o.data.polygons))
