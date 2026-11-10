"""Reject fringe-card placements against actual triangles before exporting them."""
import numpy as np

from triangle_contacts import intersect


class CardContacts:
    def __init__(self, objects):
        triangles = []
        for obj in objects:
            obj.data.calc_loop_triangles()
            points = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
            triangles.extend(points[np.array([t.vertices[:] for t in obj.data.loop_triangles])])
        self.triangles = np.asarray(triangles)
        self.minimum = self.triangles.min(1)
        self.maximum = self.triangles.max(1)

    def clear(self, quad):
        quad = np.asarray(quad)
        for triangle in quad[[[0, 1, 2], [0, 2, 3]]]:
            candidates = np.all(self.maximum >= triangle.min(0), axis=1) & np.all(self.minimum <= triangle.max(0), axis=1)
            if any(intersect(triangle, other) for other in self.triangles[candidates]):
                return False
        return True

    def add(self, quad):
        triangles = np.asarray(quad)[[[0, 1, 2], [0, 2, 3]]]
        self.triangles = np.concatenate([self.triangles, triangles])
        self.minimum = np.concatenate([self.minimum, triangles.min(1)])
        self.maximum = np.concatenate([self.maximum, triangles.max(1)])
