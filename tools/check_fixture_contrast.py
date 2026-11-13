"""Measure authored louvre and slot centres in a straight-up 2.5 m view."""
import argparse
import json
import math
from statistics import median

from PIL import Image

WEIGHTS = (.2126, .7152, .0722)
MAX_LOUVRE_SLOT_RATIO = .18
MIN_SLOT_LUMA = .75
MAX_SLOT_LUMA = .93


def measure(path, pixels_per_metre=None):
    image = Image.open(path).convert('RGB')
    width, height = image.size
    # Production camera: vertical FOV 55 degrees, recessed face 2.5 m away.
    scale = pixels_per_metre or height / (2 * math.tan(math.radians(55 / 2)) * 2.5)

    def samples(positions):
        display, linear = [], []
        for position in positions:
            x, y = round(width / 2 + position * scale), round(height / 2)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    rgb = [value / 255 for value in image.getpixel((x + dx, y + dy))]
                    display.append(sum(a * b for a, b in zip(rgb, WEIGHTS)))
                    decoded = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
                    linear.append(sum(a * b for a, b in zip(decoded, WEIGHTS)))
        return median(display), median(linear)

    # Thirteen transverse bars at 70 mm pitch, with fourteen apertures between.
    louvre, louvre_linear = samples([index * .07 for index in range(-6, 7)])
    slot, slot_linear = samples([(index + .5) * .07 for index in range(-7, 7)])
    return {
        'louvre_display_luma': louvre, 'slot_display_luma': slot,
        'display_ratio': louvre / slot if slot else math.inf,
        'louvre_linear_luminance': louvre_linear, 'slot_linear_luminance': slot_linear,
        'linear_ratio': louvre_linear / slot_linear if slot_linear else math.inf,
        'louvre_patches': 13, 'slot_patches': 14, 'patch_pixels': 9,
        'pixels_per_metre': scale,
    }


def passes(result):
    return (result['display_ratio'] <= MAX_LOUVRE_SLOT_RATIO
            and MIN_SLOT_LUMA <= result['slot_display_luma'] <= MAX_SLOT_LUMA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--pixels-per-metre', type=float)
    args = parser.parse_args()
    result = measure(args.image, args.pixels_per_metre)
    result['passed'] = passes(result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
