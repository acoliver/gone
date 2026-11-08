from pathlib import Path
import trimesh,json,numpy as np
R=Path(__file__).resolve().parent
s=trimesh.load(R/'fixture.glb',force='scene')
meshes=[];labels=[];stats={}
for node in s.graph.nodes_geometry:
 t,g=s.graph[node];m=s.geometry[g].copy();m.apply_transform(t)
 name=m.visual.material.name or node
 stats[node]={'triangles':len(m.faces),'bounds':m.bounds.tolist(),'material':name,'area_m2':float(m.area)}
 meshes.append(m);labels.extend([name]*len(m.faces))
allmesh=trimesh.util.concatenate(meshes);labels=np.array(labels)
print('BOUNDS',allmesh.bounds,'TRIS',len(allmesh.faces))
print(json.dumps(stats,indent=2))
# Two orthographic grids: full footprint and the centred armoured strip.
def cast(xs,zs,origins=None,direction=(0,1,0)):
 if origins is None:
  xx,zz=np.meshgrid(xs,zs);origins=np.column_stack([xx.ravel(),np.full(xx.size,-.6),zz.ravel()])
 dirs=np.tile(direction,(len(origins),1));idx=allmesh.ray.intersects_first(origins,dirs)
 hit=np.full(len(idx),'miss',dtype=object);hit[idx>=0]=labels[idx[idx>=0]]
 return hit,idx
results={}
for name,xs,zs in [('full_footprint',np.linspace(-.549,.549,750),np.linspace(-.109,.109,150)),('grille_strip',np.linspace(-.494,.494,750),np.linspace(-.046,.046,90))]:
 hit,idx=cast(xs,zs);u,c=np.unique(hit,return_counts=True)
 results[name]={'rays':len(hit),'fractions':dict(zip(u,(c/len(hit)).tolist()))}
 mask=hit=='RecessedFrostedGlass'
 xx,zz=np.meshgrid(xs,zs)
 allowed=np.zeros_like(mask)
 for x in np.linspace(-.455,.455,14):allowed|=(abs(xx.ravel()-x)<.01801)&(abs(zz.ravel())<.03301)
 results[name]['glass_hits_outside_slot_envelopes']=int(np.count_nonzero(mask&~allowed))
# Visible slot count from a dense centreline of the actual exported triangles.
xs=np.linspace(-.52,.52,5201)
hit,idx=cast(xs,np.array([0.]))
mask=hit=='RecessedFrostedGlass';starts=np.flatnonzero(mask&~np.roll(mask,1));ends=np.flatnonzero(mask&~np.roll(mask,-1))
runs=[[float(xs[a]),float(xs[b])] for a,b in zip(starts,ends)]
# Glass visible from below must have outward -Y normals in exported coordinates.
glass_faces=np.flatnonzero(labels=='RecessedFrostedGlass')
down=[i for i in glass_faces if allmesh.face_normals[i,1]<-.9]
# A multi-angle test measures the narrower angular aperture imposed by the 13 mm recess.
angular={}
for deg in [-55,-35,-15,15,35,55]:
 # Start just below the fixture and trace upward obliquely, independently of the ceiling.
 direction=np.array([0,np.cos(np.deg2rad(deg)),np.sin(np.deg2rad(deg))])
 xx,zz=np.meshgrid(np.linspace(-.49,.49,500),np.linspace(-.05,.05,70));o=np.column_stack([xx.ravel(),np.full(xx.size,-.13),zz.ravel()])
 h,i=cast([],[],origins=o,direction=direction)
 glass_hit=h=='RecessedFrostedGlass'
 plane=o+direction[None,:]*((-.1-o[:,1])/direction[1])[:,None]
 allowed=np.zeros(len(o),dtype=bool)
 for xc in np.linspace(-.455,.455,14):allowed|=(abs(plane[:,0]-xc)<.01801)&(abs(plane[:,2])<.03301)
 angular[str(deg)]={'glass_fraction':float(np.mean(glass_hit)),'glass_hits_outside_slots_at_grille_plane':int(np.count_nonzero(glass_hit&~allowed)),'all_visible_glass_faces_point_down':bool(np.all(allmesh.face_normals[i[glass_hit],1]<-.99))}
 assert angular[str(deg)]['glass_hits_outside_slots_at_grille_plane']==0,(deg,angular[str(deg)])
 assert angular[str(deg)]['all_visible_glass_faces_point_down'],angular[str(deg)]
# Weld UV and hard-normal seams before topology checks.
topology={}
for node in s.graph.nodes_geometry:
 t,g=s.graph[node];m=s.geometry[g].copy();m.apply_transform(t);m.merge_vertices(merge_tex=True,merge_norm=True);m.remove_unreferenced_vertices();topology[node]={'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'volume_m3':float(m.volume)}
info={'path':str(R/'fixture.glb'),'triangles':len(allmesh.faces),'bounds_gltf_m':allmesh.bounds.tolist(),'dimensions_gltf_m':allmesh.extents.tolist(),'top_mount_y_m':float(allmesh.bounds[1,1]),'axes':'+Y up, +Z front; Blender authored +Z up and -Y front; export_yup=True','objects':stats,'rays':results,'visible_slot_count':len(runs),'visible_slot_intervals_x_m':runs,'glass_downward_faces':len(down),'glass_downward_normal_y':allmesh.face_normals[down,1].tolist(),'glass_depth_behind_grille_m':.013,'angular_glass_fraction':angular,'topology':topology}
(R/'verification.json').write_text(json.dumps(info,indent=2))
print('SLOTS',len(runs),runs);print('RAYS',json.dumps(results));print('TOPOLOGY',json.dumps(topology))
assert len(allmesh.faces)<=3000
assert np.allclose(allmesh.extents,[1.1,.1,.22],atol=.0001),allmesh.extents
assert abs(allmesh.bounds[1,1])<.0001
assert len(runs)==14,runs
assert len(down)>0
assert all(v['glass_hits_outside_slot_envelopes']==0 for v in results.values())
assert all(v['winding_consistent'] for v in topology.values())
assert all(v['watertight'] for v in topology.values())
print('VERIFIED')
