"""Shared clearance deformation for dense and reduced sofa cover surfaces."""
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
