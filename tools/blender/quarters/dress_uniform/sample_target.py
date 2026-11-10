"""Measure small labelled fabric/dust/metal regions, excluding the target wall."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


REGIONS = {
    'dark_fold': (430, 720),
    'dusty_grey_blue': (620, 520),
    'faded_crest': (380, 245),
    'shoulder_dust': (640, 230),
    'fibre_dust': (520, 940),
    'brass_brown': (492, 355),
}


def sample(path, out):
    rgb = np.array(Image.open(path).convert('RGB'))
    if rgb.shape[:2] != (1024, 1024):
        raise ValueError('Labelled sample regions belong to the fixed 1024x1024 aged target')
    result = dict(source=str(path),
                  method='5x5 regional median at image-comparer-labelled garment/heap/metal locations; wall excluded',
                  colours={})
    for name, (x, y) in REGIONS.items():
        patch = rgb[y-2:y+3, x-2:x+3]
        pixel = np.median(patch, axis=(0, 1)).astype(int)
        srgb = pixel/255.
        linear = np.where(srgb <= .04045, srgb/12.92, ((srgb+.055)/1.055)**2.4)
        result['colours'][name] = dict(srgb_bytes=pixel.tolist(), linear=linear.tolist(), xy=[x, y],
                                      population=25, patch_min=patch.min((0, 1)).tolist(),
                                      patch_max=patch.max((0, 1)).tolist())
    out.write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(sample(a.target, a.out), indent=2))
