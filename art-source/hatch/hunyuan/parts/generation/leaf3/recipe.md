# Complete concept-door hatch leaf generation

Reuses leaf2 `run.py`, `blender_render.py` and `verify.py`, copied locally and adapted only for the corrected crop, two traced hinge extensions, new seeds and verification. Read first: leaf2 recipe, outline parameters, all four Python scripts, and final driver-notes section. Source and references remain read-only. All outputs, logs and writable caches are under this directory. No port or game edits, nested LLxprt processes, signalling of other workers or visual judgments.

Input source: `/Volumes/XS1000/acoliver/projects/gone/branch-1/docs/art/corridors/hatch-concept-rusted.png`. Half-open crop `[345,40,1075,1120]`, 730 x 1080 pixels. Alpha is the leaf2 fitted rounded rectangle UNION two source-gradient-traced right hinge polygons. RGB is unchanged everywhere, including partially transparent edge pixels. Source pixels outside alpha are retained as hidden RGB only. Polygon coordinates and search windows are recorded below and in `inputs/outline.json`. Numerical tracing is not a visual assessment.

Settings: full non-turbo `hunyuan3d-dit-v2-mv`, float16, 30 steps, CFG 5, octree 384, front-only, seeds 430 through 435. No mesh cleanup, scaling or learned paint. Mesh spans use the same 90 bbox-relative rays as leaf2; semantic isolation from wheel/hardware is not established. Projection is a comparison aid with baked source lighting, not a production texture.

## Commands

Read-only inspection used built-in reads of the leaf2 recipe, outline and scripts, `tail -100 ../driver-notes.md`, `git status --short`, `sed -n '1,220p' /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py` and `df -h /Volumes/XS1000`. Numeric hinge probes computed Gaussian-smoothed mean-RGB image gradients, with no image display. Their reproducible tracing implementation is `run.py:trace_hinges`.

Preparation and verification use the port Python with `-B` and `PYTHONDONTWRITEBYTECODE=1`. Every generation and render command, cache environment, return code and duration is appended below automatically. CPU Blender uses factory startup, private HOME/cache paths, 8 threads and 12-sample 512-pixel Cycles renders. No interaction with other Blender/Godot workers.
## Deterministic input

