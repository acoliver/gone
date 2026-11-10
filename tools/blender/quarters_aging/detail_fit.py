"""Fit reinforced cloth to visible support, trimming it where folds cross the patch."""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from common import recalc, surface_tree
from fabric_mesh import replace
from stress_cut import cut_faces
from triangle_contacts import intersect


def clip(polygon, axis, bound, greater):
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        inside_a = a[axis] >= bound if greater else a[axis] <= bound
        inside_b = b[axis] >= bound if greater else b[axis] <= bound
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(a + (b - a) * ((bound - a[axis]) / (b[axis] - a[axis])))
    return result


def trim_fold_contacts(obj, body):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    obj.data.calc_loop_triangles()
    body.data.calc_loop_triangles()
    a = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    b = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    af = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    bf = np.array([t.vertices[:] for t in body.data.loop_triangles])
    tree = BVHTree.FromPolygons(a.tolist(), af.tolist(), all_triangles=True)
    support = BVHTree.FromPolygons(b.tolist(), bf.tolist(), all_triangles=True)
    bad = {i for i, j in tree.overlap(support) if intersect(a[af[i]], b[bf[j]])}
    area = sum(obj.data.polygons[i].area for i in bad)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in bad], context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    cut_faces(obj, lambda p: False, 95, refine=False, fan_clearance=.0002)
    if not obj.data.polygons:
        raise ValueError(f'{obj.name}: no reinforcement remains outside the cloth folds')
    return {'removed_contact_triangles': len(bad), 'removed_area_m2': area,
            'point_fan_clearance_m': .0002}


def fit_patch(obj, body, points, upward=False):
    surface = surface_tree(body)
    body.data.calc_loop_triangles()
    axes = [0, 1] if upward else [0, 2]
    points = np.asarray(points)
    lo, hi = points[:, axes].min(0), points[:, axes].max(0)
    direction = Vector((0, 0, -1) if upward else (0, 1, 0))
    lift = Vector((0, 0, .003) if upward else (0, -.003, 0))
    vertices, faces, mapping = [], [], {}
    for triangle in body.data.loop_triangles:
        polygon = [body.matrix_world @ body.data.vertices[i].co for i in triangle.vertices]
        for axis, lower, upper in zip(axes, lo, hi):
            polygon = clip(polygon, axis, lower, True)
            polygon = clip(polygon, axis, upper, False) if polygon else []
            if not polygon:
                break
        if len(polygon) < 3:
            continue
        centre = sum(polygon, Vector()) / len(polygon)
        origin = centre.copy()
        origin[2 if upward else 1] = .1 if upward else -1
        hit, _, _, _ = surface.ray_cast(origin, direction)
        if hit is None or (hit - centre).length > .00001:
            continue
        ids = []
        for p in polygon:
            p = p + lift
            key = tuple(round(v, 8) for v in p)
            if key not in mapping:
                mapping[key] = len(vertices)
                vertices.append(tuple(p))
            ids.append(mapping[key])
        for i in range(1, len(ids) - 1):
            if len({ids[0], ids[i], ids[i + 1]}) == 3:
                faces.append((ids[0], ids[i], ids[i + 1]))
    if not faces:
        raise ValueError(f'{obj.name}: fitted patch has no visible support')
    mat = obj.data.materials[0]
    uv = (np.asarray(vertices)[:, axes] - lo) / (hi - lo)
    replace(obj, vertices, faces, mat, uv=uv)
    trim = trim_fold_contacts(obj, body)
    mat.use_backface_culling = False
    obj['bounded_cloth'] = True
    recalc(obj)
    return {'method': 'Visible support triangles clipped to the followed detail footprint and lifted 3 mm; crossing facets trimmed; planar UVs; not separately simulated',
            'triangles': len(obj.data.polygons), 'fold_trim': trim}
