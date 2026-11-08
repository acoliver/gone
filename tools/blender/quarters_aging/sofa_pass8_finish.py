"""Deterministic lip rolls and bounded game-mesh clearance, without exclusions."""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from common import recalc
from triangle_contacts import intersect


def save_lip_classes(obj, path):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.verts.layers.deform.active
    panel = obj.vertex_groups['Panel tear'].index
    lip = obj.vertex_groups['Lip shrink'].index
    points, classes = [], []
    for edge in bm.edges:
        if not edge.is_boundary or max(v[layer].get(lip, 0.) for v in edge.verts) < .5:
            continue
        points.append(tuple(obj.matrix_world@((edge.verts[0].co+edge.verts[1].co)/2)))
        classes.append('tear' if max(v[layer].get(panel, 0.) for v in edge.verts) >= .5 else 'seam')
    bm.free()
    np.savez_compressed(path, points=np.array(points), classes=np.array(classes))


def lip_curl(obj, seed):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    layer = bm.verts.layers.deform.active
    group = obj.vertex_groups['Lip shrink'].index
    positions = {v: v.co.copy() for v in bm.verts}
    moved = 0
    for v in bm.verts:
        weight = v[layer].get(group, 0.)
        if weight <= 0:
            continue
        phase = seed*.137+v.co.x*79+v.co.y*113+v.co.z*53
        height = (.0055+.0025*np.sin(phase))*weight
        # A normal lift decays over the physical 15 mm split relaxation band.
        relaxation = obj.vertex_groups.get('Lip relaxation')
        if relaxation:
            weight = v[layer].get(relaxation.index, weight)
            height = (.0055+.0025*np.sin(phase))*weight
        v.co = positions[v]+v.normal*height
        moved += 1
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return {'method': 'seeded normal lip roll, 3 to 8 mm amplitude in 15 mm band',
            'moved_vertices': moved, 'maximum_lift_m': .008}


def surface(obj):
    obj.data.calc_loop_triangles()
    points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    return points, faces, BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True, epsilon=1e-7)


def initial_contacts(obj, supports):
    import bpy
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = [obj.evaluated_get(deps), *[s.evaluated_get(deps) for s in supports]]
    _, pairs = crossings(evaluated, {obj.name})
    if pairs:
        raise ValueError(f'C5: {len(pairs)} initial SAT crossings; first: {pairs[:4]}')
    return {'changed_crossings': 0, 'broad_phase': 'triangle AABBs', 'pass': True}


def candidate_pairs(p, f, q, g):
    a, b = p[f], q[g]
    lo, hi = b.min(1), b.max(1)
    order = np.argsort(lo[:, 0])
    starts = lo[order, 0]
    for i, triangle in enumerate(a):
        lower, upper = triangle.min(0), triangle.max(0)
        subset = order[:np.searchsorted(starts, upper[0]+1e-9, side='right')]
        selected = subset[np.all(hi[subset] >= lower-1e-9, axis=1) &
                          np.all(lo[subset] <= upper+1e-9, axis=1)]
        for j in selected:
            yield i, int(j)


def crossings(objects, movable):
    data = {o.name: surface(o) for o in objects}
    pairs = []
    for ai, a in enumerate(objects):
        p, f, tree = data[a.name]
        for b in objects[ai:]:
            if a.name not in movable and b.name not in movable:
                continue
            q, g, support = data[b.name]
            for i, j in candidate_pairs(p, f, q, g):
                if a == b:
                    if i >= j or np.intersect1d(f[i], g[j]).size:
                        continue
                    if np.any(np.linalg.norm(p[f[i]][:, None]-q[g[j]][None, :], axis=2) < 1e-7):
                        continue
                if intersect(p[f[i]], q[g[j]]):
                    pairs.append((a.name, i, b.name, j))
    return data, pairs


def clearance(objects, movable, maximum=.003, clearance=.001, iterations=12):
    names = {o.name: o for o in objects}
    original = {n: np.array([o.matrix_world@v.co for v in o.data.vertices]) for n, o in names.items() if n in movable}
    counts = []
    for iteration in range(iterations+1):
        data, pairs = crossings(objects, movable)
        counts.append(len(pairs))
        print('CLEARANCE', iteration, len(pairs), flush=True)
        if not pairs or iteration == iterations or (len(counts) > 1 and counts[-1] >= counts[-2]):
            break
        corrections = {n: np.zeros_like(p) for n, p in original.items()}
        weights = {n: np.zeros(len(p)) for n, p in original.items()}
        for an, i, bn, j in pairs:
            # Prefer moving cloth instead of a fixed residue or rigid support.
            if an not in movable:
                an, bn, i, j = bn, an, j, i
            p, f, _ = data[an]
            q, g, _ = data[bn]
            a, b = p[f[i]], q[g[j]]
            normal = np.cross(b[1]-b[0], b[2]-b[0])
            length = np.linalg.norm(normal)
            if length < 1e-12:
                raise ValueError(f'Degenerate contact support {bn}/{j}')
            normal /= length
            centre = b.mean(0)
            side = np.sign((a.mean(0)-centre)@normal)
            if bn in movable and side < 0:
                normal *= -1
            distances = (a-centre)@normal
            push = np.maximum(clearance-distances, 0)
            for index, distance in zip(f[i], push):
                corrections[an][index] += normal*distance
                weights[an][index] += 1
            if bn in movable and bn != an:
                for index in g[j]:
                    corrections[bn][index] -= normal*min(float(push.max())*.5, maximum)
                    weights[bn][index] += 1
        for name, delta in corrections.items():
            active = weights[name] > 0
            if not active.any():
                continue
            delta[active] /= weights[name][active, None]
            p, f, _ = data[name]
            # Spread the correction once along 10 mm mesh edges, rather than
            # creating a pointed contact repair on an otherwise smooth panel.
            spread = delta.copy()
            for edge in names[name].data.edges:
                a, b = edge.vertices
                distance = np.linalg.norm(p[a]-p[b])
                if distance < .010:
                    factor = .35*(1-distance/.010)
                    if active[a] and not active[b]:
                        spread[b] += delta[a]*factor
                    if active[b] and not active[a]:
                        spread[a] += delta[b]*factor
            moved = p+spread-original[name]
            norms = np.linalg.norm(moved, axis=1)
            moved *= np.minimum(1., maximum/np.maximum(norms, 1e-20))[:, None]
            inverse = names[name].matrix_world.inverted()
            for vertex, point in zip(names[name].data.vertices, original[name]+moved):
                vertex.co = inverse@Vector(point)
            names[name].data.update()
            recalc(names[name])
    return {'counts': counts, 'changed_crossings': counts[-1], 'maximum_displacement_m': maximum,
            'clearance_target_m': clearance, 'falloff_m': .010,
            'exclusions': 0, 'pass': counts[-1] == 0}
