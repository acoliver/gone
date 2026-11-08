"""Camera-gate regressions independent of the Blender runtime."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_pass8_accept import box_walls, project


class CameraGateTests(unittest.TestCase):
    def test_upright_boxing_is_counted(self):
        vertices = np.array([[-.2, -.3, .4], [.2, -.3, .4], [.2, -.3, .57], [-.2, -.3, .57]])
        result = box_walls(vertices, [[0, 1, 2], [0, 2, 3]])
        self.assertTrue(result.all())

    def test_front_skirt_below_deck_is_not_boxing(self):
        vertices = np.array([[-.2, -.3, .22], [.2, -.3, .22], [.2, -.3, .43], [-.2, -.3, .43]])
        result = box_walls(vertices, [[0, 1, 2], [0, 2, 3]])
        self.assertFalse(result.any())

    def test_shallow_slack_fold_is_not_a_box_wall(self):
        vertices = np.array([[-.2, -.3, .4], [.2, -.3, .4], [.2, -.3, .43], [-.2, -.3, .43]])
        result = box_walls(vertices, [[0, 1, 2], [0, 2, 3]])
        self.assertFalse(result.any())

    def test_fixed_camera_target_projects_to_image_centre(self):
        camera = dict(eye_blender_m=[0, -3, .8], target_blender_m=[0, 0, .4],
                      resolution=[1600, 1422], scale=2.85)
        np.testing.assert_allclose(project(np.array([[0, 0, .4]]), camera), [[800, 711]])


if __name__ == '__main__':
    unittest.main()
