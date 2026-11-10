"""Background Blender control for empty pressed structural and bending sleeve rest."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_geometry import cut_tunic, detach_fallen, pressed_sleeve, refine
from aging_support import load_source
from common import recalc

body = load_source()
refine(body)
cut_tunic(body)
detach_fallen(body)
uv = body.data.uv_layers[0].data
coordinates = {}
for loop in body.data.loops:
    point = uv[loop.index].uv
    if 1.099 < point.x < 1.551:
        old = coordinates.get(loop.vertex_index)
        if old is None or point.x < old[0]:
            coordinates[loop.vertex_index] = tuple(point)
sleeve = np.array(sorted(coordinates))
pattern = np.array([coordinates[index] for index in sleeve])
original = np.array([v.co[:] for v in body.data.vertices])
rest = pressed_sleeve(body)
recalc(body)
actual = np.array([v.co[:] for v in body.data.vertices])
bending = np.array([v.co[:] for v in rest.data])
ids = sleeve[(original[sleeve, 2] < -.60) & (original[sleeve, 2] > -.70)]
assert len(ids) > 10
np.testing.assert_allclose(actual[ids], bending[ids], atol=1e-7)
angle = np.arctan2(.3, .9)
rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
measurements = []
for station in np.unique(np.round(pattern[:, 1], 6)):
    row = np.flatnonzero(np.round(pattern[:, 1], 6) == station)
    if not (-.70 < original[sleeve[row], 2].mean() < -.60):
        continue
    _, first = np.unique(np.round(pattern[row, 0], 6), return_index=True)
    indices = sleeve[row[first]]
    before = original[indices, :2]
    after = actual[indices, :2]@rotation
    old_perimeter = np.linalg.norm(np.roll(before, -1, axis=0)-before, axis=1).sum()
    perimeter = np.linalg.norm(np.roll(after, -1, axis=0)-after, axis=1).sum()
    depth = np.ptp(after[:, 1])
    assert depth <= .01201, f'Pressed sleeve remains an oval tube: {depth} m depth'
    assert abs(perimeter/old_perimeter-1) <= .05, (perimeter, old_perimeter)
    measurements.append((depth, perimeter/old_perimeter))
assert measurements
assert np.isfinite(actual).all() and np.isfinite(bending).all()
print('PASS: structural and bending rest agree, broad pressed faces retain sleeve perimeter', measurements, flush=True)
