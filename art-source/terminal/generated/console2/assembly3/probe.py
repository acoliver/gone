import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'assembly/console-with-keyboard.blend'))
body=bpy.data.objects['ConsoleBody'];tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
for x in [-.39,-.195,0,.195,.39]:
 print('X',x,flush=True)
 for z in np.arange(.470,.553,.002):
  h,n,_,_=tree.ray_cast(Vector((x,-2,float(z))),Vector((0,1,0)))
  print('Z',round(float(z),4),'Y',None if h is None else round(h.y,6),'NORMAL',list(n) if n else None,flush=True)
 for y in [-.69,-.68,-.67,-.66,-.65,-.64,-.62,-.60]:
  h,n,_,_=tree.ray_cast(Vector((x,y,.47)),Vector((0,0,1)))
  print('UNDER',y,list(h) if h else None,list(n) if n else None,flush=True)
