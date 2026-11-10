"""Measure visible alpha/lip outlines, including gashes connected to the exterior."""
import numpy as np
from scipy.ndimage import binary_dilation, binary_fill_holes, label
from scipy.spatial import cKDTree
from skimage.measure import approximate_polygon, find_contours
from skimage.morphology import medial_axis

from seat_image_gates import contour_dimension


def cloth_coverage(rgb):
    pixels = np.asarray(rgb, dtype=float)
    return (pixels[:, :, :2].sum(2) >= 127.5) & (pixels[:, :, 2] < 127.5)


def fringe_visibility(labels, before, without):
    pixels = np.asarray(labels, dtype=float)
    coverage = np.maximum(pixels[:, :, 1]-pixels[:, :, 2], 0.)/255.
    changed = np.abs(np.asarray(before, dtype=int)-np.asarray(without, dtype=int)).max(2) >= 8
    visible = float(coverage[changed].sum())
    return dict(hero_first_hit_coverage_px=float(coverage.sum()), lit_first_hit_coverage_px=visible,
                method='antialiased green coverage minus cyan crumb coverage; unchanged >=8-level lit disabled-effect difference',
                **{'pass': visible > 0.})


def visible_gashes(cloth, segments, radius=12., occluded=None):
    if not len(segments):
        return []
    samples = np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b-a)*2)+1))
                              for a, b in np.asarray(segments)])
    tree = cKDTree(samples)
    holes, _ = label(binary_fill_holes(cloth) & ~cloth)
    hidden = binary_dilation(occluded) if occluded is not None else None
    result = []
    for contour in find_contours(cloth, .5):
        selected = tree.query(contour)[0] <= radius
        if hidden is not None:
            pixel = np.rint(contour).astype(int)
            selected &= ~hidden[pixel[:, 0], pixel[:, 1]]
        closed = bool(selected.all() and np.linalg.norm(contour[0]-contour[-1]) < 1.)
        if selected.all():
            runs = [contour]
        else:
            start = int(np.flatnonzero(~selected)[0])
            contour, selected = np.roll(contour, -start, 0), np.roll(selected, -start)
            ends = np.flatnonzero(np.diff(np.r_[False, selected, False]))
            runs = [contour[a:b] for a, b in zip(ends[::2], ends[1::2])]
        for run in runs:
            length = float(np.linalg.norm(np.diff(run, axis=0), axis=1).sum())
            if len(run) < 3 or length < 12:
                continue
            simplified = approximate_polygon(run, tolerance=1.)
            longest = float(np.linalg.norm(np.diff(simplified, axis=0), axis=1).max())
            width = None
            if closed:
                xy = np.rint(run).astype(int)
                candidates = holes[xy[:, 0], xy[:, 1]]
                ids, counts = np.unique(candidates[candidates > 0], return_counts=True)
                if len(ids):
                    mask = holes == ids[counts.argmax()]
                    if mask.sum() < 128:
                        continue
                    skeleton, distances = medial_axis(mask, return_distance=True, rng=95)
                    widths = 2*distances[skeleton]
                    width = float(widths.std()/widths.mean())
            result.append(dict(length_px=length, longest_straight_run_px=longest,
                               maximum_extent_px=float(np.ptp(run, axis=0).max()),
                               contour_dimension=contour_dimension(run), width_cv=width,
                               closed=closed, bounds_px=[run.min(0).tolist(), run.max(0).tolist()],
                               points=run))
    # Open lips have no enclosed medial-axis mask. Measure their visible
    # opposing runs at uniform arclength; never add a synthetic closing edge.
    open_runs = [r for r in result if not r['closed']]
    for own in open_runs:
        p = own['points']
        others = [r['points'] for r in open_runs if r is not own]
        if not others:
            continue
        station = np.r_[0., np.linalg.norm(np.diff(p, axis=0), axis=1).cumsum()]
        sample = np.arange(0., station[-1], 1.)
        uniform = np.column_stack([np.interp(sample, station, p[:, axis]) for axis in [0, 1]])
        widths = cKDTree(np.concatenate(others)).query(uniform)[0]
        if widths.mean() > 0:
            own['width_cv'] = float(widths.std()/widths.mean())
    for item in result:
        del item['points']
    return result
