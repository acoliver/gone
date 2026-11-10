import bpy,numpy as np,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'source.blend')); b=bpy.data.objects['ConsoleBody']; vs=np.array([v.co for v in b.data.vertices]); print('PERCENTILES',np.percentile(vs[:,1],[0,1,5,10,25,50,75,90,95,99,100]),flush=True)
bvh=BVHTree.FromPolygons([v.co for v in b.data.vertices],[list(p.vertices) for p in b.data.polygons]); a=np.full((320,276),np.nan,np.float32)
for j in range(320):
 for i in range(276):
  loc,n,face,d=bvh.ray_cast(Vector((-.55+i*.004,-2,1.276-j*.004)),Vector((0,1,0)))
  if loc is not None:a[j,i]=loc.y
np.save(O/'front-depth.npy',a); np.savez(O/'geometry.npz',vertices=vs,faces=np.array([p.vertices[:] for p in b.data.polygons]),uv=np.array([v.uv for v in b.data.uv_layers.active.data]),loops=np.array([l.vertex_index for l in b.data.loops]))
print('DEPTH',np.nanpercentile(a,[0,5,10,25,50,75,90,95,99,100]),flush=True)
