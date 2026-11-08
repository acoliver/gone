"""Physical wear and capture controls for the locker's close-range finish."""
import unittest

import numpy as np

from locker_swatches import edge_reach
from streak_sources import source_rows
from visibility_gates import trail_metrics, boundary_orientation


class LockerPass4Tests(unittest.TestCase):
    def test_edge_reach_is_mostly_five_to_twenty_five_mm(self):
        reference = np.repeat(np.linspace(.2, .5, 100).reshape(10, 10, 1), 3, axis=2)
        reach = edge_reach(reference.reshape(-1, 3), reference)
        self.assertGreaterEqual(float(reach.min()), .005)
        self.assertLessEqual(float(np.quantile(reach, .95)), .025001)

    def test_runoff_lengths_vary_threefold_and_low_fasteners_are_faint(self):
        sources = [dict(part='Rivets', position_blender=[i * .03, -.3, z])
                   for i, z in enumerate(np.linspace(.2, 2.3, 60))]
        _, shape = source_rows(sources, 9501)
        self.assertGreater(float(shape[:, 0].max() / shape[:, 0].min()), 2.8)
        self.assertLess(float(shape[:8, 1].mean()), float(shape[-8:, 1].mean()) * .6)

    def test_trail_requires_continuous_forty_mm_and_near_source_start(self):
        image = np.full((160, 80, 3), [.48, .54, .51])
        image[5:65, 37:43] = [.42, .20, .08]
        receiver = np.ones((160, 80), bool)
        result = trail_metrics(image, receiver, 40, 0, 1000)
        self.assertTrue(result['passed'])
        self.assertGreaterEqual(result['length_m'], .04)
        image[:40] = [.48, .54, .51]
        self.assertFalse(trail_metrics(image, receiver, 40, 0, 1000)['passed'])

    def test_trail_rejects_wide_smear_and_invisible_colour(self):
        receiver = np.ones((160, 80), bool)
        image = np.full((160, 80, 3), [.48, .54, .51])
        image[5:90, 10:70] = [.42, .20, .08]
        self.assertFalse(trail_metrics(image, receiver, 40, 0, 1000)['passed'])
        image[:] = [.43, .21, .09]
        image[5:90, 37:43] = [.42, .20, .08]
        self.assertFalse(trail_metrics(image, receiver, 40, 0, 1000)['passed'])

    def test_hinge_outlet_stays_on_the_lower_hardware_edge(self):
        from streak_sources import outlet_position
        source = dict(part='Hinges', position_blender=[-.260, -.301, 2.110],
                      bounds_blender=[[-.270, -.311, 2.110], [-.250, -.291, 2.190]])
        np.testing.assert_allclose(outlet_position(source), [-.245, -.301, 2.110])
        self.assertLess(abs(outlet_position(source)[0] - source['bounds_blender'][1][0]), .010)

    def test_isolated_runoff_control_cannot_make_an_invisible_trail_pass(self):
        image = np.full((160, 80, 3), [.48, .54, .51])
        control = np.zeros((160, 80))
        control[5:100, 37:43] = .8
        self.assertFalse(trail_metrics(image, np.ones_like(control, bool), 40, 0, 1000, control)['passed'])

    def test_disconnected_neighbouring_spots_are_not_a_trail(self):
        image = np.full((160, 80, 3), [.48, .54, .51])
        for y in range(5, 100):
            image[y, 37 if y % 2 else 43] = [.42, .20, .08]
        self.assertFalse(trail_metrics(image, np.ones((160, 80), bool), 40, 0, 1000)['passed'])

    def test_orientation_gate_rejects_atlas_stair_steps(self):
        yy, xx = np.indices((512, 512))
        stair = xx < (180 + (yy // 16) * 4)
        self.assertGreater(boundary_orientation(stair.astype(float), np.ones_like(stair))[0], 2)

    def test_orientation_gate_accepts_round_boundaries(self):
        yy, xx = np.indices((512, 512))
        circles = np.zeros_like(xx, bool)
        for x, y in [(130, 130), (360, 160), (240, 370)]:
            circles |= (xx - x)**2 + (yy - y)**2 < 75**2
        self.assertLess(boundary_orientation(circles.astype(float), np.ones_like(circles))[0], 2)


if __name__ == '__main__':
    unittest.main()
