"""Independent exported geometry and native legend regression checks (#129)."""
import json
from pathlib import Path
import unittest

import numpy as np
from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


class ConsoleTests(unittest.TestCase):
    def test_taller_display_and_support_stay_fixed_with_reused_keyboard(self):
        scene = trimesh.load(ROOT / 'assets/props/quarters/console.glb', force='scene')
        matrix, geometry = scene.graph['Display']
        size = scene.geometry[geometry].extents
        np.testing.assert_allclose(size, [.874, .54625, .004], atol=1e-6)
        # The lower glass edge, tilt and complete key deck stay at their accepted pose.
        bottom = matrix @ [0, -size[1]/2, 0, 1]
        np.testing.assert_allclose(bottom[:3], [0, .454878712, .062092286], atol=1e-6)
        self.assertGreater(matrix[2, 2], .85)
        self.assertGreater(matrix[1, 2], .5)
        # #129 replaces the inset 4x6 grid and detached toggles with the power-room unit.
        self.assertFalse(any(n.startswith(('Key_', 'Toggle')) for n in scene.graph.nodes))
        _, support = scene.graph['DesktopSupport']
        np.testing.assert_allclose(scene.geometry[support].bounds,
                                   [[-.342223912, .018, -.204474777], [.342223912, .32, .15447478]], atol=1e-6)
        keyboard = trimesh.load(ROOT / 'assets/props/quarters/console_keyboard.glb', force='scene')
        original = trimesh.load(ROOT / 'assets/props/terminal/keyboard.glb', force='scene')
        actual = keyboard.geometry[keyboard.graph['Keyboard'][1]]
        source = original.geometry[original.graph['Keyboard'][1]]
        # Blender can split render vertices at normal seams on import/export.
        # Compare every indexed triangle and UV corner, not render indexing.
        np.testing.assert_array_equal(actual.triangles, source.triangles)
        np.testing.assert_array_equal(actual.visual.uv[actual.faces], source.visual.uv[source.faces])
        self.assertLessEqual(len(actual.faces), 30000)
        frame = np.linalg.inv(scene.graph['ControlPanel'][0]) @ keyboard.graph['Keyboard'][0]
        points = trimesh.transform_points(actual.vertices, frame)
        # Same 0.66002786 installed scale as power room, with 10 mm front margin.
        self.assertAlmostEqual(np.linalg.norm(frame[:3, 0]), .6600278615951538, places=6)
        self.assertAlmostEqual(np.ptp(points[:, 0]), 0.5278933544969685, places=6)
        self.assertAlmostEqual(points[:, 0].min() + points[:, 0].max(), 0, places=5)
        self.assertGreaterEqual(points[:, 2].min(), -.11184864)
        self.assertAlmostEqual(.11184864 - points[:, 2].max(), .010, places=5)
        self.assertGreaterEqual(points[:, 1].min(), .009 - 1e-7)
        self.assertLess(points[:, 1].min() - .009, .001)


    def test_trimmed_top_bar_preserves_glass_gap_and_side_rail_contact(self):
        scene = trimesh.load(ROOT / 'assets/props/quarters/console.glb', force='scene')
        frame, key = scene.graph['BezelTop']
        bar = scene.geometry[key]
        np.testing.assert_allclose(bar.extents, [.89, .012, .030], atol=1e-6)
        display, key = scene.graph['Display']
        glass = scene.geometry[key]
        relative = np.linalg.inv(display) @ frame
        gap = relative[1, 3] - bar.extents[1]/2 - glass.extents[1]/2
        self.assertAlmostEqual(gap, .001, places=6)
        for name, sign in [('BezelLeft', -1), ('BezelRight', 1)]:
            side, key = scene.graph[name]
            point = trimesh.transform_points([[sign*bar.extents[0]/2, 0, 0]], np.linalg.inv(side) @ frame)
            distance = trimesh.proximity.closest_point(scene.geometry[key], point)[1]
            self.assertLess(float(distance[0]), 1e-6, name)
        _, key = scene.graph['ArmouredHousing']
        housing = scene.geometry[key].copy()
        # glTF splits shared positions at UV seams and normal boundaries.
        housing.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=7)
        self.assertTrue(housing.is_watertight and housing.is_winding_consistent)
        self.assertGreater(housing.volume, 0)
        self.assertAlmostEqual(float(housing.bounds[1, 1]), .9388873216880659, places=6)

    def test_every_key_has_native_ink_in_both_state_atlases(self):
        mapping = json.loads((ROOT / 'assets/props/quarters/steel/console_keyboard/mapping.json').read_text())
        legends = mapping['native_legends']
        self.assertEqual(len(legends), 29) # #129: the reused power-room mesh has 29 caps.
        self.assertEqual([r['input'] for r in legends[:8]], list('01234567'))
        for state in ('as_built', 'aged'):
            image = np.asarray(Image.open(ROOT / f'assets/props/quarters/steel/console_keyboard/{state}_albedo.png'))
            for row in legends:
                x, y = row['ink_probe_pixel']
                self.assertTrue(45 <= int(image[y, x, :3].mean()) <= 120, f'{state} {row["key"]}')
                self.assertGreaterEqual(row['ink_texels'], 100, row['key'])
                self.assertIn(row['sign'], json.loads((HERE / 'legends.json').read_text())['syllables'])

    def test_printed_legends_fit_cap_height_without_dominating_it(self):
        mapping = json.loads((ROOT / 'assets/props/quarters/steel/console_keyboard/mapping.json').read_text())
        images = {state: np.asarray(Image.open(ROOT / f'assets/props/quarters/steel/console_keyboard/{state}_albedo.png'))
                  for state in ('as_built', 'aged')}
        for row in mapping['native_legends']:
            x0, y0, x1, y1 = row['interior_rect_px']
            left, top, right, bottom = row['ink_bounds_px']
            self.assertTrue(.35 <= (bottom-top)/(y1-y0) <= .46, row['key'])
            self.assertLessEqual(right-left, (x1-x0)*.92, row['key'])
            self.assertAlmostEqual((left+right)/2, (x0+x1)/2, delta=1)
            self.assertAlmostEqual((top+bottom)/2, (y0+y1)/2, delta=1)
            for state, image in images.items():
                x, y = row['ink_probe_pixel']
                contrast = image[y, x, :3].astype(float) - row['unprinted_probe_srgb'][state]
                self.assertTrue(np.all(contrast > 0), (state, row['key']))
                self.assertLessEqual(float(contrast.max()), 36, (state, row['key']))

    def test_sealed_storage_finish_has_bounded_variation_and_dust(self):
        from bake_legends import sealed_storage
        clean = np.array([[[84, 90, 58], [255, 255, 230], [0, 0, 0]],
                          [[42, 44, 46], [120, 120, 120], [30, 30, 30]]], float)
        positions = np.zeros((2, 3, 3))
        case = np.array([[True, True, True], [False, False, False]])
        aged = sealed_storage(clean, positions, case)
        # Housing retains the source chips; only polymer receives bounded aging.
        np.testing.assert_array_equal(aged[case], clean[case])
        self.assertLessEqual(float(np.ptp(aged[~case], axis=0).max()), 5)
        self.assertTrue(np.all(aged[~case].mean(0) > clean[1, 0]))
        self.assertTrue(np.all(aged >= 0) and np.all(aged <= 255))
        np.testing.assert_array_equal(aged, sealed_storage(clean, positions, case))

    def test_olive_tinted_polymer_keeps_d203221_finish(self):
        from bake_legends import sealed_storage
        clean = np.array([[[84, 90, 58], [255, 255, 200], [0, 0, 0]]], float)
        aged = sealed_storage(clean, np.zeros_like(clean), np.zeros((1, 3), bool))
        np.testing.assert_allclose(aged[0, 0], [86.6688, 91.7584, 61.776])
        np.testing.assert_allclose(aged[0, 1], [88.8768, 93.9664, 63.984])
        self.assertTrue(np.all(aged[0, 2] > clean[0, 2]))

    def test_remembered_housing_reduces_chip_and_oxide_masks_only(self):
        from bake_legends import cleaner_housing
        colour = np.array([[[80, 85, 55], [128, 125, 108], [105, 76, 47], [42, 44, 46]]], float)
        orm = np.array([[[220, 153, 45], [190, 122, 198], [180, 140, 89], [210, 204, 0]]], np.uint8)
        clean, material = cleaner_housing(colour, orm)
        np.testing.assert_array_equal(clean[0, [0, 3]], colour[0, [0, 3]])
        np.testing.assert_allclose(clean[0, 1], colour[0, 0]*.75 + colour[0, 1]*.25)
        np.testing.assert_allclose(clean[0, 2], colour[0, 0]*.75 + colour[0, 2]*.25)
        np.testing.assert_array_equal(material[..., 0], orm[..., 0])
        np.testing.assert_array_equal(material[0, [0, 3]], orm[0, [0, 3]])
        np.testing.assert_array_equal(material[0, 1, 1:], [145, 83])
        np.testing.assert_array_equal(material[0, 2, 1:], [150, 56])

    def test_housing_finishes_preserve_power_room_atlas_detail(self):
        terminal = ROOT / 'assets/props/terminal'
        atlas = ROOT / 'assets/props/quarters/steel/console_keyboard'
        source = {kind: np.asarray(Image.open(terminal / f'keyboard_keyboard_{kind}.png').convert('RGB'))
                  for kind in ('albedo', 'normal', 'orm')}
        # The source baker assigns nonzero metal to every housing texel, including
        # exposed chips/oxide and padding, and zero metal to caps and membrane.
        housing = source['orm'][..., 2] > 0
        self.assertGreater(int(housing.sum()), 100000)
        self.assertTrue(np.any(source['orm'][housing, 2] > 190))
        self.assertTrue(np.any(source['orm'][housing, 2] == 89))
        worn = housing & (source['orm'][..., 2] != 45)
        for state in ('as_built', 'aged'):
            for kind, expected in source.items():
                actual = np.asarray(Image.open(atlas / f'{state}_{kind}.png').convert('RGB'))
                unchanged = housing if state == 'aged' or kind == 'normal' else housing & ~worn
                np.testing.assert_array_equal(actual[unchanged], expected[unchanged], err_msg=f'{state} {kind}')
                if state == 'as_built' and kind in ('albedo', 'orm'):
                    from scipy.ndimage import distance_transform_edt
                    nearest = distance_transform_edt(source['orm'][..., 2] != 45,
                                                     return_distances=False, return_indices=True)
                    restored = expected[tuple(nearest[:, worn])].astype(float)*.75 + expected[worn]*.25
                    if kind == 'orm':
                        restored[:, 0] = expected[worn, 0]
                    np.testing.assert_array_equal(actual[worn], np.round(restored).astype(np.uint8))
                    if kind == 'albedo':
                        self.assertEqual(int(np.any(actual[worn] != expected[worn], axis=1).sum()), int(worn.sum()))
                        self.assertGreater(float(actual[housing].std()), 5)
        regions = np.asarray(Image.open(atlas / 'regions.png').convert('RGB'))
        # No procedural paint grain or roughness floor may mask the source housing.
        np.testing.assert_array_equal(regions[housing], 0)


if __name__ == '__main__':
    unittest.main()
