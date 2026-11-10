"""Exact continuous polyline-segment spacing for swept jacket envelopes."""
import numpy as np


def segment_distance(first, second):
    """Minimum distance over segment interiors and all four boundary edges."""
    a = np.asarray(first[:-1])[:, None, :]
    b = np.asarray(second[:-1])[None, :, :]
    u = np.diff(first, axis=0)[:, None, :]
    v = np.diff(second, axis=0)[None, :, :]
    w = a-b
    uu = np.sum(u*u, axis=2); vv = np.sum(v*v, axis=2)
    uv = np.sum(u*v, axis=2); uw = np.sum(u*w, axis=2); vw = np.sum(v*w, axis=2)
    denominator = uu*vv-uv*uv
    s = np.zeros_like(denominator); t = np.zeros_like(denominator)
    nonparallel = denominator>1e-20
    np.divide(uv*vw-vv*uw, denominator, out=s, where=nonparallel)
    np.divide(uu*vw-uv*uw, denominator, out=t, where=nonparallel)
    interior = nonparallel & (s>=0) & (s<=1) & (t>=0) & (t<=1)
    distance = np.where(interior, np.linalg.norm(w+s[:, :, None]*u-t[:, :, None]*v, axis=2), np.inf)
    for s_fixed in [0., 1.]:
        t_edge = np.clip((vw+s_fixed*uv)/vv, 0, 1)
        distance = np.minimum(distance, np.linalg.norm(w+s_fixed*u-t_edge[:, :, None]*v, axis=2))
    for t_fixed in [0., 1.]:
        s_edge = np.clip((t_fixed*uv-uw)/uu, 0, 1)
        distance = np.minimum(distance, np.linalg.norm(w+s_edge[:, :, None]*u-t_fixed*v, axis=2))
    return float(distance.min())
