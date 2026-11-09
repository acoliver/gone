"""Incremental strict SAT checks for a board with fixed triangle topology."""
import numpy as np
from reduced_clearance import surface
from triangle_contacts import intersect


class BoardContacts:
    def __init__(self, obj, body):
        self.points, self.faces, _ = surface(obj)
        body_points, body_faces, _ = surface(body)
        self.body = body_points[body_faces]
        self.body_low, self.body_high = self.body.min(1), self.body.max(1)
        self.incident = [np.flatnonzero(np.any(self.faces == i, axis=1)) for i in range(len(self.points))]

    def clear(self, indices):
        affected = np.unique(np.concatenate([self.incident[i] for i in indices]))
        triangles = self.points[self.faces]
        low, high = triangles.min(1), triangles.max(1)
        for i in affected:
            a = triangles[i]
            candidates = np.flatnonzero(np.all(self.body_low <= high[i]+1e-8, axis=1) &
                                        np.all(self.body_high >= low[i]-1e-8, axis=1))
            if any(intersect(a, self.body[j]) for j in candidates):
                return False
            candidates = np.flatnonzero(np.all(low <= high[i]+1e-8, axis=1) &
                                        np.all(high >= low[i]-1e-8, axis=1))
            for j in candidates:
                b = triangles[j]
                if i == j or np.any(np.linalg.norm(a[:, None]-b[None, :], axis=2) < 1e-7):
                    continue
                if intersect(a, b):
                    return False
        return True
