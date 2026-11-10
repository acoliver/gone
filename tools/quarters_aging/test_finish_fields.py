"""Physical-space corrosion controls, independent of Blender and the pilot atlas."""
import unittest
import numpy as np
from finish_fields import gravity_runs, corrosion_field
from colour import linear, delta_e_2000, lab


class FinishFieldTests(unittest.TestCase):
    def test_trail_runs_down_not_sideways_or_through_the_prop(self):
        p = np.array([[0, -.3, .95], [.02, -.3, .95], [0, -.3, 1.02], [0, .3, .95]])
        n = np.tile([0, -1, 0], (4, 1))
        sources = [dict(position_blender=[0, -.3, 1], width_m=.011, length_m=.14)]
        run = gravity_runs(p, n, sources, 9501)
        self.assertGreater(run[0], .7)
        np.testing.assert_array_equal(run[1:], 0)

    def test_trails_have_no_wide_vent_centre_source(self):
        p = np.array([[x, -.3, .92] for x in np.linspace(-.04, .04, 81)])
        n = np.tile([0, -1, 0], (81, 1))
        source = dict(position_blender=[0, -.3, 1], width_m=.011, length_m=.14)
        trail = gravity_runs(p, n, [source], 9501)
        self.assertLessEqual(np.count_nonzero(trail > .4) * .001, .015)
        self.assertGreaterEqual(np.count_nonzero(trail > .4) * .001, .004)
        np.testing.assert_array_equal(trail, gravity_runs(p, n, [source], 9501))

    def test_edges_fail_before_broad_faces(self):
        rng = np.random.default_rng(9501)
        p = rng.random((20000, 3))
        edge = np.r_[np.full(10000, .005), np.full(10000, .10)]
        rust = corrosion_field(p, edge, np.zeros(20000), np.ones(20000), 9501)
        self.assertGreater((rust[:10000] > .5).mean(), (rust[10000:] > .5).mean() * 2.5)
        self.assertTrue(.08 <= (rust[10000:] > .5).mean() <= .25)

    def test_linear_light_and_ciede2000_reference_pair(self):
        np.testing.assert_allclose(linear(np.array([0., .5, 1.])), [0, .21404114, 1], atol=1e-7)
        self.assertAlmostEqual(float(delta_e_2000(np.array([50., 2.6772, -79.7751]), np.array([50., 0., -82.7485]))), 2.0425, places=4)
        self.assertAlmostEqual(float(delta_e_2000(lab(np.array([.4, .5, .4])), lab(np.array([.4, .5, .4])))), 0.)


if __name__ == '__main__':
    unittest.main()
