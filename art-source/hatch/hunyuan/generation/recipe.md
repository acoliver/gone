# GONE Hunyuan hatch prototype

All generated files and temporary caches are under this directory. The port source and game files are not modified. No Era3D or Instant-NSR is used. No visual judgments are made. Commands are serialized, including all paint jobs. Timings are measured wall-clock seconds.

Run from this directory with the port Python: `/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py inputs`, then `shape`, then `finish`. Or use `all`.

Full shape model: hunyuan3d-dit-v2-mv, fp16, 30 steps, CFG 5.0, octree 384, seeds 410/411/412/413. A paired seed-410 front+left trial is added per category. Native model coordinates are x=horizontal, y=up, z=front, with no assumed physical units. No geometry smoothing, decimation, or component removal.

Paint selection is provisional and numerical: watertight first, then alpha-silhouette IoU, then largest-component face fraction. This cannot certify semantic fidelity or mechanical usability. Driver inspection is required. Every mesh gets concept-derived front-projection texture; selected two per category also get Hunyuan Paint with default 50-step Delight, paint resolution 768 and texture 2048.

A/B slab thickness is measured by front-to-back ray intersections through off-wheel interior patches, excluding silhouette/hardware bands; statistics describe ray span, not a guaranteed separated semantic slab. C has no leaf, so leaf thickness is not applicable.

Preparation command:
```sh
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py inputs
```

### flux-A-front, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 310 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/A-front.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front.png
```

Return code 0; elapsed 33.39 seconds; log `logs/flux-A-front-1.log`.

### flux-A-left, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 320 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/A-left.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-left.png
```

Return code 0; elapsed 26.33 seconds; log `logs/flux-A-left-1.log`.

### flux-B-front, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 310 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/B-front.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front.png
```

Return code 0; elapsed 26.48 seconds; log `logs/flux-B-front-1.log`.

### flux-B-left, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 320 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/B-left.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-left.png
```

Return code 0; elapsed 34.19 seconds; log `logs/flux-B-left-1.log`.

### flux-C-front, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 310 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/C-front.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front.png
```

Return code 0; elapsed 44.13 seconds; log `logs/flux-C-front-1.log`.

### flux-C-left, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/tools/mlximg-venv/bin/mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width 768 --height 1024 --seed 320 --image-paths /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front.png --prompt-file /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/prompts/C-left.txt --metadata --output /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-left.png
```

Return code 0; elapsed 40.24 seconds; log `logs/flux-C-left-1.log`.

Input alpha diagnostics:
```json
{
  "A": {
    "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
    "foreground_fraction": 0.7115478515625,
    "central_third_foreground_fraction": 1.0,
    "alpha_bbox": [
      83,
      23,
      705,
      993
    ],
    "left": {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-left-rgba.png",
      "foreground_fraction": 0.481170654296875,
      "central_third_foreground_fraction": 0.9962426686217009,
      "alpha_bbox": [
        178,
        22,
        721,
        994
      ]
    }
  },
  "B": {
    "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
    "foreground_fraction": 0.6060829162597656,
    "central_third_foreground_fraction": 1.0,
    "alpha_bbox": [
      123,
      32,
      658,
      995
    ],
    "left": {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-left-rgba.png",
      "foreground_fraction": 0.3373146057128906,
      "central_third_foreground_fraction": 0.8652515579178885,
      "alpha_bbox": [
        279,
        21,
        625,
        1000
      ]
    }
  },
  "C": {
    "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
    "foreground_fraction": 0.23353703816731772,
    "central_third_foreground_fraction": 0.0,
    "alpha_bbox": [
      60,
      40,
      714,
      969
    ],
    "left": {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-left-rgba.png",
      "foreground_fraction": 0.25147247314453125,
      "central_third_foreground_fraction": 0.0,
      "alpha_bbox": [
        61,
        41,
        704,
        969
      ]
    }
  }
}
```
Near-white key: RGB minimum >=235, chroma range <=18, white connected region at least 48 pixels. Interior white regions are also removed so C retains its opening. Input images must be inspected by the driver; mask checks do not establish semantic correctness.

### shape-A-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb
```

Return code 0; elapsed 281.13 seconds; log `logs/shape-A-s410-sv-1.log`.

### shape-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 411 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb
```

## Background orchestration

```sh
/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py shape
# CPU-only Blender rendering overlaps shape generation; painting starts after the shape runner exits.
/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/watch_finish.py 31842
```
The watcher polls the owned shape runner with `ps`; it sends no signals. Renderer smoke test used a disposable box under cache/render-smoke.glb and generated five views successfully. Input FLUX generation took six sequential calls; all returned zero. Side-reference masks are not certified as orthographic, so multiview results are experimental.

