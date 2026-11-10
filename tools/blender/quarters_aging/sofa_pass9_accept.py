"""Unchanged sofa gates, with exported fringe and crumb visibility evidence."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_pass8_accept import measure as measure_pass8
from sofa_decay_policy import ORDER


def rgb(path):
    return np.array(Image.open(path).convert('RGB'))


def visibility(out):
    labels = rgb(out/'hero-visibility.png')
    before = rgb(out/'sofa-after.png').astype(int)
    result = {'close_fringe_pixels': {}}
    for name in [*ORDER, 'Throw']:
        image = rgb(out/'diagnostics'/name/'labels.png')
        result['close_fringe_pixels'][name] = int(((image[:, :, 1] > 250) &
            (image[:, :, 0] < 5) & (image[:, :, 2] < 5)).sum())
    for label, channel in [('fringe', 1), ('crumbs', 2)]:
        other = [i for i in range(3) if i != channel]
        pixels = (labels[:, :, channel] > 250) & (labels[:, :, other] < 5).all(2)
        if label == 'crumbs':
            pixels = (labels[:, :, 2] > 250) & (labels[:, :, 0] < 5)
        delta = np.abs(before-rgb(out/('hero-without-'+label+'.png')).astype(int)).max(2)
        result[label] = {'hero_first_hit_pixels': int(pixels.sum()),
                         'lit_pixels_changed_by_at_least_8_levels': int((delta >= 8).sum()),
                         'lit_first_hit_pixels_changed_by_at_least_8_levels': int((pixels & (delta >= 8)).sum()),
                         'pass': bool((pixels & (delta >= 8)).any())}
        if label == 'crumbs':
            front = pixels & (labels[:, :, 1] > 250)
            result[label].update(region='sofa crumbs at height >=0.25 m; cyan is seat front y<-0.24 m',
                                 seat_front_first_hit_pixels=int(front.sum()),
                                 lit_seat_front_pixels_changed_by_at_least_8_levels=int((front & (delta >= 8)).sum()))
    return result


def measure(args):
    result = measure_pass8(args)
    result['visibility'] = visibility(args.renders)
    result['invariants']['fringe_visible_in_lit_hero'] = result['visibility']['fringe']['pass']
    result['invariants']['crumbs_visible_in_lit_hero'] = result['visibility']['crumbs']['pass']
    result['invariants']['crumbs_visible_at_seat_front'] = result['visibility']['crumbs']['lit_seat_front_pixels_changed_by_at_least_8_levels'] > 0
    result['pass'] = all(g['pass'] for g in result['gates'].values()) and all(result['invariants'].values())
    result['publication_allowed'] = result['pass']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['input', 'out', 'renders', 'collisions', 'baseline']:
        parser.add_argument('--'+flag, type=Path, required=True)
    args = parser.parse_args()
    result = measure(args)
    (args.out/'gates.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
