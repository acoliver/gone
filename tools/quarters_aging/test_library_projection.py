"""Round rails must not restart a complete corrosion image on every facet."""
import unittest

import numpy as np

from library_projection import cylinders, cylindrical_frame, is_disc, disc_to_square, DISC_SOURCE_SCALE


def round_rail():
    angles = np.arange(32)*2*np.pi/32
    vertices = np.stack([np.cos(angles)*.02, np.sin(angles)*.02, np.zeros(32)], -1)
    faces = []
    for index in range(32):
        a, b = vertices[index], vertices[(index+1)%32]
        c, d = b+[0, 0, .5], a+[0, 0, .5]
        faces.append(dict(part='Rail', triangles=[[a.tolist(), b.tolist(), c.tolist()],
                                                  [a.tolist(), c.tolist(), d.tolist()]]))
    return faces


class DiscProjectionTests(unittest.TestCase):
    def test_circle_boundary_maps_to_the_full_image_border(self):
        angles = np.linspace(0, 2*np.pi, 257)
        circle = .5+.5*np.stack([np.cos(angles), np.sin(angles)], -1)
        mapped = disc_to_square(circle)
        np.testing.assert_allclose(np.max(np.abs(mapped-.5), axis=1), .5)
        np.testing.assert_allclose(disc_to_square(np.array([[.5, .5]])), [[.5, .5]])
        self.assertTrue(np.isfinite(mapped).all())

    def test_ellipses_are_recognised_but_box_corners_are_not(self):
        angles = np.arange(96)*2*np.pi/96
        ellipse = .5+.5*np.stack([np.cos(angles), np.sin(angles)], -1)
        self.assertTrue(is_disc(ellipse, [2, 1], np.pi/2))
        self.assertFalse(is_disc([[0, 0], [0, 1], [1, 1], [1, 0]], [1, 1], 1))
        self.assertFalse(is_disc([[0, 0], [1, 0], [0, 1]], [1, 1], .5))

    def test_source_density_bound_covers_projection_contraction(self):
        singular_values = []
        for angle in np.linspace(.001, np.pi/4-.001, 257):
            point = np.array([.5+.3*np.cos(angle), .5+.3*np.sin(angle)])
            epsilon = 1e-7
            jacobian = np.stack([(disc_to_square(point+offset)-disc_to_square(point-offset))/(2*epsilon)
                                 for offset in np.eye(2)*epsilon], axis=-1)
            singular_values.append(np.linalg.svd(jacobian, compute_uv=False).min())
        self.assertGreaterEqual(min(singular_values), DISC_SOURCE_SCALE-1e-6)
        self.assertAlmostEqual(min(singular_values), DISC_SOURCE_SCALE, places=5)


class CylinderProjectionTests(unittest.TestCase):
    def test_round_rail_shares_one_circumference_and_axial_frame(self):
        faces = round_rail()
        result = cylinders(faces)
        self.assertEqual(set(result), {'Rail'})
        for face in faces:
            points = np.array(face['triangles']).reshape(-1, 3)
            uv, size = cylindrical_frame(points, result['Rail'])
            np.testing.assert_allclose(size, [2*np.pi*.02, .5], atol=1e-8)
            self.assertLess(np.ptp(uv[..., 0]), .04)
            np.testing.assert_allclose(np.ptp(uv[..., 1]), 1)

    def test_rotated_rail_retains_physical_circumference(self):
        faces = round_rail()
        rotation = np.array([[1., 0., 0.], [0., .8, -.6], [0., .6, .8]])
        for face in faces:
            face['triangles'] = (np.array(face['triangles']) @ rotation.T+[.2, -.4, .1]).tolist()
        frame = cylinders(faces)['Rail']
        self.assertAlmostEqual(abs(np.dot(frame['axis'], rotation[:, 2])), 1)
        _, size = cylindrical_frame(np.array(faces[0]['triangles']).reshape(-1, 3), frame)
        np.testing.assert_allclose(size, [2*np.pi*.02, .5], atol=1e-8)

    def test_angular_seam_interpolates_across_short_arc(self):
        frame = cylinders(round_rail())['Rail']
        angles = np.array([-.01, .01, .02])
        # This frame's seam is aligned with its negative horizontal basis.
        delta = -np.cos(angles)[:, None]*frame['horizontal']+np.sin(angles)[:, None]*frame['vertical']
        points = frame['centre']+delta*.02
        uv, _ = cylindrical_frame(points, frame)
        self.assertLess(np.ptp(uv[..., 0]), .02)

    def test_box_is_not_a_round_rail(self):
        vertices = np.array([[x, y, z] for x in (-.02, .02) for y in (-.02, .02) for z in (0, .5)])
        triangles = vertices[[[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5]]]
        self.assertEqual(cylinders([dict(part='Stile', triangles=triangles.tolist())]), {})


if __name__ == '__main__':
    unittest.main()
