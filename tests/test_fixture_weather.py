import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

SPEC = importlib.util.spec_from_file_location('fixture_weather', Path(__file__).resolve().parents[1] / 'tools/check_fixture_weather.py')
WEATHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEATHER)


class FixtureWeatherTest(unittest.TestCase):
    def test_effect_metrics_use_visible_feature_masks_not_background(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            shape = (256, 512, 3)
            zones = np.zeros(shape, dtype=np.uint8)
            zones[80:180, 200:230, 0] = 255
            zones[80:180, 240:290, 1] = 255
            zones[80:180, 200:230, 2] = 255
            dust = np.zeros(shape, dtype=np.uint8)
            dust[80:180, 240:290] = 255
            lit = np.full(shape, 240, dtype=np.uint8)
            lit[80:180, 200:290] = 120
            control = lit.copy()
            control[80:180, 200:290] = 100
            no_rust = lit.copy()
            no_rust[80:180, 200:230] = 100
            no_rust[80:180, 240:290] = 116
            no_dust = lit.copy()
            no_dust[80:180, 240:290] = 108
            for view in ('2p5m', 'close', 'ledge', 'corridor'):
                for name, values in {'weathered': lit, 'control': control, 'no_rust': no_rust, 'no_dust': no_dust, 'no_streak': no_rust, 'zones': zones, 'dustmask': dust, 'topmask': dust, 'shellmask': dust}.items():
                    Image.fromarray(values).save(directory / f'{name}-{view}.png')
            result = WEATHER.measure(directory)['close']
            self.assertEqual(result['metal_pixels'], 8000)
            self.assertAlmostEqual(result['weather_rgb_difference'], 20 / 255)
            self.assertAlmostEqual(result['edge_to_broad_rust_ratio'], 5)
            self.assertAlmostEqual(result['dust_rgb_difference'], 12 / 255)
            self.assertAlmostEqual(result['top_dust_rgb_difference'], 12 / 255)
            self.assertAlmostEqual(result['broad_shell_display_luma'], 120 / 255)
            self.assertEqual(result['broad_shell_black_fraction'], 0)

    def test_recorded_rust_everywhere_fails_all_four_ratio_gates(self):
        recorded = json.loads((Path(__file__).parent / 'fixtures/fixture-weather-scene.json').read_text())
        gates = json.loads(WEATHER.THRESHOLDS.read_text())
        checks = WEATHER.evaluate(recorded['rust_everywhere'], gates)
        ratio_checks = {name: passed for name, passed in checks.items() if name.endswith('.edge_to_broad_rust_ratio')}
        self.assertEqual(ratio_checks, {f'{view}.edge_to_broad_rust_ratio': False for view in recorded['rust_everywhere']})

    def test_recorded_merged_production_passes_all_four_ratio_gates(self):
        recorded = json.loads((Path(__file__).parent / 'fixtures/fixture-weather-scene.json').read_text())
        gates = json.loads(WEATHER.THRESHOLDS.read_text())
        checks = WEATHER.evaluate(recorded['production'], gates)
        ratio_checks = {name: passed for name, passed in checks.items() if name.endswith('.edge_to_broad_rust_ratio')}
        self.assertEqual(ratio_checks, {f'{view}.edge_to_broad_rust_ratio': True for view in recorded['production']})
        self.assertTrue(all(checks.values()))

    def test_passing_views_keep_the_accepted_ratio_minimums(self):
        gates = json.loads(WEATHER.THRESHOLDS.read_text())
        for view, minimum in {'2p5m': 83.77627832909327, 'ledge': 1339.1717902209737}.items():
            with self.subTest(view=view):
                self.assertIn('edge_to_broad_rust_ratio', gates['views'][view])
                self.assertEqual(gates['views'][view]['edge_to_broad_rust_ratio']['min'], minimum)

    def test_paint_or_dust_presence_alone_cannot_pass_visibility_gate(self):
        limits = {'views': {'close': {'dust_rgb_difference': {'min': .02, 'max': 1}, 'edge_to_broad_rust_ratio': {'min': 10, 'max': 1e9, 'edge_rust_min': .01}}}}
        result = {'close': {'dust_rgb_difference': 0, 'edge_rust_difference': .02, 'edge_to_broad_rust_ratio': 200}}
        self.assertFalse(all(WEATHER.evaluate(result, limits).values()))
        result['close']['dust_rgb_difference'] = .04
        self.assertTrue(all(WEATHER.evaluate(result, limits).values()))

    def test_rust_ratio_requires_localised_rust_and_visible_edges(self):
        limits = {'views': {'close': {'edge_to_broad_rust_ratio': {'min': 10, 'max': 1e9, 'edge_rust_min': .01}}}}
        for edge, ratio, expected in (
            (.01, 10, True),
            (.02, 9.99, False),
            (.0099, 9900, False),
            (.02, 1e9, True),
            (.02, 1e9 + 1, False),
        ):
            with self.subTest(edge=edge, ratio=ratio):
                result = {'close': {'edge_rust_difference': edge, 'edge_to_broad_rust_ratio': ratio}}
                self.assertEqual(WEATHER.evaluate(result, limits), {'close.edge_to_broad_rust_ratio': expected})

    def test_repeating_diagonal_pattern_is_detected(self):
        y, x = np.mgrid[:256, :512]
        pattern = np.sin((x + y) * 2 * np.pi / 24)
        self.assertGreater(WEATHER.tiling_peak(pattern, np.ones(pattern.shape, dtype=bool)), .99)

    def test_nonperiodic_noise_has_no_translation_peak(self):
        pattern = np.random.default_rng(720).normal(size=(256, 512))
        self.assertLess(WEATHER.tiling_peak(pattern, np.ones(pattern.shape, dtype=bool)), .05)

    def test_missing_visible_surface_fails_instead_of_fabricating_measurements(self):
        with self.assertRaisesRegex(ValueError, 'no visible samples'):
            WEATHER.masked_mean(np.zeros((2, 2)), np.zeros((2, 2), dtype=bool))

    def test_fixed_gates_match_the_accepted_native_asset_and_measurements(self):
        gates = json.loads(WEATHER.THRESHOLDS.read_text())
        accepted = json.loads((WEATHER.ROOT / gates['accepted_record']).read_text())
        self.assertEqual(accepted['decision'], 'ACCEPT')
        self.assertEqual(accepted['age_years'], 1000)
        asset = WEATHER.ROOT / 'assets/props/ceiling/fixture.glb'
        self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), accepted['glb_sha256'])
        self.assertTrue(all(WEATHER.evaluate(accepted['measurements'], gates).values()))
        self.assertEqual(accepted['source_policy'], 'all beams recessed and downward-only; no fill')
        self.assertEqual(gates['calibration'], {
            'minimum_effect_fraction': .90,
            'maximum_translation_margin': .05,
        })
        common = {'weather_rgb_difference', 'broad_shell_rgb_difference',
                  'edge_to_broad_rust_ratio', 'dust_rgb_difference',
                  'broad_face_translation_peak'}
        expected = {
            '2p5m': common | {'visible_weather_fraction', 'edge_rust_difference'},
            'close': common | {'visible_weather_fraction', 'edge_rust_difference', 'streak_rgb_difference'},
            'ledge': common | {'streak_rgb_difference'},
            'corridor': common | {'visible_weather_fraction', 'edge_rust_difference'},
        }
        production = json.loads((Path(__file__).parent / 'fixtures/fixture-weather-scene.json').read_text())['production']
        self.assertEqual(set(gates['views']), set(expected))
        self.assertEqual(sum(map(len, gates['views'].values())), 28)
        for view, limits in gates['views'].items():
            self.assertEqual(set(limits), expected[view])
            for metric, bounds in limits.items():
                reference = accepted['measurements'][view][metric]
                if metric == 'edge_to_broad_rust_ratio':
                    if view in ('close', 'corridor'):
                        reference = production[view][metric]
                    self.assertEqual(bounds['edge_rust_min'], production[view]['edge_rust_difference'] * .90)
                    self.assertEqual(bounds['max'], 1e9)
                if metric == 'broad_face_translation_peak':
                    self.assertAlmostEqual(bounds['max'], reference + .05)
                    self.assertLess(bounds['max'], .99)
                else:
                    self.assertAlmostEqual(bounds['min'], reference * .90)
                    self.assertGreater(bounds['min'], 0)

    def test_each_retained_gate_rejects_a_missing_effect_or_periodic_texture(self):
        gates = json.loads(WEATHER.THRESHOLDS.read_text())
        accepted = json.loads((WEATHER.ROOT / gates['accepted_record']).read_text())
        for view, limits in gates['views'].items():
            for metric in limits:
                with self.subTest(view=view, metric=metric):
                    result = {name: values.copy() for name, values in accepted['measurements'].items()}
                    result[view][metric] = 1 if metric == 'broad_face_translation_peak' else 0
                    self.assertFalse(WEATHER.evaluate(result, gates)[f'{view}.{metric}'])


if __name__ == '__main__':
    unittest.main()
