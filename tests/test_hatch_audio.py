import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("generate_hatch_audio", ROOT / "tools/generate_hatch_audio.py")
AUDIO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIO)

# Independent pins: changing the recipes requires an explicit asset/test update.
HASHES = {
    "grind-01.wav": "b9c015d7b2d7f0383e6f6b7491b8b52e38ea26791ad948996c7fbd93ffdda6d9",
    "grind-02.wav": "07a505651e079e63492fe04ca50859d9301d7add7446f3c6151ae37023093f00",
    "grind-03.wav": "ae726b00cb2c0510a2194c94909ab91d7b2b6aa206f402b23d8cbf219c6841bb",
    "grind-04.wav": "563d9b21b07f128060ebd8838eab510653e4372d05f5d2f17a8da0defb92c86e",
    "stall-01.wav": "9d3fb909aa8363cb48fea37ae43dbe3b92c1e227b29d9cd85923dff73647f566",
    "stall-02.wav": "3722c81371b9941c74a07b891fc8e7dd077b13404f96859b30646c967630c6cc",
    "stall-03.wav": "04b386e38e10d0e4fd0b1742f492651ae84ec6552e32ce3b1efbf849d441d016",
    "wheel-refused-01.wav": "463ffe6d5dadf0a87f3071626d05e55a69df2a65aebe3a7b60d40ee0ececd16f",
    "thud-01.wav": "ea246b2e369a1183cc714ef7e3954b7a6b87f9ff4a9762d36e3a0cea80d433db",
    "thud-02.wav": "c36d988451afb6762b0fb12f95b182658a0c523e5693dc57b861e3029f8649ee",
    "release-01.wav": "c7b1582928f382d9b25600d5399a8d5a557b7e2ba1c7cb49108b583fde1770bb",
}


class HatchAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = AUDIO.render_assets()

    def test_exact_family_inventory(self):
        counts = {}
        for recipe in AUDIO.RECIPES:
            counts[recipe[1]] = counts.get(recipe[1], 0) + 1
        self.assertEqual(counts, {"grind": 4, "stall": 3, "wheel-refused": 1, "thud": 2, "release": 1})
        self.assertEqual(len(self.assets), 11)

    def test_repeat_generation_is_byte_identical_and_hashes_are_pinned(self):
        self.assertEqual(AUDIO.render_assets(), self.assets)
        self.assertEqual({name: hashlib.sha256(data).hexdigest() for name, data in self.assets.items()}, HASHES)
        recipe = AUDIO.RECIPES[0]
        changed = (recipe[0], recipe[1], recipe[2] + 1, recipe[3])
        self.assertNotEqual(AUDIO.synthesize(changed), self.assets[recipe[0]])

    def test_pcm_format_lengths_headroom_dc_and_fades(self):
        for name, family, _seed, frames in AUDIO.RECIPES:
            with self.subTest(name=name), wave.open(io.BytesIO(self.assets[name]), "rb") as wav:
                self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getcomptype()), (1, 48000, 2, "NONE"))
                self.assertEqual(wav.getnframes(), frames)
                self.assertGreater(frames, 48000 * .2)
                self.assertLessEqual(frames, 48000 * (2.5 if family == "release" else 1.5))
                pcm = struct.unpack(f"<{frames}h", wav.readframes(frames))
            peak = max(abs(value) for value in pcm)
            self.assertLessEqual(peak, math.ceil(32767 * 10 ** (-3 / 20)))
            self.assertGreater(peak, 23000)
            self.assertLessEqual(abs(sum(pcm) / len(pcm)), .5)
            self.assertEqual((pcm[0], pcm[-1]), (0, 0))
            self.assertLess(max(abs(value) for value in pcm[:48]), peak * .08)
            self.assertLess(max(abs(value) for value in pcm[-48:]), peak * .08)

    def test_tracked_assets_and_manifest_match_without_writing(self):
        before = {path: path.stat().st_mtime_ns for path in AUDIO.OUTPUT.iterdir() if path.is_file()}
        AUDIO.check_assets(AUDIO.OUTPUT)
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in before})
        manifest = json.loads((AUDIO.OUTPUT / "manifest.json").read_text())
        self.assertEqual(manifest, AUDIO.manifest(self.assets))
        for name, data in self.assets.items():
            self.assertEqual((AUDIO.OUTPUT / name).read_bytes(), data)

    def test_check_rejects_missing_corrupt_or_stale_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises((ValueError, FileNotFoundError)):
                AUDIO.check_assets(output)
            AUDIO.write_assets(output, self.assets)
            AUDIO.check_assets(output)
            (output / AUDIO.RECIPES[0][0]).write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                AUDIO.check_assets(output)
            AUDIO.write_assets(output, self.assets)
            (output / "manifest.json").write_text("{}")
            with self.assertRaises(ValueError):
                AUDIO.check_assets(output)

    def test_finish_rejects_empty_silent_and_nonfinite_input(self):
        for samples in ([], [0.] * 4800, [float("nan")] * 4800, [float("inf")] * 4800):
            with self.subTest(samples=samples[:1]), self.assertRaises(ValueError):
                AUDIO.finish(samples)

    def test_audition_copies_all_effects_and_has_exact_twenty_second_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            AUDIO.write_audition(output, self.assets)
            for name, data in self.assets.items():
                self.assertEqual((output / name).read_bytes(), data)
            with wave.open(str(output / "demo-20s.wav"), "rb") as wav:
                self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()), (1, 48000, 2, 960000))
                pcm = struct.unpack("<960000h", wav.readframes(960000))
            self.assertLessEqual(max(abs(value) for value in pcm), 32767 * 10 ** (-1 / 20))
            self.assertEqual((pcm[0], pcm[-1]), (0, 0))
            # Eight presses, release, and two refusal attempts, each audible.
            for start in (0.5, 1.9, 3.3, 4.7, 6.1, 7.5, 8.9, 10.3, 10.4, 15., 17.):
                self.assertGreater(max(abs(value) for value in pcm[int(start * 48000):int((start + .3) * 48000)]), 1000)


if __name__ == "__main__":
    unittest.main()
