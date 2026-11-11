"""Numerical feature fitting, run with the existing Hunyuan Python environment."""
import json
from pathlib import Path
import sys

import numpy as np
from scipy import sparse
from scipy.interpolate import PchipInterpolator, RegularGridInterpolator
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.spatial import cKDTree


def stats(a):
    return dict(zip(['p50', 'p95', 'max'], np.quantile(np.asarray(a), [.5, .95, 1]).tolist()))


def fit(out):
    source = np.load(out / 'guide-samples.npz')
    vertices, faces = source['vertices'] * 1000, source['faces']
    r, angles, depth = source['radii'] * 1000, source['angles'], source['depths'] * 1000
    for row in depth:
        valid = np.isfinite(row)
        row[:] = np.interp(r, r[valid], row[valid])
    field = float(np.quantile(depth[:, (r > 7) & (r < 10)], .3))
    # Actual generated outline at a fixed, reported relief contour, not a regular star polygon.
    region = (r >= 3.8) & (r <= 11.2)
    outline = []
    for row in depth:
        rr, zz = r[region], row[region]
        crossings = np.where((zz[:-1] >= field + .22) & (zz[1:] < field + .22))[0]
        if len(crossings):
            k = crossings[0]
            outline.append(float(np.interp(field + .22, zz[k:k+2][::-1], rr[k:k+2][::-1])))
        else:
            outline.append(float(rr[-1]))
    outline_raw = np.array(outline)
    outline = gaussian_filter1d(outline_raw, 1.3, mode='wrap')
    # Preserve the five generated arms, with a bounded tip correction to clear the inner lip.
    phase_scores = [np.mean(np.interp((p + np.arange(5) * 2*np.pi/5) % (2*np.pi), angles, outline, period=2*np.pi))
                    for p in np.linspace(1.25, 1.9, 200)]
    phase = float(np.linspace(1.25, 1.9, 200)[np.argmax(phase_scores)])
    outline = np.minimum(outline, 10.9)
    profile_raw = np.median(depth, axis=0)
    profile = gaussian_filter1d(profile_raw, 2)
    landmarks = []
    for lo, hi, kind in [(11.1, 12.2, 'inner_crest'), (13.7, 14.9, 'channel'), (15.25, 15.95, 'outer_crown')]:
        mask = np.flatnonzero((r >= lo) & (r <= hi))
        j = mask[np.argmin(profile[mask]) if kind == 'channel' else np.argmax(profile[mask])]
        local = []
        for row in depth:
            k = mask[np.argmin(row[mask]) if kind == 'channel' else np.argmax(row[mask])]
            local.append([r[k], row[k]])
        landmarks.append(dict(name=kind, radius_mm=float(r[j]), depth_mm=float(profile[j]), angular_extrema=local))
    inner, channel, crown = [l['radius_mm'] for l in landmarks]
    # Denoise the actual triangles, restricting smoothing to their own feature patch.
    rad = np.linalg.norm(vertices[:, [0, 2]], axis=1)
    theta = np.arctan2(vertices[:, 2], vertices[:, 0]) % (2*np.pi)
    field_interp = RegularGridInterpolator((np.r_[angles, 2*np.pi], r), np.vstack([depth, depth[:1]]), bounds_error=False, fill_value=None)
    sample_depth = field_interp(np.c_[theta, np.clip(rad, 0, 16)])
    front = abs(-vertices[:, 1] - sample_depth) < .18
    labels = np.full(len(vertices), 1, dtype=int)  # reverse
    labels[rad > 15.6] = 2
    labels[front & (rad < inner)] = 3  # field/star
    labels[front & (rad >= inner)] = 4
    labels[vertices[:, 2] > 16] = 5
    star_radius = np.interp(theta, angles, outline, period=2*np.pi)
    labels[front & (rad < star_radius)] = 6
    ridges = abs(np.sin(5*(theta-phase)/2)) < .045
    pinned = ((abs(rad-inner) < .07) | (abs(rad-channel) < .07) | (rad > 15.9)
              | ((abs(rad-star_radius) < .09) & front) | (ridges & (labels == 6)) | (labels == 5))
    edge = np.unique(np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    edge = edge[labels[edge[:, 0]] == labels[edge[:, 1]]]
    rows, cols = np.r_[edge[:, 0], edge[:, 1]], np.r_[edge[:, 1], edge[:, 0]]
    length = np.linalg.norm(vertices[rows] - vertices[cols], axis=1)
    weight = np.exp(-length**2/(2*.16**2))
    adjacency = sparse.csr_matrix((weight, (rows, cols)), shape=(len(vertices), len(vertices)))
    degree = np.asarray(adjacency.sum(1)).ravel()
    clean = vertices.copy()
    active = (~pinned) & (degree > 0)
    for _ in range(8):
        for step in [.45, -.47]:
            change = np.zeros_like(clean)
            change[active] = step * ((adjacency @ clean)[active] / degree[active, None] - clean[active])
            clean += change
            delta = clean - vertices
            norm = np.linalg.norm(delta, axis=1)
            clean = vertices + delta * np.minimum(1, .099 / np.maximum(norm, 1e-12))[:, None]
    residual = np.linalg.norm(clean-vertices, axis=1)
    smooth_depth = gaussian_filter(depth, sigma=(1.15, 1.1), mode=('wrap', 'nearest'))
    # Fit one continuous correction profile through generated extrema, retaining measured radii.
    knots_r = np.array([inner-.35, inner, inner+.25, 12.8, 13.3, channel, 15.15, crown, 16.])
    knots_d = .85 + .55*np.interp(knots_r, r, profile)
    knots_d[0] = 1.0
    knots_d[1] = max(knots_d[1], 1.60)
    knots_d[2] = knots_d[1]-.10
    knots_d[3] = max(knots_d[3], 1.38)
    knots_d[4] = max(knots_d[4], 1.35)
    knots_d[5] = min(knots_d[5], 1.10)
    knots_d[6] = max(knots_d[6], 1.40)
    knots_d[7] = max(knots_d[7], 1.46)
    knots_d[8] = .55
    rim = PchipInterpolator(knots_r, knots_d)
    np.savez_compressed(out / 'feature-fit.npz', raw_vertices=vertices/1000, clean_vertices=clean/1000,
                        raw_faces=faces, labels=labels, pinned=pinned, angles=angles,
                        outline_raw_mm=outline_raw, outline_mm=outline, radii_mm=r,
                        raw_depth_mm=depth, smooth_depth_mm=smooth_depth,
                        rim_r_mm=knots_r, rim_d_mm=knots_d, phase=phase)
    report = dict(guide_vertex_count=len(vertices), guide_triangle_count=len(faces), sample_grid=list(depth.shape),
                  contour_threshold_above_field_mm=.22, raw_enamel_datum_mm=field,
                  landmarks=landmarks, star_phase_rad=phase,
                  outline_fairing_mm=stats(abs(outline-outline_raw)),
                  noise_only_displacement_mm=stats(residual[~pinned]), pinned_displacement_mm=stats(residual[pinned]),
                  per_feature_noise_mm={str(i): stats(residual[labels == i]) for i in np.unique(labels)},
                  rim_correction_knots_radius_depth_mm=np.c_[knots_r,knots_d].tolist(),
                  decisions=[
                      'Retain the actual generated triangles in GuideFaired, with patch-restricted Taubin fairing and pinned feature curves. No dense reprojection.',
                      'Corrected bake surface uses guide-derived continuous rim and star contour strips. Their samples retain guide triangle IDs; the raw faceting is not a manufacturing finish.',
                      'Recess enamel to 1.00 mm and compress generated star heights to a 2.20 mm maximum, preserving 1.20 mm relief rather than the old 0.65 mm.',
                      'Turn the irregular rim circular at measured feature radii; separately report manufacturing correction versus noise-only displacement.',
                      'Add two 0.26 mm-wide, 0.16 mm-deep lathe grooves and 0.14 mm star edge finishing as deliberate concept-guided details.',
                      'Widen the generated suspension to the frozen sewn-ribbon envelope. Preserve the tilted thin rear return; use rounded visible section rather than a rectangular outline.',
                      'Use twenty adaptive star-boundary samples pinned to the actual five tips and valleys, inserting the largest remaining contour-error points rather than sampling a regular polygon.',
                      'Triangulate the enamel as a constrained polygon with a real star-shaped hole. Index-based annulus bridging can cross a concave star even when the solid is watertight.',
                      'Prioritize the visible face in the 2048 UV atlas: scale the hidden reverse chart to 0.55 relative density, retaining measured 16-texel minimum gutters.',
                      'Fuse the strap cap 0.08 mm farther into the formed front crossbar, so the rounded cap junction has overlapping solid metal rather than a grazing trim.',
                      'Stage one only: no normal/AO/ORM bake, mounting, runtime shader, production export or test changes.'
                  ])
    (out / 'feature-fit.json').write_text(json.dumps(report, indent=2))
    print('FEATURE FIT COMPLETE', report['noise_only_displacement_mm'])


if __name__ == '__main__':
    fit(Path(sys.argv[1]))
