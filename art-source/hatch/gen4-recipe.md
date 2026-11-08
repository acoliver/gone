# Hatch final-size texture candidates

FLUX.2-klein-4B edit, 4-bit quantization, four steps. Leaf seeds 300 through 307 at 512x1088; frame seeds 400 through 403 at 1024x960. Generated candidates are not resized, cropped or refined after generation.

Leaf input and prompt are copied byte-for-byte from gen3. The atlas cell sizes come from tools/prepare_hatch_paint.py and assets/props/hatch/SOURCES.md.

Source: docs/art/corridors/hatch-concept-rusted.png. Pillow crop boxes use exclusive right and bottom coordinates:

- leaf reference: [365, 77, 875, 960].
- left post input: [285, 120, 365, 900].
- top band reference: [400, 30, 840, 77].

frame-left-post-crop.png is the frame edit input. frame-top-band-crop.png is an additional reference only. frame-crop-check.png marks all three boxes: cyan leaf, magenta left post, yellow top band, with labels below the concept.

Commands run sequentially with offline cached weights. On a Metal/GPU error or a 900-second generation timeout, wait 60 seconds and retry once. Other failures are recorded without retry. Only child processes started here can be terminated by the subprocess timeout. No visual assessment is performed.

## Preparation and sheet command

```sh
nohup env PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/tools/mlximg-venv/bin/python -u /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/generate.py > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/run.log 2>&1 &
```

generate.py copies the leaf input and prompt, crops the frame references, draws the crop boxes, runs the commands below and creates both sheets using Pillow. Sheet thumbnails preserve aspect ratio with LANCZOS resizing. Missing candidates get labelled failure placeholders.

## Leaf edit prompt (unchanged)

Remove the handwheel, the hinges, the latches, the rivets and bolts, and the door edge from this image. Replace all hardware and edges with a continuous rusted, peeling painted steel surface matching the surrounding surface. Preserve the extensive dark reddish-brown rust, flaking orange corrosion and scattered broken grey-green paint islands from the reference. Fill the entire image edge to edge with only this continuous flat material surface, lit flat and evenly, without shadows, seams, borders or hardware.

## Frame edit prompt

Remove every rivet, bolt, edge and shadow from this image of the heavy door frame. Replace all hardware, edges and shadows with a continuous rusted, peeling painted steel surface matching the surrounding frame surface. Preserve the extensive dark reddish-brown rust, flaking orange corrosion and scattered broken grey-green paint islands from the reference. Fill the entire image edge to edge with only this continuous flat material surface, lit flat and evenly, without shadows, seams, borders, rivets, bolts or hardware.

## Generation commands and results

### leaf-300, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 300 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-300.png
```

Success: `leaf-300.png`, 512x1088, exit `0`. Log: `leaf-300-attempt-1.log`.

### leaf-301, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 301 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-301.png
```

Success: `leaf-301.png`, 512x1088, exit `0`. Log: `leaf-301-attempt-1.log`.

### leaf-302, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 302 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-302.png
```

Success: `leaf-302.png`, 512x1088, exit `0`. Log: `leaf-302-attempt-1.log`.

### leaf-303, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 303 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-303.png
```

Success: `leaf-303.png`, 512x1088, exit `0`. Log: `leaf-303-attempt-1.log`.

### leaf-304, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 304 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-304.png
```

Success: `leaf-304.png`, 512x1088, exit `0`. Log: `leaf-304-attempt-1.log`.

### leaf-305, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 305 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-305.png
```

Success: `leaf-305.png`, 512x1088, exit `0`. Log: `leaf-305-attempt-1.log`.

### leaf-306, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 306 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-306.png
```

Success: `leaf-306.png`, 512x1088, exit `0`. Log: `leaf-306-attempt-1.log`.

### leaf-307, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 512 --height 1088 --seed 307 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/edit-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/leaf-307.png
```

Success: `leaf-307.png`, 512x1088, exit `0`. Log: `leaf-307-attempt-1.log`.

### frame-400, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 1024 --height 960 --seed 400 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-left-post-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-400.png
```

Success: `frame-400.png`, 1024x960, exit `0`. Log: `frame-400-attempt-1.log`.

### frame-401, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 1024 --height 960 --seed 401 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-left-post-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-401.png
```

Success: `frame-401.png`, 1024x960, exit `0`. Log: `frame-401-attempt-1.log`.

### frame-402, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 1024 --height 960 --seed 402 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-left-post-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-402.png
```

Success: `frame-402.png`, 1024x960, exit `0`. Log: `frame-402-attempt-1.log`.

### frame-403, attempt 1

```sh
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 1024 --height 960 --seed 403 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-left-post-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-prompt.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hatch-model/round8/gen4/frame-403.png
```

Success: `frame-403.png`, 1024x960, exit `0`. Log: `frame-403-attempt-1.log`.

Sheet: `sheet-leaf.png`, 2250x583; 9 labelled columns, each 250 pixels wide.

Sheet: `sheet-frame.png`, 2000x522; 5 labelled columns, each 400 pixels wide.

## Completion

Successful candidates: 12/12. Failed command attempts: 0. See failures.json and attempt logs. All successful PNGs decoded and matched the requested dimensions. No visual judgments were made.