### render-A-s410-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv shaded
```

Return code 0; elapsed 16.94 seconds; log `logs/render-A-s410-sv-shaded-1.log`.

### render-A-s410-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png
```

Return code 0; elapsed 25.16 seconds; log `logs/render-A-s410-sv-projection-1.log`.

Return code 0; elapsed 275.21 seconds; log `logs/shape-A-s411-sv-1.log`.

### shape-A-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 412 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s412-sv.glb
```

### render-A-s411-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv shaded
```

Return code 0; elapsed 12.79 seconds; log `logs/render-A-s411-sv-shaded-1.log`.

### render-A-s411-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png
```

Return code 0; elapsed 20.92 seconds; log `logs/render-A-s411-sv-projection-1.log`.

Return code 0; elapsed 358.55 seconds; log `logs/shape-A-s412-sv-1.log`.

### shape-A-s413-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 413 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s413-sv.glb
```

### render-A-s412-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s412-sv shaded
```

Return code 0; elapsed 13.68 seconds; log `logs/render-A-s412-sv-shaded-1.log`.

### render-A-s412-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s412-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png
```

Return code 0; elapsed 26.69 seconds; log `logs/render-A-s412-sv-projection-1.log`.

Return code 0; elapsed 349.84 seconds; log `logs/shape-A-s413-sv-1.log`.

### shape-A-s410-mv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-mv.glb --left /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-left-rgba.png
```

### render-A-s413-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s413-sv shaded
```

Return code 0; elapsed 14.22 seconds; log `logs/render-A-s413-sv-shaded-1.log`.

### render-A-s413-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s413-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png
```

Return code 0; elapsed 28.77 seconds; log `logs/render-A-s413-sv-projection-1.log`.

Return code 0; elapsed 376.26 seconds; log `logs/shape-A-s410-mv-1.log`.

### shape-B-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb
```

### render-A-s410-mv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-mv shaded
```

Return code 0; elapsed 13.73 seconds; log `logs/render-A-s410-mv-shaded-1.log`.

### render-A-s410-mv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-mv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-assembly-crop.png
```

Return code 0; elapsed 23.70 seconds; log `logs/render-A-s410-mv-projection-1.log`.

Return code 0; elapsed 346.20 seconds; log `logs/shape-B-s410-sv-1.log`.

### shape-B-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 411 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s411-sv.glb
```

### render-B-s410-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv shaded
```

Return code 0; elapsed 16.85 seconds; log `logs/render-B-s410-sv-shaded-1.log`.

### render-B-s410-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png
```

Return code 0; elapsed 24.37 seconds; log `logs/render-B-s410-sv-projection-1.log`.

## Launcher and verification commands

Run scripts with the port Python. The scripts are not executable entry points.
~~~sh
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py inputs
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py shape
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/run.py finish
~~~
The watcher command for this run is: /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/watch_finish.py 31842. The PID is run-specific; for reproduction run finish after shape.

The five-angle renderer was smoke-tested using a disposable 0.8 x 1.8 x 0.1 box. The thickness helper returned 0.1 within 1e-6. First-mesh measurements are saved in cache/first-mesh-stats.json.

Monitoring-only shell failures: a silent sleep hit the 120-second inactivity limit; a monitoring loop hit the configured 900-second foreground maximum. Neither stopped generation or rendering. Later monitors use shorter durations and periodic output. No model command has failed at this point.

Return code 0; elapsed 273.00 seconds; log `logs/shape-B-s411-sv-1.log`.

### shape-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 412 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb
```

### render-B-s411-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s411-sv shaded
```

Return code 0; elapsed 7.55 seconds; log `logs/render-B-s411-sv-shaded-1.log`.

### render-B-s411-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s411-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png
```

Return code 0; elapsed 11.40 seconds; log `logs/render-B-s411-sv-projection-1.log`.

Return code 0; elapsed 426.05 seconds; log `logs/shape-B-s412-sv-1.log`.

### shape-B-s413-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 413 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s413-sv.glb
```

### render-B-s412-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv shaded
```

Return code 0; elapsed 6.05 seconds; log `logs/render-B-s412-sv-shaded-1.log`.

### render-B-s412-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png
```

Return code 0; elapsed 11.04 seconds; log `logs/render-B-s412-sv-projection-1.log`.

Return code 0; elapsed 266.23 seconds; log `logs/shape-B-s413-sv-1.log`.

### shape-B-s410-mv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-mv.glb --left /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-left-rgba.png
```

### render-B-s413-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s413-sv shaded
```

Return code 0; elapsed 9.81 seconds; log `logs/render-B-s413-sv-shaded-1.log`.

### render-B-s413-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s413-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png
```

