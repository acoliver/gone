"""Generated-star transport and photographic enamel highlight removal."""
import numpy as np


def enamel_coat_map(existing, enamel_weight, transported_front, front, coat_weight):
    result = existing.copy()
    affected = transported_front | (front & (enamel_weight > .01))
    result[affected] = coat_weight * enamel_weight[affected, None]
    return result


def visible_star_transfer(positions, old_boundary, new_boundary, enamel_radius):
    result = radial_transfer(positions, np.minimum(old_boundary, enamel_radius),
                             new_boundary, enamel_radius)
    bezel = np.linalg.norm(positions[:, [0, 2]], axis=1) >= enamel_radius
    result[bezel] = positions[bezel]
    return result


def remove_achromatic_highlights(linear_rgb, enamel_mask):
    # Blue enamel's weakest channel bounds the achromatic reflected light.
    floor = np.percentile(linear_rgb[..., 0][enamel_mask], 25)
    reflected = np.maximum(linear_rgb[..., 0] - floor, 0)
    return linear_rgb - reflected[..., None], float(floor)


def radial_transfer(positions, old_boundary, new_boundary, enamel_radius):
    positions = np.asarray(positions)
    radius = np.linalg.norm(positions[:, [0, 2]], axis=1)
    support = np.maximum(enamel_radius, old_boundary + .0004)
    scale = new_boundary / old_boundary
    mapped = np.where(radius <= old_boundary, radius * scale,
                      new_boundary + (radius - old_boundary) *
                      (support - new_boundary) / (support - old_boundary))
    active = (positions[:, 1] < -.0006) & (radius < support)
    result = positions.copy()
    gain = np.divide(mapped, radius, out=np.ones_like(radius), where=radius > 0)
    result[active, 0] *= gain[active]
    result[active, 2] *= gain[active]
    return result


def boundary_radius(outline, angle):
    direction = np.c_[np.sin(angle), np.cos(angle)]
    result = np.full(len(angle), np.nan)
    for a, b in zip(outline, np.roll(outline, -1, axis=0)):
        edge = b - a
        cross = direction[:, 0] * edge[1] - direction[:, 1] * edge[0]
        distance = np.divide(a[0] * edge[1] - a[1] * edge[0], cross,
                             out=np.full_like(cross, -1), where=abs(cross) > 1e-15)
        hit = direction * distance[:, None]
        u = np.sum((hit - a) * edge, axis=1) / np.sum(edge * edge)
        valid = (distance > 0) & (u >= -1e-9) & (u <= 1 + 1e-9)
        result[valid] = distance[valid]
    assert np.isfinite(result).all(), 'Generated outline must meet each ray once'
    return result
