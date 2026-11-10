exec(compile((__import__('pathlib').Path(__file__).parent/'measure.py').read_text(), 'measure.py','exec'))
from mathutils import Matrix
fit=np.array(fit);normal=Vector((-fit[0],-fit[1],1)).normalized();tx=Vector((1,0,fit[0])).normalized();ty=normal.cross(tx).normalized();rotation=Matrix((tx,ty,normal)).transposed().to_quaternion()
front=-.6773526668548584;rear=-.5418;depth=(rear-front)*np.sqrt(1+fit[1]**2);scale=(depth-.020)/.24557149410247803;centre=Vector((0,(front+rear)/2,fit[1]*(front+rear)/2+fit[2]));base=bpy.data.objects['KeyboardBase'];key=bpy.data.objects['Keyboard'];base.location=centre+normal*.0005;base.rotation_mode='QUATERNION';base.rotation_quaternion=rotation;base.scale=(scale,)*3;bpy.context.view_layer.update();kt=BVHTree.FromPolygons([v.co for v in key.data.vertices],[p.vertices[:] for p in key.data.polygons]);world=BVHTree.FromPolygons([key.matrix_world@v.co for v in key.data.vertices],[p.vertices[:] for p in key.data.polygons]);print('PLACEMENT',scale,list(base.location),list(rotation),flush=True)
for y in [-.075,0,.075]:
 for x in [-.3,0,.3]:
  hit=kt.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)))
  if hit[0] is None:print('MISSING',x,y);continue
  p=key.matrix_world@hit[0];deck=tree.ray_cast(p+normal*.00001,-normal);print('GAP',x,y,'undersideZ',hit[0].z,'gapmm',deck[3]*1000 if deck[0] else None,flush=True)
print('COLLISIONS',len(world.overlap(tree)),flush=True)
localtree=kt;centres=[];data=np.load(P/'kb3/height.npz');matching=json.loads((P/'kb3/matching.json').read_text());eye=Vector((0,front-.55,1.65));occluded=[]
for r in matching['regions']:
 ix,iy=r['centre'];x=float(np.interp(ix,np.arange(len(data['xs'])),data['xs']));y=float(np.interp(iy,np.arange(len(data['ys'])),data['ys']));h=kt.ray_cast(Vector((x,y,.2)),Vector((0,0,-1)))[0];assert h is not None
 p=key.matrix_world@h;direction=(p-eye).normalized();dd=(p-eye).length;bh=tree.ray_cast(eye,direction);kh=world.ray_cast(eye,direction);visible=(bh[0] is None or bh[3]>dd-.0002) and (kh[0] is None or kh[3]>dd-.0002)
 centres.append({'key':r['design'],'local':list(h),'world':list(p),'visible':visible,'body_hit_distance':bh[3],'key_hit_distance':kh[3],'target_distance':dd})
 if not visible:occluded.append(r['design'])
print('VISIBILITY',len(centres)-len(occluded),occluded,flush=True)
screen=bpy.data.objects['DisplayPlane'];st=BVHTree.FromPolygons([screen.matrix_world@v.co for v in screen.data.vertices],[p.vertices[:] for p in screen.data.polygons]);sp=sum((screen.matrix_world@v.co for v in screen.data.vertices),Vector())/len(screen.data.vertices);direction=(sp-eye).normalized();print('SCREEN',list(sp),'BODY',tree.ray_cast(eye,direction),'DISPLAY',st.ray_cast(eye,direction),flush=True)
(O/'placement-probe.json').write_text(json.dumps({'keytops':centres,'scale':scale,'front':front,'rear':rear},indent=2))
