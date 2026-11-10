"""Source-contour fitting and planar contracts, independent of Blender scene I/O."""
import math

import numpy as np


LENGTH = 1.18
WIDTH = .58
THICKNESS = .002
RIM_DEPTH = .018
RIM_FRACTIONS = (0., .23, .44, .84, 1.)
RIM_HEIGHTS = (0., 0., 0., -.017, -RIM_DEPTH)


def signed_area(loop):
    return float(np.sum(loop[:, 0] * np.roll(loop[:, 1], -1)
                        - loop[:, 1] * np.roll(loop[:, 0], -1)) / 2)


def ccw(loop):
    return loop if signed_area(loop) > 0 else loop[::-1].copy()


def fair(loop):
    points = np.array(loop, dtype=float)
    for _ in range(2):
        points += .15 * ((np.roll(points, 1, axis=0) + np.roll(points, -1, axis=0)) / 2 - points)
    dense = []
    for i, p1 in enumerate(points):
        p0, p2, p3 = points[i - 1], points[(i + 1) % len(points)], points[(i + 2) % len(points)]
        for t in (0., .5):
            dense.append(.5 * ((2 * p1) + (-p0 + p2) * t
                              + (2*p0 - 5*p1 + 4*p2 - p3) * t*t
                              + (-p0 + 3*p1 - 3*p2 + p3) * t*t*t))
    return ccw(np.array(dense))


def cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def contains(points, loop):
    points = np.atleast_2d(points)
    a, b = loop, np.roll(loop, -1, axis=0)
    x, y = points[:, 0, None], points[:, 1, None]
    active = (a[:, 1] > y) != (b[:, 1] > y)
    dy = b[:, 1] - a[:, 1]
    dx = b[:, 0] - a[:, 0]
    hit_x = a[:, 0] + (y - a[:, 1]) * np.divide(dx, dy, out=np.zeros_like(dx), where=dy != 0)
    return np.count_nonzero(active & (x < hit_x), axis=1) % 2 == 1


def distance_to_loop(points, loop):
    points = np.atleast_2d(points)
    a, edge = loop, np.roll(loop, -1, axis=0) - loop
    v = points[:, None, :] - a
    t = np.clip(np.sum(v * edge, axis=2) / np.sum(edge * edge, axis=1), 0, 1)
    return np.sqrt(np.min(np.sum((v - t[:, :, None] * edge) ** 2, axis=2), axis=1))


def assert_simple(loop):
    edge = np.roll(loop, -1, axis=0) - loop
    assert np.min(np.linalg.norm(edge, axis=1)) > 1e-7, 'zero-length contour edge'
    delta = loop[None, :, :] - loop[:, None, :]
    denom = cross(edge[:, None, :], edge[None, :, :])
    valid = np.abs(denom) > 1e-12
    u = np.divide(cross(delta, edge[None, :, :]), denom, out=np.zeros_like(denom), where=valid)
    v = np.divide(cross(delta, edge[:, None, :]), denom, out=np.zeros_like(denom), where=valid)
    assert not np.any(valid & (u > 1e-8) & (u < 1-1e-8) & (v > 1e-8) & (v < 1-1e-8)), 'crossed contour'
    assert signed_area(loop) > 0, 'contour must have positive area'


def radial(loop, angles):
    direction = np.column_stack((np.cos(angles), np.sin(angles)))
    edge = np.roll(loop, -1, axis=0) - loop
    denom = cross(direction[:, None, :], edge[None, :, :])
    good = np.abs(denom) > 1e-12
    r = np.divide(cross(loop, edge)[None, :], denom, out=np.full_like(denom, np.inf), where=good)
    t = np.divide(cross(loop[None, :, :], direction[:, None, :]), denom,
                  out=np.full_like(denom, np.inf), where=good)
    hits = good & (r > 0) & (t >= -1e-8) & (t <= 1 + 1e-8)
    radii = np.min(np.where(hits, r, np.inf), axis=1)
    assert np.isfinite(radii).all(), 'source contour must surround fitting origin'
    return direction * radii[:, None]


