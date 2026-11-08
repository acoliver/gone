"""Regularize only sub-contact source-grid cells without collapsing their topology."""
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree


def resolve_grid_contacts(body, minimum=.0041):
    source = np.array([v.co[:] for v in body.data.vertices])
    candidates = [(p, [i]) for i, p in enumerate(source)]
    candidates += [(source[list(e.vertices)].mean(0), list(e.vertices)) for e in body.data.edges]
    candidates += [(source[list(f.vertices)].mean(0), list(f.vertices)) for f in body.data.polygons]
    tree = KDTree(len(candidates))
    for i, (point, _) in enumerate(candidates):
        tree.insert(Vector(point), i)
    tree.balance()
    mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    mesh.calc_loop_triangles()
    faces = np.array([t.vertices[:] for t in mesh.loop_triangles])
    mapping = []
    for vertex in mesh.vertices:
        _, i, distance = tree.find(vertex.co)
        if distance > 1e-6:
            raise ValueError('SIMPLE subdivision no longer has linear grid coordinates')
        mapping.append(candidates[i][1])
    width = max(map(len, mapping))
    ids = np.zeros((len(mapping), width), dtype=int)
    weights = np.zeros_like(ids, dtype=float)
    for i, vertices in enumerate(mapping):
        ids[i, :len(vertices)] = vertices
        weights[i, :len(vertices)] = 1/len(vertices)
    positions = source.copy()
    for iteration in range(120):
        evaluated = np.sum(positions[ids]*weights[:, :, None], axis=1)
        triangles = evaluated[faces]
        edges = np.linalg.norm(triangles-np.roll(triangles, -1, axis=1), axis=2)
        longest = edges.argmax(1)
        order = (longest[:, None]+np.arange(3)[None, :]) % 3
        ordered = np.take_along_axis(faces, order, axis=1)
        a, b, c = (evaluated[ordered[:, i]] for i in range(3))
        ab = b-a
        t = np.sum((c-a)*ab, axis=1)/np.sum(ab*ab, axis=1)
        perpendicular = c-a-t[:, None]*ab
        altitude = np.linalg.norm(perpendicular, axis=1)
        bad = np.flatnonzero(altitude < minimum-1e-8)
        if not len(bad):
            break
        correction = np.zeros_like(positions)
        counts = np.zeros(len(positions))
        for face in bad:
            gradient = perpendicular[face]/altitude[face]
            factors = np.array([t[face]-1, -t[face], 1.])
            gradients = {}
            for vertex, factor in zip(ordered[face], factors):
                for index, weight in zip(ids[vertex], weights[vertex]):
                    if weight:
                        gradients[index] = gradients.get(index, np.zeros(3))+gradient*factor*weight
            denominator = sum(g@g for g in gradients.values())
            for index, g in gradients.items():
                correction[index] += g*((minimum-altitude[face])/denominator)
                counts[index] += 1
        moved = counts > 0
        positions[moved] += correction[moved]/counts[moved, None]*.8
    else:
        raise ValueError(f'Source grid cannot resolve contacts: minimum {altitude.min()}')
    delta = positions-source
    for key in body.data.shape_keys.key_blocks:
        for vertex, offset in zip(key.data, delta):
            vertex.co += Vector(offset)
    for vertex, point in zip(body.data.vertices, positions):
        vertex.co = Vector(point)
    body.data.update()
    return dict(iterations=iteration, minimum_altitude_m=float(altitude.min()),
                maximum_source_motion_m=float(np.linalg.norm(delta, axis=1).max()),
                source_vertices_preserved=len(source), method='local altitude gradients on the unchanged source grid')
