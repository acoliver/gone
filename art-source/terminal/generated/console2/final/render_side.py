import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console-with-keyboard.blend'));s=bpy.context.scene;r=json.loads((O/'report.json').read_text());cam=bpy.data.objects['side'];cam.location=(3.5,-1.3,1.50);cam.rotation_euler=(Vector((0,-.35,r['standing']['height_m']/2))-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam;bpy.context.view_layer.update()
for name in ['ConsoleBody','Keyboard','DisplayPlane']:
 ob=bpy.data.objects[name];p=np.array([list(world_to_camera_view(s,cam,ob.matrix_world@v.co)) for v in ob.data.vertices]);assert p[:,:2].min()>=0 and p[:,:2].max()<=1;r['render']['frames']['side'][name]={'min':p.min(0).tolist(),'max':p.max(0).tolist()}
r['render']['side_camera_note']='Near-side view at (3.5,-1.3,1.50) m aimed at housing mid-height, so both the rusty wall and steel floor are visible rather than viewing the wall edge-on.'
(O/'report.json').write_text(json.dumps(r,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'console-with-keyboard.blend'));s.render.filepath=str(O/'side.png');bpy.ops.render.render(write_still=True);print('SIDE_DONE',flush=True)
