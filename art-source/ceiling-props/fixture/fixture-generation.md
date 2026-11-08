# Generated armoured ceiling fixture

The runtime fixture is the selected round-6 asset from Hunyuan3D seed 720. It replaces each pair of the earlier ceiling modules with one complete beam. Its exported dimensions are 1.10 × 0.10 × 0.22 m, with length along X, top mounting plane Y=0, fourteen underside apertures and a separate recessed glass material. The runtime export contains 2,664 triangles across four surfaces. The ship has been adrift for about 1000 years.

## Source and diagnosis

`concept/beam-armoured-strip-202.png` is the agreed concept. `concept/refined-beam-210.png` is the direct image input used to produce view 611. `views/611/` retains the accepted front conditioning image, exterior alpha mask, aligned image, prompt and metadata. Only `front-aligned.png` conditioned seed 720. No perpendicular view was supplied.

The earlier front and left images were nearly identical: RGB correlation 0.99823 and matching silhouette bounds. Those two perpendicular labels produced square slabs in seeds 410–412. Square input padding preserved the silhouette ratio and was not the cause. The later four-view trial 710 was a diagonal beam with a poor cross-section, as its oriented bounds showed. Front-only conditioning removed the contradictory end views. See `diagnosis.md` for the measurements and the distinction between world-axis and oriented bounds.

`hunyuan/720/raw-mesh.glb` is the generator output. `mesh.glb` is the rigidly yaw-aligned source, and `painted.glb` is its painted output. Alignment changed orientation, not proportions. `stats.json`, `fit-config.json`, `chosen.json` and `paint-result.json` retain the selection and paint records. The original command log is `recipe.md`; it records the unsuccessful candidates as well as seed 720. Those historical commands are documentation, not an installation step.

The successful shape command used the full Hunyuan3D-2mv model, subfolder `hunyuan3d-dit-v2-mv`, float16, 30 steps, guidance 5, octree resolution 384, 50,000 chunks, marching-cubes level 0, box-v 1.01, minimum component size 50 faces and seed 720:

```sh
python generate.py --model-path weights/Hunyuan3D-2mv \
  --subfolder hunyuan3d-dit-v2-mv --front views/611/front-aligned.png \
  --dtype float16 --steps 30 --guidance-scale 5 --octree-resolution 384 \
  --num-chunks 50000 --mc-level 0 --box-v 1.01 \
  --min-component-faces 50 --seed 720 --out hunyuan/720/mesh.glb
```

The subsequent paint command used the aligned mesh and the same conditioning image:

```sh
python paint.py --mesh hunyuan/720/mesh.glb \
  --image views/611/front-aligned.png --out hunyuan/720/painted.glb \
  --model-path weights/Hunyuan3D-2 --resolution 512 --texture-size 1024 \
  --seed 720 --memory-limit-gb 32 --vae-chunk 1 \
  --save-views hunyuan/720/paint-views.png \
  --save-bake-diagnostics hunyuan/720/paint-coverage.npz \
  --metallic 0.35 --roughness 0.7
```

These abbreviated historical commands assume the Hunyuan checkout and the archived input/output paths are supplied explicitly. The original recipe records the full workstation paths and environment. Installation performs no inference.

## Changes across the art rounds

Round 1 cleaned and reduced the generated mesh, fitted its envelope and assigned grille/glass regions on the generated surface. Its `build_fixture.py` is retained here. Welding before disconnected-island removal fixed the split-normal topology assumption.

Round 2 retained the generated shell and machined its lower skin into a fourteen-slot grille. It introduced the physically recessed opaque diffuser, rails and fasteners, flattened the slot-bearing skin, and closed the exposed left corner. It rebaked the painted source and added edge-directed weather. The body was not replaced with a primitive box.

Round 3 deepened the receiving channel, thickened the grille to 9.5 mm, added baffles, chamfered rails and side fasteners, and softened the generated lip. Two louvres received shallow dents. Fresh UV atlases and world-position/normal fields drove edge wear, gravity streaks and channel grime. The earlier scan-normal texture was removed.

Round 4 added capped ends, recessed bolts and ceiling flanges. It bent one louvre laterally by up to 13 mm and gave the failed three-slot section stronger output differences. Weather contrast increased and effect-isolation captures measured visible rust and streak contributions.

Round 5 reduced the bend to 1.2 mm, retained only one shallow dent, softened the end-cap treatment and reduced weather contrast. Glass output became continuous along the beam, with a single warm tint and a failed section retaining about half the physical output. This removed the previous per-slot colour steps.

Round 6 rebuilt the tapered end caps with 12 mm single-plane chamfers, thin bolted end flanges and recessed hex bolts. It placed weather contrast between rounds 4 and 5, widened edge chips and rivet footprints, extended gravity tails, and confined stronger soot to the channel and slot corners. Glass preview strength rose to 3.0. The selected file has four parts: generated body 788 triangles, retained grille 992, rails/hardware 872, glass 12.

Each round's original `recipe.md`, `build.py`, `weather.py`, `finish.py`, `verify.py` and build statistics are retained under `round2/` through `round6/`. Earlier scripts are historical stages and require the predecessor blend they name. The immediate round-5 blend is included so the final round can be rebuilt without regenerating those earlier stages.

## Rebuild and export

Author in Blender's native +Z-up frame, with front -Y. Export with `export_yup=True` to obtain glTF +Y up and front +Z. Do not fit height along Blender Y. Preview cameras, ceiling and lights are not exported. Both retained blend files pack their texture images.

The following final-round sequence comes from the round recipes. Run it on a writable copy of this source directory so generated arrays, textures and preview images do not modify the archive:

```sh
B=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
P=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
R=/absolute/path/to/writable-copy/round6
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py"
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py"
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py" -- --export-only
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/verify.py"
```

The sibling `round5/fixture.blend` and `round5/build-stats.json` must remain alongside that copy. The final `verify.py` independently checks the exported GLB with trimesh, including bounds, winding, welded closure, fourteen aperture runs and oblique glass rays. `round6/results.json` retains the original art measurements; its absolute image paths refer to the original scratch session.

To export the already finished packed blend directly from the repository root:

```sh
"$B" --background --factory-startup --threads 4 --python-exit-code 1 \
  --python tools/blender/export_ceiling_fixture.py
```

Validate the resulting GLB with the Khronos glTF Validator. Zero errors are required. Run `tools/blender/test_ceiling_props.py` in Blender and the guarded Godot suite to check runtime bounds, topology budget, separate glass, ceiling contact and circuit projection.

## Runtime installation

Godot's established scene-import settings extract the seven embedded albedo, ORM and emission images beside the GLB. Those derived PNGs and their import settings are included with the runtime asset, and the capture identity hashes them as well as the GLB.

`CeilingFixture` instantiates the complete export without a metal material override. The imported glass surface receives one duplicated material per room circuit, preserving its emission texture. Its emission colour uses the existing regular-white colour, emissive level and fade. The imported emission strength remains 3.0, matching the selected asset; the material-preservation regression checks that circuit control retains it. Emergency leaves the ceiling glass dark, as the old white lens was.

Only the housing moves up to the ceiling. Existing regular light anchors, light-source offsets, energies, ranges, masks, emergency fills and fade timing stay in place. The separate box lenses, paired module placement path and old runtime `module.glb` are removed. Wall lights and collision geometry are unchanged.
