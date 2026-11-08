# Whole-object door hardware prototype

All output is private to this directory. No game or tracked files changed. No generated mesh cleanup, fitting, squashing, texturing or quality judgments. The driver judges the images.

Read: driver-notes.md final section, leaf3 recipe and inputs, and HUNYUAN3D_WORKFLOW_ANALYSIS.md. Leaf3 used a masked crop directly, not a FLUX edit; this prototype adds the explicitly requested FLUX isolation stage.

Source: `/Volumes/XS1000/acoliver/projects/gone/branch-1/docs/art/corridors/hatch-concept-rusted.png`. Crop boxes below are source pixels, half-open xyxy; RGB crops are copied without resampling. The upper latch dog is selected around source y 225..325; the crop includes its keeper. Crops are generous to include the hinge barrel and all wheel geometry.

FLUX.2-klein-4b, 4-bit, 4 steps, output 768x768, seeds 590/591/592. The preserved edit RGB is matted with existing U2-Net weights for Hunyuan; both edit and RGBA input are saved. Hunyuan full non-turbo, front only, float16, 30 steps, CFG 5, requested octree 512, seeds 600..603 per object. A failed 512 run falls back to 384 after the single Metal retry where applicable. Each subprocess wall time includes model load and export. Timeout 1800 seconds per shape/edit attempt.

CPU Cycles clay renders: neutral grey, three area lights, orthographic front/30/60/90 degrees. Meshes are rendered without geometry edits. Comparison sheets put the concept crop at left and the four seeds to its right, front row then 30-degree row.

Preparation/orchestration command:
```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/run.py prepare
PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 nohup /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/run.py all > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/driver.log 2>&1 &
```

Helper implementations: `run.py`, `matte.py`, `render.py`. U2-Net and Hugging Face caches are read from existing external caches. Writable home, temporary files, Blender and Python caches are redirected here. Foreign GPU work may contend; no foreign process is signalled.

## Input upper-strap-hinge

Crop: `[850, 185, 1080, 395]`. PIL operation: `Image.open(SOURCE).convert("RGB").crop([850, 185, 1080, 395]).save("inputs/upper-strap-hinge/concept-crop.png")`.

Prompt: Isolate the same upper strap hinge, its mounting plate and vertical knuckle barrel together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.

FLUX seed: 590; Hunyuan seeds: 600, 601, 602, 603.

## Input latch-dog

Crop: `[380, 200, 565, 350]`. PIL operation: `Image.open(SOURCE).convert("RGB").crop([380, 200, 565, 350]).save("inputs/latch-dog/concept-crop.png")`.

Prompt: Isolate the same upper latch dog, its horizontal handle lug and keeper together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.

FLUX seed: 591; Hunyuan seeds: 600, 601, 602, 603.

## Input handwheel

Crop: `[490, 340, 890, 740]`. PIL operation: `Image.open(SOURCE).convert("RGB").crop([490, 340, 890, 740]).save("inputs/handwheel/concept-crop.png")`.

Prompt: Isolate the same handwheel, its circular rim, six spokes and central hub together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.

FLUX seed: 592; Hunyuan seeds: 600, 601, 602, 603.

## flux-upper-strap-hinge-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --seed 590 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/concept-crop.png --prompt 'Isolate the same upper strap hinge, its mounting plate and vertical knuckle barrel together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.' --width 768 --height 768 --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/isolated.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/flux-upper-strap-hinge-attempt1.log 2>&1
```

Return code 0; wall time 34.873 seconds; log `logs/flux-upper-strap-hinge-attempt1.log`.

## matte-upper-strap-hinge

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/matte.py /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/isolated.png /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/front-rgba.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/matte-upper-strap-hinge.log 2>&1
```

Return code 0; wall time 19.407 seconds; log `logs/matte-upper-strap-hinge.log`.

## flux-latch-dog-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --seed 591 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/concept-crop.png --prompt 'Isolate the same upper latch dog, its horizontal handle lug and keeper together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.' --width 768 --height 768 --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/isolated.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/flux-latch-dog-attempt1.log 2>&1
```

Return code 0; wall time 28.873 seconds; log `logs/flux-latch-dog-attempt1.log`.

## matte-latch-dog

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/matte.py /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/isolated.png /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/front-rgba.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/matte-latch-dog.log 2>&1
```

Return code 0; wall time 3.227 seconds; log `logs/matte-latch-dog.log`.

## flux-handwheel-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --seed 592 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/concept-crop.png --prompt 'Isolate the same handwheel, its circular rim, six spokes and central hub together as one whole object from the reference image. Same object, isolated, plain grey background, no other parts. Keep its exact shape, proportions, orientation and mechanical details. Remove the door, wall and surrounding hardware; show only this complete object centered with a clear margin on all sides.' --width 768 --height 768 --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/isolated.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/flux-handwheel-attempt1.log 2>&1
```

Return code 0; wall time 29.747 seconds; log `logs/flux-handwheel-attempt1.log`.

## matte-handwheel

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/matte.py /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/isolated.png /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/front-rgba.png > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/matte-handwheel.log 2>&1
```

Return code 0; wall time 2.711 seconds; log `logs/matte-handwheel.log`.

## shape-upper-strap-hinge-s600-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 600 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s600.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-upper-strap-hinge-s600-r512-attempt1.log 2>&1
```

Return code 0; wall time 642.088 seconds; log `logs/shape-upper-strap-hinge-s600-r512-attempt1.log`.

## render-upper-strap-hinge-s600

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s600.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/upper-strap-hinge-s600 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-upper-strap-hinge-s600.log 2>&1
```

Return code 0; wall time 6.699 seconds; log `logs/render-upper-strap-hinge-s600.log`.

