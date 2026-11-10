"""Resolve reduction-induced crossings against unchanged support triangles."""
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from common import recalc
from triangle_contacts import intersect


def surface(obj):
    obj.data.calc_loop_triangles()
    vertices = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    faces = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    return vertices, faces, BVHTree.FromPolygons(vertices.tolist(), faces.tolist(), all_triangles=True)


def crossing_pairs(obj, support=None):
    av, af, at = surface(obj)
    bv, bf, bt = surface(support) if support is not None else (av, af, at)
    pairs = []
    for i, j in at.overlap(bt):
        a, b = av[af[i]], bv[bf[j]]
        if support is None and (i >= j or np.any(np.linalg.norm(a[:, None]-b[None, :], axis=2) < 1e-7)):
            continue
        if intersect(a, b):
            pairs.append((i, j))
    return pairs


def push_out(obj, support, clearance=.0005, maximum=.003, paired=False):
    initial, _, _ = surface(obj)
    count = len(initial)//2
    history = []
    for iteration in range(40):
        pairs = crossing_pairs(obj, support)
        history.append(len(pairs))
        if not pairs:
            break
        vertices, faces, _ = surface(obj)
        other, other_faces, _ = surface(support)
        displacement = np.zeros_like(vertices)
        counts = np.zeros(len(vertices))
        for i, j in pairs:
            triangle = other[other_faces[j]]
            normal = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
            normal /= np.linalg.norm(normal)
            indices = faces[i]
            depth = clearance-np.min((vertices[indices]-triangle[0])@normal)
            shift = normal*min(.001, max(0., depth))
            affected = set(indices)
            if paired:
                affected |= {(int(k)+count) % len(vertices) for k in indices}
            for index in affected:
                displacement[index] += shift
                counts[index] += 1
        active = counts > 0
        proposed = vertices.copy()
        proposed[active] += displacement[active]/counts[active, None]
        delta = proposed-initial
        length = np.linalg.norm(delta, axis=1)
        limited = length > maximum
        delta[limited] *= (maximum/length[limited])[:, None]
        inverse = obj.matrix_world.inverted()
        for vertex, point in zip(obj.data.vertices, initial+delta):
            vertex.co = inverse @ Vector(point)
        recalc(obj)
    final, _, _ = surface(obj)
    return dict(crossings_before=history[0], crossings_after=len(crossing_pairs(obj, support)),
                history=history, maximum_motion_m=float(np.linalg.norm(final-initial, axis=1).max()),
                clearance_m=clearance, motion_limit_m=maximum)


def clear_reduced(body):
    report = {'TunicBody/Hanger': push_out(body, bpy.data.objects['Hanger'], clearance=.001)}
    for name in ('ShoulderBoard_L', 'ShoulderBoard_R', 'Collar', 'Placket', 'RibbonBar'):
        obj = bpy.data.objects[name]
        report[name+'/TunicBody'] = push_out(obj, body, maximum=.006 if name == 'Collar' else .003,
                                            paired=name != 'Collar')
        report[name+'/self'] = len(crossing_pairs(obj))
    return report


def compress_rim(obj, sheet_vertices):
    source = np.array([item.value for item in obj.data.attributes['Wool rim source'].data])
    if not np.array_equal(source[:sheet_vertices], np.arange(sheet_vertices)):
        raise ValueError('Solidify changed the retained sheet vertex block')
    history = []
    for _ in range(16):
        pairs = crossing_pairs(obj)
        history.append(len(pairs))
        if not pairs:
            break
        _, faces, _ = surface(obj)
        changed = {int(v) for i, j in pairs for v in np.r_[faces[i], faces[j]] if v >= sheet_vertices}
        if not changed:
            break
        for index in changed:
            # Rim-only Solidify appends boundary copies, not a full second block.
            vertex = obj.data.vertices[index]
            base = obj.data.vertices[int(source[index])].co
            offset = vertex.co-base
            if offset.length > .0001:
                vertex.co = base+offset.normalized()*max(.0001, offset.length*.5)
        recalc(obj)
    return dict(history=history, remaining_crossings=len(crossing_pairs(obj)),
                minimum_compressed_thickness_m=.0001)