```json
{
  "source": "/Volumes/XS1000/acoliver/projects/gone/branch-1/docs/art/corridors/hatch-concept-rusted.png",
  "source_size": [
    1199,
    1312
  ],
  "crop_xyxy_half_open": [
    345,
    40,
    1075,
    1120
  ],
  "conditioning": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png",
  "outline_source_xyxy": [
    384.6488246463633,
    64.96388401585426,
    990.0,
    1094.0
  ],
  "corner_radius_pixels": 162.3988828845207,
  "corner_fit_rms_pixels": 0.35667243387383757,
  "outline_fit_source": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf2/inputs/outline.json",
  "hinge_traces": [
    {
      "name": "upper",
      "top_search_y": [
        210,
        237
      ],
      "bottom_search_y": [
        318,
        336
      ],
      "right_search_x": [
        1038,
        1051
      ],
      "initial_top_y": 219,
      "initial_bottom_y": 324,
      "polygon_source_xy": [
        [
          982,
          219
        ],
        [
          986,
          219
        ],
        [
          990,
          218
        ],
        [
          994,
          218
        ],
        [
          998,
          217
        ],
        [
          1002,
          215
        ],
        [
          1006,
          215
        ],
        [
          1010,
          215
        ],
        [
          1014,
          215
        ],
        [
          1018,
          215
        ],
        [
          1022,
          218
        ],
        [
          1026,
          219
        ],
        [
          1030,
          218
        ],
        [
          1034,
          218
        ],
        [
          1038,
          218
        ],
        [
          1043,
          219
        ],
        [
          1045,
          223
        ],
        [
          1045,
          227
        ],
        [
          1045,
          231
        ],
        [
          1045,
          235
        ],
        [
          1046,
          239
        ],
        [
          1046,
          243
        ],
        [
          1046,
          247
        ],
        [
          1046,
          251
        ],
        [
          1047,
          255
        ],
        [
          1047,
          259
        ],
        [
          1047,
          263
        ],
        [
          1041,
          267
        ],
        [
          1040,
          271
        ],
        [
          1041,
          275
        ],
        [
          1041,
          279
        ],
        [
          1041,
          283
        ],
        [
          1041,
          287
        ],
        [
          1040,
          291
        ],
        [
          1040,
          295
        ],
        [
          1039,
          299
        ],
        [
          1039,
          303
        ],
        [
          1040,
          307
        ],
        [
          1040,
          311
        ],
        [
          1040,
          315
        ],
        [
          1040,
          319
        ],
        [
          1040,
          323
        ],
        [
          1048,
          324
        ],
        [
          1038,
          325
        ],
        [
          1034,
          325
        ],
        [
          1030,
          327
        ],
        [
          1026,
          327
        ],
        [
          1022,
          327
        ],
        [
          1018,
          326
        ],
        [
          1014,
          323
        ],
        [
          1010,
          323
        ],
        [
          1006,
          323
        ],
        [
          1002,
          324
        ],
        [
          998,
          325
        ],
        [
          994,
          325
        ],
        [
          990,
          320
        ],
        [
          986,
          319
        ],
        [
          982,
          319
        ]
      ]
    },
    {
      "name": "lower",
      "top_search_y": [
        766,
        791
      ],
      "bottom_search_y": [
        880,
        901
      ],
      "right_search_x": [
        1038,
        1055
      ],
      "initial_top_y": 774,
      "initial_bottom_y": 890,
      "polygon_source_xy": [
        [
          982,
          766
        ],
        [
          986,
          772
        ],
        [
          990,
          776
        ],
        [
          994,
          776
        ],
        [
          998,
          774
        ],
        [
          1002,
          774
        ],
        [
          1006,
          774
        ],
        [
          1010,
          775
        ],
        [
          1014,
          778
        ],
        [
          1018,
          775
        ],
        [
          1022,
          775
        ],
        [
          1026,
          775
        ],
        [
          1030,
          775
        ],
        [
          1034,
          779
        ],
        [
          1039,
          774
        ],
        [
          1039,
          778
        ],
        [
          1049,
          782
        ],
        [
          1049,
          786
        ],
        [
          1049,
          790
        ],
        [
          1050,
          794
        ],
        [
          1050,
          798
        ],
        [
          1050,
          802
        ],
        [
          1038,
          806
        ],
        [
          1038,
          810
        ],
        [
          1041,
          814
        ],
        [
          1051,
          818
        ],
        [
          1051,
          822
        ],
        [
          1051,
          826
        ],
        [
          1051,
          830
        ],
        [
          1051,
          834
        ],
        [
          1051,
          838
        ],
        [
          1051,
          842
        ],
        [
          1051,
          846
        ],
        [
          1051,
          850
        ],
        [
          1051,
          854
        ],
        [
          1051,
          858
        ],
        [
          1044,
          862
        ],
        [
          1044,
          866
        ],
        [
          1044,
          870
        ],
        [
          1042,
          874
        ],
        [
          1042,
          878
        ],
        [
          1043,
          882
        ],
        [
          1051,
          886
        ],
        [
          1051,
          890
        ],
        [
          1034,
          893
        ],
        [
          1030,
          893
        ],
        [
          1026,
          893
        ],
        [
          1022,
          890
        ],
        [
          1018,
          890
        ],
        [
          1014,
          893
        ],
        [
          1010,
          893
        ],
        [
          1006,
          890
        ],
        [
          1002,
          890
        ],
        [
          998,
          890
        ],
        [
          994,
          890
        ],
        [
          990,
          884
        ],
        [
          986,
          884
        ],
        [
          982,
          884
        ]
      ]
    }
  ],
  "hinge_polygons_source_xy": [
    [
      [
        982,
        219
      ],
      [
        986,
        219
      ],
      [
        990,
        218
      ],
      [
        994,
        218
      ],
      [
        998,
        217
      ],
      [
        1002,
        215
      ],
      [
        1006,
        215
      ],
      [
        1010,
        215
      ],
      [
        1014,
        215
      ],
      [
        1018,
        215
      ],
      [
        1022,
        218
      ],
      [
        1026,
        219
      ],
      [
        1030,
        218
      ],
      [
        1034,
        218
      ],
      [
        1038,
        218
      ],
      [
        1043,
        219
      ],
      [
        1045,
        223
      ],
      [
        1045,
        227
      ],
      [
        1045,
        231
      ],
      [
        1045,
        235
      ],
      [
        1046,
        239
      ],
      [
        1046,
        243
      ],
      [
        1046,
        247
      ],
      [
        1046,
        251
      ],
      [
        1047,
        255
      ],
      [
        1047,
        259
      ],
      [
        1047,
        263
      ],
      [
        1041,
        267
      ],
      [
        1040,
        271
      ],
      [
        1041,
        275
      ],
      [
        1041,
        279
      ],
      [
        1041,
        283
      ],
      [
        1041,
        287
      ],
      [
        1040,
        291
      ],
      [
        1040,
        295
      ],
      [
        1039,
        299
      ],
      [
        1039,
        303
      ],
      [
        1040,
        307
      ],
      [
        1040,
        311
      ],
      [
        1040,
        315
      ],
      [
        1040,
        319
      ],
      [
        1040,
        323
      ],
      [
        1048,
        324
      ],
      [
        1038,
        325
      ],
      [
        1034,
        325
      ],
      [
        1030,
        327
      ],
      [
        1026,
        327
      ],
      [
        1022,
        327
      ],
      [
        1018,
        326
      ],
      [
        1014,
        323
      ],
      [
        1010,
        323
      ],
      [
        1006,
        323
      ],
      [
        1002,
        324
      ],
      [
        998,
        325
      ],
      [
        994,
        325
      ],
      [
        990,
        320
      ],
      [
        986,
        319
      ],
      [
        982,
        319
      ]
    ],
    [
      [
        982,
        766
      ],
      [
        986,
        772
      ],
      [
        990,
        776
      ],
      [
        994,
        776
      ],
      [
        998,
        774
      ],
      [
        1002,
        774
      ],
      [
        1006,
        774
      ],
      [
        1010,
        775
      ],
      [
        1014,
        778
      ],
      [
        1018,
        775
      ],
      [
        1022,
        775
      ],
      [
        1026,
        775
      ],
      [
        1030,
        775
      ],
      [
        1034,
        779
      ],
      [
        1039,
        774
      ],
      [
        1039,
        778
      ],
      [
        1049,
        782
      ],
      [
        1049,
        786
      ],
      [
        1049,
        790
      ],
      [
        1050,
        794
      ],
      [
        1050,
        798
      ],
      [
        1050,
        802
      ],
      [
        1038,
        806
      ],
      [
        1038,
        810
      ],
      [
        1041,
        814
      ],
      [
        1051,
        818
      ],
      [
        1051,
        822
      ],
      [
        1051,
        826
      ],
      [
        1051,
        830
      ],
      [
        1051,
        834
      ],
      [
        1051,
        838
      ],
      [
        1051,
        842
      ],
      [
        1051,
        846
      ],
      [
        1051,
        850
      ],
      [
        1051,
        854
      ],
      [
        1051,
        858
      ],
      [
        1044,
        862
      ],
      [
        1044,
        866
      ],
      [
        1044,
        870
      ],
      [
        1042,
        874
      ],
      [
        1042,
        878
      ],
      [
        1043,
        882
      ],
      [
        1051,
        886
      ],
      [
        1051,
        890
      ],
      [
        1034,
        893
      ],
      [
        1030,
        893
      ],
      [
        1026,
        893
      ],
      [
        1022,
        890
      ],
      [
        1018,
        890
      ],
      [
        1014,
        893
      ],
      [
        1010,
        893
      ],
      [
        1006,
        890
      ],
      [
        1002,
        890
      ],
      [
        998,
        890
      ],
      [
        994,
        890
      ],
      [
        990,
        884
      ],
      [
        986,
        884
      ],
      [
        982,
        884
      ]
    ]
  ],
  "hinge_trace_method": "Source RGB mean, Gaussian sigma 1.4. Supplied hinge ROIs constrain top/bottom abs vertical-gradient maxima and right negative horizontal-gradient maxima. Sample every 4 px, median filter size 3, polygon union with the fitted leaf. Numerical tracing only; no image display or visual judgement.",
  "alpha_method": "Exact fitted rounded-rectangle signed distance UNION hinge polygons; 4x4 subpixel-center coverage. No RGB modification, resizing, relighting or inpainting.",
  "alpha_bbox_crop": [
    39,
    25,
    706,
    1054
  ],
  "foreground_fraction": 0.7783409436834094,
  "rgb_bytes_unchanged": true,
  "rgb_bytes_unchanged_inside_mask": true,
  "crop_clips_mask": false,
  "limitation": "No crop clipping. Hinge contours are numerically traced inside supplied search regions, not visually reviewed. Generated geometry and projection fidelity are unjudged. Projection retains source lighting.",
  "seconds": 2.0325322500430048
}
```


