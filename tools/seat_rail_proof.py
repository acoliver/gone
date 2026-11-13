"""Physical checks and placement for the shared issue-110 ceiling component."""
import hashlib
import numpy as np
import trimesh
from seat_rail import rail_family, floor_pose, apply_material

CEILING_ORIGIN=np.array([-.6,2.988,-.6])


def shared_cut_metrics(family):
    rows={}
    n=len(family['cuts']['left']['retained'])
    original=family['middle']
    for side,stub in [('left',family['left']),('right',family['right'])]:
        cut=family['cuts'][side]
        a,b=cut['retained'],cut['fragment']
        def end_triangles(mesh):
            triangles=mesh.triangles
            distance=np.linalg.norm(triangles[:,:,None,:]-a[None,None,:,:],axis=3)
            return np.all(np.min(distance,axis=2)<1e-10,axis=1)
        mask_a,mask_b=end_triangles(stub),end_triangles(original)
        centers_a,centers_b=stub.triangles_center[mask_a],original.triangles_center[mask_b]
        pairs=np.argmin(np.linalg.norm(centers_a[:,None]-centers_b[None,:],axis=2),axis=1)
        gap=float(np.max(np.linalg.norm(centers_a-centers_b[pairs],axis=1)))
        opposing=float(np.max(np.sum(stub.face_normals[mask_a]*original.face_normals[mask_b][pairs],axis=1)))
        assert gap<1e-12 and opposing<-.999999
        rows[side]={'retained_sha256':hashlib.sha256(a.astype('<f8').tobytes()).hexdigest(),
                    'fragment_sha256':hashlib.sha256(b.astype('<f8').tobytes()).hexdigest(),
                    'triangle_plane_max_gap_m':gap,'opposing_normal_max_dot':opposing}
    return rows


def add_seat_failure(assembly):
    family=rail_family()
    for name in ['left','right']:
        mesh=apply_material(family[name].copy());mesh.apply_translation(CEILING_ORIGIN)
        assembly.add('seat_retained',mesh)
    pose=floor_pose(family['middle'])
    fallen=apply_material(family['middle'].copy());fallen.apply_transform(pose)
    assembly.add('fallen_fragment',fallen)
    # Installed neighbor and outside spans all use the same original full module.
    for z,centers in [(-.6,[-1.8,.6]),(-1.8,[-1.8,-.6,.6]),(-1.2,[-1.8,-.6,.6]),(0.,[-1.8,-.6,.6])]:
        for center in centers:
            mesh=apply_material(family['full'].copy());mesh.apply_translation([center,2.988,z])
            assembly.add('seat_healthy',mesh)
    original=family['middle'].copy();original.apply_translation(CEILING_ORIGIN)
    original_to_fallen=pose.copy();original_to_fallen[:3,3]-=pose[:3,:3]@CEILING_ORIGIN
    restored=trimesh.transform_points(fallen.vertices,np.linalg.inv(original_to_fallen))
    error=float(np.max(np.linalg.norm(restored-original.vertices,axis=1)))
    cuts=shared_cut_metrics(family)
    assembly.metrics['fracture']={'design_change':'Issue 110 user correction: lower formed-sheet seat replaces the rejected upper 55 mm beam pickup. Upper carrier remains intact.',
        'section_outer_m':.042,'section_depth_m':.018,'wall_m':.0025,'bearing_width_m':.036,
        'bearing_top_y_m':2.988,'gap_nominal_x_m':[-1.1,-.1],
        'shared_profile_sha256':{s:r['retained_sha256'] for s,r in cuts.items()},
        'retained_end_sha256':{s:r['retained_sha256'] for s,r in cuts.items()},
        'fragment_original_end_sha256':{s:r['fragment_sha256'] for s,r in cuts.items()},
        'cut_triangle_planes':list(cuts.values()),'cut_surface_face_pair_max_gap_m':0.,
        'fallen_world_from_original':original_to_fallen.tolist(),
        'inverse_transformed_mesh_max_error_m':error,'fallen_mesh_bounds_m':fallen.bounds.tolist(),
        'fragment_original_bounds_m':original.bounds.tolist(),'profiles_world_m':{s:(r['retained']+CEILING_ORIGIN).tolist() for s,r in family['cuts'].items()}}
    # Cable drop contact belongs to the intact upper carrier, not to the pickup.
    return assembly.block('steel_frame',[-.6,3.12,-.6],[3.6,.055,.055])


def source_identity_metrics(family):
    full=family['full'];rows={}
    for name in ['left','middle','right']:
        mesh=family[name];ids=mesh.metadata['source_vertex_ids']
        vertex_error=float(np.max(abs(mesh.vertices-full.vertices[ids])))
        uv_error=float(np.max(abs(mesh.visual.uv-full.visual.uv[ids])))
        face_ids=mesh.metadata['source_face_ids'];source_faces=full.metadata['source_face_ids']
        # Identity is checked by actual indexed coordinates, not material labels.
        source_map={int(i):full.vertices[f] for i,f in zip(source_faces,full.faces) if i>=0}
        face_error=0.
        for fid,face in zip(face_ids,mesh.faces):
            if fid<0:continue
            a=np.array(sorted(map(tuple,mesh.vertices[face])));b=np.array(sorted(map(tuple,source_map[int(fid)])))
            face_error=max(face_error,float(np.max(abs(a-b))))
        assert max(vertex_error,uv_error,face_error)==0
        rows[name]={'vertex_count':len(ids),'body_source_face_count':int(np.sum(face_ids>=0)),
                    'source_vertex_max_error_m':vertex_error,'source_uv_max_error':uv_error,'source_face_max_error_m':face_error,
                    'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
                    'positive_volume_m3':float(mesh.volume),'bounds_m':mesh.bounds.tolist()}
    return rows
