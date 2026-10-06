import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

from tools import voice_clone


class VoiceCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reference = Path(self.temp.name) / "synthetic-reference.wav"
        samples = np.zeros(voice_clone.RATE * 20, dtype=np.int16)
        samples[::24] = 512
        sf.write(self.reference, samples, voice_clone.RATE, subtype="PCM_16")

    def test_validates_synthetic_pcm16_reference(self):
        voice_clone.validate_reference(self.reference)

    def test_rejects_invalid_reference_formats(self):
        cases = (
            (np.zeros(voice_clone.RATE * 20, dtype=np.float32), voice_clone.RATE, "PCM_24", "mono 24 kHz PCM16"),
            (np.zeros((voice_clone.RATE * 20, 2), dtype=np.int16), voice_clone.RATE, "PCM_16", "mono 24 kHz PCM16"),
            (np.zeros(voice_clone.RATE * 20, dtype=np.int16), 16000, "PCM_16", "mono 24 kHz PCM16"),
            (np.zeros(voice_clone.RATE * 19, dtype=np.int16), voice_clone.RATE, "PCM_16", "mono 24 kHz PCM16"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (samples, rate, subtype, message) in enumerate(cases):
                path = Path(directory) / f"bad-{index}.wav"
                sf.write(path, samples, rate, subtype=subtype)
                with self.subTest(index=index), self.assertRaisesRegex(ValueError, message):
                    voice_clone.validate_reference(path)

    def test_underwater_requires_finite_mono_24k(self):
        x = np.sin(2 * np.pi * 440 * np.arange(24000) / 24000).astype(np.float32)
        y = voice_clone.underwater(x)
        self.assertEqual(y.shape, x.shape)
        self.assertEqual(y.dtype, np.float32)
        self.assertTrue(np.isfinite(y).all())
        self.assertGreater(float(np.sqrt(np.mean((y - x) ** 2))), 0.01)
        with self.assertRaisesRegex(ValueError, "mono 24 kHz"):
            voice_clone.underwater(np.zeros((100, 2), np.float32))
        with self.assertRaisesRegex(ValueError, "mono 24 kHz"):
            voice_clone.underwater(np.zeros(100, np.float32), 16000)

    def test_plan_requires_reference_and_validates_before_model_download(self):
        missing = subprocess.run(
            [sys.executable, "tools/voice_clone.py", "--text", "Hola", "--output", str(Path(self.temp.name) / "out.wav"), "--plan"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("--reference", missing.stderr)
        invalid = Path(self.temp.name) / "invalid.wav"
        sf.write(invalid, np.zeros(100, dtype=np.int16), voice_clone.RATE)
        result = subprocess.run(
            [sys.executable, "tools/voice_clone.py", "--text", "Hola", "--output", str(Path(self.temp.name) / "out.wav"), "--reference", str(invalid), "--plan"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("20-second mono 24 kHz PCM16 WAV", result.stderr)

    def test_plan_does_not_overwrite_existing_output(self):
        output = Path(self.temp.name) / "taken.wav"
        output.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError):
            voice_clone.render("Hola", output, self.reference)
        self.assertEqual(output.read_bytes(), b"preserve")

    def _mock_runtime(self, peak, mps=True):
        torch = types.ModuleType("torch")
        torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: mps))
        torch.device = lambda name: f"device:{name}"
        torch.load = Mock(return_value="checkpoint")
        generated = Mock()
        generated.detach.return_value.float.return_value.cpu.return_value.numpy.return_value.squeeze.return_value = np.full(2400, peak, np.float32)
        model = types.SimpleNamespace(generate=Mock(return_value=generated), sr=24000)
        chatterbox = types.ModuleType("chatterbox")
        mtl_tts = types.ModuleType("chatterbox.mtl_tts")
        def load_checkpoint_during_model_setup(*args, **kwargs):
            torch.load("fake-checkpoint.bin")
            return model

        model_class = types.SimpleNamespace(from_pretrained=Mock(side_effect=load_checkpoint_during_model_setup))
        mtl_tts.ChatterboxMultilingualTTS = model_class
        chatterbox.mtl_tts = mtl_tts
        return torch, chatterbox, mtl_tts, model

    def test_render_loads_model_on_mps_and_writes_generated_audio(self):
        torch, chatterbox, mtl_tts, model = self._mock_runtime(.03)
        load_mock = torch.load
        output = Path(self.temp.name) / "nested" / "render.wav"
        with patch.dict(sys.modules, {"torch": torch, "chatterbox": chatterbox, "chatterbox.mtl_tts": mtl_tts}):
            voice_clone.render("  Hola  ", output, self.reference)
        mtl_tts.ChatterboxMultilingualTTS.from_pretrained.assert_called_once_with(device="device:mps")
        model.generate.assert_called_once_with(
            "Hola", audio_prompt_path=str(self.reference), language_id="es",
            exaggeration=.55, cfg_weight=.30, temperature=.70,
        )
        load_mock.assert_called_once_with("fake-checkpoint.bin", map_location="device:mps")
        info = sf.info(output)
        self.assertEqual((info.format, info.subtype, info.channels, info.samplerate), ("WAV", "PCM_16", 1, 24000))
        self.assertGreater(info.frames, 0)

    def test_render_refuses_destination_created_during_generation(self):
        torch, chatterbox, mtl_tts, model = self._mock_runtime(.03)
        output = Path(self.temp.name) / "race.wav"

        def generate(*args, **kwargs):
            output.write_bytes(b"created during generation")
            return model.generate.return_value

        model.generate.side_effect = generate
        with patch.dict(sys.modules, {"torch": torch, "chatterbox": chatterbox, "chatterbox.mtl_tts": mtl_tts}):
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                voice_clone.render("Hola", output, self.reference)
        self.assertEqual(output.read_bytes(), b"created during generation")
        self.assertEqual(list(Path(self.temp.name).glob("*.tmp")), [])

    def test_render_rejects_non_wav_suffix_before_loading_model(self):
        output = Path(self.temp.name) / "render.flac"
        with self.assertRaisesRegex(ValueError, r"\.wav"):
            voice_clone.render("Hola", output, self.reference)
        self.assertFalse(output.exists())

    def test_render_fails_before_writing_clipped_audio(self):
        torch, chatterbox, mtl_tts, _model = self._mock_runtime(2.0, mps=False)
        output = Path(self.temp.name) / "clipped.wav"
        with patch.dict(sys.modules, {"torch": torch, "chatterbox": chatterbox, "chatterbox.mtl_tts": mtl_tts}):
            with self.assertRaisesRegex(ValueError, "clips"):
                voice_clone.render("Hola", output, self.reference)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
