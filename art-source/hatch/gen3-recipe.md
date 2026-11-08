# Hatch leaf candidates: third batch

Source: `docs/art/corridors/hatch-concept-rusted.png`.
Crop box (left, top, right, bottom): `[365, 77, 875, 960]`, using Pillow crop coordinates (right and bottom exclusive).
FLUX.2-klein-4B edit: 4-bit quantization, 4 steps, 512x896, seeds 300, 301, 302.
Each successful edit is resized with Pillow LANCZOS to 1024x2304, then refined using Z-Image-Turbo, 4-bit quantization, 8 steps, the same seed, and literal CLI image strengths 0.3 and 0.5.
Models run sequentially using cached weights with HF_HUB_OFFLINE=1. On a Metal/GPU error or a 900-second command timeout, wait 60 seconds and retry once, then continue. Non-GPU failures are recorded without retry.
No visual assessment is performed.

## Editing prompt

Remove the handwheel, the hinges, the latches, the rivets and bolts, and the door edge from this image. Replace all hardware and edges with a continuous rusted, peeling painted steel surface matching the surrounding surface. Preserve the extensive dark reddish-brown rust, flaking orange corrosion and scattered broken grey-green paint islands from the reference. Fill the entire image edge to edge with only this continuous flat material surface, lit flat and evenly, without shadows, seams, borders or hardware.

## Material prompt (copied verbatim from gen2/prompt.txt)

A top-down macro scan of a badly corroded steel surface, mostly covered in dark reddish-brown rust, flaking orange scale and pitting; scattered ragged islands of old dull olive-grey paint remain, each with broken, lifted edges; rust streaks run downward from the paint edges; the lower part is darker with grime; flat even diffuse light, no shadows.


## Preparation commands

```sh
/Volumes/XS1000/tools/mlximg-venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/generate.py
```

The script creates leaf-crop.png and crop-check.png from the source with Pillow; crop-check.png marks the requested box with a 6-pixel cyan outline. It creates edit-<seed>-1024x2304.png via LANCZOS resizing and builds sheet.png as a labelled horizontal strip, 300 pixels per entry. Unavailable outputs are represented by labelled failure placeholders.

## Generation commands and results

### edit-300, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 896 --seed 300 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-300.png
```

Success: `edit-300.png`, 512x896. Log: `edit-300-attempt-1.log`.

### edit-301, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 896 --seed 301 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-301.png
```

Success: `edit-301.png`, 512x896. Log: `edit-301-attempt-1.log`.

### edit-302, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 896 --seed 302 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-302.png
```

Success: `edit-302.png`, 512x896. Log: `edit-302-attempt-1.log`.

### refine-300-0.3, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 300 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-300-1024x2304.png --image-strength 0.3 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-300-0.3.png
```

Success: `refine-300-0.3.png`, 1024x2304. Log: `refine-300-0.3-attempt-1.log`.

### refine-300-0.5, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 300 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-300-1024x2304.png --image-strength 0.5 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-300-0.5.png
```

Success: `refine-300-0.5.png`, 1024x2304. Log: `refine-300-0.5-attempt-1.log`.

### refine-301-0.3, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 301 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-301-1024x2304.png --image-strength 0.3 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-301-0.3.png
```

Success: `refine-301-0.3.png`, 1024x2304. Log: `refine-301-0.3-attempt-1.log`.

### refine-301-0.5, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 301 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-301-1024x2304.png --image-strength 0.5 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-301-0.5.png
```

Success: `refine-301-0.5.png`, 1024x2304. Log: `refine-301-0.5-attempt-1.log`.

### refine-302-0.3, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 302 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-302-1024x2304.png --image-strength 0.3 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-302-0.3.png
```

Success: `refine-302-0.3.png`, 1024x2304. Log: `refine-302-0.3-attempt-1.log`.

### refine-302-0.5, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-z-image-turbo --quantize 4 --steps 8 --width 1024 --height 2304 --seed 302 --image-path /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/edit-302-1024x2304.png --image-strength 0.5 --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/material-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen3/refine-302-0.5.png
```

Success: `refine-302-0.5.png`, 1024x2304. Log: `refine-302-0.5-attempt-1.log`.

## Completion

Sheet: `sheet.png`, 3000x719.
Successful generated candidates: 9.
Failed command attempts: 0.
See `results.json` for paths, dimensions, attempts, logs and failures.


## File verification and metadata notes

Verified all 15 PNG files decode and match their expected dimensions, including the 3000x719 sheet with ten 300-pixel-wide labelled entries. All nine generation commands succeeded on their first attempt; no GPU retries or skipped candidates.

FLUX edit metadata sidecars contain JSON null: `edit-300.metadata.json`, `edit-301.metadata.json`, `edit-302.metadata.json`. The full commands, prompts and seeds above and in generate.py/results.json are the parameter record.

Both refinement strengths use the requested `--steps 8`. The image-to-image scheduler reports six executed denoising steps at strength 0.3 and four at strength 0.5. No visual judgments were made.
