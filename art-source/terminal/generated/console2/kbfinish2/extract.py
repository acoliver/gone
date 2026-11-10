import bpy, numpy as np, json
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(OUT.parent/'kbfinish/keyboard.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Keyboard'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
v=np.array([v.co[:] for v in ob.data.vertices]);lo=v.min(0);hi=v.max(0)
print('bounds',lo,hi,'faces',len(ob.data.polygons),flush=True)
bvh=BVHTree.FromPolygons([Vector(p) for p in v],[tuple(p.vertices) for p in ob.data.polygons])
xs=np.linspace(lo[0],hi[0],round((hi[0]-lo[0])*1000)+1);ys=np.linspace(lo[1],hi[1],round((hi[1]-lo[1])*1000)+1)
h=np.full((len(ys),len(xs)),np.nan,np.float32)
for j,y in enumerate(ys):
 for i,x in enumerate(xs):
  hit=bvh.ray_cast(Vector((x,y,hi[2]+.1)),Vector((0,0,-1)))
  if hit[0] is not None:h[j,i]=hit[0].z
np.savez(OUT/'height.npz',height=h,xs=xs,ys=ys)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source.blend'))
print('height saved',h.shape,'finite',np.isfinite(h).sum(),flush=True)