def capsule(cx, cy, length=.108, width=.022):
    radius = width / 2
    span = length / 2 - radius
    points = []
    for center, start in ((cx + span, -math.pi/2), (cx - span, math.pi/2)):
        for angle in np.linspace(start, start + math.pi, 8):
            points.append((center + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return ccw(np.array(points))


def constraint_loop(loop, protected=()):
    """Remove redundant samples before float32 CDT can turn them into slivers."""
    indices = list(range(len(loop)))
    protected = set(protected)
    changed = True
    while changed:
        changed = False
        for position, index in enumerate(indices):
            if index in protected:
                continue
            a = loop[indices[position - 1]]
            b = loop[indices[(position + 1) % len(indices)]]
            edge = b - a
            t = np.dot(loop[index] - a, edge) / np.dot(edge, edge)
            if 0 < t < 1 and np.linalg.norm(loop[index] - (a + t*edge)) < 2e-7:
                indices.pop(position)
                changed = True
                break
    return loop[indices].astype(np.float32).astype(float)


class FittedGuides:
    def __init__(self, guide):
        section = next(level for level in guide['levels'] if level['section_y_m'] == .015)
        source_outer, source_inner = [np.array(c['smooth_80_xz']) for c in section['retained_large_contours']]
        edge = np.roll(source_outer, -1, axis=0) - source_outer
        long_edges = edge[np.abs(edge[:, 0]) > 3 * np.abs(edge[:, 1])]
        long_edges *= np.sign(long_edges[:, 0, None])
        self.angle = math.atan2(long_edges[:, 1].sum(), long_edges[:, 0].sum())
        c, s = math.cos(self.angle), math.sin(self.angle)
        # Guide coordinates are raw glTF X/Z. Blender import already maps them to X/-Y.
        self.raw_to_plan = np.array([[c, s], [s, -c]])
        outer = fair(source_outer) @ self.raw_to_plan.T
        inner = fair(source_inner) @ self.raw_to_plan.T
        self.center = (outer.min(axis=0) + outer.max(axis=0)) / 2
        self.scale = WIDTH / np.ptp(outer[:, 1])
        self.delta = LENGTH - np.ptp(outer[:, 0]) * self.scale
        self.central_halfspan = .30
        assert 1 + min(0, self.delta / 2 * 1.5 / self.central_halfspan) > 0
        source_fitted_outer, inner = ccw(self.fit_plan(outer)), ccw(self.fit_plan(inner))
        # The source rim/face is retained, but a mounting flange must fit the straight T grid.
        radius = .002
        outer = []
        for sx, sy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            for angle in np.deg2rad(np.linspace(start, start + 90, 9)):
                outer.append([sx * (LENGTH / 2 - radius) + radius * math.cos(angle),
                              sy * (WIDTH / 2 - radius) + radius * math.sin(angle)])
        outer = np.array(outer)
        # Include every fitted contour vertex and extrema, avoiding sampling shrinkage.
        angles = np.concatenate((np.arctan2(outer[:, 1], outer[:, 0]),
                                 np.arctan2(inner[:, 1], inner[:, 0]),
                                 np.linspace(-math.pi, math.pi, 128, endpoint=False),
                                 .28 + np.array([-.11, -.07, -.04, 0, .03, .06, .11]),
                                 math.pi + np.array([-.14, -.10, -.04, 0, .035, .09, .14])))
        self.angles = np.unique(np.round((angles + math.pi) % (2*math.pi) - math.pi, 10))
        self.outer = radial(outer, self.angles)
        self.inner = radial(inner, self.angles)
        self.middle = (self.outer + self.inner) / 2
        for loop in (self.outer, self.middle, self.inner):
            assert_simple(loop)
        assert contains(self.inner, self.middle).all()
        assert contains(self.middle, self.outer).all()
        self.slots = [capsule(x, y) for y in (-.135, -.045, .045, .135)
                      for x in np.linspace(-.396, .396, 7)]
        for slot in self.slots:
            assert_simple(slot)
            assert contains(slot, self.inner).all(), 'slot outside source-derived inner rim'
        self.slot_rim_gap = min(float(distance_to_loop(slot, self.inner).min()) for slot in self.slots)
        self.slot_gap = min(float(min(distance_to_loop(a, b).min(), distance_to_loop(b, a).min()))
                            for i, a in enumerate(self.slots) for b in self.slots[i+1:])
        assert self.slot_rim_gap >= .008, ('slot to rim clearance', self.slot_rim_gap)
        assert self.slot_gap >= .008, ('slot ligament', self.slot_gap)
        self.contact_indices = [int(np.argmin(np.linalg.norm(self.outer - [sx*LENGTH/2, sy*WIDTH/2], axis=1)))
                                for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1))]
        residuals = {}
        for name, raw, fitted in (('source_outer_before_mounting_flange', source_outer, source_fitted_outer), ('inner', source_inner, self.inner)):
            reference = self.fit_plan(raw @ self.raw_to_plan.T)
            residual = distance_to_loop(reference, fitted)
            residuals[name] = {'rms_m': float(np.sqrt(np.mean(residual**2))),
                               'max_m': float(residual.max()), 'samples': len(reference)}
        self.record = {
            'source_section_raw_y_m': .015,
            'plan_alignment_from_source_long_edges_degrees': math.degrees(self.angle),
            'raw_xz_to_blender_plan_matrix': self.raw_to_plan.tolist(),
            'aligned_source_center': self.center.tolist(), 'uniform_width_scale': self.scale,
            'central_length_delta_m': self.delta, 'central_halfspan_m': self.central_halfspan,
            'central_map': 'x += delta/2 * (1.5*t - 0.5*t^3) for |t=x/.30|<1; otherwise delta/2*sign(x)',
            'end_shape_policy': 'Beyond central halfspan: uniform scale and translation only; no longitudinal radius scaling.',
            'fairing': 'Two periodic Laplacian passes, weight .15; periodic Catmull-Rom sampled twice per original edge.',
            'guide_residual_to_fitted_polyline': residuals,
            'contour_samples_per_ring': len(self.outer),
            'outer_blender_xy_m': self.outer.tolist(), 'inner_blender_xy_m': self.inner.tolist(),
            'source_outer_before_mounting_flange_blender_xy_m': source_fitted_outer.tolist(),
            'mounting_flange': '1.18 x .58 m formed perimeter, 2 mm corner radius; source-derived inner rim and perforated face retained. Fits 1.2 x .6 m grid with 16 mm web and 2 mm reveals.',
        }

    def fit_plan(self, points):
        result = (points - self.center) * self.scale
        t = np.clip(result[:, 0] / self.central_halfspan, -1, 1)
        result[:, 0] += self.delta / 2 * (1.5*t - .5*t**3)
        return result

    def damage_weight(self, angles, kind):
        if kind not in ('torncorner', 'brokenedge'):
            return np.zeros(len(angles))
        center = self.angles[self.contact_indices[-1]] if kind == 'torncorner' else math.pi / 2
        # The failure-facing side has a narrower source flange, so its notch spans a wider arc.
        width = .30 if kind == 'torncorner' else .50
        t = ((angles - center + math.pi) % (2*math.pi) - math.pi) / width
        envelope = np.maximum(0., 1 - t*t)**2
        # Broad, asymmetric lobes cut one region without narrow radial teeth.
        irregularity = .88 + .07 * np.cos(7*t + .4) + .05 * np.sin(11*t)
        return envelope * irregularity * (.98 if kind == 'torncorner' else .92)

    def damaged_outer(self, kind):
        weight = self.damage_weight(self.angles, kind)
        outer = self.outer + (self.inner - self.outer) * weight[:, None]
        assert_simple(outer)
        assert contains(self.inner, outer).all(), 'notch crossed inner rim'
        return outer

    def profile_rings(self, kind):
        outer = self.damaged_outer(kind)
        return [outer + fraction * (self.inner - outer) if fraction < 1 else self.inner.copy()
                for fraction in RIM_FRACTIONS]

    def attachment_indices(self, kind):
        indices = self.contact_indices.copy()
        if kind == 'torncorner':
            # Keep the fourth fastener on the surviving top flange, away from the tear.
            indices[-1] = int(np.argmin(abs(self.angles - math.atan2(.28, .27))))
        return indices

    def attachment_points(self, kind):
        return self.profile_rings(kind)[1][self.attachment_indices(kind)]

    def displacement(self, points, kind):
        points = np.atleast_2d(points)
        if kind == 'intact':
            return np.zeros(len(points))
        angles = np.arctan2(points[:, 1], points[:, 0])
        if kind in ('torncorner', 'brokenedge'):
            outer_r = np.linalg.norm(radial(self.damaged_outer(kind), angles), axis=1)
            inner_r = np.linalg.norm(radial(self.inner, angles), axis=1)
            radial_fraction = np.clip((np.linalg.norm(points, axis=1) - inner_r) / (outer_r - inner_r), 0, 1)
            weight = self.damage_weight(angles, kind)
            # Depress and curl the surviving thin lip; the perforated face stays intact.
            return -.043 * weight * radial_fraction**1.35
        # The flat flange is stiff; pin its complete width so triangulation cannot
        # interpolate a displaced vertex through a mounting-head footprint.
        boundary = radial(self.profile_rings(kind)[2], angles)
        r = np.linalg.norm(points, axis=1) / np.linalg.norm(boundary, axis=1)
        falloff = np.maximum(0, 1 - r*r)**2
        if kind == 'sag':
            return -.036 * falloff
        return .006 * np.sin(2 * math.pi * points[:, 0] / LENGTH) * falloff
