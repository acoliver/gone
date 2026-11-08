"""sRGB reflectance and CIE colour measurements (D65, 2 degree observer)."""
import numpy as np


def linear(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def srgb(rgb):
    return np.where(rgb <= .0031308, rgb * 12.92, 1.055 * np.maximum(rgb, 0) ** (1 / 2.4) - .055)


def luminance(rgb):
    return linear(rgb) @ np.array([.2126, .7152, .0722])


def lab(rgb):
    xyz = linear(rgb) @ np.array([[.4124564, .3575761, .1804375], [.2126729, .7151522, .0721750], [.0193339, .1191920, .9503041]]).T
    xyz /= [.95047, 1., 1.08883]
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def delta_e_2000(a, b):
    l1, a1, b1 = np.moveaxis(a, -1, 0)
    l2, a2, b2 = np.moveaxis(b, -1, 0)
    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    cm = (c1 + c2) / 2
    g = .5 * (1 - np.sqrt(cm ** 7 / (cm ** 7 + 25 ** 7)))
    a1, a2 = a1 * (1 + g), a2 * (1 + g)
    c1, c2 = np.hypot(a1, b1), np.hypot(a2, b2)
    h1, h2 = np.degrees(np.arctan2(b1, a1)) % 360, np.degrees(np.arctan2(b2, a2)) % 360
    dl, dc = l2 - l1, c2 - c1
    dh = h2 - h1
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(c1 * c2 == 0, 0, dh)
    d_h = 2 * np.sqrt(c1 * c2) * np.sin(np.radians(dh / 2))
    lm, cm = (l1 + l2) / 2, (c1 + c2) / 2
    hm = np.where(abs(h1 - h2) <= 180, (h1 + h2) / 2, np.where(h1 + h2 < 360, (h1 + h2 + 360) / 2, (h1 + h2 - 360) / 2))
    hm = np.where(c1 * c2 == 0, h1 + h2, hm)
    t = 1 - .17 * np.cos(np.radians(hm - 30)) + .24 * np.cos(np.radians(2 * hm)) + .32 * np.cos(np.radians(3 * hm + 6)) - .20 * np.cos(np.radians(4 * hm - 63))
    sl = 1 + .015 * (lm - 50) ** 2 / np.sqrt(20 + (lm - 50) ** 2)
    sc, sh = 1 + .045 * cm, 1 + .015 * cm * t
    rt = -2 * np.sqrt(cm ** 7 / (cm ** 7 + 25 ** 7)) * np.sin(np.radians(60 * np.exp(-((hm - 275) / 25) ** 2)))
    return np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (d_h / sh) ** 2 + rt * (dc / sc) * (d_h / sh))