Return code 0; elapsed 13.04 seconds; log `logs/render-B-s413-sv-projection-1.log`.

Return code 0; elapsed 303.61 seconds; log `logs/shape-B-s410-mv-1.log`.

### shape-C-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb
```

### render-B-s410-mv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-mv shaded
```

Return code 0; elapsed 17.37 seconds; log `logs/render-B-s410-mv-shaded-1.log`.

### render-B-s410-mv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-mv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/concept-leaf-crop.png
```

Return code 0; elapsed 24.57 seconds; log `logs/render-B-s410-mv-projection-1.log`.

Return code 0; elapsed 276.43 seconds; log `logs/shape-C-s410-sv-1.log`.

### shape-C-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 411 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb
```

### render-C-s410-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv shaded
```

Return code 0; elapsed 19.58 seconds; log `logs/render-C-s410-sv-shaded-1.log`.

### render-C-s410-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png
```

Return code 0; elapsed 28.74 seconds; log `logs/render-C-s410-sv-projection-1.log`.

Return code 0; elapsed 282.92 seconds; log `logs/shape-C-s411-sv-1.log`.

### shape-C-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 412 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s412-sv.glb
```

### render-C-s411-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv shaded
```

Return code 0; elapsed 18.37 seconds; log `logs/render-C-s411-sv-shaded-1.log`.

### render-C-s411-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png
```

Return code 0; elapsed 26.45 seconds; log `logs/render-C-s411-sv-projection-1.log`.

Return code 0; elapsed 493.73 seconds; log `logs/shape-C-s412-sv-1.log`.

### shape-C-s413-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 413 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s413-sv.glb
```

### render-C-s412-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s412-sv shaded
```

Return code 0; elapsed 13.20 seconds; log `logs/render-C-s412-sv-shaded-1.log`.

### render-C-s412-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s412-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png
```

Return code 0; elapsed 17.85 seconds; log `logs/render-C-s412-sv-projection-1.log`.

Return code 0; elapsed 470.44 seconds; log `logs/shape-C-s413-sv-1.log`.

### shape-C-s410-mv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 410 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-mv.glb --left /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-left-rgba.png
```

### render-C-s413-sv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s413-sv shaded
```

Return code 0; elapsed 15.13 seconds; log `logs/render-C-s413-sv-shaded-1.log`.

### render-C-s413-sv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s413-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s413-sv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png
```

Return code 0; elapsed 24.31 seconds; log `logs/render-C-s413-sv-projection-1.log`.

Return code 0; elapsed 581.86 seconds; log `logs/shape-C-s410-mv-1.log`.

### render-C-s410-mv-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-mv shaded
```

Return code 0; elapsed 2.96 seconds; log `logs/render-C-s410-mv-shaded-1.log`.

### render-C-s410-mv-projection, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-mv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-mv projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png
```

Return code 0; elapsed 5.62 seconds; log `logs/render-C-s410-mv-projection-1.log`.

Paint candidates selected provisionally by geometry metrics:
```json
{
  "A": [
    "A-s410-sv",
    "A-s411-sv"
  ],
  "B": [
    "B-s410-sv",
    "B-s412-sv"
  ],
  "C": [
    "C-s411-sv",
    "C-s410-sv"
  ]
}
```

### paint-A-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/paint.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2 --subfolder hunyuan3d-paint-v2-0-turbo --resolution 768 --texture-size 2048 --seed 510 --save-views /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint/generated-views.png --save-bake-diagnostics /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint/bake.npz --memory-limit-gb 48 --metallic 0 --roughness 0.85
```

## Paint UV change

The original paint.py call completed 50-step Delight and 10-step paint inference, then remained CPU-active inside xatlas dense-mesh unwrap. At 880 seconds elapsed the owned paint child 83071 and owned watcher 48342 were explicitly terminated. Its original log is preserved as logs/paint-A-s410-sv-cli-xatlas-1.log. This was not a Metal hang and no GPU retry was needed.

Blender Smart Project prepared the same mesh UVs in a 6.98-second process, without decimation, smoothing, face deletion or geometry repair. Command:
~~~sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s410-sv.glb
~~~
Subsequent paint uses paint_frozen.py with the port DelightPipeline and PaintPipeline plus its supported atlas_uvs argument. The wrapper exports the caller-owned source frame, since that API branch returns paint-frame vertices. No port source is edited. UVs: Smart Project 66 degrees, island margin 0.005; paint: fp16 turbo, 10 steps, seed 510, 768-pixel views, 2048 texture, default six cameras; Delight 50 steps, seed 42; MLX allocation cap 48 GiB. Geometry is checked against the source before painting and again at completion. All original raw meshes and projection exports are retained.

