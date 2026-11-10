import bpy,json
import numpy as np
from pathlib import Path
root=Path('art-source/terminal/generated/console2')
def read(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/path))
    result={}
    for o in bpy.context.scene.objects:
        if o.type=='EMPTY' or o.type=='MESH':
            result[o.name]={'type':o.type,'matrix':[list(row) for row in o.matrix_world],'bounds':([[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]] if o.type=='MESH' else None),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else None}
    return result
base=read('fit/console-a.glb'); final=read('fit/console-painted.glb')
assert set(('ConsoleBody','DisplayPlane','ScreenSocket','KeyboardSocket')) <= set(final), final.keys()
for name in ('DisplayPlane','ScreenSocket','KeyboardSocket'):
    assert np.allclose(base[name]['matrix'],final[name]['matrix'],atol=1e-5), (name,base[name],final[name])
    if base[name]['bounds'] is not None: assert np.allclose(base[name]['bounds'],final[name]['bounds'],atol=1e-5),name
assert final['ConsoleBody']['triangles']==39000,final['ConsoleBody']
print(json.dumps({'objects':final,'accessories_match_original':True},indent=2))
