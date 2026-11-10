"""Shared clearance deformation for dense and reduced sofa cover surfaces."""
import heapq

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

from common import recalc


def points(obj):
    return np.array([obj.matrix_world@v.co for v in obj.data.vertices])


def carry_clearance(dense, low, original):
    """Apply the reduced mesh's finishing field to its dense bake source too."""
    low.data.calc_loop_triangles()
    faces = np.array([t.vertices[:] for t in low.data.loop_triangles])
    tree = BVHTree.FromPolygons(original.tolist(), faces.tolist(), all_triangles=True)
    displacement = points(low)-original
    inverse = dense.matrix_world.inverted()
    maximum = 0.
    for vertex in dense.data.vertices:
        world = dense.matrix_world@vertex.co
        nearest, _, index, _ = tree.find_nearest(world)
        ids = faces[index]
        shift = barycentric_transform(nearest, *[Vector(p) for p in original[ids]],
                                       *[Vector(p) for p in displacement[ids]])
        vertex.co = inverse@(world+shift)
        maximum = max(maximum, shift.length)
    recalc(dense)
    return {'method': 'same barycentric clearance field on dense and game cloth',
            'maximum_dense_displacement_m': maximum}


def open_lips(obj, seed):
    from sofa_pass8_finish import lip_curl
    report = lip_curl(obj, seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    layer = bm.verts.layers.deform.active
    group = obj.vertex_groups['Lip shrink'].index
    directions = {}
    for edge in bm.edges:
        if not edge.is_boundary or max(v[layer].get(group, 0.) for v in edge.verts) < .5:
            continue
        centre = edge.link_faces[0].calc_center_median()
        midpoint = (edge.verts[0].co+edge.verts[1].co)/2
        tangent = (edge.verts[1].co-edge.verts[0].co).normalized()
        outward = midpoint-centre
        outward = (outward-tangent*outward.dot(tangent)).normalized()
        for vertex in edge.verts:
            if vertex[layer].get(group, 0.) > 0:
                directions[vertex] = directions.get(vertex, Vector())+outward
    # Each connected panel owns its lip. Coincident opposing lips need opposite
    # curl directions, so a world-space nearest lookup would close some tears.
    positions = {v: v.co.copy() for v in bm.verts}
    displacement = {}
    pending = []
    bm.verts.index_update()
    by_index = {v.index: v for v in bm.verts}
    distances = {}
    roots = {}
    for vertex, direction in directions.items():
        phase = seed*.137+vertex.co.x*79+vertex.co.y*113+vertex.co.z*53
        displacement[vertex] = -direction.normalized()*(.0035+.002*np.sin(phase))
        distances[vertex.index] = 0.
        roots[vertex.index] = vertex
        heapq.heappush(pending, (0., vertex.index))
    while pending:
        distance, index = heapq.heappop(pending)
        if distance != distances[index]:
            continue
        vertex = by_index[index]
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            candidate = distance+edge.calc_length()
            if candidate < .015 and candidate < distances.get(other.index, float('inf')):
                distances[other.index] = candidate
                roots[other.index] = roots[index]
                heapq.heappush(pending, (candidate, other.index))
    for index, distance in distances.items():
        vertex = by_index[index]
        vertex.co = positions[vertex]+displacement[roots[index]]*(1-distance/.015)
    bm.to_mesh(obj.data)
    bm.free()
    recalc(obj)
    report.update(inward_curl_range_m=[.0015, .0055], inward_curl_band_m=.015,
                  inward_curl_vertices=len(distances))
    return report
