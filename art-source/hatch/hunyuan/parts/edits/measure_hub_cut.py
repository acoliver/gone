"""Solve the approved outermost planar cut using exact triangle sections."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.distance import pdist

import argparse
import sys
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = Path(__file__).resolve().parents[1]
ROOT = SOURCE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/blender'))
from hatch_fit import read_source_glb

measurements = json.loads((SOURCE / 'placements.json').read_text())['wheel']
nuts = json.loads((SOURCE / 'retention-nuts.json').read_text())
source = SOURCE / 'handwheel-s600.glb'
p, f = read_source_glb(source)
p[:, :2] -= measurements['source_center_xy']
p *= measurements['scale']
t = p[f]
hub_radius = measurements['hub_keep_radius_source'] * measurements['scale']
# Only triangles touching the retained central hub can define its dome section.
central = (np.linalg.norm(t[:, :, :2], axis=2) <= hub_radius).any(axis=1)
t = t[central]


def section(z):
    active = (t[:, :, 2].min(1) <= z) & (t[:, :, 2].max(1) >= z)
    tris = t[active]
    points = []
    for i, j in [(0, 1), (1, 2), (2, 0)]:
        a, b = tris[:, i], tris[:, j]
        crossing = (a[:, 2] < z) != (b[:, 2] < z)
        a, b = a[crossing], b[crossing]
        q = a + ((z - a[:, 2]) / (b[:, 2] - a[:, 2]))[:, None] * (b - a)
        q = q[np.linalg.norm(q[:, :2], axis=1) <= hub_radius]
        points.extend(q)
    q = np.asarray(points)
    if len(q) < 3:
        return q, 0.
    hull = q[ConvexHull(q[:, :2]).vertices]
    return q, float(pdist(hull[:, :2]).max())


nut = np.asarray(nuts['rows'][0]['points_part_local']) * (.643 / .888)
across = float(pdist(nut[:, [0, 2]]).max())
tip = float(t[:, :, 2].max())
# Locate the highest crossing, then solve that bracket. This scans only the
# newly authorized hub cut, not any settled placement or clearance decision.
planes = np.linspace(tip - 1e-9, float(t[:, :, 2].min()) + 1e-9, 2049)
previous = planes[0]
for plane in planes[1:]:
    _, width = section(plane)
    if width >= across:
        lo, hi = plane, previous
        break
    previous = plane
else:
    raise RuntimeError('retained hub never reaches the scaled nut width')
for _ in range(48):
    mid = (lo + hi) / 2
    if section(mid)[1] >= across:
        lo = mid
    else:
        hi = mid
seat = (lo + hi) / 2
q, diameter = section(seat)
# Match the unchanged hub test's >=85mm surrounding-shoulder radial selection.
# Clipping creates edge-plane vertices as well as retaining original ones.
kept = p[(p[:, 2] <= seat) & (np.linalg.norm(p[:, :2], axis=1) <= hub_radius)]
shoulder = kept[np.linalg.norm(kept[:, :2], axis=1) >= .085]
shoulder_z = float(shoulder[:, 2].max())
rows = []
for row in nuts['rows']:
    n = np.asarray(row['points_part_local']) * (.643 / .888)
    stations = np.unique(np.round(n[:, 1], 9))
    thickness = float(np.ptp(n[:, 1]))
    front = n[abs(n[:, 1] - n[:, 1].max()) < 1e-6]
    rows.append(dict(door=row['door'], path=row['path'], across_corners_m=across,
        cut_plane_z_m=seat, cut_depth_m=tip-seat,
        section_diameter_m=diameter, outward_section_diameter_m=section(seat+1e-6)[1],
        section_xy_spans_m=np.ptp(q[:, :2], axis=0).tolist(),
        retained_front_z_m=seat, nut_back_z_m=seat, nut_front_z_m=seat+thickness,
        nut_thickness_m=thickness, chamfer_m=float(stations[1]-stations[0]),
        front_corner_directions=len(np.unique(np.round(np.arctan2(front[:, 2], front[:, 0])*10000))),
        axial_stations=len(stations), shoulder_front_outward_z_m=shoulder_z,
        nut_relief_m=seat+thickness-shoulder_z))
    print('HUB_CUT', json.dumps(rows[-1]), flush=True)
result = dict(source=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    wheel_scale=measurements['scale'], scaled_hub_radius_m=hub_radius,
    source_outward_tip_z_m=tip, section_points=len(q),
    section_definition='maximum chord of the exact hub triangle/plane intersection', rows=rows)
(OUT / 'hub-cut.json').write_text(json.dumps(result, indent=2)+'\n')
np.savez_compressed(OUT / 'hub-cut-input.npz', vertices=p, faces=f, section=q, nut=nut)
