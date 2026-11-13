"""Reproduce the focused formed-seat source and numeric handoff evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import trimesh
from seat_rail import ROOT, ART, OUT, build, floor_pose, profile
from seat_rail_proof import source_identity_metrics, shared_cut_metrics
from seat_rail_context_checks import frame_metrics

BLENDER='/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender'
PROOF=ROOT/'tmp/verify-stasis-wiring/seat-rail'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit_guide():
    guide=trimesh.load(ART/'guide.glb',force='mesh')
    center=guide.vertices.mean(axis=0)
    _,_,axes=np.linalg.svd(guide.vertices-center,full_matrices=False)
    points=(guide.vertices-center)@axes.T
    # Principal longitudinal direction is retained. The generated broad face
    # becomes the bearing face; exact sheet thickness and fold topology are
    # constrained engineering corrections, not raw scan displacement.
    order=[0,2,1]
    basis=axes[order].T
    points=(guide.vertices-center)@basis
    if np.linalg.det(basis)<0:
        basis[:,2]*=-1;points[:,2]*=-1
    lo,hi=np.quantile(points,[.005,.995],axis=0)
    target=np.array([.32,.018,.042])
    scale=target/(hi-lo)
    fitted=guide.copy();fitted.vertices=(points-(lo+hi)/2)*scale
    fitted.vertices[:,1]-=fitted.bounds[1,1]
    fitted.export(ART/'guide-aligned.glb')
    middle=points[abs(points[:,0])<.03*(hi[0]-lo[0])]
    from shapely.geometry import Polygon, LineString, Point
    section=fitted.section(plane_origin=[0,0,0],plane_normal=[1,0,0])
    section_points=max(section.discrete,key=len)[:,1:]
    section_polygon=Polygon(section_points)
    contour=LineString(section_points)
    cage=profile()
    profile_errors=np.array([contour.distance(Point(p)) for p in cage])
    np.savez(ART/'guide-section-fit.npz',generated_section_yz=section_points,clean_profile_yz=cage,
             cage_to_generated_distance_m=profile_errors)
    record={'guide_sha256':digest(ART/'guide.glb'),'concept_sha256':digest(ART/'concept.png'),
        'generated_section_metal_area_fraction':float(section_polygon.area/np.prod(np.ptp(section_points,axis=0))),
        'clean_profile_metal_area_fraction':float(Polygon(cage).area/(.042*.018)),
        'clean_profile_to_guide_rms_m':float(np.sqrt(np.mean(profile_errors**2))),
        'clean_profile_to_guide_max_m':float(profile_errors.max()),
        'source_section_fit':'Generated section is already a hollow C (measured occupancy); fair its skew and lumps to a symmetric constant-gauge rolled profile while preserving its open underside and return layout.',
        'guide_vertices':len(guide.vertices),'guide_faces':len(guide.faces),
        'principal_axes_columns':basis.tolist(),'generated_robust_extents':(hi-lo).tolist(),
        'engineering_fit_extents_m':target.tolist(),'central_section_sample_count':len(middle),
        'method':'Sparse manufactured C-section cage aligned to the generated longitudinal/broad-face axes; hollow thin-sheet topology, 36 mm bearing and continuous gauge corrected explicitly. No dense projection onto generated noise.',
        'bearing_width_m':.036,'total_width_m':.042,'depth_m':.018,'gauge_m':.0025,
        'outer_fold_radius_m':.003,'inner_fold_radius_m':.0005,'returned_lip_m':.003,
        'width_decision':'36 mm flat bearing retained; each rounded fold adds 3 mm outside it. Shrinking the flat seat to 30 mm would change the accepted bearing.'}
    (ART/'fit.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def panel_clearance(rail):
    panel_scene=trimesh.load(ROOT/'assets/props/bay-ceiling/intact.glb',force='scene')
    panel=next(m.copy() for n,m in panel_scene.geometry.items() if 'shell' in n)
    panel.apply_translation([0,2.99,.3])
    rail=rail.copy();rail.apply_translation([0,2.988,0])
    # All finite rail edges are tested against the actual accepted shell, not
    # against its generous whole-mesh bounding box. Bearing contact is allowed.
    edges=rail.vertices[rail.edges_unique]
    vector=edges[:,1]-edges[:,0];length=np.linalg.norm(vector,axis=1)
    locations,rays,_=panel.ray.intersects_location(edges[:,0],vector/length[:,None],multiple_hits=True)
    distance=np.linalg.norm(locations-edges[rays,0],axis=1)
    inside_segment=(distance>1e-7)&(distance<length[rays]-1e-7)
    below_bearing=locations[:,1]<2.988-1e-7
    intersections=int(np.sum(inside_segment&below_bearing))
    panel_under=panel.vertices[panel.vertices[:,1]<2.988-1e-7]
    contained=int(np.sum(rail.contains(panel_under)))
    rail_under=rail.vertices[rail.vertices[:,1]<2.988-1e-7]
    contained+=int(np.sum(panel.contains(rail_under)))
    assert intersections==0 and contained==0, (intersections,contained)
    # Actual flange underside at z = +12..+17 mm rests on the flat top.
    samples=np.array([[x,2.988,z] for x in [-.4,0,.4] for z in [.012,.015,.017]])
    _,distance,_=trimesh.proximity.closest_point(panel,samples)
    rail_top_distance=trimesh.proximity.closest_point(rail,samples)[1]
    assert np.max(distance)<1e-6 and np.max(rail_top_distance)<1e-6
    lower_rim=panel.vertices[panel.vertices[:,1]<2.985-1e-7]
    # Signed width separation is valid here because the whole lower rim is
    # inboard of the return, independently confirmed by the edge tests above.
    gap=float(lower_rim[:,2].min()-rail.bounds[1,2])
    return {'panel_asset_sha256':digest(ROOT/'assets/props/bay-ceiling/intact.glb'),
        'actual_edge_intersections_below_bearing':intersections,'actual_contained_vertices':contained,
        'actual_flange_contact_samples':len(samples),'flange_to_bearing_max_gap_m':float(max(distance.max(),rail_top_distance.max())),
        'lower_rim_to_outer_return_lateral_clearance_m':gap,'bearing_top_y_m':2.988}


def verify(family):
    middle=family['middle'];pose=floor_pose(middle)
    moved=middle.copy();moved.apply_transform(pose)
    bay=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    world=moved.vertices@bay.T
    center=np.array([-1.4,.05,.6])
    margins=np.array([.22,.10,1.15])/2-np.max(abs(world-center),axis=0)
    assert np.all(margins>=0),margins
    inverse=trimesh.transform_points(moved.vertices,np.linalg.inv(pose))
    exported={}
    for name in ['full','left','middle','right']:
        scene=trimesh.load(OUT/(name+'.glb'),force='scene')
        mesh=scene.to_mesh()
        from scipy.spatial import cKDTree
        distances,ids=cKDTree(family[name].vertices).query(mesh.vertices)
        uv_error=float(np.max(abs(mesh.visual.uv-family[name].visual.uv[ids])))
        assert np.max(distances)<1e-7 and uv_error<1e-6
        mesh.merge_vertices()
        np.testing.assert_allclose(mesh.bounds,family[name].bounds,atol=1e-7)
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        exported[name]={'bounds_m':mesh.bounds.tolist(),'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
                        'actual_exported_uv_source_max_error':uv_error,'actual_exported_vertex_source_max_error_m':float(np.max(distances))}
    gauge=[]
    for origin,direction in [([.1,.01,0],[0,-1,0]),([.1,-.008,.03],[0,0,-1]),([.1,-.008,-.03],[0,0,1]),([.1,-.03,.016],[0,1,0])]:
        hits,_,_=family['full'].ray.intersects_location([origin],[direction],multiple_hits=True)
        distance=np.sort(np.linalg.norm(hits-np.array(origin),axis=1))
        gauge.append(float(distance[1]-distance[0]))
    np.testing.assert_allclose(gauge,.0025,atol=1e-9)
    metrics={'source_identity':source_identity_metrics(family),'paired_cuts':shared_cut_metrics(family),
        'actual_top_return_lip_ray_gauges_m':gauge,
        'exported_gltf_axes_and_bounds':exported,'slenderness':float(middle.extents[0]/middle.extents[2]),
        'floor_pose_bay_local':pose.tolist(),'floor_roll_degrees':115.,
        'floor_min_y_m':float(moved.bounds[0,1]),'floor_max_y_m':float(moved.bounds[1,1]),
        'floor_opening_direction_bay':(pose[:3,:3]@np.array([0,-1,0])).tolist(),
        'bay_local_long_axis':pose[:3,0].tolist(),'world_long_axis':(bay@pose[:3,0]).tolist(),
        'world_picker_proxy_size_m':[.22,.10,1.15],'world_picker_min_margin_m':margins.tolist(),
        'floor_proxy_headroom_m':float(.10-moved.bounds[1,1]),
        'floor_center_bay_xz_m':[-.6,-1.4], 'pickup_reach_m':1.3,
        'inverse_floor_pose_max_error_m':float(np.max(abs(inverse-middle.vertices))),
        'panel_contact':panel_clearance(family['full']),
        'prototype_frame':frame_metrics(),
        'material':json.loads((OUT/'material.json').read_text())}
    inputs=[ART/'concept.png',ART/'guide.glb',ART/'guide-aligned.glb',ART/'fit.json',ART/'source-cage.npz',
            ROOT/'tools/seat_rail.py',ROOT/'tools/build_seat_rail.py',ROOT/'tools/seat_rail_proof.py',
            ROOT/'tools/blender/seat_rail.py']
    inputs+=list(OUT.glob('*.glb'))+list(OUT.glob('*.png'))+[ART/'seat-rail.blend']
    metrics['sources_sha256']={str(p.relative_to(ROOT)):digest(p) for p in inputs}
    (OUT/'manifest.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (PROOF/'measurements.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics,indent=2))


def main():
    PROOF.mkdir(parents=True,exist_ok=True)
    fit_guide()
    family=build()
    subprocess.run([BLENDER,'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'tools/blender/seat_rail.py')],check=True,cwd=ROOT)
    verify(family)


def update_floor_only():
    """Repose the baked pickup without rebuilding source meshes or unrelated buffers."""
    import struct
    from seat_rail import rail_family
    from seat_rail_proof import CEILING_ORIGIN
    old=np.asarray(json.loads((OUT/'manifest.json').read_text())['floor_pose_bay_local'])
    family=rail_family();new=floor_pose(family['middle'])
    delta=new@np.linalg.inv(old)
    path=OUT.parent/'fault-frame-pair.glb'
    raw=path.read_bytes();json_length=struct.unpack_from('<I',raw,12)[0]
    header=json.loads(raw[20:20+json_length])
    binary=bytearray(raw[28+json_length:])
    node=next(n for n in header['nodes'] if n['name']=='fallen_fragment')
    attributes=header['meshes'][node['mesh']]['primitives'][0]['attributes']
    changed=[]
    for semantic in ['POSITION','NORMAL']:
        accessor=header['accessors'][attributes[semantic]]
        view=header['bufferViews'][accessor['bufferView']]
        assert accessor['componentType']==5126 and accessor['type']=='VEC3'
        assert 'byteStride' not in view
        offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        array=np.frombuffer(binary,dtype='<f4',count=accessor['count']*3,offset=offset).reshape(-1,3)
        transformed=array@delta[:3,:3].T
        if semantic=='POSITION':
            from scipy.spatial import cKDTree
            source=family['middle'].vertices
            distance,ids=cKDTree(trimesh.transform_points(source,old)).query(array)
            assert distance.max()<1e-6, 'baked pickup must match the previous source pose'
            transformed=trimesh.transform_points(source[ids],new)
        array[:]=transformed
        accessor['min']=array.min(axis=0).tolist();accessor['max']=array.max(axis=0).tolist()
        changed.append((offset,offset+array.nbytes))
    original=raw[28+json_length:]
    differences=np.flatnonzero(np.frombuffer(original,dtype='u1')!=np.frombuffer(binary,dtype='u1'))
    assert all(any(a<=i<b for a,b in changed) for i in differences)
    encoded=json.dumps(header,separators=(',',':')).encode()
    encoded+=b' '*((-len(encoded))%4)
    data=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))
    data+=struct.pack('<II',len(encoded),0x4e4f534a)+encoded
    data+=struct.pack('<II',len(binary),0x004e4942)+binary
    path.write_bytes(data)
    metadata_path=OUT.parent/'proof-assemblies.json'
    metadata=json.loads(metadata_path.read_text())
    assembly=metadata['assemblies']['fault-frame-pair']
    fracture=assembly['metrics']['fracture']
    transform=new.copy();transform[:3,3]-=new[:3,:3]@CEILING_ORIGIN
    moved=family['middle'].copy();moved.apply_transform(new)
    fracture['fallen_world_from_original']=transform.tolist()
    fracture['fallen_mesh_bounds_m']=moved.bounds.tolist()
    restored=trimesh.transform_points(moved.vertices,np.linalg.inv(new))
    fracture['inverse_transformed_mesh_max_error_m']=float(np.max(abs(restored-family['middle'].vertices)))
    assembly['sha256']=digest(path)
    metadata_path.write_text(json.dumps(metadata,indent=2)+chr(10))
    verify(family)
    print('FLOOR_ONLY_PASS: only fallen POSITION/NORMAL binary ranges changed; source assets untouched')


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--floor-only']: update_floor_only()
    else: main()
