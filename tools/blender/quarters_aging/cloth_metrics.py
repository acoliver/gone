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


def lip_lift(obj):
    from mathutils.kdtree import KDTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    group = obj.vertex_groups['Lip shrink'].index
    layer = bm.verts.layers.deform.active
    points = np.array([obj.matrix_world@v.co for v in bm.verts])
    tree = KDTree(len(points))
    for i, point in enumerate(points):
        tree.insert(point, i)
    tree.balance()
    total, lifted = 0., 0.
    samples = []
    for edge in bm.edges:
        if not edge.is_boundary or max(v[layer].get(group, 0.) for v in edge.verts) < .5:
            continue
        a, b = [v.index for v in edge.verts]
        middle = (points[a]+points[b])/2
        neighbours = np.array([points[i] for _, i, d in tree.find_range(middle, .020) if d >= .009])
        if len(neighbours) < 3:
            raise ValueError('Tear lip has insufficient local plane samples')
        centre = neighbours.mean(0)
        normal = np.linalg.svd(neighbours-centre)[2][-1]
        height = abs(float((middle-centre)@normal))
        length = float(np.linalg.norm(points[a]-points[b]))
        total += length
        lifted += length*(height > .003)
        samples.append({'length_m': length, 'lift_m': height})
    bm.free()
    if total == 0:
        raise ValueError('No authored tear lips to measure')
    return {'lip_length_m': total, 'lifted_length_m': lifted, 'fraction': lifted/total,
            'threshold': .30, 'pass': lifted/total >= .30, 'samples': samples}


def save_surface(obj, path):
    obj.data.calc_loop_triangles()
    np.savez_compressed(path, vertices=np.array([obj.matrix_world@v.co for v in obj.data.vertices]),
                        faces=np.array([t.vertices[:] for t in obj.data.loop_triangles]))
