"""Released sleeve cloth can fall without moving stitches or crushing its section."""
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aging_support import load_source
from aging_geometry import cut_tunic, detach_fallen
from pressed_pattern import released_cap_drop

body = load_source()
cut_tunic(body)
detach_fallen(body)
uv = body.data.uv_layers[0].data
cap = {loop.vertex_index for loop in body.data.loops if 1.099 < uv[loop.index].uv.x < 1.551}
retained = {loop.vertex_index for loop in body.data.loops
            if loop.vertex_index in cap and uv[loop.index].uv.x < 1.}
original = np.array([vertex.co[:] for vertex in body.data.vertices])
rest = body.shape_key_add(name='Control rest')
report = released_cap_drop(body, rest, sorted(cap), outward=0.)
points = np.array([point.co[:] for point in rest.data])
fixed = sorted(set(range(len(original)))-cap | retained)
np.testing.assert_array_equal(points[fixed], original[fixed])
np.testing.assert_array_equal(points[:, :2], original[:, :2])
lower = sorted(i for i in cap if original[i, 2] < -.60)
np.testing.assert_allclose(points[lower, 2]-original[lower, 2], -.06, atol=1e-7)
assert report['retained_vertices'] == len(retained)
assert np.isfinite(points).all()
print('PASS: underarm stitches and torso stay fixed; lower sleeve falls 60 mm without section collapse')
for point, source in zip(rest.data, original):
    point.co = source
released_cap_drop(body, rest, sorted(cap))
opened = np.array([point.co[:] for point in rest.data])
np.testing.assert_array_equal(opened[fixed], original[fixed])
np.testing.assert_array_equal(opened[:, 1], original[:, 1])
np.testing.assert_allclose(opened[lower, 0]-original[lower, 0], .025, atol=1e-7)
np.testing.assert_allclose(opened[lower, 2]-original[lower, 2], -.06, atol=1e-7)
print('PASS: released cap falls outward 25 mm while retained underarm stitches remain fixed')
