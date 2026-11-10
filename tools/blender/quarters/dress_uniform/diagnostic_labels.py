"""Decode tunic label renders without mistaking material antialiasing for holes."""
import numpy as np


def decode_labels(rgb):
    red, green, blue = np.moveaxis(np.asarray(rgb, dtype=np.float64), -1, 0)
    # Red wool, green fringe and magenta fittings all have R+G = 1.
    # Their antialiased mixtures retain that coverage; blue wire and black
    # openings have R+G = 0. Decode coverage before choosing a material ID.
    coverage = red+green >= 127.5
    labels = np.zeros(rgb.shape[:2], np.uint8)
    labels[coverage] = 2
    labels[coverage & (red > 230) & (green < 20) & (blue < 20)] = 1
    # Fittings occlude a tear; their perimeter is not a wool lip.
    labels[coverage & (blue > (red+green)*.25)] = 5
    white = (red >= 127.5) & (green >= 127.5) & (blue >= 127.5) & (abs(red-green) < 32)
    labels[coverage & white] = 4
    return labels
