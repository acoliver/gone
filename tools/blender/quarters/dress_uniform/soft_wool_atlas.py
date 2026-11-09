"""Curled wool bundles wide enough to retain fractional coverage in close views."""
import numpy as np


def bundle_alpha(seed):
    rng = np.random.default_rng(seed)
    alpha = np.zeros((1024, 1024), np.float32)
    for variant in range(8):
        tile = alpha[variant*128:(variant+1)*128]
        for index in range(14):
            root = 70+(index+.5)*884/14+rng.uniform(-12, 12)
            length = rng.uniform(64, 116)
            curl = rng.uniform(24, 54)*rng.choice([-1, 1])
            t = np.linspace(0, 1, 24)
            x = root+curl*np.sin(t*np.pi*1.35)*t
            y = t*length+np.sin(t*np.pi*1.6)*9
            radius = rng.uniform(7, 12)*(1-.45*t)
            for i in range(len(t)-1):
                a, b = np.array([x[i], y[i]]), np.array([x[i+1], y[i+1]])
                margin = radius[i]+2
                lo = np.maximum([0, 0], np.floor(np.minimum(a, b)-margin).astype(int))
                hi = np.minimum([1023, 127], np.ceil(np.maximum(a, b)+margin).astype(int))
                xx, yy = np.meshgrid(np.arange(lo[0], hi[0]+1), np.arange(lo[1], hi[1]+1))
                p = np.stack([xx, yy], axis=-1)
                along = np.clip(np.sum((p-a)*(b-a), axis=-1)/np.sum((b-a)**2), 0, 1)
                distance = np.linalg.norm(p-a-along[:, :, None]*(b-a), axis=-1)
                width = radius[i]*(1-along)+radius[i+1]*along
                coverage = np.clip((width+1.5-distance)/3, 0, 1)
                region = tile[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
                np.maximum(region, coverage, out=region)
    return alpha
