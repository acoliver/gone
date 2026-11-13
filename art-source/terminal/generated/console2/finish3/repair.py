import bpy, numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'geometry.blend'));b=bpy.data.objects['ConsoleBody'];bvh=BVHTree.FromPolygons([v.co for v in b.data.vertices],[p.vertices[:] for p in b.data.polygons])
for z in [.45,.48,.50,.52,.54,.56,.58,.60,.62,.64,.66,.68,.70,.72,.75,1.,1.2]:
 vals=[]
 for x in [-.5,-.4,0,.4,.5]:
  h,n,f,d=bvh.ray_cast(Vector((x,-2,z)),Vector((0,1,0)));vals.append(None if h is None else round(h.y,4))
 print('FRONT_DEPTH',z,vals,flush=True)
for y in [-.66,-.64,-.62,-.60,-.58,-.56,-.54,-.52,-.50,-.48,-.46,-.42,-.38,-.30,-.15]:
 vals=[]
 for x in [-.4,-.2,0,.2,.4]:
  h,n,f,d=bvh.ray_cast(Vector((x,y,.75)),Vector((0,0,-1)));vals.append(None if h is None else round(h.z,4))
 print('DECK_HEIGHT',y,vals,flush=True)