## Launch and verification commands

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/run.py prepare > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/logs/prepare.log 2>&1
PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 nohup /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/driver.py > /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/logs/driver.log 2>&1 &
PYTHONDONTWRITEBYTECODE=1 /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python -B /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/verify.py
```

The driver sets private cache/environment paths before mesh measurement and launches sequential generation and rendering. Before launch, an independent input check passed: exact 730 x 1080 crop, RGB equality across all pixels and all nonzero-alpha pixels, transparent margin on all sides. Monitoring only reads this run's logs and summary, with no process signals.
### shape-430

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 430 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s430.glb
```

Return code 0; elapsed 385.16 seconds; log `logs/shape-430.log`.

### shape-431

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 431 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s431.glb
```

Return code 0; elapsed 271.45 seconds; log `logs/shape-431.log`.

### shape-432

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 432 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s432.glb
```

Return code 0; elapsed 270.37 seconds; log `logs/shape-432.log`.

### shape-433

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 433 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s433.glb
```

Return code 0; elapsed 396.22 seconds; log `logs/shape-433.log`.

### shape-434

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 434 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s434.glb
```

Return code 0; elapsed 418.68 seconds; log `logs/shape-434.log`.

### shape-435

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/generate.py --model-path /Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/weights/Hunyuan3D-2mv --subfolder hunyuan3d-dit-v2-mv --front /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/concept-leaf-rgba.png --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 --seed 435 --out /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s435.glb
```

Return code 0; elapsed 430.70 seconds; log `logs/shape-435.log`.

### render-430-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s430.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s430 shaded
```

