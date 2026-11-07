#!/usr/bin/env python3
"""Generate quarters prop renders and compose contact sheets."""

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERO_MODEL = "filipstrand/Z-Image-Turbo-mflux-4bit"
EDIT_MODEL = "black-forest-labs/FLUX.2-klein-4B"
HERO_TOOL = "/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo"
EDIT_TOOL = "/Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit"


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as image:
        for chunk in iter(lambda: image.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def prop_data(prompts_path, prop_id):
    data = json.loads(Path(prompts_path).read_text())
    prop = next((item for item in data["props"] if item["id"] == prop_id), None)
    if prop is None:
        raise ValueError(f"Unknown prop: {prop_id}")
    return data, prop


def run_job(command, output, metadata, dry_run):
    output = Path(output)
    marker = output.with_suffix(".done")
    if dry_run:
        print(shlex.join(command))
        return
    if marker.exists() and output.exists() and output.with_suffix(".json").exists():
        print(f"SKIP {output}", flush=True)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    marker.unlink(missing_ok=True)
    started = time.monotonic()
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        tail = "\n".join(result.stderr.splitlines()[-30:])
        raise RuntimeError(f"Command failed ({result.returncode}): {shlex.join(command)}\n{tail}")
    if not output.is_file():
        raise RuntimeError(f"Command succeeded but did not create {output}\n{result.stderr}")
    metadata["sha256"] = digest(output)
    metadata["elapsed_seconds"] = round(time.monotonic() - started, 3)
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    marker.write_text("done\n")
    print(f"DONE {output} ({metadata['elapsed_seconds']:.3f}s)", flush=True)


def hero(args):
    data, prop = prop_data(args.prompts, args.prop)
    seeds = args.seeds or prop["seeds"]
    destination = Path(args.out) / args.prop
    prompt = f"{data['style']} {prop['prompt']} {data['tail']}"
    for seed in seeds:
        output = destination / f"hero-s{seed}.png"
        command = ["env", "HF_HOME=/Volumes/XS1000/hf-cache", "HF_HUB_OFFLINE=1",
                   HERO_TOOL, "--model", HERO_MODEL, "--quantize", "4", "--steps", "8",
                   "--seed", str(seed), "--width", "1024", "--height", "1024",
                   "--output", str(output), "--prompt", prompt]
        metadata = {"command": shlex.join(command), "prompt": prompt, "seed": seed,
                    "model_id": HERO_MODEL}
        run_job(command, output, metadata, args.dry_run)


def views(args):
    data, _ = prop_data(args.prompts, args.prop)
    destination = Path(args.out) / args.prop
    for name, prompt in data["views"].items():
        output = destination / f"view-{name}.png"
        prompt_file = destination / f"view-{name}.prompt.txt"
        if not args.dry_run:
            destination.mkdir(parents=True, exist_ok=True)
            prompt_file.write_text(prompt + "\n")
        command = ["env", "HF_HOME=/Volumes/XS1000/hf-cache", "HF_HUB_OFFLINE=1",
                   EDIT_TOOL, "--base-model", "flux2-klein-4b", "--model", EDIT_MODEL,
                   "--quantize", "8", "--image-paths", str(Path(args.hero)),
                   "--seed", str(args.seed), "--steps", "4", "--output", str(output),
                   "--prompt-file", str(prompt_file)]
        metadata = {"command": shlex.join(command), "prompt": prompt, "seed": args.seed,
                    "model_id": EDIT_MODEL, "source_image": str(Path(args.hero)),
                    "source_sha256": digest(args.hero) if not args.dry_run else None}
        run_job(command, output, metadata, args.dry_run)


def sheet(args):
    from PIL import Image, ImageDraw, ImageFont

    folder = Path(args.out) / args.prop
    names = ["view-front", "view-left", "view-right", "view-back"]
    heroes = sorted(folder.glob("hero-s*.png"))
    if not heroes:
        raise FileNotFoundError(f"No hero-s<seed>.png image found in {folder}")
    paths = [heroes[0]] + [folder / f"{name}.png" for name in names]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing sheet inputs: " + ", ".join(missing))
    images = [Image.open(path).convert("RGB") for path in paths]
    hero_image, views_images = images[0], images[1:]
    cell_w = max(image.width for image in views_images)
    cell_h = max(image.height for image in views_images)
    label_h, gap, margin = 44, 24, 24
    left_w = max(hero_image.width, cell_w * 2 + gap)
    right_w = cell_w * 2 + gap
    grid_w = margin * 2 + left_w + gap + right_w
    grid_h = margin * 2 + max(hero_image.height, cell_h * 2 + gap + label_h * 2)
    canvas = Image.new("RGB", (grid_w, grid_h), (238, 238, 234))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=28)
    hero_x = margin + (left_w - hero_image.width) // 2
    hero_y = margin + (grid_h - margin * 2 - hero_image.height) // 2
    canvas.paste(hero_image, (hero_x, hero_y))
    draw.text((hero_x + 8, max(0, hero_y - label_h)), "Hero", fill=(20, 20, 20), font=font)
    right_x = margin + left_w + gap
    for index, (name, image) in enumerate(zip(names[1:], views_images)):
        x = right_x + (index % 2) * (cell_w + gap)
        y = margin + (index // 2) * (cell_h + label_h + gap)
        draw.text((x + 8, y), name.removeprefix("view-").title(), fill=(20, 20, 20), font=font)
        canvas.paste(image, (x, y + label_h))
    output = folder / "sheet.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    provenance = {"prop": args.prop, "inputs": [
        {"path": str(path), "sha256": digest(path)} for path in paths
    ], "output": str(output), "sha256": digest(output), "mode": "RGB", "bit_depth": 8}
    (folder / "sheet.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"DONE {output}", flush=True)


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    hero_parser = commands.add_parser("hero")
    hero_parser.add_argument("--prompts", required=True)
    hero_parser.add_argument("--prop", required=True)
    hero_parser.add_argument("--out", required=True)
    hero_parser.add_argument("--seeds", nargs="+", type=int)
    hero_parser.add_argument("--dry-run", action="store_true")
    hero_parser.set_defaults(run=hero)
    views_parser = commands.add_parser("views")
    views_parser.add_argument("--prompts", required=True)
    views_parser.add_argument("--prop", required=True)
    views_parser.add_argument("--hero", required=True)
    views_parser.add_argument("--out", required=True)
    views_parser.add_argument("--seed", type=int, default=1)
    views_parser.add_argument("--dry-run", action="store_true")
    views_parser.set_defaults(run=views)
    sheet_parser = commands.add_parser("sheet")
    sheet_parser.add_argument("--prop", required=True)
    sheet_parser.add_argument("--out", required=True)
    sheet_parser.set_defaults(run=sheet)
    return root


def main():
    args = parser().parse_args()
    try:
        args.run(args)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
