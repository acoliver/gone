"""Measured cloth tangent and generated suspension fitting for #130."""
import numpy as np
from mathutils import Vector


def cloth_frame(origin, frame, support):
    hits = []
    for x in np.linspace(-.012, .012, 9):
        for z in np.linspace(-.012, .012, 9):
            hit = support.ray_cast(Vector(origin + np.array([x, -.02, z]) @ frame),
                                   Vector(frame[1]), .05)[0]
            assert hit is not None
            hits.append(hit[:])
    positions = np.array(hits)
    _, _, axes = np.linalg.svd(positions - positions.mean(0))
    depth = axes[-1] * np.sign(axes[-1] @ frame[1])
    horizontal = frame[0] - (frame[0] @ depth) * depth
    horizontal /= np.linalg.norm(horizontal)
    result = np.array([horizontal, depth, np.cross(horizontal, depth)])
    # The reverse is subsequently conformed to the frozen cloth, with a 0.35 mm gap.
    return positions.mean(0) - depth * .0018, result
