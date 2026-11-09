"""Cap clearance measures the typical opening, not one outlying wide sample."""
import numpy as np

from opening_audit import armhole_gap

body = np.array([[.18, 0., -.20], [.22, 0., -.20], [.20, 0., -.23]])
faces = np.array([[0, 1, 2], [3, 4, 5]])
uv = np.array([[[.5, .8], [.5, .9], [.6, .8]],
               [[1.2, 0.], [1.3, 0.], [1.4, 0.]]])
for gap, expected in ((.012, False), (.030, True)):
    vertices = np.vstack([body, body+[0., gap, 0.]])
    report = armhole_gap(vertices, faces, uv)
    np.testing.assert_allclose(report['median_clear_gap_m'], gap, atol=1e-12)
    assert report['pass_gap'] is expected, report
print('PASS: 12 mm cap gap fails and 30 mm cap gap passes the unchanged 25 mm requirement')
