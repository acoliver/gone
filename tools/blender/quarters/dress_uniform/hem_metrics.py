"""Measure recurring hem-height periods without treating broad drape as a notch."""
import numpy as np
from scipy.signal import find_peaks


def periodic_peak(station, height):
    station = np.asarray(station)
    height = np.asarray(height, dtype=float).copy()
    if len(station) < 42:
        raise ValueError('Hem needs at least 42 mm of sampled boundary')
    height -= np.polyval(np.polyfit(station, height, 1), station)
    values = [1.]
    maximum = min(121, len(height)-20)
    for lag in range(1, maximum+1):
        a, b = height[:-lag], height[lag:]
        denominator = np.linalg.norm(a)*np.linalg.norm(b)
        values.append(float(np.dot(a, b)/denominator) if denominator > 1e-15 else 0.)
    # The zero-lag correlation and its descending shoulder occur on every
    # continuous hem. Only a later local maximum measures a repeated period.
    peaks = [i for i in find_peaks(values)[0] if 20 <= i <= 120]
    return max([0.]+[values[i] for i in peaks]), values[20:121]
