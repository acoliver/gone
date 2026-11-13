"""Reciprocal opening-disc proof for the centred #130 suspension."""
import numpy as np


def section_contours(vertices, faces, plane_x):
    adjacency, coordinates = {}, {}
    for triangle in vertices[np.asarray(faces)]:
        cut = []
        for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
            if (a[0] - plane_x) * (b[0] - plane_x) < 0:
                cut.append(a[1:] + (b[1:] - a[1:]) * (plane_x - a[0]) / (b[0] - a[0]))
        if len(cut) != 2:
            continue
        a, b = [tuple(np.rint(p / 1e-9).astype(np.int64)) for p in cut]
        if a == b:
            continue
        coordinates[a], coordinates[b] = cut
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    assert adjacency and all(len(v) == 2 for v in adjacency.values()), 'Closed ring section required'
    remaining, curves = set(adjacency), []
    while remaining:
        start = next(iter(remaining))
        previous, current, curve = None, start, []
        while current != start or not curve:
            curve.append(coordinates[current])
            remaining.remove(current)
            following = next(n for n in adjacency[current] if n != previous)
            previous, current = current, following
        curves.append(np.asarray(curve))
    return curves


def contains(curve, point):
    a = curve - point
    b = np.roll(a, -1, axis=0)
    angle = np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], np.einsum('ij,ij->i', a, b)).sum()
    return abs(angle) > np.pi


def disc_crossings(curve, center, normal):
    result = []
    for a, b in zip(curve, np.roll(curve, -1, axis=0)):
        da, db = (a - center) @ normal, (b - center) @ normal
        if da * db < 0:
            result.append(a + (b - a) * da / (da - db))
    return result


def reciprocal_interlink(vertices, faces, ring_plane, loop):
    center = np.asarray(loop['center_m'])
    up, normal = np.asarray(loop['up']), np.asarray(loop['normal'])
    radius, wire = loop['radius_m'], loop['wire_radius_m']
    assert abs(normal[0]) < 1e-12, 'The two link planes must be perpendicular'
    theta = np.arange(loop['major_segments']) * 2 * np.pi / loop['major_segments']
    centerline = center + radius * (np.cos(theta)[:, None] * [1, 0, 0] + np.sin(theta)[:, None] * up)
    curves = section_contours(vertices, faces, ring_plane)
    cuts = disc_crossings(centerline, np.array([ring_plane, 0, 0]), np.array([1, 0, 0]))
    assert len(cuts) == 2
    enclosed = [[c for c in curves if contains(c, p[1:])] for p in cuts]
    through = [i for i, contours in enumerate(enclosed) if len(contours) >= 2 and cuts[i][2] > .0162]
    assert len(through) == 1, 'Loop centreline must cross the upper ring opening exactly once'
    opening = min(enclosed[through[0]], key=lambda c: np.ptp(c[:, 0]) * np.ptp(c[:, 1]))
    origin = opening.mean(0)
    assert contains(opening, origin)
    # Midpoints of the measured inner/outer radial section intersections trace
    # a closed path inside the actual soldered ring, rather than a guessed ellipse.
    ring_line = []
    for angle in (np.arange(192) + .317) * 2 * np.pi / 192:
        direction = np.array([np.cos(angle), np.sin(angle)])
        distances = []
        for curve in curves:
            a = curve - origin
            edge = np.roll(curve, -1, axis=0) - curve
            determinant = direction[0] * edge[:, 1] - direction[1] * edge[:, 0]
            valid = abs(determinant) > 1e-15
            t = np.divide(a[:, 0] * edge[:, 1] - a[:, 1] * edge[:, 0], determinant, out=np.zeros(len(a)), where=valid)
            u = np.divide(a[:, 0] * direction[1] - a[:, 1] * direction[0], determinant, out=np.zeros(len(a)), where=valid)
            distances.extend(t[valid & (t > 0) & (u >= 0) & (u < 1)])
        distances = sorted(distances)
        assert len(distances) >= 2
        point = origin + direction * ((distances[0] + distances[1]) / 2)
        assert sum(contains(c, point) for c in curves) % 2 == 1, 'Ring centreline must stay inside metal'
        ring_line.append([ring_plane, *point])
    ring_cuts = disc_crossings(np.asarray(ring_line), center, normal)
    radii = [float(np.linalg.norm(p - center)) for p in ring_cuts]
    interior = [p for p, r in zip(ring_cuts, radii) if r < radius - wire]
    assert len(interior) == 1, ('Ring centreline must cross the loop opening exactly once', radii)
    return dict(loop_through_ring_disc=True, ring_through_loop_disc=True,
                loop_ring_opening_crossing_m=cuts[through[0]].tolist(),
                ring_loop_opening_crossing_m=interior[0].tolist(),
                ring_disc_crossing_radii_m=radii, perpendicular_plane_normal_dot=float(normal[0]),
                loop_inner_opening_diameter_m=2 * (radius - wire), ring_centerline_samples=len(ring_line))
