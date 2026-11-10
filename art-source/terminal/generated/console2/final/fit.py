import bpy,json,numpy as np,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;A=O.parent/'assembly3';sys.path.insert(0,str(A))
from placement import tree_for,frame
bpy.ops.wm.open_mainfile(filepath=str(O/'deformed.blend'))
r=json.loads((O/'geometry-report.json').read_text());old=json.loads((A/'report.json').read_text());delta=r['standing']['delta_m'];body=bpy.data.objects['ConsoleBody'];key=bpy.data.objects['Keyboard'];base=bpy.data.objects['KeyboardBase'];display=bpy.data.objects['DisplayPlane'];tree=tree_for(body);world=tree_for(key);local=tree_for(key,False);dt=tree_for(display)
a,b,c=r['deck']['plane_z_equals_ax_plus_by_plus_c'];F=frame(a,b);normal=F.col[2];centre=bpy.data.objects['KeyboardSocket'].location.copy();front=r['deck']['front_y_m'];depth=r['deck']['along_slope_depth_m'];gaps=[]
for row in old['keyboard']['underside_samples']:
 h=Vector(row['local_underside_m']);start=key.matrix_world@h;hit=tree.ray_cast(start,-normal,.02)
 if hit[0] is None:
  back=tree.ray_cast(start,normal,.02);gap=-back[3] if back[0] else None
 else:gap=hit[3]
 gaps.append({'world_underside_m':list(start),'gap_mm':None if gap is None else gap*1000})
intersections=world.overlap(tree);wp=np.array([list(key.matrix_world@v.co) for v in key.data.vertices]);proj=(wp-np.array(centre))@np.array(F);eye=Vector((0,front-.55,1.65));keytops=[]
for row in old['keyboard']['keytops']:
 target=key.matrix_world@Vector(row['local_top_m']);ray=(target-eye).normalized();distance=(target-eye).length;hits=[]
 for name,t in [('ConsoleBody',tree),('Keyboard',world),('DisplayPlane',dt)]:
  h=t.ray_cast(eye,ray)
  if h[0] is not None:hits.append((h[3],name))
 first=min(hits);near=tree.find_nearest(target);keytops.append({'key':row['key'],'world_top_m':list(target),'visible':first[0]>=distance-.0002,'first_hit':first[1],'console_clearance_mm':near[3]*1000})
screen=sum((display.matrix_world@v.co for v in display.data.vertices),Vector())/len(display.data.vertices);ray=(screen-eye).normalized();hits=[]
for name,t in [('ConsoleBody',tree),('Keyboard',world),('DisplayPlane',dt)]:
 h=t.ray_cast(eye,ray)
 if h[0] is not None:hits.append({'object':name,'distance_m':h[3]})
hits.sort(key=lambda h:h['distance_m']);frontclear=proj[:,1].min()+depth/2;rearclear=depth/2-proj[:,1].max();side=r['deck']['usable_width_m']/2-max(abs(proj[:,0].min()),abs(proj[:,0].max()))
checks={'nine_support_gaps_0_to_1_5_mm':all(g['gap_mm'] is not None and 0<=g['gap_mm']<=1.5 for g in gaps),'no_intersection':len(intersections)==0,'no_front_overhang':wp[:,1].min()>=front and frontclear>=0,'no_rear_overhang':rearclear>=0,'no_side_overhang':side>=0,'key_tops_clear_head':min(k['console_clearance_mm'] for k in keytops)>0 and not intersections,'at_least_27_of_29_visible':sum(k['visible'] for k in keytops)>=27,'screen_ray_hits_DisplayPlane_first':hits[0]['object']=='DisplayPlane'}
r['keyboard']={'uniform_scale':float(base.scale.x),'width_m':float(key.dimensions.x),'deck_frame_dimensions_m':np.ptp(proj,axis=0).tolist(),'front_vertical_clearance_mm':float((wp[:,1].min()-front)*1000),'front_deck_clearance_mm':float(frontclear*1000),'rear_deck_clearance_mm':float(rearclear*1000),'side_clearance_mm':float(side*1000),'support_samples':gaps,'intersections':len(intersections),'visible_keytops':sum(k['visible'] for k in keytops),'keytop_count':len(keytops),'keytops':keytops,'operator_eye_m':list(eye),'screen_ray_hits':hits,'minimum_keytop_body_clearance_mm':min(k['console_clearance_mm'] for k in keytops)};r['checks']={k:bool(v) for k,v in checks.items()}
placement=json.loads((A/'keyboard-placement.json').read_text());placement['location']=list(base.location);placement['glTF_y_up']['location']=[base.location.x,base.location.z,-base.location.y];placement['standing_lift_m']=delta
(O/'keyboard-placement.json').write_text(json.dumps(placement,indent=2));(O/'fit-report.json').write_text(json.dumps(r,indent=2));print('FIT',json.dumps({'standing':r['standing'],'checks':r['checks'],'keyboard':{k:v for k,v in r['keyboard'].items() if k not in ['support_samples','keytops']}}),flush=True)
assert all(checks.values()),checks
print('FIT_DONE',flush=True)
