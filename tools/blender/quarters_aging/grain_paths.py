"""Physical-length tear walks using the fitted pattern UV gradient on each triangle."""
import math

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def surface_walk(obj, start, length, seed, step=.004):
    obj.data.calc_loop_triangles()
    triangles = list(obj.data.loop_triangles)
    points = [obj.matrix_world@v.co for v in obj.data.vertices]
    tree = BVHTree.FromPolygons(points, [t.vertices[:] for t in triangles], all_triangles=True)
    uv = obj.data.uv_layers[0].data
    rng = np.random.default_rng(seed)
    current, _, face, _ = tree.find_nearest(Vector(start))
    inverse = obj.matrix_world.inverted()
    path = [tuple(inverse@current)]
    distance, next_turn, axis, sign = 0., rng.uniform(.02, .04), 0, 1
    previous = None
    while distance < length:
        tri = triangles[face]
        p = np.array([points[i] for i in tri.vertices])
        pattern = np.array([uv[i].uv[:] for i in tri.loops])
        delta = pattern[1:]-pattern[0]
        determinant = np.linalg.det(delta)
        if abs(determinant) < 1e-12:
            raise ValueError('Tear path reaches a degenerate pattern triangle')
        tangents = np.linalg.solve(delta, p[1:]-p[0])
        warp = tangents[axis]/np.linalg.norm(tangents[axis])
        normal = np.cross(p[1]-p[0], p[2]-p[0])
        normal /= np.linalg.norm(normal)
        if distance >= next_turn:
            if rng.random() < .25:
                axis = 1-axis
                warp = tangents[axis]/np.linalg.norm(tangents[axis])
                sign = int(rng.choice([-1, 1]))
                previous = None
            next_turn = distance+rng.uniform(.02, .04)
        if previous is not None and np.dot(warp*sign, previous) < 0:
            sign = -sign
        angle = rng.uniform(-math.pi/15, math.pi/15)
        direction = warp*sign*np.cos(angle)+np.cross(normal, warp)*sign*np.sin(angle)
        stride = min(step*rng.uniform(.75, 1.25), length-distance)
        candidate = current+Vector(direction)*stride
        following, _, next_face, _ = tree.find_nearest(candidate)
        actual = (following-current).length
        if actual < stride*.1:
            raise ValueError('Tear walk reached an open pattern boundary')
        distance += actual
        path.append(tuple(inverse@following))
        current, face, previous = following, next_face, direction
    return path