Paint candidates selected provisionally by geometry metrics:
```json
{
  "A": [
    "A-s410-sv",
    "A-s411-sv"
  ],
  "B": [
    "B-s410-sv",
    "B-s412-sv"
  ],
  "C": [
    "C-s411-sv",
    "C-s410-sv"
  ]
}
```

### paint-A-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint
```

Return code 1; elapsed 1.61 seconds; log `logs/paint-A-s410-sv-1.log`.

### uv-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s411-sv.glb
```

Return code 0; elapsed 3.97 seconds; log `logs/uv-A-s411-sv-1.log`.

### paint-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s411-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint
```

Return code 1; elapsed 1.93 seconds; log `logs/paint-A-s411-sv-1.log`.

### uv-B-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s410-sv.glb
```

Return code 0; elapsed 2.75 seconds; log `logs/uv-B-s410-sv-1.log`.

### paint-B-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint
```

Return code 1; elapsed 1.48 seconds; log `logs/paint-B-s410-sv-1.log`.

### uv-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s412-sv.glb
```

Return code 0; elapsed 3.07 seconds; log `logs/uv-B-s412-sv-1.log`.

### paint-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s412-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint
```

Return code 1; elapsed 1.35 seconds; log `logs/paint-B-s412-sv-1.log`.

### uv-C-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s411-sv.glb
```

Return code 0; elapsed 3.11 seconds; log `logs/uv-C-s411-sv-1.log`.

### paint-C-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s411-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint
```

Return code 1; elapsed 1.31 seconds; log `logs/paint-C-s411-sv-1.log`.

### uv-C-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s410-sv.glb
```

Return code 0; elapsed 2.46 seconds; log `logs/uv-C-s410-sv-1.log`.

### paint-C-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint
```

Return code 1; elapsed 0.93 seconds; log `logs/paint-C-s410-sv-1.log`.

## Completion

{
  "mesh_variants": 30,
  "shape_meshes": 15,
  "selected": {
    "A": [
      "A-s410-sv",
      "A-s411-sv"
    ],
    "B": [
      "B-s410-sv",
      "B-s412-sv"
    ],
    "C": [
      "C-s411-sv",
      "C-s410-sv"
    ]
  },
  "seconds_by_stage": {
    "flux": 204.75600516592385,
    "shape": 5361.45328299806,
    "render": 510.865480124834,
    "paint": 888.5984836680582,
    "uv": 22.340050292045344
  },
  "failed_attempts": [
    {
      "name": "paint-cli-xatlas-A-s410-sv",
      "attempt": 1,
      "seconds": 880.0,
      "returncode": -15,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-cli-xatlas-1.log",
      "reason": "Explicitly interrupted owned process after 14:40 elapsed; model inference finished, dense xatlas unwrap still consumed CPU; no Metal error."
    },
    {
      "name": "paint-A-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint"
      ],
      "seconds": 1.6050381250097416,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-1.log"
    },
    {
      "name": "paint-A-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint"
      ],
      "seconds": 1.925034791987855,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s411-sv-1.log"
    },
    {
      "name": "paint-B-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint"
      ],
      "seconds": 1.4825445839669555,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s410-sv-1.log"
    },
    {
      "name": "paint-B-s412-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s412-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint"
      ],
      "seconds": 1.3451186250313185,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s412-sv-1.log"
    },
    {
      "name": "paint-C-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint"
      ],
      "seconds": 1.3132223330321722,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s411-sv-1.log"
    },
    {
      "name": "paint-C-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint"
      ],
      "seconds": 0.9275252090301365,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s410-sv-1.log"
    }
  ],
  "sheets": [
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-inputs.png"
  ],
  "stats": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/stats.json",
  "multiview": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/multiview-comparison.json"
}

Renders: five orthographic views at 0,30,60,90,180 degrees, 512 pixels square per image. Contact-sheet panels are 512 pixels high excluding their 68-pixel label headers. Main category sheets contain a shaded row and a projection row per shape, plus Paint+Delight rows for selected meshes. Paint exports have an additional shaded set. Raw watertightness and welded watertightness are both reported because UV seams duplicate vertices. Paint.py recenters and uniformly rescales its input; that does not repair or regenerate geometry. Front projection is an image-comparison baseline, retains source lighting, and has neutral rust on back/edge faces. A/B projection uses the original concept crops, while C uses the concept-derived FLUX empty-frame edit.

No visual judgments made. No meshes are production-approved or installed in the game. No metric dimensions are inferred. The side views are generated hypotheses, not measured orthographic references.

Frozen-UV adapter preflight failed for six meshes before model loading: the UV GLB had TEXCOORD_0 but no material, and Trimesh loaded ColorVisuals and discarded UVs. This was an adapter input-contract error. The Blender UV exporter now supplies a packed 1x1 white carrier material. No geometry changes; carrier appearance is discarded before Hunyuan texturing. Original six error logs are preserved, and new logs have unique suffixes.

### uv-A-s410-sv-carrier, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s410-sv.glb
```

