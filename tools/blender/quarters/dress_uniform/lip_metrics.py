"""Measure alpha-tested tear lips as open polylines, including exterior gaps."""
import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import approximate_polygon, find_contours


def segment_samples(segments, step=.5):
    return np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b-a)/step)+1))
                           for a, b in np.asarray(segments)])


def contour_runs(cloth, segments, radius):
    if not len(segments):
        return []
    reference = cKDTree(segment_samples(segments))
    runs = []
    for contour in find_contours(cloth, .5):
        selected = reference.query(contour)[0] <= radius
        if selected.all():
            candidates = [contour]
        else:
            # Roll a closed silhouette to a point outside the selected lip.
            start = int(np.flatnonzero(~selected)[0])
            contour = np.roll(contour, -start, axis=0)
            selected = np.roll(selected, -start)
            ends = np.flatnonzero(np.diff(np.r_[False, selected, False]))
            candidates = [contour[a:b] for a, b in zip(ends[::2], ends[1::2])]
        for run in candidates:
            if len(run) >= 2 and np.linalg.norm(np.diff(run, axis=0), axis=1).sum() >= 12:
                runs.append(run)
    return runs


def polyline_metrics(points):
    points = np.asarray(points)
    simplified = approximate_polygon(points, tolerance=1.)
    length = float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())
    # No artificial endpoint closure: the exterior connection is not a lip.
    longest = float(np.linalg.norm(np.diff(simplified, axis=0), axis=1).max())
    scales = np.array([1, 2, 4, 8, 16, 32])
    local = points-points.min(0)
    counts = [len(np.unique(np.floor(local/scale).astype(int), axis=0)) for scale in scales]
    dimension = float(np.polyfit(np.log(1/scales), np.log(counts), 1)[0])
    return dict(length_px=length, longest_straight_run_px=longest, contour_dimension=dimension,
                bounds_px=[points.min(0).tolist(), points.max(0).tolist()])


def gap_width_cv(a, b):
    a = [np.asarray(a)] if isinstance(a, np.ndarray) else a
    b = [np.asarray(b)] if isinstance(b, np.ndarray) else b
    # Uniform arclength sampling prevents dense zigzags from weighting the gap.
    # Disconnected visible runs never acquire an invented connecting segment.
    widths = []
    for own_runs, opposite in [(a, b), (b, a)]:
        tree = cKDTree(np.concatenate(opposite))
        for own in own_runs:
            station = np.r_[0., np.cumsum(np.linalg.norm(np.diff(own, axis=0), axis=1))]
            keep = np.r_[True, np.diff(station) > 1e-8]
            sample = np.arange(0, station[-1], 1.)
            points = np.column_stack([np.interp(sample, station[keep], own[keep, axis]) for axis in [0, 1]])
            widths.extend(tree.query(points)[0].tolist())
    widths = np.asarray(widths)
    if not len(widths) or widths.mean() <= 0:
        raise ValueError('Tear gap has no measurable width')
    return float(widths.std()/widths.mean())


def evaluate_lips(views):
    measurements = []
    for camera, cloth, seeds in views:
        for tear, sides in seeds.items():
            runs = {side: contour_runs(cloth, data['segments_yx'], data['radius_px'])
                    for side, data in sides.items()}
            visible = {side: values for side, values in runs.items() if values}
            if not visible:
                continue
            lip_values = [dict(side=side, **polyline_metrics(run))
                          for side, values in visible.items() for run in values]
            width = None
            if len(visible) == 2:
                a, b = list(visible.values())
                width = gap_width_cv(a, b)
            measurements.append(dict(camera=camera, tear=tear, lips=lip_values, width_cv=width))
    lips = [lip for item in measurements for lip in item['lips']]
    resolved = [lip for lip in lips if lip['length_px'] >= 64]
    widths = [item['width_cv'] for item in measurements]
    return dict(G3=dict(value=[lip['longest_straight_run_px'] for lip in lips],
                        pass_gate=bool(lips) and all(lip['longest_straight_run_px'] <= 12 for lip in lips)),
                G4=dict(value=widths, pass_gate=bool(widths) and all(w is not None and w >= .35 for w in widths)),
                G6=dict(value=[lip['contour_dimension'] for lip in resolved],
                        pass_gate=bool(resolved) and all(1.15 <= lip['contour_dimension'] <= 1.40 for lip in resolved)),
                openings=measurements)
