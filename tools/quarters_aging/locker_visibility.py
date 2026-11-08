"""Additional locker checks, retaining the first pass's capture gates unchanged."""
import json
import numpy as np
from scipy.ndimage import binary_erosion

from colour import linear, lab, luminance, delta_e_2000
from visibility_gates import dust_visibility, trail_metrics, boundary_orientation, longest_straight_boundary, secondary_correlation


def measure_visibility(directory, masks, preview, finish_file):
    from locker_gates import rgb, rust_pixels, hsv, project
    values, gates, thresholds = {}, {}, {}

    def record(name, value, threshold, passed):
        values[name], thresholds[name], gates[name] = value, threshold, bool(passed)

    ids = rgb(directory / 'aged-ids-top.png')
    up = binary_erosion((ids[..., 1] > .95) & (ids[..., 2] > .95), iterations=1)
    for lane in ('albedo', 'neutral', 'present'):
        dust = rgb(directory / f'aged-{lane}-top.png')
        disabled = rgb(directory / f'aged-nodust-{lane}-top.png')
        difference = dust_visibility(dust, disabled, up)
        record(f'dust_linear_difference_{lane}', difference, '>=0.06', difference >= .06)
        hue, saturation, _ = hsv(dust)
        warm = float(((hue[up] >= 20) & (hue[up] <= 55) & (saturation[up] >= .06) & (saturation[up] <= .25)).mean())
        record(f'dust_warm_low_saturation_{lane}', warm, '>=0.70 of up faces', warm >= .70)

    ids = rgb(directory / 'aged-ids-front.png')
    painted = (ids[..., 0] > .95) & (ids[..., 2] > .95)
    regions = rgb(directory / 'aged-regions-front.png')
    edge = painted & (regions[..., 0] > .95)
    broad = painted & (regions[..., 1] > .95)
    camera = preview['cameras']['front']
    ppm = camera['image_size'][1] / camera['size']
    fasteners = []
    runoff_control = linear(rgb(directory / 'aged-streakmask-front.png'))[..., 0]
    sources = [source for source in masks['sources'] if source['part'] in ('Rivets', 'Hinges')]
    for lane in ('albedo', 'neutral', 'present'):
        image = rgb(directory / f'aged-{lane}-front.png')
        rust = rust_pixels(image)
        edge_fraction, broad_fraction = float(rust[edge].mean()), float(rust[broad].mean())
        ratio = edge_fraction / max(broad_fraction, 1e-8)
        record(f'edge_broad_ratio_{lane}', ratio, '>=2.5', ratio >= 2.5)
        record(f'broad_face_rust_{lane}', broad_fraction, '[0.08,0.25]', .08 <= broad_fraction <= .25)
        lane_results = []
        for source in sources:
            from streak_sources import outlet_position
            x, y, z = outlet_position(source)
            cx, top = project([x, z, -y], camera)
            result = trail_metrics(image, painted, cx, top, ppm, runoff_control)
            result['source'] = source
            # Rivets belong to the carcass, not the door leaf. Include
            # its upper half plus all three door hinges, including the low one.
            result['eligible'] = bool(source['part'] == 'Hinges' or z >= 1.2)
            lane_results.append(result)
        eligible = [row for row in lane_results if row['eligible']]
        if not eligible: raise ValueError('no door/upper-side fasteners')
        fraction = sum(row['passed'] for row in eligible) / len(eligible)
        record(f'visible_fastener_streaks_{lane}', fraction, '>=0.50 of door/upper-side fasteners; contiguous rust run>=40mm, onset<=10mm, both-flank linear contrast>=0.03, width<=15mm', fraction >= .5)
        fasteners.append(dict(lane=lane, eligible=len(eligible), excluded=len(sources)-len(eligible), measurements=lane_results))

    from locker_swatches import paint_field
    closeup = rgb(directory / 'streaks-closeup.png')[:, 1024:]
    close_ids = rgb(directory / 'aged-ids-streaks.png')
    close_valid = (close_ids[..., 0] > .95) & (close_ids[..., 2] > .95)
    # Analytic vertical runoff is not atlas-sampled and naturally has a 0-degree
    # gradient peak. Its isolated control keeps it out of the texel-step test.
    runoff = linear(rgb(directory / 'aged-streakmask-streaks.png'))[..., 0]
    from scipy.ndimage import maximum_filter
    close_valid &= maximum_filter(runoff, size=9) < .01
    ratio, histogram, samples = boundary_orientation(1 - paint_field(closeup), close_valid)
    record('closeup_atlas_axis_peak_ratio', ratio, '<=2.0 at 0 and 90 degrees relative to median, 10-degree bins', ratio <= 2.)
    values['closeup_boundary_orientation_histogram'] = histogram
    values['closeup_boundary_samples'] = samples

    # Door interior only: no silhouette, surround, recess or hardware boundaries.
    a = project([-.245, 2.29, .274], camera)
    b = project([.245, .14, .274], camera)
    left, top = np.ceil(a).astype(int)
    right, bottom = np.floor(b).astype(int)
    image = rgb(directory / 'aged-albedo-front.png')[top:bottom, left:right]
    valid = rgb(directory / 'aged-doorface-front.png')[top:bottom, left:right, 0] > .95
    straight = longest_straight_boundary(rust_pixels(image), valid, ppm)
    record('longest_straight_rust_boundary_m', straight, '<=0.040 within 0.001m', straight <= .040)
    peak = secondary_correlation(image, ppm, valid)
    record('door_secondary_autocorrelation', peak, '<=0.5 at offsets>0.050m', peak <= .5)

    bare_count = rust_count = 0
    clean_bare, roughness = [], []
    for angle in ('front', 'detail', 'hero', 'streaks'):
        region = rgb(directory / f'aged-regions-{angle}.png')
        bare = binary_erosion(region[..., 2] > .95, iterations=1)
        if not bare.any(): continue
        aged = rgb(directory / f'aged-albedo-{angle}.png')
        clean = rgb(directory / f'as_built-albedo-{angle}.png')
        orm = linear(rgb(directory / f'as_built-orm-{angle}.png'))
        bare_count += int(bare.sum())
        rust_count += int((rust_pixels(aged) & bare).sum())
        clean_bare.extend(luminance(clean)[bare].tolist())
        roughness.extend(orm[..., 0][bare].tolist())
    hardware_rust = rust_count / bare_count
    record('aged_bare_steel_rust', hardware_rust, '>=0.30', hardware_rust >= .30)
    steel_luma = float(np.mean(clean_bare))
    record('as_built_bare_steel_linear_luminance', steel_luma, '>=0.35', steel_luma >= .35)
    rough_max = float(np.max(roughness))
    record('as_built_bare_steel_roughness_max', rough_max, '<=0.45', rough_max <= .45)
    finish = json.loads(finish_file.read_text())
    clean = rgb(directory / 'as_built-albedo-front.png')
    median = np.median(clean[broad], axis=0)
    difference = float(delta_e_2000(lab(median), lab(np.array(finish['as_built_paint_srgb']))))
    record('as_built_design_delta_e_2000', difference, '<=6', difference <= 6)
    lo, hi = masks['density_range_px_m']
    record('streak_texel_density_range_px_m', [lo, hi], '304.6 +/-15%', lo >= 304.6*.85 and hi <= 304.6*1.15)
    return dict(values=values, gates=gates, thresholds=thresholds, visibility_fasteners=fasteners)
