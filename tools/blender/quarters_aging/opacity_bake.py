"""Rasterize sub-3 mm lip breakup and worn pinholes into the game mesh's BakeUV."""
from pathlib import Path

import numpy as np
from mathutils.kdtree import KDTree

from bake_down import boundary_samples, boundary_segments
from fringe_cards import image_from_array


def value_noise(points, wavelength, seed):
    p = np.asarray(points)/wavelength
    cell = np.floor(p)
    fraction = p-cell
    smooth = fraction*fraction*(3-2*fraction)
    result = np.zeros(len(p))
    for x in [0, 1]:
        for y in [0, 1]:
            for z in [0, 1]:
                corner = np.array([x, y, z])
                phase = (cell[:, 0]+x)*12.9898+(cell[:, 1]+y)*78.233+(cell[:, 2]+z)*37.719+seed*.123
                hashed = np.sin(phase)*43758.5453
                value = (hashed-np.floor(hashed))*2-1
                weight = np.prod(np.where(corner, smooth, 1-smooth), axis=1)
                result += value*weight
    return result


def opacity_bake(obj, out, size=4096, seed=9501, gain=3.5):
    samples = boundary_samples(boundary_segments(obj), .001)
    if not samples:
        raise ValueError('Opacity lip bake requires open cloth boundaries')
    tree = KDTree(len(samples))
    for i, p in enumerate(samples):
        tree.insert(p, i)
    tree.balance()
    positions = np.array([obj.matrix_world@v.co for v in obj.data.vertices])
    distance = np.array([tree.find(p)[2] for p in positions])
    obj.data.calc_loop_triangles()
    uv = obj.data.uv_layers['BakeUV'].data
    mask = np.ones((size, size), dtype=np.float32)
    frequencies = np.array([.002, .001, .0007, .0005])
    weights = np.array([.5, .25, .15, .1])
    for triangle in obj.data.loop_triangles:
        ids = np.array(triangle.vertices)
        tex = np.array([uv[i].uv[:] for i in triangle.loops])*size
        lo = np.maximum(0, np.floor(tex.min(0)).astype(int))
        hi = np.minimum(size-1, np.ceil(tex.max(0)).astype(int))
        if np.any(hi < lo):
            continue
        x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
        a, b, c = tex
        det = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(det) < 1e-12:
            continue
        u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/det
        v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/det
        w = 1-u-v
        inside = (u >= 0) & (v >= 0) & (w >= 0)
        if not inside.any():
            continue
        bary = np.stack([u[inside], v[inside], w[inside]], axis=1)
        p = bary@positions[ids]
        d = bary@distance[ids]
        noise = np.zeros(len(p))
        for octave, (wavelength, weight) in enumerate(zip(frequencies, weights)):
            noise += weight*value_noise(p, wavelength, seed+octave)
        opaque = (d >= .003) | (d/.003+noise*gain >= .35)
        # Isolated pinholes on the worn front, away from intact seam interiors.
        pinhole = (p[:, 1] < -.24) & (noise > .65) & (d > .006)
        tile = mask[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        tile[inside] = (opaque & ~pinhole).astype(np.float32)
    rgba = np.ones((size, size, 4), dtype=np.float32)
    rgba[:, :, :3] = mask[:, :, None]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image = image_from_array(obj.name+'_Opacity', rgba, out, noncolor=True)
    return image, {'path': str(out), 'size': size, 'transparent_texels': int((mask < .5).sum()),
                   'lip_band_m': .003, 'noise_gain': gain, 'feature_wavelengths_m': frequencies.tolist()}
