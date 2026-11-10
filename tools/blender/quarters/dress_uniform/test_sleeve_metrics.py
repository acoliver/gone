"""A sideways thin ellipse must not pass the camera-visible pressed-sleeve gate."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sleeve_metrics import section_ratio, pressed_sections


class SleeveSections(unittest.TestCase):
    def test_visible_flat_section_passes(self):
        t = np.linspace(0, 2*np.pi, 1000)
        points = np.c_[.05*np.cos(t), .01*np.sin(t), np.zeros(len(t))]
        self.assertLess(section_ratio(points, [0, 0, 1], [0, -1, 0])['ratio'], .45)

    def test_edge_on_flat_section_fails(self):
        t = np.linspace(0, 2*np.pi, 1000)
        points = np.c_[.01*np.cos(t), .05*np.sin(t), np.zeros(len(t))]
        self.assertGreater(section_ratio(points, [0, 0, 1], [0, -1, 0])['ratio'], .45)

    def test_sampling_density_does_not_change_extent(self):
        points = np.array([[.05, 0, 0], [0, .01, 0], [-.05, 0, 0], [0, -.01, 0]])
        biased = np.vstack([points, np.repeat(points[:1], 100, axis=0)])
        self.assertEqual(section_ratio(points, [0, 0, 1], [0, -1, 0]),
                         section_ratio(biased, [0, 0, 1], [0, -1, 0]))

    def test_perspective_uses_ray_to_each_section(self):
        count = 32
        vertices = np.array([(.05*np.cos(t), .01*np.sin(t), .5*s-.5)
                             for s in np.linspace(0, 1, 21)
                             for t in np.linspace(0, 2*np.pi, count, endpoint=False)])
        faces = []
        for row in range(20):
            for col in range(count):
                a, b = row*count+col, row*count+(col+1) % count
                faces += [(a, b, b+count), (a, b+count, a+count)]
        faces = np.array(faces)
        uv = np.empty((len(faces), 3, 2))
        uv[:, :, 0] = 1.25
        uv[:, :, 1] = (vertices[faces, 2]+.5)/.5
        eye = np.array([0., -.5, 0.])
        near = pressed_sections(vertices, faces, uv, eye)
        far = pressed_sections(vertices+np.array([1., 0., 0.]), faces, uv, eye)
        self.assertLess(near['ratio'], .45)
        self.assertGreater(far['ratio'], .45)


if __name__ == '__main__':
    unittest.main()
