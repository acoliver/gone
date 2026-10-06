#!/usr/bin/env python3
"""Render Spanish speech with Chatterbox Multilingual V2 and a local reference."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import numpy as np
import scipy.signal as signal
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
RATE = 24000


def validate_reference(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"voice reference is missing: {path}")
    info = sf.info(path)
    if (info.format != "WAV" or info.subtype != "PCM_16"
            or info.channels != 1 or info.samplerate != RATE
            or info.frames != RATE * 20):
        raise ValueError("voice reference must be 20-second mono 24 kHz PCM16 WAV")


def _filter(samples: np.ndarray, kind: str, hz: float, order: int) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, hz, btype=kind, fs=RATE, output="sos"), samples)


def underwater(samples: np.ndarray, sample_rate: int = RATE) -> np.ndarray:
    """The existing mono underwater treatment: dry presence plus modulated wet delay."""
    x = np.asarray(samples, dtype=np.float32)
    if sample_rate != RATE or x.ndim != 1 or x.size == 0 or not np.isfinite(x).all():
        raise ValueError("expected finite, non-empty mono 24 kHz audio")
    direct = _filter(_filter(x, "highpass", 65, 1), "lowpass", 8000, 2)
    wet = _filter(_filter(x, "highpass", 80, 2), "lowpass", 1200, 2)
    t = np.arange(len(x), dtype=np.float64) / RATE
    delays = (.038 + .0015 * np.sin(2 * np.pi * .22 * t)) * RATE
    delayed = np.interp(np.arange(len(x)) - delays, np.arange(len(x)), wet, left=0, right=0)
    return (direct + delayed * .45).astype(np.float32)


def _patch_torch_load(torch, device) -> None:
    """Load CUDA-tagged checkpoints onto the selected runtime device."""
    original_load = torch.load

    def load(*args, **kwargs):
        kwargs["map_location"] = device
        return original_load(*args, **kwargs)

    torch.load = load


def render(text: str, output: Path, reference: Path) -> None:
    validate_reference(reference)
    if output.suffix.lower() != ".wav":
        raise ValueError("output path must have a .wav suffix")
    if not text.strip():
        raise ValueError("text must not be empty")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    import torch

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    torch_device = torch.device(device)
    _patch_torch_load(torch, torch_device)
    model = ChatterboxMultilingualTTS.from_pretrained(device=torch_device)
    wav = model.generate(
        text.strip(), audio_prompt_path=str(reference), language_id="es",
        exaggeration=.55, cfg_weight=.30, temperature=.70,
    )
    samples = wav.detach().float().cpu().numpy().squeeze()
    if samples.ndim != 1:
        raise ValueError(f"model produced unexpected audio dimensions: {samples.shape}")
    generated_rate = int(model.sr)
    if generated_rate != RATE:
        samples = signal.resample_poly(samples, RATE, generated_rate).astype(np.float32)
    processed = underwater(samples, RATE)
    peak = float(np.max(np.abs(processed)))
    if peak == 0 or not np.isfinite(peak):
        raise ValueError("model produced silent or non-finite audio")
    if peak > 1.0:
        raise ValueError(f"processed audio clips (peak={peak:.6f}); refusing to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as staged:
        temporary = Path(staged.name)
    try:
        sf.write(temporary, processed, RATE, format="WAV", subtype="PCM_16")
        try:
            os.link(temporary, output)
        except FileExistsError:
            raise FileExistsError(f"refusing to overwrite existing output: {output}") from None
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, help="arbitrary Spanish text to speak")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path, help="your local 20-second mono 24 kHz PCM16 WAV")
    parser.add_argument("--plan", action="store_true", help="validate inputs and print the render plan without loading the model")
    args = parser.parse_args()
    try:
        validate_reference(args.reference)
        if args.output.suffix.lower() != ".wav":
            raise ValueError("output path must have a .wav suffix")
        if args.output.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
        if not args.text.strip():
            raise ValueError("text must not be empty")
        if args.plan:
            print(f"Chatterbox multilingual V2 / es; reference={args.reference}; 24 kHz mono; underwater DSP; output={args.output}")
        else:
            render(args.text, args.output, args.reference)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
