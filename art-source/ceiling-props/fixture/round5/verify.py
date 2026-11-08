from pathlib import Path
import trimesh,json,numpy as np
R=Path(__file__).resolve().parent
s=trimesh.load(R/'fixture.glb',force='scene')
meshes=[];labels=[];stats={};topology={}
for node in s.graph.nodes_geometry:
 t,g=s.graph[node];m=s.geometry[g].copy();m.apply_transform(t)
 name=m.visual.material.name or node
 stats[node]={'triangles':len(m.faces),'bounds':m.bounds.tolist(),'material':name,'area_m2':float(m.area)}
 meshes.append(m);labels.extend([name]*len(m.faces))
 welded=m.copy();welded.merge_vertices(merge_tex=True,merge_norm=True);welded.remove_unreferenced_vertices()
 topology[node]={'watertight':bool(welded.is_watertight),'winding_consistent':bool(welded.is_winding_consistent),'volume_m3':float(welded.volume)}
allmesh=trimesh.util.concatenate(meshes);labels=np.array(labels)
print('BOUNDS',allmesh.bounds,'TRIANGLES',len(allmesh.faces),flush=True)

def cast(xs,zs,origins=None,direction=(0,1,0)):
 if origins is None:
  xx,zz=np.meshgrid(xs,zs);origins=np.column_stack([xx.ravel(),np.full(xx.size,-.6),zz.ravel()])
 dirs=np.tile(direction,(len(origins),1));idx=allmesh.ray.intersects_first(origins,dirs)
 hit=np.full(len(idx),'miss',dtype=object);hit[idx>=0]=labels[idx[idx>=0]]
 return hit,idx

def allowed_slots(points):
 allowed=np.zeros(len(points),dtype=bool)
 bend=.0012*np.maximum(0,1-abs(points[:,2])/.033)
 for index,xc in enumerate(np.linspace(-.455,.455,14)):
  # Rounded terminal corners remain anchored to the unbent frame. The
  # aperture envelope includes those corners as well as the displaced bar.
  lo=xc-.01802
  hi=xc+.01802+(bend if index==4 else 0)
  allowed|=(points[:,0]>lo)&(points[:,0]<hi)&(abs(points[:,2])<.03302)
 return allowed

results={}
for name,xs,zs in [('full_footprint',np.linspace(-.549,.549,750),np.linspace(-.109,.109,150)),('grille_strip',np.linspace(-.494,.494,750),np.linspace(-.057,.057,110))]:
 hit,idx=cast(xs,zs);u,c=np.unique(hit,return_counts=True)
 xx,zz=np.meshgrid(xs,zs);points=np.column_stack([xx.ravel(),np.full(xx.size,-.0995),zz.ravel()])
 mask=hit=='RecessedFrostedGlass'
 print('OUTSIDE_POINTS',name,points[mask&~allowed_slots(points)].tolist(),flush=True)
 results[name]={'rays':len(hit),'fractions':dict(zip(u,(c/len(hit)).tolist())),'glass_hits_outside_slot_envelopes':int(np.count_nonzero(mask&~allowed_slots(points)))}
xs=np.linspace(-.52,.52,5201);hit,idx=cast(xs,np.array([0.]))
mask=hit=='RecessedFrostedGlass';starts=np.flatnonzero(mask&~np.roll(mask,1));ends=np.flatnonzero(mask&~np.roll(mask,-1))
runs=[[float(xs[a]),float(xs[b])] for a,b in zip(starts,ends)]
glass_faces=np.flatnonzero(labels=='RecessedFrostedGlass');down=[i for i in glass_faces if allmesh.face_normals[i,1]<-.9]
angular={}
for axis in ['across','along']:
 for deg in [-55,-35,-15,15,35,55]:
  direction=np.array([0,np.cos(np.deg2rad(deg)),np.sin(np.deg2rad(deg))])
  if axis=='along':direction=direction[[2,1,0]]
  xx,zz=np.meshgrid(np.linspace(-.515,.515,500),np.linspace(-.066,.066,90));o=np.column_stack([xx.ravel(),np.full(xx.size,-.13),zz.ravel()])
  h,i=cast([],[],origins=o,direction=direction);glass_hit=h=='RecessedFrostedGlass'
  # Compare first against the physical projected aperture rather than a flat
  # plane that would incorrectly treat chamfered lips as another opening.
  # The top throat lies 9.5 mm behind the louvre's low face.
  # A ray that reaches glass must cross the bounding rectangle of a slot at
  # some height in the finite-thickness grille, including the bent bars.
  valid=np.zeros(len(o),dtype=bool)
  for height in np.linspace(-.0995,-.0881,45):
   plane=o+direction[None,:]*((height-o[:,1])/direction[1])[:,None]
   valid|=allowed_slots(plane)
  angular[f'{axis}_{deg}']={'rays':len(o),'glass_fraction':float(np.mean(glass_hit)),'glass_hits_outside_slots_through_grille_depth':int(np.count_nonzero(glass_hit&~valid)),'all_visible_glass_faces_point_down':bool(np.all(allmesh.face_normals[i[glass_hit],1]<-.99))}
# Record louvre thickness from undented end sections of the retained skin.
grille_mesh=next(m for m in meshes if m.visual.material.name=='DarkArmouredSteel')
low,high=grille_mesh.bounds[:,1]
body=next(m for m in meshes if m.visual.material.name=='OliveSteel_StructuredWeather')
info={'path':str(R/'fixture.glb'),'triangles':len(allmesh.faces),'bounds_gltf_m':allmesh.bounds.tolist(),'dimensions_gltf_m':allmesh.extents.tolist(),'top_mount_y_m':float(allmesh.bounds[1,1]),'axes':'+Y up, +Z front; Blender authored +Z up and -Y front; export_yup=True','objects':stats,'rays':results,'visible_slot_count':len(runs),'visible_slot_intervals_x_m':runs,'glass_downward_faces':len(down),'glass_downward_normal_y':allmesh.face_normals[down,1].tolist(),'glass_depth_behind_grille_m':float(-.087-low),'grille_total_depth_including_dent_m':float(high-low),'undented_louvre_thickness_m':.0095,'angular_glass_fraction':angular,'topology':topology,'generated_body_triangles':len(body.faces)}
end_bolt_seats=[]
for sign in [-1,1]:
 for front in [-.077,.077]:
  origin=np.array([[sign*.60,-.013,front]]);direction=np.array([[-sign,0,0]])
  locations,_,_=allmesh.ray.intersects_location(origin,direction,multiple_hits=True)
  nearest=locations[np.argmin(np.linalg.norm(locations-origin,axis=1))]
  assert .5483<abs(nearest[0])<.5489,nearest
  end_bolt_seats.append({'end_sign':sign,'front_z_m':front,'first_hit_x_m':float(nearest[0]),'head_recess_from_end_plane_m':float(.55-abs(nearest[0]))})
info['end_bolt_seat_rays']=end_bolt_seats
(R/'verification.json').write_text(json.dumps(info,indent=2))
print(json.dumps(info,indent=2),flush=True)
assert len(allmesh.faces)<=3000
assert np.allclose(allmesh.extents,[1.1,.1,.22],atol=.0001),allmesh.extents
assert abs(allmesh.bounds[1,1])<.0001
assert len(runs)==14,runs
assert len(down)==2
assert all(v['glass_hits_outside_slot_envelopes']==0 for v in results.values())
assert all(v['glass_hits_outside_slots_through_grille_depth']==0 and v['all_visible_glass_faces_point_down'] for v in angular.values())
assert all(v['winding_consistent'] and v['watertight'] for v in topology.values()),topology
print('VERIFIED',flush=True)
