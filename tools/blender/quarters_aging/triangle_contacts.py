"""Continuous triangle/triangle SAT, including coplanar overlap."""
import numpy as np


def intersect(a, b, tolerance=1e-9):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ea = np.roll(a, -1, axis=0) - a
    eb = np.roll(b, -1, axis=0) - b
    na, nb = np.cross(ea[0], ea[1]), np.cross(eb[0], eb[1])
    axes = np.vstack([na, nb, np.cross(ea[:, None], eb[None, :]).reshape(-1, 3),
                      np.cross(na, ea), np.cross(nb, eb)])
    norms = np.linalg.norm(axes, axis=1)
    axes = axes[norms > 1e-14] / norms[norms > 1e-14, None]
    if not len(axes):
        raise ValueError('Degenerate triangle in collision check')
    pa, pb = a @ axes.T, b @ axes.T
    return bool(np.all(pa.max(0) >= pb.min(0) - tolerance) and np.all(pb.max(0) >= pa.min(0) - tolerance))
