"""Measure visible shoulder-top dust in identical lit ON/OFF captures."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def measure(directory):
    on = np.asarray(Image.open(directory/'context/after-closeup.png').convert('RGB'), dtype=float)
    off = np.asarray(Image.open(directory/'dust-off/after-closeup.png').convert('RGB'), dtype=float)
    mask = np.asarray(Image.open(directory/'shoulder-mask.png').convert('RGB'))[:, :, 0] >= 230
    if on.shape != off.shape or on.shape[:2] != mask.shape or not mask.any():
        raise ValueError('Matched lit captures and a nonempty shoulder mask are required')
    difference = (on-off).mean(2)[mask]
    fraction = float(np.mean(difference >= 8))
    result = dict(method='Positive mean-RGB sRGB byte increase, dust ON minus OFF, on visible upward upper cloth',
                  mask='Geometry normal Z > 0.35 and world height > 1.31 m, body/collar/boards, alpha-aware, full coverage pixels',
                  shoulder_pixels=int(mask.sum()), mean_srgb_levels=float(difference.mean()),
                  median_srgb_levels=float(np.median(difference)), fraction_at_least_8=fraction,
                  required_srgb_levels=8, required_fraction='>0.5 (most shoulder tops)',
                  pass_gate=bool(fraction > .5), **{'pass': bool(fraction > .5)})
    (directory/'dust-lit-difference.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(0 if measure(a.out.resolve())['pass'] else 1)
