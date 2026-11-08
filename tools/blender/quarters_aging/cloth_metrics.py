"""Dense and game surface diagnostics in Blender's native world frame."""
import bmesh
import numpy as np


def surface_metrics(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    angles = np.array([e.calc_face_angle() for e in bm.edges if len(e.link_faces) == 2])
    points = np.array([obj.matrix_world@v.co for v in bm.verts])
    result = {'triangles': len(bm.faces), 'dihedral_over_30_share': float(np.mean(angles > np.pi/6)),
              'bounds_blender_m': [points.min(0).tolist(), points.max(0).tolist()]}
    bm.free()
    return result


def within_frame(obj, frame, margin=.15):
    points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    rigid = np.array([frame.matrix_world@v.co for v in frame.data.vertices])
    lo, hi = rigid.min(0)-margin, rigid.max(0)+margin
    outside = np.any((points < lo) | (points > hi), axis=1)
    return {'margin_m': margin, 'allowed_bounds_blender_m': [lo.tolist(), hi.tolist()],
            'outside_vertices': int(outside.sum()), 'pass': not bool(outside.any())}
