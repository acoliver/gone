"""Controls for the aged-only finishing fields."""
import unittest
import numpy as np
from refinement_fields import convex_outline, powder_field, cloth_color, powder_normals, without_foot_corner, fringe_groups
from powder_visibility import visible_fraction
from PIL import Image
import trimesh


class RefinementTests(unittest.TestCase):
    def test_outline_retains_the_existing_plate_footprint(self):
        points = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [.5, .5], [0, 0]])
        outline = convex_outline(points)
        self.assertEqual(len(outline), 4)
        following = np.roll(outline, -1, axis=0)
        area = (outline[:, 0] * following[:, 1] - outline[:, 1] * following[:, 0]).sum() / 2
        self.assertAlmostEqual(area, 1)

    def test_missing_crust_corner_is_a_clipped_closed_footprint(self):
        outline = np.array([[.3, -1.], [.7, -1.], [.7, -.6], [.3, -.6]])
        clipped = without_foot_corner(outline)
        self.assertTrue(np.all(clipped[:, 0] - clipped[:, 1] <= 1.35 + 1e-12))
        following = np.roll(clipped, -1, axis=0)
        area = (clipped[:, 0] * following[:, 1] - clipped[:, 1] * following[:, 0]).sum() / 2
        self.assertAlmostEqual(area, .4 * .4 - .35 * .35 / 2)
        np.testing.assert_array_equal(without_foot_corner(outline - [1, 0]), outline - [1, 0])

    def test_powder_has_a_deposit_and_a_soft_empty_margin(self):
        alpha = powder_field(95246, 256)
        y, x = np.mgrid[-1:1:256j, -1:1:256j]
        radius = np.hypot(x, y)
        self.assertGreater(alpha[radius < .45].mean(), .35)
        self.assertLess(alpha[radius > .96].max(), .01)
        self.assertGreater(np.mean((alpha > .05) & (alpha < .8)), .2)
        np.testing.assert_array_equal(alpha, powder_field(95246, 256))

    def test_powder_normal_uses_both_physical_texel_pitches(self):
        height = np.broadcast_to(np.linspace(0, .001, 32), (16, 32))
        normal = powder_normals(height, (.5, .25))
        expected = np.array([-.001, 0., 1.])
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(normal, np.broadcast_to(expected, normal.shape), atol=1e-12)
        self.assertGreater(normal[:, :, 2].min(), .999)
        narrow = powder_normals(height, (.001, .25))
        self.assertAlmostEqual(narrow[0, 0, 0], -.5 / np.sqrt(1.25))

    def test_powder_visibility_rejects_an_occluded_card(self):
        visual = trimesh.visual.TextureVisuals(
            uv=[[0, 0], [1, 0], [1, 1], [0, 1]],
            material=trimesh.visual.material.PBRMaterial(baseColorTexture=Image.new('RGBA', (4, 4), 'white')))
        card = trimesh.Trimesh(vertices=[[-.2, 0, -.2], [.2, 0, -.2], [.2, 0, .2], [-.2, 0, .2]],
                               faces=[[0, 1, 2], [0, 2, 3]], visual=visual, process=False)
        support = trimesh.creation.box(extents=[2, .1, 2])
        support.apply_translation([0, -.1, 0])
        camera = np.array([0., 2., .01])
        self.assertEqual(visible_fraction(card, support, camera, False, np.random.default_rng(95)), 1.)
        support.apply_translation([0, 1, 0])
        self.assertEqual(visible_fraction(card, support, camera, False, np.random.default_rng(95)), 0.)

    def test_fringe_roots_survive_small_mips_without_a_solid_tip(self):
        alpha = fringe_groups(95264, width=128, height=32)
        mip = alpha.reshape(8, 4, 8, 4, 32).mean(axis=(2, 4))
        self.assertGreater(mip[:, 0, :].min(), .65)
        self.assertLess(mip[:, -1, :].mean(), .2)
        np.testing.assert_array_equal(alpha, fringe_groups(95264, width=128, height=32))

    def test_baked_pigment_variation_remains_visible_under_top_dust(self):
        color = cloth_color(np.ones(2), np.ones(2), np.array([.2, .8]))
        self.assertGreater(color[1, 0] / color[0, 0], 1.5)

    def test_folds_dark_and_dust_on_upward_faces_without_cream(self):
        color = cloth_color(np.array([0., 1., 1.]), np.array([0., 0., 1.]),
                            np.array([.5, .5, .5]), wool=False)
        self.assertTrue(np.all(color[0] < color[1]))
        self.assertGreater(color[2].mean(), color[1].mean())
        self.assertLess(color.max(), .26)
        self.assertTrue(np.all(color[:, 0] > color[:, 1]))
        self.assertTrue(np.all(color[:, 1] > color[:, 2]))


if __name__ == '__main__':
    unittest.main()
