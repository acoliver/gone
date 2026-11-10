import bpy,json,math,numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

def tree_for(ob,world=True):
 return BVHTree.FromPolygons([(ob.matrix_world@v.co) if world else v.co for v in ob.data.vertices],[p.vertices[:] for p in ob.data.polygons])

def frame(a,b):
 n=Vector((-float(a),-float(b),1)).normalized();x=Vector((1,0,float(a))).normalized();y=n.cross(x).normalized()
 return Matrix((x,y,n)).transposed()

def place(O,report):
 P=O.parent;body=bpy.data.objects['ConsoleBody'];tree=tree_for(body)
 geometry=json.loads((O/'geometry-report.json').read_text());deck=geometry['deck'];fit=np.array(deck['plane_z_equals_ax_plus_by_plus_c']);samples=deck['ray_samples'];res=np.array(samples)[:,2]-np.c_[np.array(samples)[:,:2],np.ones(25)]@fit
 F=frame(*fit[:2]);normal=F.col[2];front=deck['front_y_m'];rear=deck['rear_y_m'];rears=deck['rear_boundary_samples_y_m']
 key=bpy.data.objects['Keyboard'];base=bpy.data.objects['KeyboardBase'];local=tree_for(key,False)
 # Find a conservative common planar width across the occupied depth.
 widths=[]
 for y in np.linspace(front+.012,rear-.010,5):
  limits=[]
  for sign in [-1,1]:
   end=0
   for x in np.arange(0,.55,.001):
    h,n,_,_=tree.ray_cast(Vector((float(sign*x),float(y),.9)),Vector((0,0,-1)))
    if h is None or abs(h.z-(fit[0]*sign*x+fit[1]*y+fit[2]))>.0015 or n.dot(normal)<.96:break
    end=float(x)
   limits.append(end)
  widths.append(limits)
 halfwidth=min(min(row) for row in widths);deckwidth=2*halfwidth
 # The generated underside is flat but tilted relative to its bounding-box axes.
 # Fit its real support plane rather than seating the bounding box through the deck.
 under=[]
 for y in np.linspace(-.075,.075,5):
  for x in np.linspace(-.30,.30,5):
   h=local.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)))[0];assert h is not None
   under.append(list(h))
 u=np.array(under);UA=np.c_[u[:,:2],np.ones(25)];uf=np.linalg.lstsq(UA,u[:,2],rcond=None)[0];ur=u[:,2]-UA@uf;UF=frame(*uf[:2]);R=F@UF.transposed();verts=np.array([v.co[:] for v in key.data.vertices]);level=np.einsum('ni,ij->nj',verts,np.array(UF))
 lo=level.min(0);hi=level.max(0);depth=(rear-front)*math.sqrt(1+fit[1]**2);scale=min((depth-.020)/(hi[1]-lo[1]),(deckwidth-.060)/(hi[0]-lo[0]))
 localcentre=UF@Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,float(uf[2]/math.sqrt(1+uf[0]**2+uf[1]**2))))
 centre=Vector((0,(front+rear)/2,fit[1]*(front+rear)/2+fit[2]))
 position=centre+normal*.0005-(R@localcentre)*scale
 # Keep the entire raised-key silhouette inside the front edge without reducing
 # the requested depth. The remaining 20 mm depth allowance need not be split
 # equally between front and rear in the inclined support frame.
 rotated=np.einsum('ij,nj->ni',np.array(R),verts-np.array(localcentre))
 projected_front=centre.y+normal.y*.0005+scale*rotated[:,1].min()
 slide=max(0,float(front+.0001-projected_front))/F.col[1].y
 position+=F.col[1]*slide
 socket=bpy.data.objects['KeyboardSocket'];socket.location=centre;socket.rotation_mode='QUATERNION';socket.rotation_quaternion=F.to_quaternion()
 base.location=position;base.rotation_mode='QUATERNION';base.rotation_quaternion=R.to_quaternion();base.scale=(scale,)*3;bpy.context.view_layer.update();world=tree_for(key)
 gaps=[]
 for y in [-.075,0,.075]:
  for x in [-.3,0,.3]:
   h=local.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)))[0];start=key.matrix_world@h;hit=tree.ray_cast(start,-normal,.02)
   # A ray in the opposite direction reports penetration with a negative sign.
   if hit[0] is None:
    back=tree.ray_cast(start,normal,.02);gap=-back[3] if back[0] else None
   else:gap=hit[3]
   gaps.append({'local_underside_m':list(h),'world_underside_m':list(start),'gap_mm':None if gap is None else float(gap*1000)})
 overlaps=world.overlap(tree);wp=np.array([list(key.matrix_world@v.co) for v in key.data.vertices]);proj=np.einsum('ni,ij->nj',wp-np.array(centre),np.array(F))
 front_clear=proj[:,1].min()+depth/2;rear_clear=depth/2-proj[:,1].max()
 eye=Vector((0,front-.55,1.65));height=np.load(P/'kb3/height.npz');matching=json.loads((P/'kb3/matching.json').read_text());centres=[]
 for r in matching['regions']:
  ix,iy=r['centre'];x=float(np.interp(ix,np.arange(len(height['xs'])),height['xs']));y=float(np.interp(iy,np.arange(len(height['ys'])),height['ys']));h=local.ray_cast(Vector((x,y,.2)),Vector((0,0,-1)))[0];assert h is not None
  target=key.matrix_world@h;ray=(target-eye).normalized();distance=(target-eye).length;hits=[]
  for name,t in [('ConsoleBody',tree),('Keyboard',world),('DisplayPlane',tree_for(bpy.data.objects['DisplayPlane']))]:
   hit=t.ray_cast(eye,ray)
   if hit[0] is not None:hits.append((hit[3],name))
  first=min(hits);visible=first[0]>=distance-.0002
  near=tree.find_nearest(target);centres.append({'key':r['design'],'local_top_m':list(h),'world_top_m':list(target),'visible':visible,'first_hit':first[1],'target_distance_m':distance,'first_hit_distance_m':first[0],'console_clearance_mm':near[3]*1000})
 display=bpy.data.objects['DisplayPlane'];screen=sum((display.matrix_world@v.co for v in display.data.vertices),Vector())/len(display.data.vertices);ray=(screen-eye).normalized();screen_hits=[]
 for name,t in [('ConsoleBody',tree),('Keyboard',world),('DisplayPlane',tree_for(display))]:
  hit=t.ray_cast(eye,ray)
  if hit[0] is not None:screen_hits.append({'object':name,'distance_m':hit[3]})
 screen_hits.sort(key=lambda h:h['distance_m'])
 checks={'underside_9_gaps_0_to_1_5_mm':all(g['gap_mm'] is not None and 0<=g['gap_mm']<=1.5 for g in gaps),'no_body_bvh_intersections':len(overlaps)==0,'no_front_overhang':float(wp[:,1].min())>=front and front_clear>=0,'no_rear_overhang':rear_clear>=0,'side_clearances_at_least_30_mm':halfwidth-max(abs(proj[:,0].min()),abs(proj[:,0].max()))>=.030,'requested_depth_or_width_limit':abs(np.ptp(proj,axis=0)[1]-min(depth-.020,(deckwidth-.060)/(hi[0]-lo[0])*(hi[1]-lo[1])))<1e-5,'key_tops_clear_head_bezel':min(c['console_clearance_mm'] for c in centres)>0 and len(overlaps)==0,'at_least_27_of_29_visible':sum(c['visible'] for c in centres)>=27,'screen_ray_hits_display_first':screen_hits[0]['object']=='DisplayPlane'}
 checks={k:bool(v) for k,v in checks.items()}
 report.update({'deck':{'plane_z_equals_ax_plus_by_plus_c':fit.tolist(),'ray_samples':samples,'flatness_peak_to_peak_mm':float(np.ptp(res)*1000),'front_y_m':front,'rear_y_m':rear,'rear_boundary_samples_y_m':rears,'along_slope_depth_m':depth,'usable_width_m':deckwidth,'slope_degrees':math.degrees(math.atan(math.sqrt(fit[0]**2+fit[1]**2)))},'keyboard':{'source_dimensions_m':np.ptp(verts,axis=0).tolist(),'deck_usable_width_m':deckwidth,'deck_width_boundary_rays_m':widths,'side_clearance_mm':float((halfwidth-max(abs(proj[:,0].min()),abs(proj[:,0].max())))*1000),'rearward_slide_mm':slide*1000,'uniform_scale':scale,'scale_constraint':'Uniform scale to deck depth minus 20 mm, or deck width minus 60 mm if narrower. Offset rearward only enough to retain 0.1 mm front vertical silhouette clearance.','scaled_local_dimensions_m':(np.ptp(verts,axis=0)*scale).tolist(),'deck_frame_dimensions_m':np.ptp(proj,axis=0).tolist(),'source_underside_plane_z_equals_ax_plus_by_plus_c':uf.tolist(),'source_underside_plane_flatness_mm':float(np.ptp(ur)*1000),'source_underside_axis_tilt_degrees':math.degrees(math.atan(math.hypot(*uf[:2]))),'support_plane_gap_mm':.5,'front_clearance_mm':float(front_clear*1000),'rear_clearance_mm':float(rear_clear*1000),'underside_samples':gaps,'bvh_triangle_intersections':len(overlaps),'visible_keytops':sum(c['visible'] for c in centres),'keytop_count':len(centres),'keytops':centres,'operator_eye_m':list(eye),'screen_ray_hits':screen_hits},'checks':checks})
 placement={'coordinate_system':'Blender right-handed Z-up, operator -Y, units metres','quaternion_order':'w,x,y,z','location':list(base.location),'rotation_quaternion':list(base.rotation_quaternion),'scale':list(base.scale),'glTF_y_up':{'location':[base.location.x,base.location.z,-base.location.y],'quaternion_order':'x,y,z,w','rotation_quaternion':[base.rotation_quaternion.x,base.rotation_quaternion.z,-base.rotation_quaternion.y,base.rotation_quaternion.w],'scale':list(base.scale)},'application':'Apply this transform to KeyboardBase of the unchanged local-space keyboard.glb, relative to console origin.','support_plane_note':'Generated underside is planar but slightly tilted in source local coordinates. Placement aligns that measured support plane to the measured deck plane with 0.5 mm normal clearance. Geometry and source KeyboardBase remain unchanged.'}
 (O/'keyboard-placement.json').write_text(json.dumps(placement,indent=2));(O/'fit-report.json').write_text(json.dumps(report,indent=2));print('FIT_REPORT',json.dumps({'deck':report['deck'],'keyboard':{k:v for k,v in report['keyboard'].items() if k not in ['keytops','underside_samples']},'checks':checks}),flush=True)
 failed=[k for k,v in checks.items() if not v]
 assert not failed,'ASSEMBLY FIT FAILED: '+', '.join(failed)
 return key,base
