"""Seeded material fields in Blender's physical Z-up frame, never UV space."""
import numpy as np


def noise(points, frequency, seed):
    p = points * frequency
    grid = np.floor(p)
    blend = p - grid
    blend = blend * blend * (3 - 2 * blend)
    value = np.zeros(points.shape[:-1], np.float32)
    for x in (0, 1):
        for y in (0, 1):
            for z in (0, 1):
                dot = ((grid + [x, y, z]) * [127.1, 311.7, 74.7]).sum(-1) + seed * .13
                sample = np.mod(np.sin(dot) * 43758.5453, 1)
                weight = (blend[..., 0] if x else 1 - blend[..., 0])
                weight = weight * (blend[..., 1] if y else 1 - blend[..., 1])
                weight = weight * (blend[..., 2] if z else 1 - blend[..., 2])
                value += sample * weight
    return value


def gravity_runs(points, normals, sources, seed):
    runs = np.zeros(points.shape[:-1], np.float32)
    rng = np.random.default_rng(seed)
    for source in sources:
        origin = np.array(source['position_blender'])
        width = source['width_m'] * rng.uniform(.92, 1.08)
        length = source['length_m'] * rng.uniform(.95, 1.05)
        drop = origin[2] - points[..., 2]
        for along, across in ((0, 1), (1, 0)):
            candidates = (drop >= 0) & (drop < length)
            candidates &= (abs(points[..., along] - origin[along]) < width)
            candidates &= (abs(points[..., across] - origin[across]) < .035) & (abs(normals[..., across]) > .6)
            lateral = abs(points[candidates, along] - origin[along])
            # width is the full visible trail width, not a Gaussian radius.
            ragged_width = width * .54 + .0015 * np.sin(drop[candidates] * 240 + origin[0] * 733)
            profile = np.clip((ragged_width - lateral) / .0012, 0, 1)
            trail = profile * np.clip((length - drop[candidates]) / .025, 0, 1)
            if 'start_fade_m' in source:
                onset = .006 + .004 * np.sin(points[candidates, along] * 240 + origin[2] * 31)
                trail *= np.clip((drop[candidates] - onset) / source['start_fade_m'], 0, 1)
            runs[candidates] = np.maximum(runs[candidates], trail * source.get('strength', 1))
    return runs


def corrosion_field(points, edge_distance, contact, ownership, seed):
    warp = np.stack([noise(points, 37, seed + i) for i in (5, 6, 7)], -1)
    p = (points + (warp - .5) * .018) @ np.array([[.36, -.48, .8], [.8, .60, 0], [-.48, .64, .6]])
    edge_flakes = noise(p, 35, seed + 1) * .70 + noise(p, 112, seed + 2) * .30
    pinholes = noise(p, 103, seed + 3) * .70 + noise(p, 237, seed + 4) * .30
    edge_weight = np.exp(-edge_distance / .020)
    flakes = pinholes * (1 - edge_weight) + edge_flakes * edge_weight
    threshold = .655 - 1.60 * np.exp(-edge_distance / .018) - contact * .19
    corrosion = np.clip((flakes - threshold) / .035 + .5, 0, 1)
    # Hardware loses its protective film throughout, with dark pits between oxide.
    corrosion = np.where(ownership == 2, np.clip((flakes - .50) * 12, 0, 1), corrosion)
    return corrosion
