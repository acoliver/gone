"""Additional image-source and geometry-resolved gates for the aged locker."""
import json

import numpy as np
from PIL import Image

from locker_swatches import paint_field, edge_variation, load_swatches, SOURCE, read_rgb, class_scores
from streak_sources import source_rows


def panel_edge_variations(colour, fields):
    occupied = fields['occupied']
    p, n = fields['position'][occupied], fields['normal'][occupied]
    painted = fields['ownership'][occupied] == 1
    rust = paint_field(colour[occupied][None])[0] < .5
    results = {}
    for axis in range(3):
        planar = painted & (abs(n[:, axis]) > .999)
        coordinates = np.round(p[:, axis], 3)
        for plane in np.unique(coordinates[planar]):
            face = planar & (coordinates == plane)
            if face.sum() < 4500:
                continue
            axes = [a for a in range(3) if a != axis]
            lo, hi = p[face][:, axes].min(0), p[face][:, axes].max(0)
            if min(hi - lo) < .12 or face.sum() / (304.55**2 * np.prod(hi - lo)) < .5:
                continue
            for across in range(2):
                along = 1 - across
                for side, coordinate in [('low', lo[across]), ('high', hi[across])]:
                    band = face & (abs(p[:, axes[across]] - coordinate) <= .025)
                    fractions = []
                    for start in np.arange(lo[along], hi[along] - .01, .025):
                        strip = band & (p[:, axes[along]] >= start) & (p[:, axes[along]] < start + .025)
                        if strip.sum() >= 5:
                            fractions.append(float(rust[strip].mean()))
                    if len(fractions) < 4:
                        raise ValueError(f'panel edge has insufficient samples: axis={axis}, plane={plane}, extents={hi-lo}, across={across}, side={side}, band={band.sum()}, bins={len(fractions)}')
                    key = f'axis{axis}_plane{plane:.3f}_along{axes[along]}_{side}'
                    results[key] = dict(coefficient_of_variation=edge_variation(fractions),
                                        rust_fractions=fractions, bin_length_m=.025, band_width_m=.025)
    if not results:
        raise ValueError('no broad panel edges measured')
    return results


def measure_swatches(directory, atlas, fields, masks, preview):
    from locker_gates import rgb, project
    values, gates, thresholds = {}, {}, {}
    def record(name, value, threshold, passed):
        values[name], thresholds[name], gates[name] = value, threshold, bool(passed)
    ids = rgb(directory / 'aged-ids-front.png')
    regions = rgb(directory / 'aged-regions-front.png')
    painted = (ids[..., 0] > .95) & (ids[..., 2] > .95)
    rust = paint_field(rgb(directory / 'aged-albedo-front.png')) < .5
    broad = painted & (regions[..., 1] > .95)
    edge = painted & (regions[..., 0] > .95)
    fraction = float(rust[broad].mean())
    ratio = float(rust[edge].mean()) / max(fraction, 1e-8)
    record('chroma_broad_face_rust', fraction, '[0.08,0.25] hatch paint_fields, unlit capture', .08 <= fraction <= .25)
    record('chroma_edge_broad_rust_ratio', ratio, '>=2.5 hatch paint_fields, unlit capture', ratio >= 2.5)
    rows = source_rows(masks['sources'], masks['seed'])
    widths, parameters = rows
    # Isolated coverage control measures the shader's tapered trail rather than
    # confusing surrounding panel corrosion with the width of the runoff.
    control = rgb(directory / 'aged-streakmask-front.png')[..., 0]
    from colour import linear
    control = linear(control)
    camera = preview['cameras']['front']
    ppm = camera['image_size'][1] / camera['size']
    from scipy.ndimage import label, find_objects
    from scipy.spatial.distance import pdist
    islands, _ = label(rust & broad & (control < .01), np.ones((3, 3)))
    diameters = []
    for index, bounds in enumerate(find_objects(islands), 1):
        points = np.argwhere(islands[bounds] == index)
        diameter = float(pdist(points).max()) if len(points) > 1 else 0.
        diameters.append((diameter + 1) / ppm)
    largest = max(diameters)
    record('broad_face_island_max_m', largest, '<=0.060 max Feret diameter; broad front receivers, analytic runoff excluded', largest <= .060)
    yy, xx = np.indices(control.shape)
    allowed = np.zeros_like(control, bool)
    for origin, shape in zip(widths, parameters):
        cx, top = project(origin[:3], camera)
        _, bottom = project(origin[:3] - [0, shape[0], 0], camera)
        radius = (origin[3] * .5 + shape[2] * 3.2) * ppm + 2
        allowed |= (abs(xx - cx) <= radius) & (yy >= top - 1) & (yy <= bottom + 1)
    flat_door = rgb(directory / 'aged-doorface-front.png')[..., 0] > .95
    unattached = float(control[flat_door & ~allowed].max())
    record('unattached_runoff_max', unattached, '<=0.01 linear coverage outside outlet envelopes on the flat door plane', unattached <= .01)
    measured = []
    for origin, shape in zip(widths, parameters):
        cx, cy = project(origin[:3] - np.array([0, shape[0] * .30, 0]), camera)
        x, y = int(round(cx)), int(round(cy))
        if not (0 <= y < 1024 and 8 <= x < 1016) or not painted[y, x]:
            continue
        row = control[y]
        peak = float(row[x-1:x+2].max())
        if peak < .02:
            continue
        if row[x] < peak * .5:
            continue
        left = right = x
        while left > 0 and row[left-1] >= peak * .5: left -= 1
        while right < len(row)-1 and row[right+1] >= peak * .5: right += 1
        measured.append(float(right-left+1) / ppm)
    if not measured:
        raise ValueError('no isolated runoff widths')
    median = float(np.median(measured))
    record('streak_width_median_m', median, '[0.004,0.012] half-opacity contour at 30% drop', .004 <= median <= .012)
    record('streak_source_length_range_m', [float(parameters[:, 0].min()), float(parameters[:, 0].max())],
           '[0.060,0.200]', parameters[:, 0].min() >= .060 and parameters[:, 0].max() <= .200)
    record('streak_reduced_opacity_max', float(parameters[:, 1].max()), '<1', parameters[:, 1].max() < 1)
    arrays = np.load(fields)
    colour = np.asarray(Image.open(atlas / 'aged_albedo.png').convert('RGB'), np.float32) / 255
    edges = panel_edge_variations(colour, arrays)
    minimum = min(row['coefficient_of_variation'] for row in edges.values())
    record('panel_edge_rust_cv_min', minimum, '>=0.35 on every 25 mm band, 25 mm bins', minimum >= .35)
    images, calibration = load_swatches()
    for name, image in images.items():
        scores = class_scores(image, read_rgb(SOURCE / calibration['regions'][name]['reference']))
        for metric, value in scores.items():
            record(f'swatch_{name}_{metric}', value, '<=8 D65 Lab', value <= 8)
        correlation = calibration['regions'][name]['scores']['secondary_autocorrelation']
        record(f'swatch_{name}_autocorrelation', correlation, '<=0.5 beyond 50 mm', correlation <= .5)
    return dict(values=values, gates=gates, thresholds=thresholds,
                panel_edges=edges, measured_streak_widths_m=measured)
