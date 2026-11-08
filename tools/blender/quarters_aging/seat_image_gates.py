"""Alpha-aware close-camera opening and normal-pass measurements."""
import numpy as np
from scipy.ndimage import binary_erosion, binary_fill_holes, label
from skimage.measure import approximate_polygon, find_contours
from skimage.morphology import medial_axis


def visible_dihedrals(vertices, faces, identifiers, images):
    import trimesh
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.merge_vertices(digits_vertex=7)
    adjacent = mesh.face_adjacency
    selected = np.zeros(len(adjacent), dtype=bool)
    views = []
    for image in images:
        image = np.asarray(image, dtype=np.uint32)
        encoded = image[:, :, 0]+(image[:, :, 1] << 8)+(image[:, :, 2] << 16)
        middle = encoded[1:-1, 1:-1]
        stable = ((middle == encoded[:-2, 1:-1]) & (middle == encoded[2:, 1:-1]) &
                  (middle == encoded[1:-1, :-2]) & (middle == encoded[1:-1, 2:]))
        visible = np.isin(identifiers, np.unique(middle[stable]))
        pairs = visible[adjacent[:, 0]] & visible[adjacent[:, 1]]
        selected |= pairs
        views.append({'visible_faces': int(visible.sum()), 'visible_pairs': int(pairs.sum())})
    count = int(selected.sum())
    if not count:
        raise ValueError('No reliable adjacent face IDs visible in the acceptance cameras')
    sharp = int(np.sum(mesh.face_adjacency_angles[selected] > np.radians(30)))
    return {'fraction': sharp/count, 'sharp_pairs': sharp, 'visible_pairs': count, 'views': views,
            'all_sheet_fraction': float(np.mean(mesh.face_adjacency_angles > np.radians(30))),
            'threshold': .08, 'pass': sharp/count <= .08}


def normal_jumps(encoded, cloth):
    normal = np.asarray(encoded, dtype=float)/255.*2-1
    normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-12)
    interior = binary_erosion(cloth, iterations=3)
    measured = np.zeros(cloth.shape, dtype=bool)
    sharp = np.zeros(cloth.shape, dtype=bool)
    for axis in [0, 1]:
        other = np.roll(normal, -1, axis=axis)
        valid = interior & np.roll(interior, -1, axis=axis)
        measured |= valid
        sharp |= valid & (np.sum(normal*other, axis=2) < np.cos(np.radians(10)))
    count = int(measured.sum())
    if not count:
        raise ValueError('No visible cloth interior in the normal pass')
    return {'fraction': float(sharp.sum()/count), 'interior_pixels': count,
            'threshold': .02, 'pass': bool(sharp.sum()/count <= .02)}


def contour_dimension(contour):
    points = np.asarray(contour)-np.min(contour, axis=0)
    scales = np.array([1, 2, 4, 8, 16, 32])
    counts = np.array([len(np.unique(np.floor(points/scale).astype(int), axis=0)) for scale in scales])
    return float(np.polyfit(np.log(1/scales), np.log(counts), 1)[0])


def opening_metrics(cloth, minimum_area=100):
    holes = binary_fill_holes(cloth) & ~cloth
    labels, count = label(holes)
    openings = []
    for index in range(1, count+1):
        mask = labels == index
        if mask.sum() < minimum_area:
            continue
        contours = find_contours(mask, .5)
        contour = max(contours, key=len)
        polygon = approximate_polygon(np.vstack([contour, contour[0]]), tolerance=1.)
        longest = float(np.linalg.norm(np.diff(polygon, axis=0), axis=1).max())
        skeleton, distances = medial_axis(mask, return_distance=True, rng=95)
        widths = distances[skeleton]*2
        cv = float(widths.std()/widths.mean())
        dimension = contour_dimension(contour)
        openings.append({'pixels': int(mask.sum()), 'longest_straight_run_px': longest,
                         'maximum_extent_px': float(np.ptp(contour, axis=0).max()),
                         'width_cv': cv, 'contour_dimension': dimension,
                         'bounds_px': [np.argwhere(mask).min(0).tolist(), np.argwhere(mask).max(0).tolist()]})
    return openings


def evaluate(labels, normal):
    # IDs are emitted after material alpha tests, including fringe strands.
    cloth = (labels == 1) | (labels == 2)
    openings = opening_metrics(cloth)
    resolved = [o for o in openings if o['maximum_extent_px'] >= 64]
    return {'G2': normal_jumps(normal, labels == 1),
            'G3': {'value': [o['longest_straight_run_px'] for o in openings], 'threshold': '<=12 px',
                   'pass': bool(openings) and all(o['longest_straight_run_px'] <= 12 for o in openings)},
            'G4': {'value': [o['width_cv'] for o in openings], 'threshold': '>=0.35 each',
                   'pass': bool(openings) and all(o['width_cv'] >= .35 for o in openings)},
            'G6': {'value': [o['contour_dimension'] for o in resolved], 'threshold': '1.15..1.40 each resolved contour',
                   'minimum_extent_px': 64, 'all_contour_values': [o['contour_dimension'] for o in openings],
                   'unresolved_contours': len(openings)-len(resolved),
                   'pass': bool(resolved) and all(1.15 <= o['contour_dimension'] <= 1.40 for o in resolved)},
            'openings': openings}
