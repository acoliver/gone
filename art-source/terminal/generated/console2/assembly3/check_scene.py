import bpy,json,numpy as np,bmesh
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'console-with-keyboard.blend'))
s=bpy.context.scene;k=bpy.data.objects['Keyboard'];d=bpy.data.objects['DisplayPlane'];body=bpy.data.objects['ConsoleBody'];r=json.loads((O/'report.json').read_text());pts=np.array([list(k.matrix_world@v.co) for v in k.data.vertices]);front=r['deck']['front_y_m'];extra={'keyboard_frontmost_world_y_m':float(pts[:,1].min()),'frontmost_vertical_projection_clearance_mm':float((pts[:,1].min()-front)*1000),'render_settings_match':s.render.engine=='CYCLES' and s.cycles.samples==64 and s.cycles.use_denoising and (s.render.resolution_x,s.render.resolution_y)==(1600,900),'frames':{}}
for name in r['render']['views']:
 c=bpy.data.objects[name];p=np.array([list(world_to_camera_view(s,c,k.matrix_world@v.co)) for v in k.data.vertices]);q=np.array([list(world_to_camera_view(s,c,d.matrix_world@v.co)) for v in d.data.vertices]);extra['frames'][name]={'keyboard_ndc_min':p.min(0).tolist(),'keyboard_ndc_max':p.max(0).tolist(),'screen_ndc_min':q.min(0).tolist(),'screen_ndc_max':q.max(0).tolist()}
extra['operator_keyboard_in_frame']=all(extra['frames']['operator']['keyboard_ndc_min'][i]>=0 and extra['frames']['operator']['keyboard_ndc_max'][i]<=1 for i in [0,1]);extra['operator_screen_in_frame']=all(extra['frames']['operator']['screen_ndc_min'][i]>=0 and extra['frames']['operator']['screen_ndc_max'][i]<=1 for i in [0,1]);extra['operator_screen_above_keyboard']=extra['frames']['operator']['screen_ndc_min'][1]>extra['frames']['operator']['keyboard_ndc_max'][1]
before=np.load(O/'source-vertices.npy');after=np.array([v.co[:] for v in body.data.vertices]);faces=np.load(O/'source-faces.npy');edges=np.concatenate((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]));oldedge=np.linalg.norm(before[edges[:,1]]-before[edges[:,0]],axis=1);newedge=np.linalg.norm(after[edges[:,1]]-after[edges[:,0]],axis=1)
extra['maximum_edge_length_stretch_factor']=float((newedge/oldedge).max());extra['head_vertices_exactly_unchanged']=bool(np.array_equal(before[before[:,2]>=.625],after[before[:,2]>=.625]));extra['behind_deck_above_lip_vertices_exactly_unchanged']=bool(np.array_equal(before[(before[:,1]>=r['deck']['rear_y_m'])&(before[:,2]>=.478)],after[(before[:,1]>=r['deck']['rear_y_m'])&(before[:,2]>=.478)]))
assert extra['head_vertices_exactly_unchanged'] and extra['behind_deck_above_lip_vertices_exactly_unchanged']
for name,data in r['protected_objects_before'].items():
 ob=bpy.data.objects[name];assert data['matrix']==[list(row) for row in ob.matrix_world]
 if data['vertices']:assert data['vertices']==[list(v.co) for v in ob.data.vertices]
# Explain the stretch maximum using the source triangle's geometry, rather than
# treating its extremely narrow altitude as a representative texel density.
p=before[faces];e=p[:,1]-p[:,0];f=p[:,2]-p[:,0];cross=np.linalg.norm(np.cross(e,f),axis=1);longest=np.maximum.reduce([np.linalg.norm(e,axis=1),np.linalg.norm(f,axis=1),np.linalg.norm(p[:,2]-p[:,1],axis=1)]);altitude=cross/longest
extra['source_smallest_triangle_altitude_mm']=float(altitude.min()*1000)
extra['body_vertices']=len(before);extra['body_triangles']=len(faces)
wall=bpy.data.objects['Review rust wall'];floor=bpy.data.objects['Review dark steel floor'];extra['wall_y_m']=float(wall.location.y);extra['floor_z_m']=float(floor.location.z);extra['body_back_y_m']=float(after[:,1].max());extra['body_min_z_m']=float(after[:,2].min());assert wall.location.y==floor.location.z==0;assert abs(after[:,1].max())<1e-7 and abs(after[:,2].min())<1e-7
bm=bmesh.new();bm.from_mesh(body.data);extra['nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges);extra['boundary_edges']=sum(e.is_boundary for e in bm.edges);bm.free();assert extra['nonmanifold_edges']==extra['boundary_edges']==0
centre=Vector((0,(front+r['deck']['rear_y_m'])/2,0));a,b,c=r['deck']['plane_z_equals_ax_plus_by_plus_c'];centre.z=b*centre.y+c;assert (bpy.data.objects['KeyboardSocket'].location-centre).length<1e-7
assert extra['frontmost_vertical_projection_clearance_mm']>=0,'Keyboard overhangs front edge in vertical projection'
assert extra['render_settings_match'],'Incorrect render settings'
assert extra['operator_keyboard_in_frame'] and extra['operator_screen_in_frame'] and extra['operator_screen_above_keyboard'],'Operator camera framing fails'
(O/'scene-checks.json').write_text(json.dumps(extra,indent=2));print(json.dumps(extra,indent=2),flush=True);print('SCENE_CHECKS_PASSED',flush=True)
