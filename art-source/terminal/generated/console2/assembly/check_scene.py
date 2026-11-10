import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console-with-keyboard.blend'))
s=bpy.context.scene;k=bpy.data.objects['Keyboard'];d=bpy.data.objects['DisplayPlane'];r=json.loads((O/'report.json').read_text());pts=np.array([list(k.matrix_world@v.co) for v in k.data.vertices]);front=r['deck']['front_y_m'];extra={'keyboard_frontmost_world_y_m':float(pts[:,1].min()),'frontmost_vertical_projection_clearance_mm':float((pts[:,1].min()-front)*1000),'render_settings_match':s.render.engine=='CYCLES' and s.cycles.samples==64 and s.cycles.use_denoising and (s.render.resolution_x,s.render.resolution_y)==(1600,900),'frames':{}}
for name in r['render']['views']:
 c=bpy.data.objects[name];p=np.array([list(world_to_camera_view(s,c,k.matrix_world@v.co)) for v in k.data.vertices]);q=np.array([list(world_to_camera_view(s,c,d.matrix_world@v.co)) for v in d.data.vertices]);extra['frames'][name]={'keyboard_ndc_min':p.min(0).tolist(),'keyboard_ndc_max':p.max(0).tolist(),'screen_ndc_min':q.min(0).tolist(),'screen_ndc_max':q.max(0).tolist()}
extra['operator_keyboard_in_frame']=all(extra['frames']['operator']['keyboard_ndc_min'][i]>=0 and extra['frames']['operator']['keyboard_ndc_max'][i]<=1 for i in [0,1]);extra['operator_screen_in_frame']=all(extra['frames']['operator']['screen_ndc_min'][i]>=0 and extra['frames']['operator']['screen_ndc_max'][i]<=1 for i in [0,1]);extra['operator_screen_above_keyboard']=extra['frames']['operator']['screen_ndc_min'][1]>extra['frames']['operator']['keyboard_ndc_max'][1]
(O/'scene-checks.json').write_text(json.dumps(extra,indent=2));print(json.dumps(extra,indent=2),flush=True)
assert extra['frontmost_vertical_projection_clearance_mm']>=0,'Keyboard overhangs front edge in vertical projection'
assert extra['render_settings_match'],'Incorrect render settings'
assert extra['operator_keyboard_in_frame'] and extra['operator_screen_in_frame'] and extra['operator_screen_above_keyboard'],'Operator camera framing fails'
print('SCENE_CHECKS_PASSED',flush=True)
