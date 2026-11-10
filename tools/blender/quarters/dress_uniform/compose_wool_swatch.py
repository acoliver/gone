"""Compare equal-size chest/target crops without exposure or colour corrections."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def compose(out, target):
    aged = Image.open(out/'aged-chest-neutral.png').convert('RGB')
    reference = Image.open(target).convert('RGB').crop((596, 496, 645, 545))
    if aged.size != reference.size:
        raise ValueError('Wool swatches must have identical pixel dimensions')
    report = dict(
        units='sRGB bytes, arithmetic mean of all 2401 pixels; no colour/exposure adjustment',
        aged_mean_rgb=np.array(aged, dtype=float).mean((0, 1)).tolist(),
        target_mean_rgb=np.array(reference, dtype=float).mean((0, 1)).tolist(),
        aged_median_rgb=np.median(np.array(aged), axis=(0, 1)).tolist(),
        target_median_rgb=np.median(np.array(reference), axis=(0, 1)).tolist(),
        target_crop_xyxy=[596, 496, 645, 545],
        target_source=str(target),
        target_lighting='Fixed generated reference with baked lighting; its original illumination/exposure cannot be recovered from a PNG.',
        comparison='Candidate uses neutral white lighting at exposure 0. Both crops remain unadjusted display RGB. Physical target scale is approximate; see neutral-light.json.',
        enlargement='Both 49-square crops enlarged identically 8x with nearest-neighbour sampling')
    reference.save(out/'target-wool-crop.png')
    canvas = Image.new('RGB', (49*16+48, 49*8+64), (90, 90, 90))
    canvas.paste(aged.resize((392, 392), Image.Resampling.NEAREST), (16, 48))
    canvas.paste(reference.resize((392, 392), Image.Resampling.NEAREST), (424, 48))
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 12), 'AGED CHEST / NEUTRAL WHITE / EXPOSURE 0', fill='white')
    draw.text((424, 12), 'FIXED TARGET / ORIGINAL DISPLAY RGB', fill='white')
    canvas.save(out.parent/'wool-neutral-swatch-sheet.png')
    (out/'measured-colours.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    a = p.parse_args()
    compose(a.out.resolve(), a.target.resolve())
