"""Bounded fairing of reduced cloth and local untangling at the throw hold."""
import bmesh
import numpy as np
from mathutils import Vector

from common import recalc
from sofa_pass9_finish import points


def fair_interior(obj, maximum=.006, iterations=10):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    original = {v: v.co.copy() for v in bm.verts}
    fixed = {v for v in bm.verts if v.is_boundary}
    layer = bm.verts.layers.deform.active
    hold = obj.vertex_groups.get('Retained stitches')
    if hold:
        fixed.update(v for v in bm.verts if v[layer].get(hold.index, 0.) > .5)
    for _ in range(iterations):
        updates = {}
        for vertex in bm.verts:
            if vertex in fixed or not vertex.link_edges:
                continue
            mean = sum((e.other_vert(vertex).co for e in vertex.link_edges), Vector())/len(vertex.link_edges)
            target = vertex.co+.45*(mean-vertex.co)-original[vertex]
            if target.length > maximum:
                target *= maximum/target.length
            updates[vertex] = original[vertex]+target
        for vertex, position in updates.items():
            vertex.co = position
    moved = max(((v.co-original[v]).length for v in bm.verts), default=0.)
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    return {'method': 'bounded one-ring fairing; open boundaries and retained stitches fixed',
            'iterations': iterations, 'displacement_limit_m': maximum, 'maximum_displacement_m': moved}


def restore_hold_patch(obj, rest, centre=(1.113, .130, .755), inner=.022, outer=.055):
    original = points(obj)
    rest = np.asarray(rest)
    if rest.shape != original.shape:
        raise ValueError('Hold repair requires the matching prepared cloth topology')
    distance = np.linalg.norm(original-np.asarray(centre), axis=1)
    weight = np.clip((outer-distance)/(outer-inner), 0, 1)
    weight = weight*weight*(3-2*weight)
    hold = obj.vertex_groups['Retained stitches'].index
    for vertex in obj.data.vertices:
        if any(g.group == hold and g.weight > .5 for g in vertex.groups):
            weight[vertex.index] = 0.
    result = original+(rest-original)*weight[:, None]
    inverse = obj.matrix_world.inverted()
    for vertex, position in zip(obj.data.vertices, result):
        vertex.co = inverse@Vector(position)
    recalc(obj)
    return {'method': 'restore the prepared local fold around the retained stitches, smooth collar into solved hang',
            'inner_radius_m': inner, 'outer_radius_m': outer, 'centre_blender_m': list(centre),
            'moved_vertices': int(np.count_nonzero(weight)),
            'maximum_displacement_m': float(np.linalg.norm(result-original, axis=1).max())}