Return code 0; elapsed 4.60 seconds; log `logs/render-430-shaded.log`.

### render-430-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s430.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s430 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 7.45 seconds; log `logs/render-430-projection.log`.

### render-431-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s431.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s431 shaded
```

Return code 0; elapsed 4.56 seconds; log `logs/render-431-shaded.log`.

### render-431-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s431.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s431 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 6.24 seconds; log `logs/render-431-projection.log`.

### render-432-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s432.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s432 shaded
```

Return code 0; elapsed 4.44 seconds; log `logs/render-432-shaded.log`.

### render-432-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s432.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s432 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 6.13 seconds; log `logs/render-432-projection.log`.

### render-433-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s433.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s433 shaded
```

Return code 0; elapsed 4.46 seconds; log `logs/render-433-shaded.log`.

### render-433-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s433.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s433 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 6.13 seconds; log `logs/render-433-projection.log`.

### render-434-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s434.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s434 shaded
```

Return code 0; elapsed 4.24 seconds; log `logs/render-434-shaded.log`.

### render-434-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s434.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s434 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 6.38 seconds; log `logs/render-434-projection.log`.

### render-435-shaded

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s435.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s435 shaded
```

Return code 0; elapsed 4.78 seconds; log `logs/render-435-shaded.log`.

### render-435-projection

```sh
cd /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3
HF_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/huggingface HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/numba MPLCONFIGDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/matplotlib TMPDIR=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/tmp XDG_CACHE_HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/xdg HOME=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/home BLENDER_USER_CONFIG=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/config BLENDER_USER_SCRIPTS=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/scripts BLENDER_USER_DATAFILES=/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/cache/blender/datafiles /Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender --background --factory-startup --threads 8 --python-exit-code 1 --python /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/blender_render.py -- /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s435.glb /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/renders/leaf-s435 projection /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/inputs/projection-reference.png
```

Return code 0; elapsed 6.70 seconds; log `logs/render-435-projection.log`.

## Completion

```json
{
  "meshes": [
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s430.glb",
      "vertices": 256202,
      "faces": 512436,
      "watertight": false,
      "welded_vertices": 256202,
      "welded_watertight": false,
      "bounds": [
        [
          -0.6816734075546265,
          -0.9997913837432861,
          -0.13693788647651672
        ],
        [
          0.6492807269096375,
          0.9946148991584778,
          0.13223153352737427
        ]
      ],
      "extents": [
        1.330954134464264,
        1.994406282901764,
        0.269169420003891
      ],
      "components": 5,
      "largest_component_face_fraction": 0.9999921941471716,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.04974114999999999,
        "p10": 0.04950776,
        "p90": 0.06491316,
        "minimum": 0.0492842,
        "maximum": 0.0658448,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.02494032957398682,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 430,
      "measurement_seconds": 1.4369027080247179
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s431.glb",
      "vertices": 241346,
      "faces": 482720,
      "watertight": true,
      "welded_vertices": 241346,
      "welded_watertight": true,
      "bounds": [
        [
          -0.6661603450775146,
          -0.9998162984848022,
          -0.14853845536708832
        ],
        [
          0.6536638140678406,
          0.994455099105835,
          0.13418777287006378
        ]
      ],
      "extents": [
        1.3198241591453552,
        1.9942713975906372,
        0.2827262282371521
      ],
      "components": 2,
      "largest_component_face_fraction": 0.9999834272456082,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.04381135,
        "p10": 0.04371307000000001,
        "p90": 0.04955839,
        "minimum": 0.04361960000000001,
        "maximum": 0.050420400000000004,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.02196859968654734,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 431,
      "measurement_seconds": 1.4463722079526633
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s432.glb",
      "vertices": 250344,
      "faces": 500740,
      "watertight": false,
      "welded_vertices": 250344,
      "welded_watertight": false,
      "bounds": [
        [
          -0.6837643384933472,
          -0.9999479055404663,
          -0.13352937996387482
        ],
        [
          0.6630576252937317,
          0.9944763779640198,
          0.13813093304634094
        ]
      ],
      "extents": [
        1.3468219637870789,
        1.994424283504486,
        0.27166031301021576
      ],
      "components": 17,
      "largest_component_face_fraction": 0.9999680472900108,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.03899414999999999,
        "p10": 0.038623979999999995,
        "p90": 0.04330738000000002,
        "minimum": 0.03845799999999999,
        "maximum": 0.04627680000000001,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.0195515820392448,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 432,
      "measurement_seconds": 1.3310576670337468
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s433.glb",
      "vertices": 248193,
      "faces": 496412,
      "watertight": false,
      "welded_vertices": 248193,
      "welded_watertight": false,
      "bounds": [
        [
          -0.6634345650672913,
          -0.9999291896820068,
          -0.1481046974658966
        ],
        [
          0.6588839888572693,
          0.9947115778923035,
          0.15447011590003967
        ]
      ],
      "extents": [
        1.3223185539245605,
        1.9946407675743103,
        0.3025748133659363
      ],
      "components": 11,
      "largest_component_face_fraction": 0.9999637397967817,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.011789549999999996,
        "p10": 0.011631270000000004,
        "p90": 0.023942460000000002,
        "minimum": 0.011532999999999988,
        "maximum": 0.026381799999999997,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.005910613174891291,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 433,
      "measurement_seconds": 1.3287434999947436
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s434.glb",
      "vertices": 246274,
      "faces": 492592,
      "watertight": false,
      "welded_vertices": 246274,
      "welded_watertight": false,
      "bounds": [
        [
          -0.6756850481033325,
          -0.9998499155044556,
          -0.0906393900513649
        ],
        [
          0.6698466539382935,
          0.9947010278701782,
          0.1159285381436348
        ]
      ],
      "extents": [
        1.345531702041626,
        1.9945509433746338,
        0.2065679281949997
      ],
      "components": 7,
      "largest_component_face_fraction": 0.9992854126741807,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.014870799999999997,
        "p10": 0.014761620000000003,
        "p90": 0.018289850000000003,
        "minimum": 0.014573199999999994,
        "maximum": 0.1431645,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.007455713301982497,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 434,
      "measurement_seconds": 1.2349786669947207
    },
    {
      "path": "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/meshes/leaf-s435.glb",
      "vertices": 250417,
      "faces": 500818,
      "watertight": true,
      "welded_vertices": 250417,
      "welded_watertight": true,
      "bounds": [
        [
          -0.6682710647583008,
          -0.9999260306358337,
          -0.14177225530147552
        ],
        [
          0.6627104878425598,
          0.9948957562446594,
          0.14728248119354248
        ]
      ],
      "extents": [
        1.3309815526008606,
        1.9948217868804932,
        0.289054736495018
      ],
      "components": 10,
      "largest_component_face_fraction": 0.9998083135989522,
      "units": "native normalized Hunyuan units; no metric fitting",
      "off_wheel_slab_ray_span": {
        "median": 0.0207337,
        "p10": 0.020588459999999996,
        "p90": 0.038347760000000015,
        "minimum": 0.020418999999999993,
        "maximum": 0.041941599999999996,
        "valid_rays": 90,
        "attempted_rays": 90,
        "median_over_height": 0.01039376055362991,
        "method": "Same as previous run: frontmost minus backmost z at 90 bbox-relative samples, x=25..75%, y=18..33% and 72..82%. Intended off-wheel bands, not verified semantic segmentation. No semantic isolation of wheel or hardware is established."
      },
      "seed": 435,
      "measurement_seconds": 1.3776468749856576
    }
  ],
  "seconds_by_stage": {
    "shape": 2172.5866773761227,
    "render": 66.1139255410526
  },
  "failed_commands": [],
  "sheets": [
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/sheet.png",
    "/Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/overview.png"
  ],
  "input_limitation": "No crop clipping. Hinge contours are numerically traced inside supplied search regions, not visually reviewed. Generated geometry and projection fidelity are unjudged. Projection retains source lighting.",
  "visual_judgments": false,
  "production_fit": false
}
```

No smoothing, decimation, component removal, learned paint, side conditioning or source modification. Five shaded views and two concept-projection views per seed. Each image panel is 512 pixels high plus 68 pixels of labels. The crop includes the complete fitted outline and traced hinge extensions with margin. These are generated scratch candidates, with no visual verdict or production approval. No lighting flattening was applied.

## Final statistics

| Seed | Vertices | Faces | Watertight | X / Y / Z extents | Ray median / p10 / p90 | Shape seconds |
| --- | ---: | ---: | --- | --- | --- | ---: |
| 430 | 256202 | 512436 | False | 1.330954 / 1.994406 / 0.269169 | 0.049741 / 0.049508 / 0.064913 | 385.16 |
| 431 | 241346 | 482720 | True | 1.319824 / 1.994271 / 0.282726 | 0.043811 / 0.043713 / 0.049558 | 271.45 |
| 432 | 250344 | 500740 | False | 1.346822 / 1.994424 / 0.271660 | 0.038994 / 0.038624 / 0.043307 | 270.37 |
| 433 | 248193 | 496412 | False | 1.322319 / 1.994641 / 0.302575 | 0.011790 / 0.011631 / 0.023942 | 396.22 |
| 434 | 246274 | 492592 | False | 1.345532 / 1.994551 / 0.206568 | 0.014871 / 0.014762 / 0.018290 | 418.68 |
| 435 | 250417 | 500818 | True | 1.330982 / 1.994822 / 0.289055 | 0.020734 / 0.020588 / 0.038348 | 430.70 |

Generation command durations: 2172.59 seconds. Rendering: 66.11 seconds. Mesh measurement: 8.16 seconds. Input preparation: 2.03 seconds. Driver elapsed including verification: 2247.95 seconds.

Failed generation/render commands: 0. Verification passed; see `logs/verify.log`. Six raw meshes, 42 renders, `sheet.png` (3584 x 3480), `overview.png` (3072 x 1740). Mesh paths, full raw/welded topology statistics and ray coverage are in `stats.json`. All measurements are native, unscaled model units. No visual judgments.


## Monitoring interruption

One read-only monitor used `sleep 300` and was terminated by the shell tool after 120 seconds without output (SIGTERM 15). The detached generation/render driver was unaffected and exited 0. There were no failed generation or render commands and no retries. Later monitoring used this read-only loop, printing every 60 seconds:

```sh
for n in 1 2 3 4 5; do
  sleep 60
  date -u
  tail -n 1 /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/commands.jsonl
  tail -c 180 /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/logs/driver.log
  if test -f /Volumes/XS1000/acoliver/projects/gone/branch-1/tmp/hunyuan-hatch/leaf3/summary.json; then break; fi
done
```

Equivalent later loops printed compact parsed command names/return codes/durations and the final shape-log tail. No signals were sent to any process belonging to other workers. Final managed task status: completed, exit 0. Verification read PNG headers/data for integrity only; no image was displayed or judged.
