"""Verify Batch 1 game exports with trimesh, independently of Blender."""
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely import Polygon, STRtree


def welded(mesh):
    vertices, inverse=np.unique(np.round(mesh.vertices,7),axis=0,return_inverse=True)
    return trimesh.Trimesh(vertices=vertices,faces=inverse[mesh.faces],process=False)


def uv_report(meshes):
    polygons=[]; density=[]; out_of_bounds=0
    for mesh in meshes.values():
        uv=mesh.visual.uv
        if uv is None:
            return {'pass':False,'missing_uv':True}
        out_of_bounds+=int(np.sum((uv<-.000001)|(uv>1.000001)))
        for face,area in zip(mesh.faces,mesh.area_faces):
            poly=Polygon(uv[face])
            if area>1e-10:
                polygons.append(poly)
                density.append(float(np.sqrt(poly.area/area)))
    tree=STRtree(polygons)
    overlaps=0; largest=0.0
    for i,poly in enumerate(polygons):
        for j in tree.query(poly,predicate='intersects'):
            if j<=i: continue
            area=poly.intersection(polygons[j]).area
            if area>1e-11:
                overlaps+=1; largest=max(largest,area)
    q=np.percentile(density,[5,50,95]).tolist()
    return {'overlapping_triangle_pairs':overlaps,'max_overlap_area_uv2':largest,
            'out_of_unit_square_coordinates':out_of_bounds,'linear_texel_density_p05_p50_p95':q,
            'density_p95_p05_ratio':q[2]/q[0],
            'pass':overlaps==0 and out_of_bounds==0 and q[2]/q[0]<=1.25}


def closure(mesh):
    mesh=welded(mesh)
    components=mesh.split(only_watertight=False, repair=False)
    misses=0; total=0
    for part in components:
        lo,hi=part.bounds; centre=(lo+hi)/2
        origins=[]
        for axis in range(3):
            other=[i for i in range(3) if i!=axis]
            for side in (0,1):
                for u in (.3,.5,.7):
                    for v in (.3,.5,.7):
                        point=centre.copy()
                        point[axis]=(lo[axis]-.0001 if side==0 else hi[axis]+.0001)
                        point[other[0]]=lo[other[0]]+(hi[other[0]]-lo[other[0]])*u
                        point[other[1]]=lo[other[1]]+(hi[other[1]]-lo[other[1]])*v
                        origins.append(point)
        origins=np.array(origins); dirs=centre-origins
        max_dist=np.linalg.norm(dirs,axis=1); dirs/=max_dist[:,None]
        hits,rays,_=part.ray.intersects_location(origins,dirs,multiple_hits=False)
        valid=np.unique(rays[np.linalg.norm(hits-origins[rays],axis=1)<=max_dist[rays]+1e-7])
        misses+=len(origins)-len(valid); total+=len(origins)
    return {'component_count':len(components),'probe_count':total,'missed_rays':misses,
            'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
            'positive_volume':bool(all(p.volume>0 for p in components)),
            'pass':bool(misses==0 and mesh.is_watertight and mesh.is_winding_consistent and all(p.volume>0 for p in components))}


def visibility(meshes, combined, camera, names, orthographic_target=None):
    offsets={}; offset=0
    for name,mesh in meshes.items():
        offsets[name]=(offset,offset+len(mesh.faces)); offset+=len(mesh.faces)
    if orthographic_target is not None:
        forward=orthographic_target-camera
        forward/=np.linalg.norm(forward)
    result={}
    for name in names:
        mesh=meshes[name]
        toward=(camera-mesh.triangles_center if orthographic_target is None else -forward)
        front=(mesh.face_normals*toward).sum(axis=1)>0
        ids=np.where(front)[0]
        target=mesh.triangles_center[ids]
        if orthographic_target is None:
            dirs=target-camera; distances=np.linalg.norm(dirs,axis=1)
            dirs/=distances[:,None]
            origins=np.repeat(camera[None,:],len(ids),axis=0)
            weights=mesh.area_faces[ids]*np.maximum(0,-(mesh.face_normals[ids]*dirs).sum(axis=1))/distances**2
        else:
            dirs=np.repeat(forward[None,:],len(ids),axis=0)
            origins=target-((target-camera)@forward)[:,None]*forward
            weights=mesh.area_faces[ids]*np.maximum(0,-(mesh.face_normals[ids]*dirs).sum(axis=1))
        face=combined.ray.intersects_first(origins,dirs)
        low,high=offsets[name]
        visible=(face>=low)&(face<high)
        fraction=float(np.sum(weights[visible])/np.sum(weights))
        result[name]={'sample_count':len(ids),'visible_projected_area_fraction':fraction,
                      'visible_triangle_fraction':float(visible.mean()),
                      'projection':'perspective' if orthographic_target is None else 'orthographic',
                      'minimum':.60,'pass':fraction>=.60}
    return result


