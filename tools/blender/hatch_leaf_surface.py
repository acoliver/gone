"""Seed-430 body sampling and declared rib attachment cuts."""
import numpy as np
import hatch_fit as fit


def _close(points, faces, ancestry, surface):
    count = len(faces)
    points, faces, parents = fit.close_selection(points, faces, np.arange(count), 'leaf cut')
    retained = surface[parents] & (np.arange(len(faces)) < count)
    triangles = points[faces]
    positive = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) > 0
    if np.any(retained & ~positive):
        raise fit.FitError('leaf cut: collapsed retained source triangle')
    return points, faces[positive], ancestry[parents][positive], retained[positive]


def _cut(points, faces, ancestry, surface, axis, plane, direction):
    # Cache intersections by source edge. Rounding independently clipped
    # triangles can leave different endpoints on their shared attachment cut.
    vertices = points.tolist()
    intersections = {}
    clipped, parents = [], []
    for index, face in enumerate(faces):
        polygon = []
        previous = int(face[-1])
        for value in face:
            current = int(value)
            before = direction * (points[previous, axis] - plane)
            after = direction * (points[current, axis] - plane)
            if (before < 0) != (after < 0):
                edge = tuple(sorted((previous, current)))
                if edge not in intersections:
                    if before == 0:
                        intersections[edge] = previous
                    elif after == 0:
                        intersections[edge] = current
                    else:
                        a, b = points[list(edge)]
                        point = a + (b - a) * ((plane - a[axis]) / (b[axis] - a[axis]))
                        point[axis] = plane
                        intersections[edge] = len(vertices)
                        vertices.append(point.tolist())
                polygon.append(intersections[edge])
            if after >= 0:
                polygon.append(current)
            previous = current
        for corner in range(1, len(polygon) - 1):
            triangle = [polygon[0], polygon[corner], polygon[corner + 1]]
            a, b, c = np.asarray([vertices[i] for i in triangle])
            if np.linalg.norm(np.cross(b - a, c - a)) > 0:
                clipped.append(triangle)
                parents.append(index)
    if not clipped:
        raise fit.FitError('leaf cut: empty source region')
    used, remap = np.unique(clipped, return_inverse=True)
    parents = np.asarray(parents)
    return _close(np.asarray(vertices)[used], remap.reshape(-1, 3), ancestry[parents], surface[parents])


def seated_hardware(points, triangles, ancestry, size, rotation, scale, registered_center=None):
    points = np.einsum('ij,kj->ik', np.asarray(points), np.asarray(rotation))
    span = np.ptp(points, axis=0)
    depth_scale = min(scale, size[2] / span[2])
    center = (points.max(axis=0) + points.min(axis=0)) / 2
    apex = points[points[:, 2].argmax()]
    # Retain the raised crown through both lateral reservation cuts.
    center[:2] = np.clip(center[:2], apex[:2] - np.asarray(size[:2]) / (2 * scale),
                        apex[:2] + np.asarray(size[:2]) / (2 * scale))
    if registered_center is not None:
        center = np.asarray(registered_center)
    points = (points - center) * [scale, scale, depth_scale]
    # The attachment cut gets a real seating face and side skirts, not
    # isolated extrema. Its depth never contributes to the measured ratio.
    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    _, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
    boundary = edges[counts[inverse] == 1]
    used, remap = np.unique(boundary, return_inverse=True)
    back = points[used].copy()
    back[:, 2] = -size[2] / 2
    n = len(points)
    back_index = dict(zip(used, range(n, n + len(used))))
    faces = triangles.tolist()
    parents = ancestry.tolist()
    for a, b in boundary:
        pa, pb = back_index[a], back_index[b]
        faces.extend([[int(b), int(a), pa], [int(b), pa, pb]])
        parent = int(ancestry[np.flatnonzero((triangles == a).any(axis=1) & (triangles == b).any(axis=1))[0]])
        parents.extend([parent, parent])
    points = np.concatenate([points, back])
    points, inverse = np.unique(points, axis=0, return_inverse=True)
    faces = inverse[np.asarray(faces)]
    area = np.linalg.norm(np.cross(points[faces[:, 1]]-points[faces[:, 0]], points[faces[:, 2]]-points[faces[:, 0]]), axis=1)
    surface = np.arange(len(faces)) < len(triangles)
    if np.any(surface & (area == 0)):
        raise fit.FitError("seating cut: collapsed source triangle")
    surface = surface[area > 0]
    faces, parents = faces[area > 0], np.asarray(parents)[area > 0]
    points, faces, parents, surface = _close(points, faces, parents, surface)
    for axis in range(2):
        for sign in [-1, 1]:
            points, faces, parents, surface = _cut(points, faces, parents, surface, axis, sign * size[axis] / 2, -sign)
    actual = np.ptp(points, axis=0)
    error = max(abs(points.min(axis=0) + np.asarray(size) / 2).max(), abs(actual-size).max())
    return points, faces, parents, error, depth_scale / scale


def slab_geometry(part, source, base_geometry, high=False, label=None):
    """Resample the generated broad face inside the exact structural perimeter."""
    vertices, faces = base_geometry(part, True)
    paint_end = len(vertices)
    sample = source.recipe['body']['high' if high else 'low']
    boundary = sample['boundary_vertices']
    # The perimeter, bevel, reverse repair and lifted paint sheets are the
    # retained functional construction; only the broad source face is replaced.
    faces = [face for face in faces if not all(index < boundary for index in face)]
    mapping = list(range(boundary))
    base = source.recipe['body']['base_z']
    height_scale = part['size'][1] / source.recipe['body']['source_height']
    for row in sample['samples'][boundary:]:
        x, y = np.asarray(row['uv']) * part['size'][:2]
        relief = 0.
        if row['repair'] is None:
            raw = np.asarray(row['barycentric']) @ source.vertices[source.faces[row['source_face']]]
            relief = np.clip((raw[2] - base) * height_scale, 0, part['paint_layer_depth'] * .4)
        if label is not None:
            point = np.array([x, y]) + part['transform']['origin'][:2]
            center = np.asarray(label['center'])
            if (abs(point - center) <= np.asarray(label['size']) / 2 + .03).all():
                relief = 0.
        mapping.append(len(vertices))
        vertices.append((x, y, -part['size'][2] / 2 + part['paint_layer_depth'] - relief))
    faces.extend(tuple(mapping[index] for index in face) for face in sample['faces'])
    return vertices, faces, paint_end
