"""Measure the exported glTF in its game frame: X across, Y up, +Z front."""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
import trimesh

NAMES = ['Frame','Feet','Rivets','SeatCushion_L','SeatCushion_C','SeatCushion_R',
         'BackCushion_L','BackCushion_C','BackCushion_R','Throw']


def welded(mesh):
    mesh=mesh.copy();mesh.merge_vertices(merge_tex=True,merge_norm=True)
    mesh.remove_unreferenced_vertices()
    return mesh


def world_meshes(path):
    scene=trimesh.load(path,force='scene')
    meshes={}
    for name in scene.graph.nodes_geometry:
        transform,geometry=scene.graph.get(name)
        mesh=scene.geometry[geometry].copy();mesh.apply_transform(transform)
        meshes[name]=welded(mesh)
    return scene,meshes


def top_height(mesh,x,z):
    origin=np.array([[x,mesh.bounds[1,1]+1,z]])
    points,rays,tri=mesh.ray.intersects_location(origin,[[0,-1,0]],multiple_hits=True)
    if not len(points):raise ValueError('Top measurement ray missed cushion')
    return float(points[:,1].max())


def seat_shape(mesh):
    lo,hi=mesh.bounds;c=(lo+hi)/2
    top=top_height(mesh,c[0],c[2]);edges=[];bulges=[]
    for axis in (0,2):
        for sign in (-1,1):
            p=c.copy();p[axis]=lo[axis]+.020 if sign<0 else hi[axis]-.020
            edges.append(top_height(mesh,p[0],p[2]))
            direction=np.zeros((1,3));direction[0,axis]=-sign
            origin=c.copy();origin[axis]+=sign*2
            def side(y):
                origin[1]=y
                hits,_,_=mesh.ray.intersects_location(origin[None,:],direction,multiple_hits=True)
                if not len(hits):raise ValueError('Side measurement ray missed cushion')
                return hits[:,axis].min() if sign<0 else hits[:,axis].max()
            bulges.append(float(sign*(side(c[1])-side(hi[1]-.025))))
    crown=top-float(np.mean(edges));extents=hi-lo
    return {'extents_xyz_m':extents.tolist(),'top_center_y_m':top,'top_20mm_edge_y_m':edges,
            'crown_m':crown,'side_bulges_m':bulges,
            'pass':bool(abs(extents[0]-.66)<=.010 and abs(extents[2]-.70)<=.010
                        and .14<=extents[1]<=.17 and .012<=crown<=.030
                        and all(.005<=x<=.020 for x in bulges))}


def penetration(a,b):
    # Check vertices and face interiors against each closed component. The BVH pass
    # separately checks triangle crossings so a thin crossing cannot escape sampling.
    maximum=0.
    for part in b.split(only_watertight=False):
        if not part.is_watertight:raise ValueError('Penetration target has an open boundary')
        samples=np.vstack((a.vertices,a.triangles_center))
        mask=np.all(samples>=part.bounds[0]-1e-6,axis=1)&np.all(samples<=part.bounds[1]+1e-6,axis=1)
        samples=samples[mask]
        if not len(samples):continue
        inside=part.contains(samples)
        if inside.any():
            distance=trimesh.proximity.closest_point(part,samples[inside])[1]
            maximum=max(maximum,float(distance.max()))
    return maximum


def welt_fit(body,pipe):
    edges=pipe.edges_unique
    length=np.linalg.norm(pipe.vertices[edges[:,0]]-pipe.vertices[edges[:,1]],axis=1)
    adjacency=[set() for _ in pipe.vertices]
    for a,b in edges[length<.0065]:adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(range(len(pipe.vertices)));rings=[]
    while remaining:
        stack=[remaining.pop()];ring=[]
        while stack:
            i=stack.pop();ring.append(i);extra=adjacency[i]&remaining;remaining.difference_update(extra);stack.extend(extra)
        rings.append(ring)
    distance=trimesh.proximity.closest_point(body,pipe.vertices)[1]
    contact=[float(distance[r].min()) for r in rings]
    diameter=[float(np.linalg.norm(pipe.vertices[r][:,None,:]-pipe.vertices[r][None,:,:],axis=2).max()) for r in rings]
    depth=penetration(pipe,body)
    return {'rings':len(rings),'vertices_per_ring':sorted(set(len(r) for r in rings)),
            'max_surface_gap_m':max(contact),'diameter_range_m':[min(diameter),max(diameter)],
            'max_penetration_m':depth,
            'pass':bool(all(len(r)==6 for r in rings) and max(contact)<=.001
                        and max(abs(x-.008) for x in diameter)<.0001 and depth<=.001)}


