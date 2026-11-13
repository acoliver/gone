"""Unwrap the cut mesh and isolate UV triangles collapsed by SLIM."""
import math
import bpy
from atlas import isolate_overlapping_triangles


def unwrap(objects):
 bpy.ops.object.select_all(action='DESELECT')
 for obj in objects:
  obj.select_set(True)
  for edge in obj.data.edges:edge.use_seam=False
 bpy.context.view_layer.objects.active=objects[0]
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=math.radians(42),island_margin=.006,margin_method='FRACTION',area_weight=.1,scale_to_bounds=False)
 bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
 bpy.ops.uv.unwrap(method='MINIMUM_STRETCH',no_flip=True,iterations=30,margin_method='FRACTION',margin=.006)
 bpy.ops.object.mode_set(mode='OBJECT')
 collapsed=0
 for obj in objects:
  mesh=obj.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active.data
  for t in mesh.loop_triangles:
   p=[uv[i].uv.copy() for i in t.loops];a,b=p[1]-p[0],p[2]-p[0]
   area=abs(a.x*b.y-a.y*b.x)/2
   if area<=1e-10:
    assert len(mesh.polygons[t.polygon_index].vertices)==3
    x=2+collapsed*.03
    for loop,co in zip(t.loops,[(x,0),(x+.02,0),(x,.02)]):uv[loop].uv=co
    collapsed+=1
 conflicts=isolate_overlapping_triangles(objects)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.select_all(action='SELECT')
 bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
 bpy.ops.uv.pack_islands(rotate=True,scale=True,merge_overlap=False,margin_method='FRACTION',margin=.006,shape_method='CONCAVE')
 bpy.ops.object.mode_set(mode='OBJECT')
 print('UV8_ISOLATED_COLLAPSED_TRIANGLES',collapsed,'OVERLAP_TRIANGLES',conflicts,flush=True)
 return {'collapsed_uv_triangles_detached':collapsed,'overlapping_uv_triangles_detached':conflicts,'method':'Smart-project charts, minimum-stretch SLIM, detach collapsed UV triangles and overlap participants, then pack all charts with the existing 0.006 fractional margin. Geometry and export UV checks unchanged.'}
