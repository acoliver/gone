import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'assembly3/console-with-keyboard.blend'))
b=bpy.data.objects['ConsoleBody'];v=np.array([x.co[:] for x in b.data.vertices]);t=BVHTree.FromPolygons([x.co for x in b.data.vertices],[p.vertices[:] for p in b.data.polygons])
print('OBJECTS',[(x.name,x.type,x.parent.name if x.parent else None,list(x.location)) for x in bpy.context.scene.objects],flush=True)
print('BOUNDS',v.min(0),v.max(0),flush=True)
for y in [-.715,-.711,-.708,-.705,-.700,-.695,-.690,-.680]:
 rows=[]
 for x in [-.45,-.39,-.3,0,.3,.39,.45]:
  h=t.ray_cast(Vector((x,y,.40)),Vector((0,0,1)))[0];rows.append(None if h is None else list(h))
 print('UNDER',y,rows,flush=True)
print('LIPVERT',v[(v[:,1]<-.69)&(v[:,2]>.44)&(v[:,2]<.55)].min(0),flush=True)
