"""Measure fitting bases from their authored anchors, independently of their pose."""
import numpy as np


def base_indices(original, anchors, tolerance=1e-6):
    original, anchors = np.asarray(original), np.asarray(anchors)
    distances = np.linalg.norm(anchors[:, None]-original[None, :], axis=2)
    indices = distances.argmin(1)
    errors = distances[np.arange(len(anchors)), indices]
    if errors.max() > tolerance:
        raise ValueError(f'Authored fitting base has no matching vertex: {errors.max():.9f} m')
    if len(set(indices)) != len(indices):
        raise ValueError('Authored fitting base maps multiple anchors to one vertex')
    return indices


def rigid_normal(original, destination, indices, outward):
    """Transport the authored base normal, rather than guessing the thinnest axis."""
    original, destination = np.asarray(original), np.asarray(destination)
    src, dst = original-original.mean(0), destination-destination.mean(0)
    u, _, vt = np.linalg.svd(src.T@dst)
    if np.linalg.det(u@vt) < 0:
        u[:, -1] *= -1
    base = original[indices]
    normal = np.linalg.svd(base-base.mean(0))[2][-1]
    normal *= 1 if normal@outward >= 0 else -1
    return normal@u@vt