def verify(path,spec_path,report_path,reexport):
    spec=json.loads(Path(spec_path).read_text()); scene=trimesh.load(path,force='scene')
    meshes={}
    for node in sorted(scene.graph.nodes_geometry):
        transform,geometry=scene.graph[node]
        mesh=scene.geometry[geometry].copy(); mesh.apply_transform(transform); meshes[node]=mesh
    combined=trimesh.util.concatenate(list(meshes.values()))
    body=trimesh.util.concatenate([m for n,m in meshes.items() if n not in spec.get('bounds_exclude',[])])
    target=np.array(spec['bounds_gltf'])
    error=float(np.max(np.abs(body.bounds-target)))
    topology={n:closure(m) for n,m in meshes.items()}
    degenerate=sum(int(np.sum(m.area_faces<1e-12)) for m in meshes.values())
    names=set(scene.graph.nodes)
    hierarchy={}
    for child,parent in spec.get('parents',{}).items():
        actual=scene.graph.transforms.parents.get(child)
        hierarchy[child]={'actual':actual,'expected':parent,'pass':actual==parent}
    pivots={}
    for name,expected in spec.get('pivots_gltf',{}).items():
        matrix,_=scene.graph[name]
        pivots[name]={'actual':matrix[:3,3].tolist(),'expected':expected,
                      'pass':bool(np.max(np.abs(matrix[:3,3]-expected))<.001)}
    materials=sorted({m.visual.material.name for m in meshes.values()})
    uv=uv_report(meshes)
    tx,ty,tz=spec['hero_target_native']
    vis=visibility(meshes,combined,np.array(spec['hero_camera_gltf']),spec['visible_details'],
                   orthographic_target=np.array([tx,tz,-ty]))
    tri=sum(len(m.faces) for m in meshes.values())
    byte_identical=Path(path).read_bytes()==Path(reexport).read_bytes()
    report={'asset':spec['id'],'bounds_gltf':{'actual':body.bounds.tolist(),'expected':target.tolist(),
            'max_error_m':error,'tolerance_m':.01,'pass':error<=.01},
            'origin_at_floor':{'min_y_m':float(combined.bounds[0,1]),'pass':bool(abs(combined.bounds[0,1])<.001)},
            'required_nodes':{'missing':sorted(set(spec['required_nodes'])-names),'pass':set(spec['required_nodes'])<=names},
            'hierarchy':hierarchy,'pivots':pivots,
            'topology':topology,'degenerate_faces':degenerate,'triangle_count':tri,'triangle_limit':spec['triangle_limit'],
            'material_slots':materials,'required_materials_pass':set(spec['materials'])<=set(materials),
            'UV':uv,'hero_first_hit_visibility':vis,'byte_identical_reexport':byte_identical,
            'axis_contract':'Blender Z-up/-Y front -> exported glTF +Y up/+Z front; bounds measured outside Blender'}
    report['pass']=(error<=.01 and report['origin_at_floor']['pass'] and
        report['required_nodes']['pass'] and all(v['pass'] for v in hierarchy.values()) and
        all(v['pass'] for v in pivots.values()) and all(v['pass'] for v in topology.values()) and
        degenerate==0 and tri<=spec['triangle_limit'] and report['required_materials_pass'] and
        uv['pass'] and all(v['pass'] for v in vis.values()) and byte_identical)
    Path(report_path).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='topology'},indent=2))
    if not report['pass']: raise SystemExit('Export verification failed')
    return report
