"""Measure atlas overlap and physical texel anisotropy on sofa triangles."""
import numpy as np


def measure(uv, positions, size=512):
    from finish_materials import pixels
    coverage = np.zeros((size, size), np.uint16)
    ratios = []
    for chart, triangle in zip(uv, positions):
        raster = pixels(chart, size)
        if raster is not None:
            coverage[raster[0], raster[1]] += 1
        delta_uv = np.stack([chart[1] - chart[0], chart[2] - chart[0]], 1)
        if abs(np.linalg.det(delta_uv)) < 1e-12:
            continue
        delta_xyz = np.stack([triangle[1] - triangle[0], triangle[2] - triangle[0]], 1)
        singular = np.linalg.svd(delta_xyz @ np.linalg.inv(delta_uv), compute_uv=False)
        if singular[-1] > 1e-9:
            ratios.append(singular[0] / singular[-1])
    occupied = coverage > 0
    if not occupied.any() or not ratios:
        raise ValueError('UV metric requires nondegenerate occupied triangles')
    return dict(overlap_fraction=float((coverage[occupied] > 1).mean()),
                maximum_layers=int(coverage.max()),
                anisotropy_median=float(np.median(ratios)),
                anisotropy_p90=float(np.quantile(ratios, .9)))
