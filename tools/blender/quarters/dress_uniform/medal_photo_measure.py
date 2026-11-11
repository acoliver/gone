"""Reference segmentation and exposure-relative medal measurements for issue #130."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, gaussian_filter, label, map_coordinates
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[4]
Y = np.array([.2126, .7152, .0722])
REFERENCES = {'remembered': {'medal': 'remembered-front-seed1304102.png',
                             'oblique-context': 'remembered-oblique-seed1304201.png'},
              'present': {'medal': 'present-front-seed1304101.png',
                          'oblique-context': 'present-oblique-seed1304201.png'}}
PALETTE = {'faces': (255, 170, 20), 'edges': (255, 255, 100), 'recesses': (160, 60, 10),
           'star': (250, 80, 160), 'enamel': (40, 160, 255), 'ribbon': (100, 255, 120),
           'wool': (180, 170, 255)}


def load(path):
    rgb = np.asarray(Image.open(path).convert('RGB'), float) / 255
    return rgb, np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def reference_masks(rgb):
    yy, xx = np.indices(rgb.shape[:2])
    # Warm/cool colour clusters are constrained to the pendant's lower image region.
    gold = (rgb[:, :, 0] > rgb[:, :, 1] * 1.13) & (rgb[:, :, 1] > rgb[:, :, 2] * 1.25) & (rgb[:, :, 0] > .16)
    search = (yy > 350) & (xx > 450) & (xx < 1100)
    points = []
    for row in range(350, rgb.shape[0]):
        cols = np.flatnonzero(gold[row] & search[row])
        if len(cols) > 30:
            points.extend([(np.percentile(cols, .2), row), (np.percentile(cols, 99.8), row)])
    points = np.array(points)
    def residual(p):
        cx, cy, rx, ry, shear = p
        dx = points[:, 0] - cx - shear * (points[:, 1] - cy)
        return np.sqrt((dx / rx) ** 2 + ((points[:, 1] - cy) / ry) ** 2) - 1
    fit = least_squares(residual, [780, 540, 245, 240, 0], loss='soft_l1', f_scale=.02,
                        bounds=([650, 450, 150, 170, -.4], [900, 650, 320, 310, .4])).x
    cx, cy, rx, ry, shear = fit
    radius = np.sqrt(((xx - cx - shear * (yy - cy)) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    disc = radius < .985
    blue = (rgb[:, :, 2] > rgb[:, :, 0] * 1.10) & (rgb[:, :, 2] > rgb[:, :, 1] * 1.02)
    brass = disc & ~blue
    lum = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4) @ Y
    # Grooves are narrow dark departures from the local annulus, not the unlit hemisphere.
    groove = (radius > .68) & (radius < .96) & (lum < gaussian_filter(lum, 4) * .82)
    edges = brass & ((radius > .93) | ((radius > .68) & (lum > gaussian_filter(lum, 4) * 1.16)))
    faces = brass & (radius > .71) & (radius < .93) & ~groove & ~edges
    star = brass & (radius < .66)
    recesses = brass & groove
    ribbon = (yy < cy - ry * 1.25) & (yy > 15) & (abs(xx - cx) < rx * .70)
    wool = (radius > 1.12) & (radius < 1.65) & (yy > cy - ry * .50) & ~gold
    result = dict(faces=faces, edges=edges, recesses=recesses, star=star,
                  enamel=disc & blue & (radius < .72), ribbon=ribbon, wool=wool,
                  brass=brass)
    return result, 2 * rx / 32, {'ellipse_cx_cy_rx_ry_shear': fit.tolist()}


def game_masks(game, state, view):
    data = np.load(game / f'{state}-{view}-raw-masks.npz')
    role, region = data['role'], data['region']
    fields = np.load(ROOT / 'tmp/issue130-photoreal/stage2/material-fields.npz')
    uv = data['uv']
    coords = np.array([uv[:, :, 1] * 2048 - .5, uv[:, :, 0] * 2048 - .5])
    cavity = map_coordinates(np.flipud(fields['tarnish']), coords, order=1, mode='nearest')
    convex = map_coordinates(np.flipud(fields['convex']), coords, order=1, mode='nearest')
    names = data['names'].tolist()
    radius = np.hypot(data['local'][:, :, 0], data['local'][:, :, 2])
    brass = (role == 1) & (radius <= .0161)
    annulus = brass & (region == names.index('rim'))
    result = dict(faces=annulus & (cavity < .01) & (convex < .12),
                  edges=brass & ((radius > .0149) | (convex > .08)), recesses=brass & (cavity > .65),
                  star=brass & np.isin(region, [names.index(n) for n in ['star_roof', 'star_center', 'star_bevel']]),
                  enamel=role == 2, ribbon=role == 3, wool=role == 4, brass=brass)
    yy, xx = np.indices(role.shape)
    selected = annulus & (cavity < .01)
    x, z = data['local'][:, :, 0][selected][::20] * 1000, data['local'][:, :, 2][selected][::20] * 1000
    sx, sy = xx[selected][::20], yy[selected][::20]
    one, zero = np.ones_like(x), np.zeros_like(x)
    a = np.r_[np.c_[x, z, one, zero, zero, zero, -sx * x, -sx * z],
              np.c_[zero, zero, zero, x, z, one, -sy * x, -sy * z]]
    projection = np.linalg.lstsq(a, np.r_[sx, sy], rcond=None)[0]
    return result, float(data['width']) / 32, {'source': str(game / f'{state}-{view}-raw-masks.npz'),
                                               'local_mm_to_screen_homography': projection.tolist()}


def chroma_hue(samples):
    # Fix Y before Lab conversion so exposure does not masquerade as chroma change.
    rgb = samples.mean(0)
    rgb = rgb * .18 / (rgb @ Y)
    xyz = np.array([[.4124564, .3575761, .1804375], [.2126729, .7151522, .0721750],
                    [.0193339, .1191920, .9503041]]) @ rgb / [.95047, 1., 1.08883]
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    a, b = 500 * (f[0] - f[1]), 200 * (f[1] - f[2])
    return float(np.hypot(a, b)), float(np.degrees(np.arctan2(b, a)) % 360)


def band_contrast(lum, mask, pixels_per_mm, low_mm, high_mm):
    a = gaussian_filter(lum, low_mm * pixels_per_mm / 2.355)
    b = gaussian_filter(lum, high_mm * pixels_per_mm / 2.355)
    selected = binary_erosion(mask, iterations=max(1, int(low_mm * pixels_per_mm / 2)))
    assert selected.any(), 'Empty physical-scale texture mask'
    return float(np.sqrt(np.mean(((a - b) / np.maximum(b, .005))[selected] ** 2)))


def tangential_mottling(lum, mask, geometry):
    from scipy.ndimage import gaussian_filter1d
    angle = np.arange(2048) * (2 * np.pi / 2048)
    radii = np.linspace(11.5, 15., 48)
    radius, theta = np.meshgrid(radii, angle, indexing='ij')
    x, z = radius * np.cos(theta), radius * np.sin(theta)
    if 'ellipse_cx_cy_rx_ry_shear' in geometry:
        cx, cy, rx, ry, shear = geometry['ellipse_cx_cy_rx_ry_shear']
        sy = cy + z / 16 * ry
        sx = cx + x / 16 * rx + shear * (sy - cy)
    else:
        a, b, c, d, e, f, g, h = geometry['local_mm_to_screen_homography']
        sx = (a * x + b * z + c) / (g * x + h * z + 1)
        sy = (d * x + e * z + f) / (g * x + h * z + 1)
    polar = map_coordinates(lum, [sy, sx], order=1, mode='nearest')
    selected = map_coordinates(mask.astype(float), [sy, sx], order=1, mode='constant') > .99
    variance = []
    for i, r in enumerate(radii):
        arc_pitch = 2 * np.pi * r / 2048
        # Tangential filtering excludes the accepted concentric lathe profile from mottling.
        low = gaussian_filter1d(polar[i], .5 / 2.355 / arc_pitch, mode='wrap')
        high = gaussian_filter1d(polar[i], 2. / 2.355 / arc_pitch, mode='wrap')
        valid = gaussian_filter1d(selected[i].astype(float), 1. / 2.355 / arc_pitch, mode='wrap') > .99
        if valid.any():
            variance.extend(((low - high) / np.maximum(high, .005))[valid] ** 2)
    assert variance, 'No broad-face tangential texture samples'
    return float(np.sqrt(np.mean(variance)))


def statistics(rgb, linear, regions, pixels_per_mm, geometry=None):
    lum = linear @ Y
    wool = float(np.median(lum[regions['wool']]))
    face = float(np.median(lum[regions['faces']]))
    assert wool > 0 and face > 0
    result = {'wool_y': wool, 'regions': {}}
    for name, mask in regions.items():
        assert mask.any(), ('Empty region', name)
        samples = lum[mask]
        chroma, hue = chroma_hue(linear[mask])
        result['regions'][name] = {'pixels': int(mask.sum()), 'y_over_wool_p10_p50_p90': (np.percentile(samples, [10, 50, 90]) / wool).tolist(),
                                   'chroma_at_y018': chroma, 'hue_degrees': hue,
                                   'near_highlight_fraction': float(np.mean(samples > face * 2.5)),
                                   'clipped_fraction': float(np.any(rgb[mask] >= .99, axis=1).mean())}
    result['face_raw_bandpass_rms_05_2mm'] = band_contrast(lum, regions['faces'], pixels_per_mm, .5, 2.)
    result['face_mottling_rms_05_2mm'] = (tangential_mottling(lum, regions['faces'], geometry) if geometry is not None
                                         else result['face_raw_bandpass_rms_05_2mm'])
    result['recess_over_face'] = float(np.median(lum[regions['recesses']]) / face)
    result['enamel_highlight_fraction'] = float(np.mean(lum[regions['enamel']] > max(face, np.median(lum[regions['enamel']]) * 3)))
    result['ribbon_fine_rms_01_04mm'] = band_contrast(lum, regions['ribbon'], pixels_per_mm, .1, .4)
    return result


def overlay(path, rgb, regions):
    result = rgb.copy()
    for name, colour in PALETTE.items():
        mask = regions[name]
        result[mask] = .50 * rgb[mask] + .50 * np.array(colour) / 255
        Image.fromarray(np.uint8(mask) * 255).save(path.with_name(path.stem + '-' + name + '.png'))
    Image.fromarray(np.uint8(np.clip(result, 0, 1) * 255 + .5)).save(path)


def flat_metrics(row):
    result = {k: row[k] for k in ['face_mottling_rms_05_2mm', 'recess_over_face', 'enamel_highlight_fraction', 'ribbon_fine_rms_01_04mm']}
    for region in ['faces', 'brass', 'enamel']:
        values = row['regions'][region]
        for i, percentile in enumerate([10, 50, 90]):
            result[f'{region}.y_over_wool_p{percentile}'] = values['y_over_wool_p10_p50_p90'][i]
        if region in ['faces', 'brass']:
            for key in ['chroma_at_y018', 'hue_degrees', 'near_highlight_fraction', 'clipped_fraction']:
                result[f'{region}.{key}'] = values[key]
    return result


def targets(references):
    result = {}
    for state, views in references.items():
        rows = [flat_metrics(row) for row in views.values()]
        result[state] = {}
        for key in rows[0]:
            values = [r[key] for r in rows]
            lo, hi = min(values), max(values)
            if key.endswith('clipped_fraction'):
                margin = .005
            elif key.endswith('highlight_fraction'):
                margin = .03
            elif key.endswith('hue_degrees'):
                margin = 8.
            elif key.endswith('chroma_at_y018'):
                margin = 8.
            else:
                margin = max(hi * .25, .01)
            lower = 0. if key.endswith('clipped_fraction') else max(0., lo - margin)
            result[state][key] = [lower, hi + margin]
    return result


def measure(reference_dir, game, output, target_file=None):
    output.mkdir(parents=True, exist_ok=True)
    report = {'method': 'Linear Rec.709 / median surrounding first-hit wool. Reference warm/cool clusters constrained by fitted pendant ellipse; geometry and UV-derived masks in game. Lab chroma and hue at fixed Y=.18. Highlight Y > 2.5x median face; clipping any sRGB channel >=.99. Texture RMS is Gaussian bandpass normalized by local mean, at physical FWHM scales.',
              'references': {}, 'game': {}}
    for state, views in REFERENCES.items():
        report['references'][state] = {}
        report['game'][state] = {}
        for view, filename in views.items():
            rgb, lin = load(reference_dir / filename)
            masks, scale, geometry = reference_masks(rgb)
            overlay(output / f'{state}-{view}-reference-overlay.png', rgb, masks)
            row = statistics(rgb, lin, masks, scale, geometry)
            row['segmentation'] = geometry
            report['references'][state][view] = row
            rgb, lin = load(game / f'{state}-{view}{"-full" if view == "oblique-context" else ""}.png')
            masks, scale, geometry = game_masks(game, state, view)
            overlay(output / f'{state}-{view}-game-overlay.png', rgb, masks)
            row = statistics(rgb, lin, masks, scale, geometry)
            row['segmentation'] = geometry
            report['game'][state][view] = row
    ranges = json.loads(target_file.read_text()) if target_file else targets(report['references'])
    report['targets'] = ranges
    report['comparison'] = {state: {view: {key: {'value': value, 'range': ranges[state][key],
                      'pass': ranges[state][key][0] <= value <= ranges[state][key][1]}
                      for key, value in flat_metrics(row).items()} for view, row in views.items()}
                      for state, views in report['game'].items()}
    (output / 'measurements.json').write_text(json.dumps(report, indent=2) + '\n')
    if not target_file:
        (output / 'targets.json').write_text(json.dumps(ranges, indent=2) + '\n')
    for state, views in report['comparison'].items():
        for view, metrics in views.items():
            print(state, view)
            for key, row in metrics.items():
                print('PASS' if row['pass'] else 'FAIL', key, round(row['value'], 5), [round(x, 5) for x in row['range']])
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--references', type=Path, required=True)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--targets', type=Path)
    a = p.parse_args()
    measure(a.references.resolve(), a.game.resolve(), a.output.resolve(), a.targets)