## shape-upper-strap-hinge-s601-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 601 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s601.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-upper-strap-hinge-s601-r512-attempt1.log 2>&1
```

Return code 0; wall time 700.475 seconds; log `logs/shape-upper-strap-hinge-s601-r512-attempt1.log`.

## render-upper-strap-hinge-s601

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s601.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/upper-strap-hinge-s601 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-upper-strap-hinge-s601.log 2>&1
```

Return code 0; wall time 9.270 seconds; log `logs/render-upper-strap-hinge-s601.log`.

## shape-upper-strap-hinge-s602-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 602 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s602.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-upper-strap-hinge-s602-r512-attempt1.log 2>&1
```

Return code 0; wall time 697.988 seconds; log `logs/shape-upper-strap-hinge-s602-r512-attempt1.log`.

## render-upper-strap-hinge-s602

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s602.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/upper-strap-hinge-s602 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-upper-strap-hinge-s602.log 2>&1
```

Return code 0; wall time 9.851 seconds; log `logs/render-upper-strap-hinge-s602.log`.

## shape-upper-strap-hinge-s603-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/upper-strap-hinge/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 603 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s603.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-upper-strap-hinge-s603-r512-attempt1.log 2>&1
```

Return code 0; wall time 656.207 seconds; log `logs/shape-upper-strap-hinge-s603-r512-attempt1.log`.

## render-upper-strap-hinge-s603

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/upper-strap-hinge-s603.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/upper-strap-hinge-s603 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-upper-strap-hinge-s603.log 2>&1
```

Return code 0; wall time 6.946 seconds; log `logs/render-upper-strap-hinge-s603.log`.

## shape-latch-dog-s600-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 600 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s600.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-latch-dog-s600-r512-attempt1.log 2>&1
```

Return code 0; wall time 705.506 seconds; log `logs/shape-latch-dog-s600-r512-attempt1.log`.

## render-latch-dog-s600

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s600.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/latch-dog-s600 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-latch-dog-s600.log 2>&1
```

Return code 0; wall time 5.816 seconds; log `logs/render-latch-dog-s600.log`.

## shape-latch-dog-s601-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 601 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s601.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-latch-dog-s601-r512-attempt1.log 2>&1
```

Return code 0; wall time 649.122 seconds; log `logs/shape-latch-dog-s601-r512-attempt1.log`.

## render-latch-dog-s601

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s601.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/latch-dog-s601 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-latch-dog-s601.log 2>&1
```

Return code 0; wall time 4.938 seconds; log `logs/render-latch-dog-s601.log`.

## shape-latch-dog-s602-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 602 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s602.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-latch-dog-s602-r512-attempt1.log 2>&1
```

Return code 0; wall time 626.032 seconds; log `logs/shape-latch-dog-s602-r512-attempt1.log`.

## render-latch-dog-s602

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s602.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/latch-dog-s602 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-latch-dog-s602.log 2>&1
```

Return code 0; wall time 5.580 seconds; log `logs/render-latch-dog-s602.log`.

## shape-latch-dog-s603-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/latch-dog/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 603 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s603.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-latch-dog-s603-r512-attempt1.log 2>&1
```

Return code 0; wall time 680.837 seconds; log `logs/shape-latch-dog-s603-r512-attempt1.log`.

## render-latch-dog-s603

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/latch-dog-s603.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/latch-dog-s603 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-latch-dog-s603.log 2>&1
```

Return code 0; wall time 5.878 seconds; log `logs/render-latch-dog-s603.log`.

## shape-handwheel-s600-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 600 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s600.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-handwheel-s600-r512-attempt1.log 2>&1
```

Return code 0; wall time 615.696 seconds; log `logs/shape-handwheel-s600-r512-attempt1.log`.

## render-handwheel-s600

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s600.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/handwheel-s600 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-handwheel-s600.log 2>&1
```

Return code 0; wall time 10.723 seconds; log `logs/render-handwheel-s600.log`.

## shape-handwheel-s601-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 601 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s601.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-handwheel-s601-r512-attempt1.log 2>&1
```

Return code 0; wall time 651.001 seconds; log `logs/shape-handwheel-s601-r512-attempt1.log`.

## render-handwheel-s601

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s601.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/handwheel-s601 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-handwheel-s601.log 2>&1
```

Return code 0; wall time 5.224 seconds; log `logs/render-handwheel-s601.log`.

## shape-handwheel-s602-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 602 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s602.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-handwheel-s602-r512-attempt1.log 2>&1
```

Return code 0; wall time 513.806 seconds; log `logs/shape-handwheel-s602-r512-attempt1.log`.

## render-handwheel-s602

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s602.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/handwheel-s602 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-handwheel-s602.log 2>&1
```

Return code 0; wall time 4.664 seconds; log `logs/render-handwheel-s602.log`.

## shape-handwheel-s603-r512-attempt1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/inputs/handwheel/front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 512 --seed 603 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s603.glb > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/shape-handwheel-s603-r512-attempt1.log 2>&1
```

Return code 0; wall time 514.303 seconds; log `logs/shape-handwheel-s603-r512-attempt1.log`.

## render-handwheel-s603

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto
HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/home XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/xdg TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/tmp NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/matplotlib BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/cache/blender/datafiles HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 U2NET_HOME=/Users/acoliver/.u2net /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/meshes/handwheel-s603.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/renders/handwheel-s603 > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/parts-proto/logs/render-handwheel-s603.log 2>&1
```

Return code 0; wall time 4.633 seconds; log `logs/render-handwheel-s603.log`.

## Completion

Twelve raw meshes, forty-eight clay renders, three comparison sheets and stats.json produced. No visual assessment performed. See stats.json and commands.jsonl for exact timings, attempts and resolution per run.
