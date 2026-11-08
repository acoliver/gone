"""Closed roof/underside sampling of the stable residue envelope within its budget."""
import numpy as np


def balanced_grid(width, depth, height, seed, back=False):
    nx, ny = (10, 8) if back else (12, 12)
    rng = np.random.default_rng(seed)
    x, y = np.meshgrid(np.linspace(-width/2, width/2, nx+1),
                       np.linspace(-depth/2, depth/2, ny+1))
    xx = x*(1-.06*(np.abs(y)/(depth/2))**8)
    yy = y*(1-.06*(np.abs(x)/(width/2))**8)
    points = np.c_[xx.ravel(), yy.ravel()]
    bottom = .0005+rng.uniform(0, .010, len(points))
    top = np.asarray(height(points), dtype=float)
    if top.shape != bottom.shape or not np.isfinite(top).all():
        raise ValueError('Residue grid needs a finite height for every column')
    top = np.maximum(top, bottom+.004)
    # A vertically extruded outline gives every side a planar rectangular
    # cap. The fractured underside has its own irregular, slightly inset rim.
    underside = points*.99+rng.uniform(-.0015, .0015, points.shape)
    vertices = np.vstack([np.c_[points, top], np.c_[underside, bottom]])
    n = len(points)
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j*(nx+1)+i
            b, c, d = a+1, a+nx+1, a+nx+2
            faces.extend([(a, b, d), (a, d, c), (a+n, d+n, b+n), (a+n, c+n, d+n)])
    edge = [*range(nx+1), *[j*(nx+1)+nx for j in range(1, ny+1)],
            *[ny*(nx+1)+i for i in range(nx-1, -1, -1)],
            *[j*(nx+1) for j in range(ny-1, 0, -1)]]
    for a, b in zip(edge, edge[1:]+edge[:1]):
        faces.extend([(a, a+n, b+n), (a, b+n, b)])
    faces = np.asarray(faces, dtype=np.int32)
    rough_underside(vertices, faces, n)
    return vertices, faces


def rough_underside(vertices, faces, roof_count):
    """Keep sampled fracture relief from accidentally joining into planar caps."""
    underside_faces = faces[np.all(faces >= roof_count, axis=1)]
    edges = {}
    adjacent = []
    for index, face in enumerate(underside_faces):
        for a, b in zip(face, np.roll(face, 1)):
            edge = tuple(sorted((int(a), int(b))))
            if edge in edges:
                adjacent.append((edges[edge], index))
            else:
                edges[edge] = index
    adjacent = np.asarray(adjacent)
    cosine_limit = np.cos(np.deg2rad(2))
    def penalties():
        triangles = vertices[underside_faces]
        normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        cosine = np.sum(normals[adjacent[:, 0]]*normals[adjacent[:, 1]], axis=1)
        return np.maximum(cosine-cosine_limit, 0)
    for _ in range(12):
        penalty = penalties()
        if not np.any(penalty):
            break
        for pair in adjacent[penalty > 0]:
            indices = np.unique(underside_faces[pair])
            best = (float(penalties().sum()), None, None)
            for index in indices:
                original = vertices[index, 2]
                ceiling = min(.012, vertices[index-roof_count, 2]-.004)
                for height in np.linspace(.0005, ceiling, 7):
                    vertices[index, 2] = height
                    score = float(penalties().sum())
                    if score < best[0]:
                        best = (score, index, height)
                vertices[index, 2] = original
            if best[1] is not None:
                vertices[best[1], 2] = best[2]
