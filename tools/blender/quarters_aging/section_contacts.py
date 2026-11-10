"""Find thread extensions whose section would cross an existing cloth face."""
import numpy as np
from mathutils.bvhtree import BVHTree

from triangle_contacts import intersect


def impossible_fibres(obj, source):
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = np.asarray([obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float32).astype(float)
    faces = np.asarray([t.vertices[:] for t in mesh.loop_triangles])
    tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
    ids = [a.value for a in source.attributes['FrayID'].data]
    ids += ids
    bad = set()
    for i, j in tree.overlap(tree):
        if i >= j or set(faces[i]) & set(faces[j]):
            continue
        labels = {ids[k] for k in [*faces[i], *faces[j]] if ids[k]}
        if labels and intersect(points[faces[i]], points[faces[j]]):
            bad |= labels
    return bad


def prune_surface_fibres(obj):
    import bmesh
    removed = 0
    while True:
        bad = impossible_fibres(obj, obj.data)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        labels = bm.verts.layers.int['FrayID']
        tips = bm.verts.layers.int['FrayTip']
        selected = [v for v in bm.verts if v[tips] and v[labels] in bad]
        if not selected:
            bm.free()
            break
        removed += len(selected)
        bmesh.ops.delete(bm, geom=selected, context='VERTS')
        bm.to_mesh(obj.data)
        bm.free()
    obj['pruned_impossible_fibres'] = removed
    return removed
