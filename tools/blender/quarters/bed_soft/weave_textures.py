"""Colour the sofa pilot's existing fine yarn scan for the provisional bed wool."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'assets/props/quarters/bed_soft_textures'
COLORS = {'WovenWool': (.14, .105, .075), 'WoolCuff': (.19, .15, .11),
          'WoolBinding': (.075, .053, .035), 'BrittleWool': (.32, .27, .21)}


def srgb(value):
    return np.where(value <= .0031308, value * 12.92, 1.055 * np.maximum(value, 0) ** (1 / 2.4) - .055)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scan = np.asarray(Image.open(ROOT / 'assets/props/quarters/sofa/weave.png').convert('RGB'), dtype=float) / 255
    grain = scan @ np.array([.2126, .7152, .0722])
    fine = grain / gaussian_filter(grain, 6, mode='wrap') - 1
    fine = np.clip(fine, -.65, .65)
    for name, color in COLORS.items():
        pixels = srgb(np.array(color)[None, None, :] * (1 + .28 * fine[:, :, None]))
        Image.fromarray(np.uint8(np.clip(pixels, 0, 1) * 255)).save(OUT / f'{name.lower()}_weave.png')
    height = fine * .00012
    dy, dx = np.gradient(height, .12 / grain.shape[0], .12 / grain.shape[1])
    normals = np.stack([-dx, -dy, np.ones_like(dx)], axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    Image.fromarray(np.uint8(np.clip(normals * .5 + .5, 0, 1) * 255)).save(OUT / 'wool_weave_normal.png')


if __name__ == '__main__':
    main()
