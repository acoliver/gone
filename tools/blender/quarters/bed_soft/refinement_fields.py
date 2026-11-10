"""Deterministic footprint and pigment fields for dry bed-soft-goods decay."""
import numpy as np


def convex_outline(points):
    points = sorted(set(map(tuple, points)))

    def half(sequence):
        result = []
        for point in sequence:
            while len(result) >= 2:
                a, b = np.array(result[-2]), np.array(result[-1])
                delta, step = b - a, np.array(point) - b
                if delta[0] * step[1] - delta[1] * step[0] > 1e-9:
                    break
                result.pop()
            result.append(point)
        return result

    return np.array(half(points)[:-1] + half(reversed(points))[:-1])


def without_foot_corner(outline):
    clipped = []
    for a, b in zip(outline, np.roll(outline, -1, axis=0)):
        da, db = 1.35 - a[0] + a[1], 1.35 - b[0] + b[1]
        if da >= 0:
            clipped.append(a)
        if (da >= 0) != (db >= 0):
            clipped.append(a + (b - a) * da / (da - db))
    return np.array(clipped)


def powder_field(seed, size=1024):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
    angle = np.arctan2(y, x)
    radius = np.hypot(x, y)
    edge = .81 + .035 * np.sin(angle * 7) + .035 * np.sin(angle * 11 + 1.3)
    fade = np.clip((edge - radius) / .31, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    pools = .64 + .15 * np.sin(x * 8 + y * 4) * np.cos(y * 9 - x * 3)
    grain = .78 + .22 * rng.random((size, size))
    return (fade * pools * grain).astype(np.float32)


def powder_normals(height, extent):
    dy, dx = np.gradient(height, 2 * extent[1] / (height.shape[0] - 1),
                         2 * extent[0] / (height.shape[1] - 1))
    normals = np.stack([-dx, -dy, np.ones_like(dx)], axis=2)
    return normals / np.linalg.norm(normals, axis=2, keepdims=True)


def fringe_groups(seed, width=1024, height=256):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:1:complex(height), 0:1:complex(width)]
    variants = []
    for _ in range(8):
        alpha = np.clip((.22 - y) / .08, 0, 1)
        for center in np.linspace(.05, .95, 8) + rng.uniform(-.025, .025, 8):
            length, half_width, phase = rng.uniform(.35, .95), rng.uniform(.035, .075), rng.uniform(0, 6.28)
            taper = np.clip(1 - (y / length) ** 1.7, 0, 1)
            path = center + .005 * np.sin(y * 15 + phase)
            lobe = np.clip((half_width * taper - np.abs(x - path)) / .008, 0, 1)
            alpha = np.maximum(alpha, lobe * np.clip((length - y) / .10, 0, 1))
        variants.append(alpha)
    return np.array(variants, dtype=np.float32)


def cloth_color(occlusion, upward, variation, wool=False):
    base = np.array([.115, .083, .040] if wool else [.175, .125, .063])
    shadow = .36 + .64 * occlusion
    faded = base * shadow[..., None] * (.35 + 1.3 * variation[..., None])
    dust = np.clip(upward, 0, 1) ** 2 * occlusion * .30
    return faded * (1 - dust[..., None]) + np.array([.235, .195, .130]) * dust[..., None]