Return code 0; elapsed 2.12 seconds; log `logs/uv-A-s410-sv-carrier-1-353334159642000.log`.

Paint candidates selected provisionally by geometry metrics:
```json
{
  "A": [
    "A-s410-sv",
    "A-s411-sv"
  ],
  "B": [
    "B-s410-sv",
    "B-s412-sv"
  ],
  "C": [
    "C-s411-sv",
    "C-s410-sv"
  ]
}
```

### paint-A-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint
```

Return code 0; elapsed 85.07 seconds; log `logs/paint-A-s410-sv-1-353384083333208.log`.

### render-A-s410-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint textured
```

Return code 0; elapsed 5.47 seconds; log `logs/render-A-s410-sv-paint-textured-1-353471021764541.log`.

### render-A-s410-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint shaded
```

Return code 0; elapsed 5.47 seconds; log `logs/render-A-s410-sv-paint-shaded-1-353476497278708.log`.

### uv-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s411-sv.glb
```

Return code 0; elapsed 3.76 seconds; log `logs/uv-A-s411-sv-1-353481967806708.log`.

### paint-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s411-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint
```

Return code 1; elapsed 0.82 seconds; log `logs/paint-A-s411-sv-1-353485725965875.log`.

### uv-B-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s410-sv.glb
```

Return code 0; elapsed 2.48 seconds; log `logs/uv-B-s410-sv-1-353486544232541.log`.

### paint-B-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint
```

Return code 0; elapsed 109.68 seconds; log `logs/paint-B-s410-sv-1-353489028290041.log`.

### render-B-s410-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint textured
```

Return code 0; elapsed 5.48 seconds; log `logs/render-B-s410-sv-paint-textured-1-353600121380416.log`.

### render-B-s410-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint shaded
```

Return code 0; elapsed 5.22 seconds; log `logs/render-B-s410-sv-paint-shaded-1-353605602496416.log`.

### uv-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s412-sv.glb
```

Return code 0; elapsed 2.31 seconds; log `logs/uv-B-s412-sv-1-353610826770541.log`.

### paint-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s412-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint
```

Return code 1; elapsed 0.93 seconds; log `logs/paint-B-s412-sv-1-353613137183583.log`.

### uv-C-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/C-s411-sv.glb
```

Return code 0; elapsed 2.05 seconds; log `logs/uv-C-s411-sv-1-353614074007041.log`.

### paint-C-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/C-s411-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint
```

## Exact zero-area cleanup

The UV carrier preflight passed. Further face-count checks found that the Blender importer/exporter removes exact zero-area source triangles with repeated vertex indices. Measured raw/UV counts: A-s411-sv 599268/599266 (2 zero-area faces), B-s412-sv 378104/378086 (18 zero-area faces), C-s410-sv 277912/277904 (8 zero-area faces). A-s410-sv, B-s410-sv and C-s411-sv have zero such faces. Total surface area is unchanged. The adapter now explicitly validates UV face count against positive-area source faces, compares total area and checks both directions of positive-area face-centre correspondence. All original source meshes remain unchanged. This bounded cleanup removes no positive-area face and does not decimate, smooth, fill holes or reshape hardware. Failed preflight calls occurred before model loading and are retained in commands.jsonl.

Return code 0; elapsed 129.00 seconds; log `logs/paint-C-s411-sv-1-353616166934208.log`.

### render-C-s411-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint textured
```

Return code 0; elapsed 3.28 seconds; log `logs/render-C-s411-sv-paint-textured-1-353745679993416.log`.

### render-C-s411-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint shaded
```

Return code 0; elapsed 3.16 seconds; log `logs/render-C-s411-sv-paint-shaded-1-353748964260791.log`.

### uv-C-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_uv.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/C-s410-sv.glb
```

Return code 0; elapsed 1.45 seconds; log `logs/uv-C-s410-sv-1-353752127980791.log`.

### paint-C-s410-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/C-s410-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint
```

Return code 0; elapsed 124.73 seconds; log `logs/paint-C-s410-sv-1-353753578628250.log`.

### render-C-s410-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint textured
```

Return code 0; elapsed 4.70 seconds; log `logs/render-C-s410-sv-paint-textured-1-353878974950666.log`.

