"""Separated physical blisters, with enough intact paint to keep islands apart."""
import numpy as np
from scipy.spatial import cKDTree

from finish_fields import noise


def spots(bounds, coverage, radius_range, seed, gap=.008):
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(bounds)
    area = np.prod(hi - lo)
    centres, radii = [], []
    covered = 0.
    for attempt in range(100000):
        # At high coverage, small early spots block later large losses.
        if coverage >= .30:
            radius = np.clip(radius_range[1] * np.exp(-attempt / 2500) * rng.uniform(.9, 1.1), *radius_range)
        else:
            radius = rng.uniform(*radius_range)
        point = rng.uniform(lo, hi)
        if centres and np.any(np.linalg.norm(np.asarray(centres) - point, axis=1) < np.asarray(radii) + radius + gap):
            continue
        centres.append(point)
        radii.append(radius)
        covered += np.pi * radius ** 2
        if covered >= coverage * area:
            return np.asarray(centres), np.asarray(radii)
    raise ValueError('blister packing cannot reach the requested physical coverage')


def shape_profiles(radii, gap, seed):
    """Vary each contour while preserving its area and clearance envelope."""
    rng = np.random.default_rng(seed)
    amplitudes = rng.uniform(.08, .28, (len(radii), 3))
    phases = rng.uniform(0, 2 * np.pi, (len(radii), 3))
    angles = np.linspace(0, 2 * np.pi, 256, endpoint=False)
    wave = angular_wave(angles[None, :], amplitudes[:, None], phases[:, None])
    # Reserve 11.5 mm of the diameter budget for shear and fine breakup.
    limit = np.minimum(radii + gap * .20, .0242)
    low, high = np.zeros(len(radii)), np.full(len(radii), 2.)
    for _ in range(20):
        middle = (low + high) * .5
        radius = np.clip(radii[:, None] * (middle[:, None] + wave), radii[:, None] * .10, limit[:, None])
        smaller = (radius ** 2).mean(-1) < radii ** 2
        low = np.where(smaller, middle, low)
        high = np.where(smaller, high, middle)
    return amplitudes, phases, (low + high) * .5, limit


def angular_wave(angles, amplitudes, phases):
    return (np.sin(angles[..., None] * [3, 5, 7] + phases) * amplitudes).sum(-1)


def corrugate(uv, seed):
    result = uv.copy()
    height = np.column_stack([np.zeros((len(uv), 2)), uv[:, 1]])
    result[:, 0] += (noise(height, 105, seed + 301) - .5) * .006
    return result


def blister_field(points, normals, seed):
    axis = abs(normals).argmax(-1)
    result = np.zeros(len(points), np.float32)
    physical = points @ np.array([[.36, -.48, .8], [.8, .60, 0], [-.48, .64, .6]])
    ragged = (noise(physical, 137, seed + 71) - .5) * .004
    ragged += (noise(physical, 293, seed + 72) - .5) * .0015
    for normal_axis, plane in [(0, (1, 2)), (1, (0, 2)), (2, (0, 1))]:
        selected = axis == normal_axis
        # A height-dependent shear preserves island area and paint gaps while
        # corrugating the contour, instead of leaving circular corrosion dots.
        uv = corrugate(points[selected][:, plane], seed)
        bounds = [uv.min(0) - .030, uv.max(0) + .030]
        coverage = .42 if normal_axis == 0 else .240
        radii = (.006, .024) if normal_axis == 0 else (.007, .021)
        gap = .006 if normal_axis == 0 else .010
        centres, radius = spots(bounds, coverage, radii, seed + normal_axis * 91, gap=gap)
        amplitudes, phases, bias, limit = shape_profiles(radius, gap, seed + normal_axis * 113)
        distances, indices = cKDTree(centres).query(uv, k=8)
        delta = uv[:, None] - centres[indices]
        angles = np.arctan2(delta[..., 1], delta[..., 0])
        wave = angular_wave(angles, amplitudes[indices], phases[indices])
        shaped = np.clip(radius[indices] * (bias[indices] + wave), radius[indices] * .10, limit[indices])
        signed = (shaped - distances).max(-1) + ragged[selected]
        result[selected] = np.clip(signed / .003 + .5, 0, 1)
    return result
