"""Display-to-albedo fitting for sofa-only target pigments."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'quarters_aging'))
from colour import linear, srgb


def update_albedo(albedo, displayed_bytes, target_bytes):
    displayed = linear(np.asarray(displayed_bytes, float) / 255)
    target = linear(np.asarray(target_bytes, float) / 255)
    if np.any(displayed <= 0):
        raise ValueError('Calibration swatch must resolve above black')
    return np.clip(albedo * target / displayed, 0, 1)


def calibrated_scan(scan, albedo):
    colour = linear(scan)
    return np.clip(srgb(colour * np.asarray(albedo) / colour.mean((0, 1))), 0, 1)