### render-C-s410-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint shaded
```

Return code 0; elapsed 4.51 seconds; log `logs/render-C-s410-sv-paint-shaded-1-353883675796541.log`.

## Completion

{
  "mesh_variants": 34,
  "shape_meshes": 15,
  "selected": {
    "A": [
      "A-s410-sv",
      "A-s411-sv"
    ],
    "B": [
      "B-s410-sv",
      "B-s412-sv"
    ],
    "C": [
      "C-s411-sv",
      "C-s410-sv"
    ]
  },
  "seconds_by_stage": {
    "flux": 204.75600516592385,
    "shape": 5361.45328299806,
    "render": 548.1605737928767,
    "paint": 1338.828883542039,
    "uv": 36.50752104302636
  },
  "failed_attempts": [
    {
      "name": "paint-cli-xatlas-A-s410-sv",
      "attempt": 1,
      "seconds": 880.0,
      "returncode": -15,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-cli-xatlas-1.log",
      "reason": "Explicitly interrupted owned process after 14:40 elapsed; model inference finished, dense xatlas unwrap still consumed CPU; no Metal error."
    },
    {
      "name": "paint-A-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint"
      ],
      "seconds": 1.6050381250097416,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-1.log"
    },
    {
      "name": "paint-A-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint"
      ],
      "seconds": 1.925034791987855,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s411-sv-1.log"
    },
    {
      "name": "paint-B-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint"
      ],
      "seconds": 1.4825445839669555,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s410-sv-1.log"
    },
    {
      "name": "paint-B-s412-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s412-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint"
      ],
      "seconds": 1.3451186250313185,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s412-sv-1.log"
    },
    {
      "name": "paint-C-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint"
      ],
      "seconds": 1.3132223330321722,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s411-sv-1.log"
    },
    {
      "name": "paint-C-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint"
      ],
      "seconds": 0.9275252090301365,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s410-sv-1.log"
    },
    {
      "name": "paint-A-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint"
      ],
      "seconds": 0.8166879579657689,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s411-sv-1-353485725965875.log"
    },
    {
      "name": "paint-B-s412-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s412-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint"
      ],
      "seconds": 0.9338629159610718,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s412-sv-1-353613137183583.log"
    }
  ],
  "sheets": [
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-inputs.png"
  ],
  "stats": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/stats.json",
  "multiview": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/multiview-comparison.json"
}

Renders: five orthographic views at 0,30,60,90,180 degrees, 512 pixels square per image. Contact-sheet panels are 512 pixels high excluding their 68-pixel label headers. Main category sheets contain a shaded row and a projection row per shape, plus Paint+Delight rows for selected meshes. Paint exports have an additional shaded set. Raw watertightness and welded watertightness are both reported because UV seams duplicate vertices. Paint.py recenters and uniformly rescales its input; that does not repair or regenerate geometry. Front projection is an image-comparison baseline, retains source lighting, and has neutral rust on back/edge faces. A/B projection uses the original concept crops, while C uses the concept-derived FLUX empty-frame edit.

No visual judgments made. No meshes are production-approved or installed in the game. No metric dimensions are inferred. The side views are generated hypotheses, not measured orthographic references.

Paint candidates selected provisionally by geometry metrics:
```json
{
  "A": [
    "A-s410-sv",
    "A-s411-sv"
  ],
  "B": [
    "B-s410-sv",
    "B-s412-sv"
  ],
  "C": [
    "C-s411-sv",
    "C-s410-sv"
  ]
}
```

### paint-A-s411-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s411-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint
```

Return code 0; elapsed 67.10 seconds; log `logs/paint-A-s411-sv-1-353996202773291.log`.

### render-A-s411-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint textured
```

Return code 0; elapsed 4.71 seconds; log `logs/render-A-s411-sv-paint-textured-1-354065092934583.log`.

### render-A-s411-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint shaded
```

Return code 0; elapsed 4.25 seconds; log `logs/render-A-s411-sv-paint-shaded-1-354069802939041.log`.

### paint-B-s412-sv, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py --mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb --uv-mesh /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s412-sv.glb --image /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb --save-dir /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint
```

Return code 0; elapsed 108.61 seconds; log `logs/paint-B-s412-sv-1-354075109155833.log`.

### render-B-s412-sv-paint-textured, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint textured
```

Return code 0; elapsed 4.31 seconds; log `logs/render-B-s412-sv-paint-textured-1-354184908360125.log`.

