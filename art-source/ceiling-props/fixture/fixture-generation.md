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

## November 9, 2026 aging pass

The selected appearance is now `aging/fixture.blend`, accepted in native game art round 7. It keeps the round-6 seed-720 geometry, UVs, 2,664 triangles, four surfaces and fourteen slots. The earlier rounds above remain historical sources. No new inference, geometry fitting or scene-light energy change was used for this aging pass.

World-position fields, surface normals, sharp edges and fastener positions drive chalked olive paint, uneven pale dust, localized dark oxide, gravity streaks and soot around the recessed grille. The hardware has its own oxidized-steel treatment rather than inheriting the painted housing's chalk fade. Dust on that hardware settles on upward-facing ledges instead of coating its vertical and downward faces. The metal ORM maps are completely rough and nonmetallic. Six apertures have selective staining or weakened output, while eight retain bright cores. Glass stains affect the emission texture, not the scene sources.

Native source isolation corrected the initial specular diagnosis. In the original installation, the source was about 113 mm below the glass and directly illuminated the exterior housing. Disabling that source reduced the fixed bright-edge luma from 0.856700 to 0.038325; forcing specular off did not change it. During art acceptance, the shared fixture work temporarily fitted the beam assembly to the old source. The driver then required restoring the flush ceiling mounting and seating the source at the recessed glass. The integrated `FixtureEmitter.beam` from the shared fixture branch reuses its emitter binding and moves the source, not the housing; no hanging beam support remains. This aging branch keeps that seating implementation unchanged. Runtime metal calibration retains the authored albedo, roughness and metallic maps, disables metal specular, and retains the 0.35 grille albedo calibration. Existing glass glare calibration remains in place.

The source-position, spotlight and falloff prototypes used during diagnosis are not shipped here. The shared fixture branch owns source placement and illuminance policy. This aging branch changes no source energy, range, falloff, receiver mask, fade input, emergency fixture or illumination threshold.

A further material-isolation pass identified pale hardware, rather than glass rim or specular, as the remaining edge problem. Correcting its weather recipe reduced the same fixed round-6 bright-edge mean from 0.734191 to 0.275913. The accepted 2.5 m louvre/slot ratio is 0 and median slot display luma is 0.774467. The unchanged contrast limits remain 0.18 maximum ratio and 0.75 to 0.93 slot luma.

`aging/accepted.json` retains the historical round-7 renderer, asset identity and effect-isolation measurements. `aging/downward.json` records the same asset under #111's final recessed, downward-only emission, accepted by the driver as an asset change with the lighting limit below. The final capture exited successfully with all 44 images and no script or renderer pairing errors. Diagnostic masks include both regular meshes and batched geometry as black occluders, so lit surroundings cannot contaminate feature measurements.

`assets/props/ceiling/fixture-weather-gates.json` fixes 28 requirements against that downward-only baseline. Minimum lit weather/control, broad-shell, visible-weather fraction, dust, edge-rust localization and streak effects remain at 90% of the accepted measurements. Translation-correlation ceilings remain at the reference plus 0.05; the repeating-diagonal regression exceeds 0.99. Every retained gate has a test showing that a missing effect or periodic texture fails.

The driver approved removing seven art checks that relied on the old lighting or hanging assembly: four absolute broad-face brightness minima, the grazing upward-face pixel-count minimum, and two upward-only dust contrast minima. Flush mounting changes visible upward area, and downward-only sources cannot illuminate those faces. Visible-face dust/control checks remain in all four views, including close dust difference 0.021415 and grazing difference 0.014483. These are visual-gate changes, not relaxed code-quality, slot-contrast or test limits. The gate does not infer age from texture coverage alone.

### Known lighting limit

Under physically correct downward-only emission and no global illumination, the housing and ceiling around each beam render near-black from below. Final broad-shell display luma is 0.000367 at 2.5 m, 0.048268 close, 0.059048 grazing and 0.004427 in the corridor. At 2.5 m, 99.67% of sampled broad-shell pixels are below 0.025 luma. The weather/control RGB difference is still 0.022392 across the sampled metal, but only 0.000308 across the broad shell; this does not establish readable olive paint on its unlit underside.

The earlier production-triangle audit with interpolated normals, per-source masks and falloff, and camera-ray visibility found mean incident light of 0.000276543 renderer units on the exterior underside, with 93.13% of sampled area unlit. Flat grille undersides received zero. Lit inner channel walls do not establish exterior paint illumination. An earlier native flat-white control reached only 0.115463 mean broad-face luma, versus 0.653865 in the original self-lit installation. These earlier figures precede the final all-downward emission and are retained as diagnostic history. Real floor/wall diffuse bounce driven by the actual fixtures, or a placement that exposes the housing to other real fixtures, is needed to reveal more of the underside. No ambient, fill, emissive metal or production GI change was added. The driver is investigating engine GI separately.

### Rebuilding and checking the aged appearance

Use a writable copy of this fixture source tree, retaining sibling `round6/fixture.blend` and `round6/build-stats.json`. Set `R` to its `aging/` directory, then run the same Blender/Python executables defined above:

```sh
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/build.py"
PYTHONDONTWRITEBYTECODE=1 "$P" "$R/weather.py"
"$B" --background --factory-startup --threads 4 --python-exit-code 1 --python "$R/finish.py"
```

`build.py` rebakes geometry fields without changing the original mesh or UVs. `weather.py` generates albedo, ORM, glass emission and effect-isolation maps. `finish.py` packs those images and exports with Blender-native Z up and `export_yup=True`. It does not create preview lights. The repository exporter now selects the packed aged blend directly.

After installing the GLB and extracted textures into a worktree, capture the actual production scene and run both gates:

```sh
GONE_FIXTURE_MAPS="$R" godot --path . -s tools/capture_fixture_weather.gd -- /absolute/path/to/captures
"$P" tools/check_fixture_weather.py /absolute/path/to/captures
"$P" tools/check_fixture_contrast.py /absolute/path/to/captures/weathered-2p5m.png
```

The capture requires a native renderer, uses secondary-white power and seed 91, follows the actual glass centre, and captures weathered, disabled-control and isolated-effect variants at 2.5 m, close, ledge and corridor views. Masks are unshaded measurements only; acceptance and effect differences use lit captures. Native windowed verification must be serialized with other fixture work.
