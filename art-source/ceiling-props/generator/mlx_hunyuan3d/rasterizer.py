"""Forward triangle rasteriser — the one piece of Hunyuan3D-Paint that is a CUDA kernel.

Upstream's texture stack depends on `custom_rasterizer`, a CUDAExtension built from
rasterizer_gpu.cu. Its entire public surface is two functions, and only one of them is
actually a kernel:

    rasterize(pos, tri, resolution) -> (findices, barycentric)
    interpolate(col, findices, barycentric, tri)      # four lines of plain tensor ops

`raster_texture` raises "not implemented" and `raster_antialias` is a no-op in that
backend, and nothing in the render path touches autograd, so only FORWARD rasterisation is
needed. That is what this module provides, in NumPy, portably.

Output convention matches the CUDA kernel exactly so the rest of the stack is unchanged:
    findices    (H, W) int32, ONE-BASED face index; 0 means background
    barycentric (H, W, 3) float32 weights for that face's three vertices

The implementation is fully vectorised — no Python loop over triangles. Every triangle's
pixel-bounding-box candidates are enumerated at once, tested, and resolved with a single
depth sort. A per-triangle loop (as in tests/make_test_views.py) is fine for a handful of
preview renders but is far too slow for texture baking, which rasterises a 200k-face mesh
from many viewpoints.
"""

from __future__ import annotations

import numpy as np


def rasterize(
    vertices: np.ndarray,
    faces: np.ndarray,
    resolution: tuple[int, int],
    max_candidates: int = 200_000_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Rasterise screen-space triangles.

    `vertices` is (V, 3) with x/y already in pixel units and z as depth where SMALLER IS
    NEARER. `faces` is (F, 3) vertex indices. `resolution` is (height, width).
    """
    height, width = int(resolution[0]), int(resolution[1])
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    # Signed area in screen space; a zero area is a degenerate/edge-on triangle.
    area = ((v1[:, 0] - v0[:, 0]) * (v2[:, 1] - v0[:, 1])
            - (v1[:, 1] - v0[:, 1]) * (v2[:, 0] - v0[:, 0]))

    x_lo = np.clip(np.floor(np.minimum.reduce([v0[:, 0], v1[:, 0], v2[:, 0]])), 0, width).astype(np.int64)
    x_hi = np.clip(np.ceil(np.maximum.reduce([v0[:, 0], v1[:, 0], v2[:, 0]])) + 1, 0, width).astype(np.int64)
    y_lo = np.clip(np.floor(np.minimum.reduce([v0[:, 1], v1[:, 1], v2[:, 1]])), 0, height).astype(np.int64)
    y_hi = np.clip(np.ceil(np.maximum.reduce([v0[:, 1], v1[:, 1], v2[:, 1]])) + 1, 0, height).astype(np.int64)

    box_w = np.maximum(x_hi - x_lo, 0)
    box_h = np.maximum(y_hi - y_lo, 0)
    counts = box_w * box_h
    counts[area == 0] = 0

    total = int(counts.sum())
    findices = np.zeros((height, width), dtype=np.int32)
    barycentric = np.zeros((height, width, 3), dtype=np.float32)
    if total == 0:
        return findices, barycentric
    if total > max_candidates:
        raise MemoryError(
            f"rasterizer would enumerate {total:,} candidate pixels (limit {max_candidates:,}); "
            "lower the resolution or simplify the mesh"
        )

    # Expand every triangle's bounding box into candidate pixels without looping: repeat the
    # triangle id by its pixel count, then recover each candidate's offset within its box.
    tri_id = np.repeat(np.arange(faces.shape[0], dtype=np.int64), counts)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    local = np.arange(total, dtype=np.int64) - np.repeat(starts, counts)
    w_of = box_w[tri_id]
    px = x_lo[tri_id] + (local % w_of)
    py = y_lo[tri_id] + (local // w_of)

    # Edge functions at pixel centres give barycentric weights directly.
    cx = px + 0.5
    cy = py + 0.5
    a = area[tri_id]
    t0, t1, t2 = v0[tri_id], v1[tri_id], v2[tri_id]
    w0 = ((t2[:, 0] - t1[:, 0]) * (cy - t1[:, 1]) - (t2[:, 1] - t1[:, 1]) * (cx - t1[:, 0])) / a
    w1 = ((t0[:, 0] - t2[:, 0]) * (cy - t2[:, 1]) - (t0[:, 1] - t2[:, 1]) * (cx - t2[:, 0])) / a
    w2 = 1.0 - w0 - w1

    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not inside.any():
        return findices, barycentric

    tri_id, px, py = tri_id[inside], px[inside], py[inside]
    w0, w1, w2 = w0[inside], w1[inside], w2[inside]
    depth = w0 * t0[inside, 2] + w1 * t1[inside, 2] + w2 * t2[inside, 2]

    # Depth resolution without atomics: order by pixel then by depth, and keep the first
    # entry for each pixel, which is the nearest surviving fragment.
    flat = py * width + px
    order = np.lexsort((depth, flat))
    flat_sorted = flat[order]
    first = np.ones(flat_sorted.shape[0], dtype=bool)
    first[1:] = flat_sorted[1:] != flat_sorted[:-1]
    winner = order[first]
    won_flat = flat_sorted[first]

    ys, xs = np.divmod(won_flat, width)
    findices[ys, xs] = (tri_id[winner] + 1).astype(np.int32)
    barycentric[ys, xs, 0] = w0[winner]
    barycentric[ys, xs, 1] = w1[winner]
    barycentric[ys, xs, 2] = w2[winner]
    return findices, barycentric


def interpolate(attr: np.ndarray, findices: np.ndarray, barycentric: np.ndarray,
                faces: np.ndarray) -> np.ndarray:
    """Barycentric interpolation of a per-vertex attribute. Port of the reference's
    `interpolate`, including its trick of clamping background pixels to face 0 and letting
    the zero barycentric weights blank them out."""
    faces = np.asarray(faces, dtype=np.int64)
    index = findices - 1 + (findices == 0)
    corners = attr[faces[index]]                       # (H, W, 3, C)
    return (barycentric[..., None] * corners).sum(axis=-2)


def look_at_screen(vertices: np.ndarray, resolution: tuple[int, int],
                   azimuth: float, elevation: float = 0.0,
                   ortho_scale: float = 1.2) -> np.ndarray:
    """Orthographic camera placement matching upstream MeshRender (camera_type='orth').

    Returns (V, 3) screen-space vertices: x/y in pixels, z as depth with smaller nearer.
    """
    height, width = int(resolution[0]), int(resolution[1])
    verts = np.asarray(vertices, dtype=np.float64)

    ar, er = np.radians(azimuth), np.radians(elevation)
    ca, sa = np.cos(ar), np.sin(ar)
    rot_y = np.array([[ca, 0.0, sa], [0.0, 1.0, 0.0], [-sa, 0.0, ca]])
    ce, se = np.cos(er), np.sin(er)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, ce, -se], [0.0, se, ce]])
    view = verts @ rot_y.T @ rot_x.T

    scale = min(width, height) / ortho_scale
    screen = np.empty_like(view)
    screen[:, 0] = view[:, 0] * scale + width * 0.5
    screen[:, 1] = height * 0.5 - view[:, 1] * scale
    screen[:, 2] = -view[:, 2]  # +z faces the camera, so negate to make smaller = nearer
    return screen
