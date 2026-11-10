"""Measure weather visibility on native, lit production-scene capture pairs."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = ROOT / 'assets/props/ceiling/fixture-weather-gates.json'


def image(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=float) / 255


def masked_mean(values, mask):
    if not np.any(mask):
        raise ValueError('capture has no visible samples for the requested surface')
    return float(values[mask].mean())


def tiling_peak(effect, broad):
    """Correlate texture residual after removing smooth lighting and dust gradients."""
    weight = gaussian_filter(broad.astype(float), 10)
    smooth = gaussian_filter(effect * broad, 10) / np.maximum(weight, 1e-9)
    effect = effect - smooth
    peak = 0.0
    for dx in (24, 48, 72, 96):
        for dy in (-48, -24, 0, 24, 48):
            a = effect[48:-48, 96:-96]
            b = effect[48 + dy:effect.shape[0] - 48 + dy, 96 + dx:effect.shape[1] - 96 + dx]
            mask = broad[48:-48, 96:-96] & broad[48 + dy:effect.shape[0] - 48 + dy, 96 + dx:effect.shape[1] - 96 + dx]
            if np.count_nonzero(mask) < 80:
                continue
            left, right = a[mask], b[mask]
            left, right = left - left.mean(), right - right.mean()
            denominator = np.linalg.norm(left) * np.linalg.norm(right)
            if denominator > 1e-8:
                peak = max(peak, float(left @ right / denominator))
    return peak


def measure(directory):
    directory = Path(directory)
    result = {}
    for view in ('2p5m', 'close', 'ledge', 'corridor'):
        lit = image(directory / f'weathered-{view}.png')
        control = image(directory / f'control-{view}.png')
        zones = image(directory / f'zones-{view}.png')
        edge, broad = zones[:, :, 0] > .65, zones[:, :, 1] > .65
        metal = edge | broad
        effect = np.abs(lit - control).mean(axis=2)
        rust_effect = np.abs(lit - image(directory / f'no_rust-{view}.png')).mean(axis=2)
        dust_effect = np.abs(lit - image(directory / f'no_dust-{view}.png')).mean(axis=2)
        streak_effect = np.abs(lit - image(directory / f'no_streak-{view}.png')).mean(axis=2)
        dust = image(directory / f'dustmask-{view}.png')[:, :, 0] > .65
        top = image(directory / f'topmask-{view}.png')[:, :, 0] > .65
        shell = image(directory / f'shellmask-{view}.png')[:, :, 0] > .65
        edge_rust = masked_mean(rust_effect, edge)
        broad_rust = masked_mean(rust_effect, broad)
        result[view] = {
            'weather_rgb_difference': masked_mean(effect, metal),
            'broad_shell_rgb_difference': masked_mean(effect, shell),
            'broad_shell_display_luma': masked_mean(lit @ [.2126, .7152, .0722], shell),
            'broad_shell_black_fraction': float(((lit @ [.2126, .7152, .0722])[shell] < .025).mean()),
            'broad_shell_visible_weather_fraction': float((effect[shell] > .04).mean()),
            'visible_weather_fraction': float((effect[metal] > .025).mean()),
            'edge_rust_difference': edge_rust,
            'broad_rust_difference': broad_rust,
            'edge_to_broad_rust_ratio': edge_rust / max(broad_rust, 1e-9),
            'dust_rgb_difference': masked_mean(dust_effect, dust) if np.any(dust) else 0.0,
            'top_dust_rgb_difference': masked_mean(dust_effect, top) if np.any(top) else 0.0,
            'visible_upward_pixels': int(top.sum()),
            'streak_rgb_difference': masked_mean(streak_effect, zones[:, :, 2] > .65) if np.any(zones[:, :, 2] > .65) else 0.0,
            'metal_pixels': int(metal.sum()), 'dust_pixels': int(dust.sum()),
            'broad_face_translation_peak': tiling_peak((lit - control).mean(axis=2), broad),
        }
    return result


def evaluate(result, thresholds):
    checks = {}
    for name, limits in thresholds['views'].items():
        for metric, bounds in limits.items():
            if metric == 'rust_localisation':
                # The ratio's broad-face denominator is below display quantisation.
                checks[f'{name}.{metric}'] = (
                    result[name]['edge_rust_difference'] >= bounds['edge_rust_min']
                    and result[name]['broad_rust_difference'] <= bounds['broad_rust_max']
                )
            else:
                value = result[name][metric]
                checks[f'{name}.{metric}'] = bounds['min'] <= value <= bounds['max']
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path)
    parser.add_argument('--measure-only', action='store_true')
    args = parser.parse_args()
    result = measure(args.captures)
    report = {'measurements': result}
    if not args.measure_only:
        report['checks'] = evaluate(result, json.loads(THRESHOLDS.read_text()))
    print(json.dumps(report, indent=2))
    return 0 if args.measure_only or all(report['checks'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
