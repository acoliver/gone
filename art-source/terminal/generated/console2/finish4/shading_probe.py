import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console.blend'));body=bpy.data.objects['ConsoleBody'];p=next(n for n in body.active_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Specular IOR Level'].default_value=.10
s=bpy.context.scene;s.camera=bpy.data.objects['ThreeQuarter'];s.render.filepath=str(O/'shading-probe.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'finish3/console.blend'));body=bpy.data.objects['ConsoleBody'];bv=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons]);rows=[]
for x in [.35,.4,.425,.45,.475,.5]:
 row=[]
 for y in np.arange(-.665,-.524,.01):
  h,n,f,d=bv.ray_cast(Vector((x,y,.645)),Vector((0,0,-1)))
  if h:row.append([float(y),float(h.z),float((h.z-(.49489266*y+.88683933))*1000)])
 rows.append({'x':x,'samples_y_z_plane_residual_mm':row})
print('RIGHT_DECK',json.dumps(rows),flush=True);(O/'right-deck-diagnosis.json').write_text(json.dumps(rows,indent=2))
