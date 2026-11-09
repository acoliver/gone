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


def cloth_color(occlusion, upward, variation, wool=False):
    base = np.array([.115, .083, .040] if wool else [.175, .125, .063])
    shadow = .36 + .64 * occlusion
    faded = base * shadow[..., None] * (.82 + .32 * variation[..., None])
    dust = np.clip(upward, 0, 1) ** 2 * occlusion * .30
    return faded * (1 - dust[..., None]) + np.array([.235, .195, .130]) * dust[..., None]