### render-B-s412-sv-paint-shaded, attempt 1

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch
HF_HOME=/Volumes/XS1000/hf-cache HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/tmp /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint shaded
```

Return code 0; elapsed 4.27 seconds; log `logs/render-B-s412-sv-paint-shaded-1-354189218223291.log`.

## Completion

{
  "mesh_variants": 36,
  "shape_meshes": 15,
  "selected": {
    "A": [
      "A-s410-sv",
      "A-s411-sv"
    ],
    "B": [
      "B-s410-sv",
      "B-s412-sv"
    ],
    "C": [
      "C-s411-sv",
      "C-s410-sv"
    ]
  },
  "seconds_by_stage": {
    "flux": 204.75600516592385,
    "shape": 5361.45328299806,
    "render": 565.6978572928347,
    "paint": 1514.5323084589909,
    "uv": 36.50752104302636
  },
  "failed_attempts": [
    {
      "name": "paint-cli-xatlas-A-s410-sv",
      "attempt": 1,
      "seconds": 880.0,
      "returncode": -15,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-cli-xatlas-1.log",
      "reason": "Explicitly interrupted owned process after 14:40 elapsed; model inference finished, dense xatlas unwrap still consumed CPU; no Metal error."
    },
    {
      "name": "paint-A-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/paint"
      ],
      "seconds": 1.6050381250097416,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s410-sv-1.log"
    },
    {
      "name": "paint-A-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/A-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint"
      ],
      "seconds": 1.925034791987855,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s411-sv-1.log"
    },
    {
      "name": "paint-B-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/paint"
      ],
      "seconds": 1.4825445839669555,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s410-sv-1.log"
    },
    {
      "name": "paint-B-s412-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/B-s412-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint"
      ],
      "seconds": 1.3451186250313185,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s412-sv-1.log"
    },
    {
      "name": "paint-C-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/paint"
      ],
      "seconds": 1.3132223330321722,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s411-sv-1.log"
    },
    {
      "name": "paint-C-s410-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv/C-s410-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/C-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/paint"
      ],
      "seconds": 0.9275252090301365,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-C-s410-sv-1.log"
    },
    {
      "name": "paint-A-s411-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/A-s411-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/A-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/paint"
      ],
      "seconds": 0.8166879579657689,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-A-s411-sv-1-353485725965875.log"
    },
    {
      "name": "paint-B-s412-sv",
      "attempt": 1,
      "argv": [
        "/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/paint_frozen.py",
        "--mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv.glb",
        "--uv-mesh",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/cache/uv-textured/B-s412-sv.glb",
        "--image",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/inputs/B-front-rgba.png",
        "--out",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
        "--save-dir",
        "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/paint"
      ],
      "seconds": 0.9338629159610718,
      "returncode": 1,
      "log": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/logs/paint-B-s412-sv-1-353613137183583.log"
    }
  ],
  "sheets": [
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-A.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-B.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C-overview.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-C.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/sheet-inputs.png"
  ],
  "stats": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/stats.json",
  "multiview": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/multiview-comparison.json"
}

Renders: five orthographic views at 0,30,60,90,180 degrees, 512 pixels square per image. Contact-sheet panels are 512 pixels high excluding their 68-pixel label headers. Main category sheets contain a shaded row and a projection row per shape, plus Paint+Delight rows for selected meshes. Paint exports have an additional shaded set. Raw watertightness and welded watertightness are both reported because UV seams duplicate vertices. Paint.py recenters and uniformly rescales its input; that does not repair or regenerate geometry. Front projection is an image-comparison baseline, retains source lighting, and has neutral rust on back/edge faces. A/B projection uses the original concept crops, while C uses the concept-derived FLUX empty-frame edit.

No visual judgments made. No meshes are production-approved or installed in the game. No metric dimensions are inferred. The side views are generated hypotheses, not measured orthographic references.

## Verification

Command: /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/verify.py must be run with the port Python.

{
  "shape_meshes": 15,
  "projection_meshes": 15,
  "paint_delight_meshes": 6,
  "decoded_pngs": 254,
  "geometry_preservation": [
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-mv/A-s410-mv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 24,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s410-sv/A-s410-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s411-sv/A-s411-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 2,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s412-sv/A-s412-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 14,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/A-s413-sv/A-s413-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 44,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-mv/B-s410-mv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 28,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s410-sv/B-s410-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s411-sv/B-s411-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 14,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s412-sv/B-s412-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 18,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/B-s413-sv/B-s413-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 6,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-mv/C-s410-mv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 12,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s410-sv/C-s410-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 8,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s411-sv/C-s411-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s412-sv/C-s412-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 10,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/renders/C-s413-sv/C-s413-sv-projection.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 12,
      "maximum_bidirectional_vertex_deviation": 0.0,
      "maximum_bidirectional_positive_face_centre_deviation": 0.0,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s410-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 4.241370932201034e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 3.880360672061944e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/A-s411-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 2,
      "maximum_bidirectional_vertex_deviation": 4.350691178597385e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 3.900555495236009e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s410-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 4.175803861713916e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 3.7252437828615253e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/B-s412-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 18,
      "maximum_bidirectional_vertex_deviation": 4.158898734878336e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 3.7361093096599984e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s411-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 0,
      "maximum_bidirectional_vertex_deviation": 4.206105704692357e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 4.0628129369923425e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/meshes/C-s410-sv-paint.glb",
      "positive_area_faces_preserved": true,
      "exact_zero_area_faces_removed": 8,
      "maximum_bidirectional_vertex_deviation": 4.2056276160036405e-08,
      "maximum_bidirectional_positive_face_centre_deviation": 3.8454046674930255e-08,
      "normalization": "paint recenters bbox and uniformly rescales; projection preserves original native frame"
    }
  ],
  "visual_judgments_made": false,
  "validated_category_sheets": {
    "A": [
      2560,
      6960
    ],
    "B": [
      2560,
      6960
    ],
    "C": [
      2560,
      6960
    ]
  }
}

All expected seed/settings combinations, mesh variant counts, five-angle render sets and category-sheet dimensions were checked. Every PNG was decoded, without inspecting its appearance. Texture exports preserve all positive-area source faces and vertex positions within 2e-6 after paint uniform normalization. Exact zero-area triangles removed by Blender are counted explicitly; bidirectional positive-area face-centre correspondence is also checked. Slab-thickness unit test passed on a 0.1-thick box. No visual quality judgment is included.

## Final result

All 15 full-model shape candidates, 15 projection exports and six Paint+Delight exports are complete. Earlier Completion sections were intermediate snapshots during adapter work; this section follows successful final verification. No production or visual approval is claimed.

Verification command:
~~~sh
/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/verify.py
~~~

Verification passed: 254 PNGs decode; all expected render sets and 2560 x 6960 category sheets exist; source surface geometry is preserved, with exact zero-area triangle removal explicitly counted. All six painted meshes are watertight after welding UV seam duplicates. Raw UV-split GLBs are not topologically watertight before welding.

Measured cumulative command durations (seconds): FLUX 204.76; full shape 5361.45; Blender renders 565.70; UV preparation 36.51; successful Paint+Delight 624.18. The stopped xatlas paint attempt added 880 seconds, and eight failed adapter preflights occurred before model loading. No shape or FLUX command failed. No Metal retry was used. Durations are subprocess sums, not overall elapsed time, because CPU rendering overlapped shape generation.

### Raw generated meshes

Native normalized units, no physical scale. Slab thickness is the off-wheel 90-ray median described above; C has no leaf.

| Mesh | Vertices | Faces | Raw watertight | Median slab | Front mask IoU |
|---|---:|---:|---|---:|---:|
| A-s410-mv.glb | 444482 | 888948 | False | 0.793612 | 0.973699 |
| A-s410-sv.glb | 282002 | 564032 | True | 0.052520 | 0.972113 |
| A-s411-sv.glb | 299621 | 599268 | False | 0.056750 | 0.987505 |
| A-s412-sv.glb | 365827 | 731700 | False | 0.492382 | 0.977085 |
| A-s413-sv.glb | 270088 | 540244 | False | 0.095732 | 0.971999 |
| B-s410-mv.glb | 339516 | 679104 | False | 0.038655 | 0.972159 |
| B-s410-sv.glb | 183454 | 366924 | True | 0.046738 | 0.973992 |
| B-s411-sv.glb | 181377 | 362784 | False | 0.038436 | 0.973518 |
| B-s412-sv.glb | 189035 | 378104 | False | 0.102865 | 0.979454 |
| B-s413-sv.glb | 185103 | 370228 | False | 0.042767 | 0.978761 |
| C-s410-mv.glb | 211526 | 423064 | False | N/A | 0.847070 |
| C-s410-sv.glb | 138952 | 277912 | False | N/A | 0.889914 |
| C-s411-sv.glb | 142862 | 285724 | True | N/A | 0.830489 |
| C-s412-sv.glb | 134147 | 268304 | False | N/A | 0.865832 |
| C-s413-sv.glb | 136360 | 272732 | False | N/A | 0.865509 |

Complete per-mesh bounds, extents, watertightness (raw and welded), components, thickness distributions and paths for all 36 deliverables: stats.json. Per-command timings and logs: commands.jsonl. Side-view comparisons: multiview-comparison.json. Visual review remains with the driver. No game asset has been replaced or installed.