def measure(path,mesh_data=None):
    scene,meshes=world_meshes(path)
    checks={};bodies={};parts={}
    checks['named_nodes']={'actual':list(meshes),'pass':set(meshes)==set(NAMES)}
    geometry_count=len(scene.geometry)
    unique_count=len({scene.graph.get(name)[1] for name in scene.graph.nodes_geometry})
    checks['unique_geometry']={'geometry_count':geometry_count,'unique_geometry_count':unique_count,
                               'pass':geometry_count==unique_count==len(NAMES)}
    for name,mesh in meshes.items():
        split=sorted(mesh.split(only_watertight=False),key=lambda p:-len(p.faces));parts[name]=split
        if 'Cushion' in name:bodies[name]=split[0]
    checks['topology']={name:{'watertight':mesh.is_watertight,'winding_consistent':mesh.is_winding_consistent,
        'positive_component_volumes':all(p.volume>0 for p in parts[name]),
        'triangles':len(mesh.faces),'components':len(parts[name])} for name,mesh in meshes.items()}
    checks['topology_pass']=all(v['watertight'] and v['winding_consistent'] and v['positive_component_volumes'] for v in checks['topology'].values())
    checks['seats']={name:seat_shape(mesh) for name,mesh in bodies.items() if name.startswith('Seat')}
    normals={}
    for name,body in bodies.items():
        if not name.startswith('Seat'):continue
        top=body.bounds[1,1]
        mask=(body.triangles_center[:,1]>top-.006)&(body.face_normals[:,1]>.9)
        maximum=float(body.face_normals[mask,1].max()) if mask.any() else -1
        normals[name]={'upward_faces':int(mask.sum()),'max_top_normal_y':maximum,
                       'pass':bool(mask.any() and maximum>.99)}
    checks['seat_top_normals']=normals
    checks['welts']={name:welt_fit(parts[name][0],parts[name][1]) for name in bodies}
    gaps={}
    for group in ('Seat','Back'):
        for left,right in (('L','C'),('C','R')):
            a=bodies[group+'Cushion_'+left];b=bodies[group+'Cushion_'+right]
            gap=float(b.bounds[0,0]-a.bounds[1,0]);gaps[group+left+right]={'gap_m':gap,'pass':.008<=gap<=.012}
    checks['neighbour_gaps']=gaps
    cushion_pairs={}
    for a,b in itertools.combinations(list(bodies)+['Frame'],2):
        ma=meshes[a];mb=meshes[b]
        if np.any(ma.bounds[1]<mb.bounds[0]) or np.any(mb.bounds[1]<ma.bounds[0]):continue
        d=max(penetration(ma,mb),penetration(mb,ma));cushion_pairs[a+'/'+b]={'max_penetration_m':d,'pass':d<=.001}
    checks['cushion_contacts']=cushion_pairs
    deck_gaps={}
    for name,body in bodies.items():
        if not name.startswith('Seat'):continue
        lo,hi=body.bounds;center=(lo+hi)/2
        # Bottom-centre and quarter-depth points lie over the actual broad support deck.
        values=[]
        for dz in (-.15,0,.15):
            hits,_,_=body.ray.intersects_location([[center[0],lo[1]-1,center[2]+dz]],[[0,1,0]],multiple_hits=True)
            bottom=float(hits[:,1].min());origin=[center[0],bottom+.000001,center[2]+dz]
            hits,_,_=meshes['Frame'].ray.intersects_location([origin],[[0,-1,0]],multiple_hits=True)
            values.append(bottom-float(hits[:,1].max()))
        deck_gaps[name]={'gaps_m':values,'pass':all(-.001<=x<=.003 for x in values)}
    checks['seat_deck_gaps']=deck_gaps
    throw=meshes['Throw'];frame=meshes['Frame'];lo,hi=throw.bounds
    # Restrict the hang to material outside the arm. Inner folds do not define it.
    outside=throw.vertices[:,0]>frame.bounds[1,0]+.002
    outside_bottom=float(throw.vertices[outside,1].min()) if outside.any() else float('nan')
    cap_top=.8075;hang=cap_top-outside_bottom;extension=float(hi[0]-1.1)
    cap_samples=throw.vertices[(throw.vertices[:,0]>=1.025)&(throw.vertices[:,0]<=1.080)&(np.abs(throw.vertices[:,2])<.25)]
    # Use face samples as well because a sparse grid may straddle the cap.
    all_samples=np.vstack((throw.vertices,throw.triangles_center))
    cap_samples=all_samples[(all_samples[:,0]>=1.025)&(all_samples[:,0]<=1.080)&(np.abs(all_samples[:,2])<.25)&(all_samples[:,1]>=cap_top-.001)]
    cap_gap=float((cap_samples[:,1]-cap_top).min()) if len(cap_samples) else float('inf')
    depths={n:max(penetration(throw,meshes[n]),penetration(meshes[n],throw)) for n in ['Frame','SeatCushion_R','SeatCushion_C','BackCushion_R']}
    checks['throw']={'bounds_xyz_m':throw.bounds.tolist(),'outside_hang_m':hang,'outward_extension_m':extension,
                     'cap_gap_m':cap_gap,'penetration_m':depths,'triangles':len(throw.faces),
                     'pass':bool(.35<=hang<=.5 and extension<=.060 and -.001<=cap_gap<=.003 and max(depths.values())<=.00001 and len(throw.faces)<4000)}
    bounds=scene.bounds
    checks['bounds']={'xyz_m':bounds.tolist(),'pass':bool(bounds[0,0]>=-1.105 and bounds[1,0]<=1.16 and bounds[0,1]>=-.001 and bounds[1,1]<=.855 and np.all(np.abs(bounds[:,2])<=.480))}
    count=sum(len(m.faces) for m in meshes.values());checks['triangle_budget']={'triangles':count,'limit':18000,'pass':count<18000 and all(len(meshes[n].faces)<2500 for n in bodies)}
    checks['pass']=bool(checks['named_nodes']['pass'] and checks['unique_geometry']['pass'] and checks['topology_pass'] and checks['bounds']['pass'] and checks['triangle_budget']['pass'] and checks['throw']['pass']
        and all(v['pass'] for group in ['seats','seat_top_normals','welts','neighbour_gaps','cushion_contacts','seat_deck_gaps'] for v in checks[group].values()))
    if mesh_data:
        payload={name:[{'vertices':p.vertices.tolist(),'faces':p.faces.tolist()} for p in split] for name,split in parts.items()}
        Path(mesh_data).write_text(json.dumps(payload))
    return checks


def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('--mesh-data',type=Path);ap.add_argument('--report',type=Path)
    args=ap.parse_args();result=measure(args.input,args.mesh_data)
    if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['pass'] else 1)

if __name__=='__main__':main()
