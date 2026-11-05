#!/usr/bin/env python3
"""Render the fixed hatch rig, then enforce its rendered-colour targets."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--godot", default="godot")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    image = output / "lookdev-neutral.png"
    # A stale capture must not turn a failed render into a colour pass.
    image.unlink(missing_ok=True)
    command = [args.godot, "--path", str(ROOT), "-s", "tools/capture_hatch_lookdev.gd", "--", str(output)]
    with subprocess.Popen(command, cwd=ROOT) as process:
        print(f"spawned app pid {process.pid}", flush=True)
        code = process.wait()
    if code:
        raise subprocess.CalledProcessError(code, command)
    subprocess.run([sys.executable, str(ROOT / "tests/test_hatch_colour.py")], cwd=ROOT,
                   env=dict(os.environ, HATCH_NEUTRAL_IMAGE=str(image)), check=True)


if __name__ == "__main__":
    main()
