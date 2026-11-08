"""UV-grain walks snapped to mesh edges, split without deleting cloth area."""
import heapq
import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree


def grain_walk(start, length, seed, step=.004, angle=0.):
    rng = np.random.default_rng(seed)
    points = [np.asarray(start, dtype=float)]
    distance, turn_distance = 0., 0.
    while distance < length:
        stride = min(step * rng.uniform(.75, 1.25), length-distance)
        if turn_distance >= .02 and rng.random() < .25:
            angle += rng.choice([-1, 1]) * math.pi/2
            turn_distance = 0.
        jitter = rng.uniform(-math.pi/15, math.pi/15)
        points.append(points[-1] + stride*np.array([math.cos(angle+jitter), math.sin(angle+jitter)]))
        distance += stride
        turn_distance += stride
    return np.asarray(points)


def split_polyline(obj, points, shrink_band=.008, max_length=None):
    """Points are in local 3D space, normally lifted from the pattern UVs."""
    if shrink_band <= 0 or (max_length is not None and max_length <= 0):
        raise ValueError('Tear relaxation band and length limit must be positive')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    tree = KDTree(len(bm.verts))
    for v in bm.verts:
        tree.insert(v.co, v.index)
    tree.balance()
    targets = [tree.find(Vector(p))[1] for p in points]
    polyline = np.asarray(points)
    starts, delta = polyline[:-1], np.diff(polyline, axis=0)
    lengths2 = (delta*delta).sum(1)
    if not len(lengths2) or np.any(lengths2 == 0):
        bm.free()
        raise ValueError('Tear polyline needs distinct consecutive points')
    def distance(point):
        t = np.clip(((point-starts)*delta).sum(1)/lengths2, 0, 1)
        return np.linalg.norm(point-starts-t[:, None]*delta, axis=1).min()
    penalties = [distance(np.asarray(e.verts[0].co+e.verts[1].co)/2) for e in bm.edges]
    path = set()
    path_length, stopped = 0., False
    for source, target in zip(targets, targets[1:]):
        if source == target:
            continue
        queue, costs, parents = [(0., source)], {source: 0.}, {}
        while queue:
            cost, index = heapq.heappop(queue)
            if cost != costs[index]:
                continue
            if index == target:
                break
            for edge in bm.verts[index].link_edges:
                other = edge.other_vert(bm.verts[index]).index
                candidate = cost+edge.calc_length()+5*penalties[edge.index]
                if candidate < costs.get(other, float('inf')):
                    costs[other] = candidate
                    parents[other] = (index, edge.index)
                    heapq.heappush(queue, (candidate, other))
        if target not in costs:
            bm.free()
            raise ValueError('Tear crosses disconnected pattern islands')
        current = target
        chain = []
        while current != source:
            current, edge_index = parents[current]
            chain.append(edge_index)
        for edge_index in reversed(chain):
            if edge_index in path:
                continue
            edge = bm.edges[edge_index]
            added_length = edge.calc_length() if len(edge.link_faces) == 2 else 0.
            if max_length is not None and path_length+added_length > max_length:
                stopped = True
                break
            path.add(edge_index)
            path_length += added_length
        if stopped:
            break
    edges = [bm.edges[i] for i in sorted(path) if len(bm.edges[i].link_faces) == 2]
    if max_length is not None:
        if not edges:
            bm.free()
            raise ValueError('Length-limited tear has no interior mesh edges')
        starts = np.array([e.verts[0].co[:] for e in edges])
        delta = np.array([e.verts[1].co[:] for e in edges])-starts
        lengths2 = (delta*delta).sum(1)
    area = sum(f.calc_area() for f in bm.faces)
    split_length = sum(e.calc_length() for e in edges)
    bmesh.ops.split_edges(bm, edges=edges)
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    lip_ids = {v.index for e in bm.edges if e.is_boundary for v in e.verts}
    lip = obj.vertex_groups.get('Lip shrink') or obj.vertex_groups.new(name='Lip shrink')
    relaxation = None
    if shrink_band != .008:
        relaxation = obj.vertex_groups.get('Lip relaxation') or obj.vertex_groups.new(name='Lip relaxation')
    layer = bm.verts.layers.deform.verify()
    boundary_points = np.array([bm.verts[i].co[:] for i in sorted(lip_ids)]) if lip_ids else np.empty((0, 3))
    # Only the authored split receives shrink, not the original panel perimeter.
    for v in bm.verts:
        d = distance(np.asarray(v.co))
        if d < .008:
            v[layer][lip.index] = 1-float(d/.008)
        if relaxation is not None and d < shrink_band:
            v[layer][relaxation.index] = max(v[layer].get(relaxation.index, 0.), 1-float(d/shrink_band))
    final_area = sum(f.calc_area() for f in bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return {'split_length_m': split_length, 'area_before_m2': area,
            'area_after_m2': final_area, 'removed_area_m2': area-final_area,
            'boundary_vertex_count': len(boundary_points)}


def lift_pattern_path(obj, points):
    """Lift UV points onto the source triangles using barycentric coordinates."""
    obj.data.calc_loop_triangles()
    uv = obj.data.uv_layers[0].data
    triangles = list(obj.data.loop_triangles)
    coords = np.array([[uv[i].uv[:] for i in t.loops] for t in triangles])
    result = []
    for point in points:
        a, b, c = coords[:, 0], coords[:, 1], coords[:, 2]
        v0, v1, v2 = b-a, c-a, point-a
        determinant = v0[:, 0]*v1[:, 1]-v0[:, 1]*v1[:, 0]
        valid = abs(determinant) > 1e-12
        u = np.divide(v2[:, 0]*v1[:, 1]-v2[:, 1]*v1[:, 0], determinant, out=np.full(len(a), -1.), where=valid)
        v = np.divide(v0[:, 0]*v2[:, 1]-v0[:, 1]*v2[:, 0], determinant, out=np.full(len(a), -1.), where=valid)
        candidates = np.flatnonzero(valid & (u >= -1e-6) & (v >= -1e-6) & (u+v <= 1+1e-6))
        if not len(candidates):
            raise ValueError(f'Tear path leaves pattern at {point}')
        i = candidates[0]
        p = [obj.data.vertices[j].co for j in triangles[i].vertices]
        result.append(tuple(p[0]*(1-u[i]-v[i])+p[1]*u[i]+p[2]*v[i]))
    return result
