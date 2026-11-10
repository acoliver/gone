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
    def test_display_is_16_by_10_without_moving_keyboard_or_support(self):
        scene = trimesh.load(ROOT / 'assets/props/quarters/console.glb', force='scene')
        matrix, geometry = scene.graph['Display']
        size = scene.geometry[geometry].extents
        np.testing.assert_allclose(size, [.874, .54625, .004], atol=1e-6)
        # The lower glass edge, tilt and complete key deck stay at their accepted pose.
        bottom = matrix @ [0, -size[1]/2, 0, 1]
        np.testing.assert_allclose(bottom[:3], [0, .454878712, .062092286], atol=1e-6)
        self.assertGreater(matrix[2, 2], .85)
        self.assertGreater(matrix[1, 2], .5)
        for row, y in enumerate((-.0675, -.0225, .0225, .0675)):
            for col in range(6):
                frame, key = scene.graph[f'Key_{row}_{col}']
                np.testing.assert_allclose(scene.geometry[key].extents, [.073, .014, .034], atol=1e-6)
                control, _ = scene.graph['ControlPanel']
                np.testing.assert_allclose(frame[:3, 3], (control @ [-.425+col*.105, .016, -y, 1])[:3], atol=1e-6)
        _, support = scene.graph['DesktopSupport']
        np.testing.assert_allclose(scene.geometry[support].bounds,
                                   [[-.342223912, .018, -.204474777], [.342223912, .32, .15447478]], atol=1e-6)
        self.assertEqual(len([n for n in scene.graph.nodes_geometry if n.startswith('Toggle_')]), 3)

    def test_every_key_has_native_ink_in_both_state_atlases(self):
        mapping = json.loads((ROOT / 'assets/props/quarters/steel/console/mapping.json').read_text())
        legends = mapping['native_legends']
        self.assertEqual(len(legends), 24)
        self.assertEqual([r['input'] for r in legends[:8]], list('01234567'))
        for state in ('as_built', 'aged'):
            image = np.asarray(Image.open(ROOT / f'assets/props/quarters/steel/console/{state}_albedo.png'))
            for row in legends:
                x, y = row['ink_probe_pixel']
                self.assertGreater(int(image[y, x, :3].min()), 160, f'{state} {row["key"]}')
                self.assertGreaterEqual(row['ink_texels'], 100, row['key'])
                self.assertIn(row['sign'], json.loads((HERE / 'legends.json').read_text())['syllables'])


if __name__ == '__main__':
    unittest.main()
