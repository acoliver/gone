"""Strict tunic contacts with an unchanged hanger as the sole baseline."""
import numpy as np


def triangle_signature(triangles):
    faces = np.asarray(triangles, dtype=np.float64).copy()
    faces = np.array([face[np.lexsort(face.T[::-1])] for face in faces])
    flattened = faces.reshape(len(faces), 9)
    return flattened[np.lexsort(flattened.T[::-1])]


def contact_gate(current, baseline, unaged_hanger, aged_hanger):
    old = baseline['self']['Hanger']['count']
    hanger = current['self']['Hanger']['count']
    changed = sum(value['count'] for name, value in current['self'].items() if name != 'Hanger')
    changed += sum(value['count'] for value in current['pairs'].values())
    before, after = triangle_signature(unaged_hanger), triangle_signature(aged_hanger)
    exact = before.shape == after.shape and np.array_equal(before, after)
    return {'changed_intersections': changed, 'hanger': hanger, 'unaged_hanger': old,
            'hanger_geometry_exact': bool(exact),
            'pass': bool(changed == 0 and hanger == old and exact)}
