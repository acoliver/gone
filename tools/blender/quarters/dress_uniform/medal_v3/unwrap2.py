"""Use continuous front/rear charts and separate body-side charts for fit2."""
import math
import bpy
import numpy as np
from unwrap8 import unwrap as hardware_unwrap

def unwrap(objects):
 body=objects[0];hardware_unwrap(objects[1:]);m=body.data
 uv=m.uv_layers.active or m.uv_layers.new(name='UVMap');v=np.array([p.co[:] for p in m.vertices])*1000
 region=m.attributes['body_region2'];regions=[p.value for p in region.data];seam_triangles=0
 for p in m.polygons:
  q=v[list(p.vertices)];label=region.data[p.index].value
  if label in [1,2]:
   coords=q[:,[0,2]].copy();coords[:,0]+=100*label
  else:
   angle=np.arctan2(q[:,2],q[:,0]);
   if np.ptp(angle)>math.pi:angle[angle<0]+=2*math.pi;seam_triangles+=1
   coords=np.c_[angle*15.8+400,q[:,1]]
  for i,co in zip(p.loop_indices,coords):uv.data[i].uv=co
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False);bpy.ops.object.mode_set(mode='OBJECT')
 for p in m.vertices:p.select=False
 for p in m.edges:p.select=False
 bpy.context.tool_settings.mesh_select_mode=(False,False,True)
 for p in m.polygons:p.select=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.unwrap(method='MINIMUM_STRETCH',no_flip=True,iterations=50,margin_method='FRACTION',margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=body
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.select_all(action='SELECT');bpy.ops.uv.seams_from_islands(mark_seams=True,mark_sharp=False)
 bpy.ops.uv.pack_islands(rotate=True,scale=True,merge_overlap=False,margin_method='FRACTION',margin=.008,shape_method='CONCAVE');bpy.ops.object.mode_set(mode='OBJECT')
 return {'method':'Continuous front/rear charts initialized from evaluated X/Z, side initialized from azimuth/depth; all three receive intrinsic minimum-stretch relaxation to allocate area to steep walls. Hardware retains existing unwrap. No front island edge at a star notch; 0.008 chart padding.','side_angle_seam_triangles':seam_triangles}
