"""Supplement #130 visibility gates with broad-face colour and oblique context measurements."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from medal_game_measure import compare, linear_image, luminance, masks

ROOT = Path(__file__).resolve().parents[4]
Y = np.array([.2126, .7152, .0722])


def colour_statistics(rgb, selected):
    samples = rgb[selected]
    luminance = samples @ Y
    mean = samples.mean(0)
    return {'pixels': int(selected.sum()), 'mean_linear_rgb': mean.tolist(),
            'mean_y': float(luminance.mean()), 'y_p10_p50_p95': np.percentile(luminance, [10, 50, 95]).tolist(),
            'mean_rgb_over_y': (mean / (mean @ Y)).tolist(),
            'r_over_g': float(mean[0] / mean[1]), 'g_over_b': float(mean[1] / mean[2])}


def measure(game):
    fields = np.load(ROOT / 'tmp/issue130-photoreal/stage2/material-fields.npz')
    concept = linear_image(ROOT / 'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png')[348:871, 266:779]
    srgb = np.asarray(Image.open(ROOT / 'docs/art/quarters/sheets/medal/c-machined-rim-seed130303.png').convert('RGB'), float)[348:871, 266:779] / 255
    lum = concept @ Y
    brass = (srgb[:, :, 0] > srgb[:, :, 2] * 1.5) & (srgb[:, :, 0] > srgb[:, :, 1] * 1.08) & (srgb[:, :, 1] > .12) & (lum > .035) & (lum < .70)
    report = {'method': 'LDR decoded to linear Rec.709. Broad faces are first-hit rim samples excluding cavity and convex-edge masks. Concept brass uses the retained stage-two colour-source selection; it is a different illumination reference, not a reflectance measurement.',
              'concept_brass': colour_statistics(concept, brass), 'states': {}}
    for state in ['remembered', 'present']:
        m = masks(game, state, 'medal')
        data = np.load(game / f'{state}-medal-raw-masks.npz')
        uv = data['uv']
        coords = np.array([uv[:, :, 1] * 2048 - .5, uv[:, :, 0] * 2048 - .5])
        cavity = map_coordinates(np.flipud(fields['tarnish']), coords, order=1, mode='nearest')
        convex = map_coordinates(np.flipud(fields['convex']), coords, order=1, mode='nearest')
        broad = m['rim'] & (cavity < .01) & (convex < .12)
        exposed = m['brass'] & (cavity < .01) & (convex < .12)
        full = linear_image(game / f'{state}-medal.png')
        off = linear_image(game / f'{state}-medal-local-probe-off.png')
        before = linear_image(game.parent / 'baseline/game' / f'{state}-medal.png')
        row = {'broad_faces': colour_statistics(full, broad), 'baseline_broad_faces': colour_statistics(before, broad),
               'probe_off_broad_faces': colour_statistics(off, broad),
               'broad_probe_nmae': compare(full @ Y, off @ Y, broad),
               'exposed_brass': colour_statistics(full, exposed),
               'exposed_age_off_nmae': compare(full @ Y, luminance(game / f'{state}-medal-age-off.png'), exposed),
               'probe_rgb_delta': (full - off)[broad].mean(0).tolist()}
        row['broad_y_over_concept'] = row['broad_faces']['mean_y'] / report['concept_brass']['mean_y']
        row['broad_chroma_minus_concept'] = (np.array(row['broad_faces']['mean_rgb_over_y']) - report['concept_brass']['mean_rgb_over_y']).tolist()
        ldr = np.asarray(Image.open(game / f'{state}-medal.png').convert('RGB'), float) / 255
        row['broad_clipped_fraction'] = float(np.any(ldr[broad] >= .99, axis=1).mean())
        row['broad_all_channels_clipped_fraction'] = float(np.all(ldr[broad] >= .99, axis=1).mean())
        row['broad_clipped_fraction_by_channel'] = np.mean(ldr[broad] >= .99, axis=0).tolist()
        context = masks(game, state, 'oblique-context')
        a = luminance(game / f'{state}-oblique-context-full.png')
        contact_off = luminance(game / f'{state}-oblique-context-contact-off.png')
        weave_off = luminance(game / f'{state}-oblique-context-weave-off.png')
        row['additional_oblique_context'] = {'visible_pixels': {key: int(context[key].sum()) for key in ['brass', 'enamel', 'ribbon', 'cloth', 'contact']},
            'weave_nmae': compare(a, weave_off, context['ribbon']),
            'contact_median_reduction': float(np.median(((contact_off-a)/np.maximum(contact_off,.02))[context['contact']]))}
        report['states'][state] = row
    (game.parent / 'brass-gates.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True)
    measure(p.parse_args().game.resolve())
