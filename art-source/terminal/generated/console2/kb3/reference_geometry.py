import bpy,json
import numpy as np
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT.parents[1]/'kbmodel/keyboard.blend'))
s=bpy.context.scene
bpy.ops.object.camera_add(location=(0,-.015,1.60));cam=bpy.context.object;cam.data.lens=50;cam.rotation_euler=(Vector((0,0,.035))-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam
bpy.context.view_layer.update()
w,h=s.render.resolution_x,s.render.resolution_y
objects=[o for o in s.objects if o.type=='MESH' and o.name!='Dark studio floor']
def bounds(o):
 coords=[world_to_camera_view(s,cam,o.matrix_world@Vector(c)) for c in o.bound_box]
 return [min(v.x for v in coords)*w,(1-max(v.y for v in coords))*h,max(v.x for v in coords)*w,(1-min(v.y for v in coords))*h]
keys=sorted([o for o in objects if o.name.startswith('Keycap ')],key=lambda o:o.name)
r={'image_size':[w,h],'keyboard_bounds':np.array([bounds(o) for o in objects]).tolist(),'keys':[{'name':o.name,'rect':bounds(o)} for o in keys]}
(OUT/'reference_geometry.json').write_text(json.dumps(r,indent=2))
print('image',w,h,'keys',len(keys),'bounds',np.array(r['keyboard_bounds']).min(0),np.array(r['keyboard_bounds']).max(0))
