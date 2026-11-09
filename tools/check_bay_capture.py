"""Check the quiescent bay circuit captures for white squares and red haze."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image


def white_squares(rgb):
    mask = rgb.min(axis=2) > 220
    seen = set()
    squares = []
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if (y, x) in seen:
            continue
        pending = [(y, x)]
        seen.add((y, x))
        points = []
        while pending:
            point = pending.pop()
            points.append(point)
            for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                other = (point[0] + dy, point[1] + dx)
                if 0 <= other[0] < height and 0 <= other[1] < width and mask[other] and other not in seen:
                    seen.add(other)
                    pending.append(other)
        bounds = np.array(points)
        low, high = bounds.min(axis=0), bounds.max(axis=0)
        size = high - low + 1
        if 12 <= size.min() and size.max() <= 64 and 0.8 <= size[0] / size[1] <= 1.25 and len(points) / size.prod() >= 0.9:
            squares.append((low.tolist(), high.tolist()))
    return squares


def check(directory):
    failures = []
    for circuit in ['emergency-red-orange', 'secondary-white']:
        path = Path(directory) / (circuit + '-bay.png')
        rgb = np.array(Image.open(path).convert('RGB'))
        if rgb.shape != (1296, 2304, 3):
            failures.append(f'{path}: expected native 2304x1296 image')
            continue
        squares = white_squares(rgb)
        mean = rgb.mean(axis=(0, 1))
        print(f'{circuit}: white_squares={len(squares)} mean_rgb={mean.tolist()}')
        if squares:
            failures.append(f'{path}: solid white billboard squares: {squares}')
        # The settled reference has R-G = 12.10; the flashing regression has 80.31.
        if circuit == 'emergency-red-orange' and mean[0] - mean[1] >= 20.0:
            failures.append(f'{path}: red wash, mean R-G={mean[0] - mean[1]:.3f} >= 20')
    return failures


if __name__ == '__main__':
    errors = check(sys.argv[1])
    for error in errors:
        print('FAIL', error)
    raise SystemExit(1 if errors else 0)
