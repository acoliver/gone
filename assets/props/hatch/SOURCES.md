# Shared modelled hatch

## Production generated assembly

The production build fits the frozen machine-generated `art-source/hatch/hunyuan/C-s410-sv.glb` frame together with the generated `parts/leaf-s430.glb` leaf, whole `parts/latch-dog-s601.glb` latches and edited `parts/handwheel-s600.glb` wheels. These part paths are relative to `art-source/hatch/hunyuan/`. This is a build-stage composition; runtime has one imported asset path. Raw source SHA-256 is `ba8831fbf528fe8de5b586b6c4c6c7c5a95f77eda2c137fb73db2b20f811ec78`. Source selections, conditioning inputs, model/checkpoint identities, generator snapshot and exact licence evidence are frozen under `art-source/hatch/hunyuan/`; `parts.json` records their hashes and the fitting operations. No inference or Hunyuan Paint runs during rebuilding.

`hatch_generated_parts.py` fits the repaired generated leaf body and its two retained ribs, and reduces each whole latch into its simulation-owned reservation. The wheel repeats the selected outer spoke/rim sector six times at 60-degree intervals, joins it to the source hub, and cuts the hub dome at the recorded nut-seat plane. `parts/wheel-edit.json`, `wheel-fit.json`, `hub-cut.json` and `retention-nuts.json` record the edits and fitted retention nut. The frozen `parts/wheel-low.npz` and `wheel-high.npz` caches supply delivered geometry and part-isolated normal transfer; `parts/edits/` and `parts/provenance.json` preserve the edit recipe and input hashes. No generation runs during export, construction or baking.

**Distribution restriction:** the Tencent Hunyuan 3D 2.0 Community License excludes the EU, UK and South Korea and restricts output distribution/display outside its Territory. Local asset promotion does not resolve that release restriction. See `art-source/hatch/hunyuan/LICENSE`, `Notice` and `SOURCES.md`; do not distribute these assets as unrestricted worldwide content.

`hatch_generated_frame.py` partitions the frozen ring, rivet and hinge source surfaces, removes declared zero-area faces, repairs the original hinge attachment from the opposite clean ring half, and relocates extracted hardware into the two exported hinge stations. Generated rivets are reused at the exported stations. The ring's visible front relief is cut at source Z = -0.0131168831, then fitted between 28 mm proud and 6 mm proud of the wall. Front-relief depth scale divided by in-plane scale is 0.2389911578. The exported generated ring retains distinct crown normals and depth levels; delivered-mesh measurements and clay captures are required independently of this provenance record.

The collision reservations remain unchanged. Rendered collar posts, top and stops are trimmed inside those reservations, behind or flush with the generated ring; the floor threshold retains its full reservation. The driver explicitly accepted this separation of rendered surfaces from collision margins. The three latch keepers and two jamb-running hinge plates remain intended fixed hardware. Required interface seals remain explicitly authored surfaces. `fit_recipe` records the bounded edits; `build_dependencies` records fitting/baking module hashes. Generated-source selected-to-active normal transfer is part-isolated.

Use the Asset rebuild command below with a freshly exported contract. Validate any candidate before promotion, then import twice and check runtime counts against `parts.json`. The production build retains the 2048 maps, concept-derived paint atlas, 22,894,480-byte shared GPU payload and ten runtime submissions. Delivered variants contain 37,365 and 37,689 triangles in `parts.json`. Aligning the third keeper with its latch removes its former upper-corner clip and four triangles per variant. The limits remain 40,000 triangles, twelve submissions and 24,000,000 bytes. Historical slice 2 retained an authored leaf and primitive wheels and delivered 39,531 / 39,855 triangles; earlier primitive-frame counts below are also historical. This section and the delivered manifest describe production.

## Concept-derived painted finish
Godot's direct `.blend` importer is disabled in `project.godot`: this pipeline exports GLB explicitly with pinned Blender. Otherwise a saved scratch `.blend` triggers an unset editor-Blender-path error during headless `--import`, which can exit zero without updating any imported resources. Check the imported hatch source MD5 and actual runtime triangle counts after rebuilding; a zero import exit status alone is insufficient.


Leaf and fixed-frame colour uses the driver's selected concept-derived images, replacing the text-only round-seven sources. `art-source/hatch/leaf-front.png` is the unchanged 512 by 896 `round8/gen3/edit-300.png`; `leaf-back.png` is its horizontal mirror, preserving downward runs. `frame.png` is the unchanged 1024 by 960 `round8/gen4/frame-402.png`. No gen4 leaf or Z-Image refinement is used. Hardware, wheel and rivets retain the CC0 scan finish below. Andrew changed the proportions on 2026-11-05: a narrow raised ring, a nearly flush leaf and a heavy solid slab replace the recessed thin leaf. Simulation reservations and the imported asset follow that design together.

The input is our own `docs/art/corridors/hatch-concept-rusted.png`. `docs/art/corridors/README.md` records that the concept images were image-model generated. Leaf input crop: `[365,77,875,960]`. Frame input crop: `[285,120,365,900]`; `[400,30,840,77]` was an additional top-band reference only. Coordinates use Pillow's exclusive right and bottom edges. The concept supplies paint imagery, never dimensions.

Generation used [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), mflux 0.17.5 on local MLX, four steps, 4-bit weights, leaf seed 300 and frame seed 402. Full original recipes, prompts and literal CLI flags are preserved in `art-source/hatch/gen3-recipe.md`, `gen4-recipe.md`, `leaf-prompt.txt`, `frame-prompt.txt` and the per-image `.metadata.json` records. FLUX's original edit sidecars contained JSON null; the recipes preserve the actual commands. `HF_HOME=/Volumes/XS1000/hf-cache`, `HF_HUB_OFFLINE=1`. Generation runs sequentially with `mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width WIDTH --height HEIGHT --seed SEED --image-paths INPUT --prompt-file PROMPT --metadata --output OUTPUT`.

Licence: **Apache-2.0**, including commercial use. The cached weights are revision `e7b7dc27f91deacad38e78976d1f2b499d76a294` under `/Volumes/XS1000/hf-cache/hub/models--black-forest-labs--FLUX.2-klein-4B/`. That snapshot did not contain its model card or licence file. Both were retrieved from the exact revision, rather than inferring the licence from a model name: [model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/e7b7dc27f91deacad38e78976d1f2b499d76a294/README.md), [licence](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/e7b7dc27f91deacad38e78976d1f2b499d76a294/LICENSE.md). Copies are `art-source/hatch/FLUX.2-klein-4B-model-card.md` and `Apache-2.0.txt`. The card declares `license: apache-2.0` and links the Apache terms.

Run `tools/prepare_hatch_paint.py` with Pillow and NumPy before the Blender rebuild. It uses a fractional centre crop `[32,0,480,896]` and uniform scale `1088/896` for each leaf, yielding separate 544 by 1088 cells. The frame is centre-cropped to the 1088:960 cell aspect and scaled uniformly into the lower cell. The packed atlas is 1088 by 2048. The wider cells retain the existing one-texel-per-pixel floor after Andrew widened the leaf and brought it forward; the 24 MB payload ceiling is unchanged. UV2 and vertex-colour ownership retain the shared material and geometry-derived projections; hardware never selects painted cells. Fronts keep their X/Y projection. Depth faces select the dominant geometric-normal plane and include Z in their UV2, at the same physical texel scale. The old X/Y-only projection collapsed depth into one line and produced alpha-height bands. `tests/hatch_paint_projection_test.gd` checks singular values of the delivered UV2-to-surface mapping for painted depth triangles: both axes must be nonzero and within 4:1 density.

The visible reverse skin is `BackingLapBody/lap`, with a narrow latch lap beside it. It sits in front of the reverse slab. Those caps formerly selected the repeating steel/oxide scans, so changing the concealed slab did not change the grid on screen. The backing's broad caps now select the reverse paint cell and project through the reverse slab's coordinate frame. The whole face shares one mirrored image without tiling. Depth edges retain their machined scan finish. The slab's original raised sheets, all geometry, hardware and collision reservations remain unchanged.

RGB stores prepared albedo. Alpha separates paint sheets from rust by the original source chroma, representing paint raised 1.5 mm. `paint_height.png`, `paint_normal.png` and `paint_roughness.png` remain derived authoring maps and do not change during colour conversion. Runtime differentiates alpha height in physical space and derives roughness without extra samplers. Painted areas sample that RGB directly, without the former 0.32 darkening, red tint, second oxide/steel overlay or second grime multiplication. A narrow geometric leaf-perimeter wear mask still exposes steel. Unpainted hardware keeps its scan finish and geometry-owned weather masks. AO affects ambient illumination only (`AO_LIGHT_AFFECT = 0.0`).

### Measured albedo conversion

`art-source/hatch/albedo-calibration.json` records the measured response, fixed concept rectangles and factors. Andrew's narrower frame moves the sampled surfaces inside the unchanged frame rectangle, so round ten repeats its zero/unit measurement using the committed rig. The leaf retains the passing round-nine factors. The original generated PNGs are untouched. `prepare_hatch_paint.py` decodes their sRGB to linear RGB, applies the measured per-cell conversion, then re-encodes sRGB. Both leaf faces use the same factor; the frame has its own. There is no runtime colour-conversion control.

The unchanged round-eight neutral lookdev rig supplies a white 2.6-energy key and 0.13 ambient. The owner's leaf box is `[420,560,560,900]`; frame is `[300,300,340,700]`. Mean per-pixel linear RGB was measured in the concept (`T`), an unscaled direct-albedo render (`U`) and a zero-paint render (`Z`). `Z` retains hardware, edge wear and specular contributions. The initial channel factor is `(T-Z)/(U-Z)`. The round-nine measurements ruled out one shared brightness scalar: unscaled leaf luminance was 0.7553 of its reference, while the former frame was 1.3854. The frame response below is the new measurement after the proportion change.

| Cell | Concept linear RGB T | Unit response U | Zero response Z | Final linear RGB factor |
| --- | --- | --- | --- | --- |
| Leaf, both faces | [0.066240, 0.032680, 0.018296] | [0.046381, 0.025408, 0.017378] | [0.022193, 0.013532, 0.009267] | [1.821003, 1.612374, 1.740712] |
| Frame | [0.058145, 0.023194, 0.013709] | [0.096311, 0.045090, 0.036544] | [0.006741, 0.006741, 0.006741] | [0.573895, 0.429029, 0.233795] |

An unconstrained leaf blue factor of 1.113208 matched broad-box linear RGB but failed the existing small leaf HSV saturation check. The same zero/unit pixel response gives a blue-factor interval `[1.397418,2.084006]` satisfying both the unchanged patch HSV tolerance and the new broad-box HSL tolerance. Its midpoint, 1.740712, completes the conversion. Red and green retain their direct measurement factors. No reference rectangle or tolerance changes. Broad-box requirements are mean linear luminance within 10%, hue within 12 degrees and HSL saturation within 0.10; HSL matches the brief's saturation definition. The older leaf/wheel/hazard patch gates retain their HSV definition. `tests/test_hatch_colour.py` checks the new targets from a native capture; `tests/test_hatch_paint.py` checks linear-space conversion and unchanged alpha.

The upper ring/lip/throat faces are downward outward soffits. They cannot face an above-door key. The ray tests retain outward camera-facing normals and clear key-facing threshold checks. `tests/hatch_soffit_capture.gd` checks ray-identified soffit rows in both production X=30 close captures: every sampled maximum channel exceeds 2/255 and mean linear luminance is below the exposed upper leaf. A white-circuit end bounce at the existing layout-owned position supplies the fill absent after emergency handoff, using 0.12 of regular-strip energy, the white fade and only the hallway fill layer. Emergency keys and fills still extinguish.

The original smart-projected atlas contains subpixel bevel/contour triangles. A white-emission coverage bake found 4,551 centroids with no initial shaded texel, which an eight-pixel margin cannot repair. The bake copy now gives subpixel triangles a conservative three-texel footprint centred on their runtime centroid's texel. Cycles evaluates the actual material there and applies the existing dilation. The delivered UVs, topology, paint projection and vertex positions are untouched. `hatch_coverage.png` is a white-emission authoring mask, not a runtime sampler. Build-time checks and `tests/hatch_bake_coverage_test.gd` require covered centroids for every triangle; zero AO from genuine occlusion remains valid.

The painted BC7 RGBA atlas with full mips occupies 2,971,216 bytes. Total shared hatch GPU payload is 22,894,480 bytes including all detail samplers. Each leaf supplies at least 461.02 texels/metre. The density tests measure the actual face and camera positions and retain the one-texel-per-pixel painted and two-texel-per-pixel tiled-detail floors. The historical primitive-frame build had 35,478 / 35,474 triangles and ten draw submissions; production counts are listed above. Limits remain 40,000 triangles, twelve submissions and 24,000,000 bytes. The GLB embeds only the original three runtime maps; `Surfaces` owns the external paint atlas.

## Rebuild

### Reproducible rendered-colour lane

From the repository root, with Godot's native renderer and Python with Pillow/NumPy:

```sh
python tools/check_hatch_colour.py tmp/hatch-model/round10/lookdev
```

This command removes any stale neutral image, runs the committed `tools/capture_hatch_lookdev.gd` rig, then runs `tests/test_hatch_colour.py`. Missing images, wrong dimensions, altered settings or a response-atlas override fail the lane. The fixed rig writes warm, neutral and three-quarter PNGs plus `lookdev-settings.json`; the viewport is 1199 by 1312, 2x MSAA, FOV 46, camera `[0,1.28,-3.65]` toward `[0,1.28,0]`, ambient 0.13 and a white 2.6-energy key at `[1.1,2.9,-1.5]` with range 7. The test retains the original rectangles and all colour tolerances.

For a zero/unit measurement, preserve the paint alpha and generate RGB from the unconverted authoring sources through the same packer:

```sh
python - <<'PY'
from pathlib import Path
import importlib.util
from PIL import Image
spec = importlib.util.spec_from_file_location('paint', 'tools/prepare_hatch_paint.py')
paint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paint)
out = Path('tmp/hatch-model/round10/response')
out.mkdir(parents=True, exist_ok=True)
images = [Image.open(paint.ROOT / 'art-source/hatch' / (name + '.png')).convert('RGB')
          for name in ('leaf-front', 'leaf-back', 'frame')]
for name, factor in (('zero', 0), ('unit', 1)):
    atlas, _ = paint.pack(*images, gains=[[factor] * 3] * 3)
    atlas.save(out / (name + '.png'))
PY
godot --path . -s tools/capture_hatch_lookdev.gd -- \
  tmp/hatch-model/round10/response/zero --paint-atlas tmp/hatch-model/round10/response/zero.png
godot --path . -s tools/capture_hatch_lookdev.gd -- \
  tmp/hatch-model/round10/response/unit --paint-atlas tmp/hatch-model/round10/response/unit.png
```

Measure per-pixel linear RGB in the unchanged rectangles with `tests/test_hatch_colour.py`'s `measure()` function. Calculate `(T-Z)/(U-Z)` per channel and record the result in `art-source/hatch/albedo-calibration.json` before regenerating paint and rebuilding the asset. Response captures cannot pass as production colour captures. Production capture identity enumerates every bound hatch sampler and hashes both image bytes and import settings through the same `Surfaces.hatch_runtime_textures()` mapping used by the material. Lighting owns the existing regular end-fill policy; Hallway supplies placement and fade only.

### Asset rebuild

Keep the supplied GLB and PNG `.import` files. From the repository root:

```sh
mkdir -p tmp/hatch-model/round10
godot --headless --path . -s tools/export_hatch_parts.gd -- \
  --output tmp/hatch-model/round10/parts-source.json
/Volumes/XS1000/tools/mlximg-venv/bin/python tools/prepare_hatch_paint.py \
  --parts tmp/hatch-model/round10/parts-source.json
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 --python tools/blender/build_hatch.py -- \
  --input tmp/hatch-model/round10/parts-source.json --output assets/props/hatch/hatch.glb \
  --resolution 2048 --samples 8
node tmp/pipeline/valtool/validate.cjs assets/props/hatch/hatch.glb \
  tmp/hatch-model/round10/validate.json
godot --headless --path . --import
godot --headless --path . --import
```

Blender 4.5.11 LTS and the import/validator pipeline are described in `docs/dev/asset-pipeline.md`. Cycles uses CPU baking, eight threads, eight samples and fixed seed 7308. Geometry, UVs and weather fields are deterministic. `--reuse-bakes` rejects changed source reservations, either authoring module, photographic inputs, resolution or sample count.

`parts.json` records the exported dimensions, transforms, contours and corrected source vertices for both hinge variants. It also records source and recipe hashes, photographic input hashes, per-node reservations, texture hashes, AO measurements and delivered GLB triangle counts. The authoring triangle count is separate because glTF export can omit collapsed loop triangles. Texture measurements distinguish the three original runtime maps, external paint atlas and nine detail maps from auxiliary authoring maps, including bake coverage.

## Photographic inputs

The approved downloads, exact URLs, SHA-256 values and CC0 license are recorded in `assets/surfaces/steel/SOURCES.md`. The full license text is `assets/surfaces/steel/CC0-1.0.txt`. No new downloads are required.

| Layer | Albedo | OpenGL normal | ORM |
| --- | --- | --- | --- |
| Steel | `art-source/steel/rusty_metal_04_albedo.jpg` | `rusty_metal_04_normal.jpg` | `rusty_metal_04_orm.jpg` |
| Paint remnants | `art-source/steel/green_metal_rust_albedo.jpg` | `green_metal_rust_normal.jpg` | `green_metal_rust_orm.jpg` |
| Oxide | `r3-rust_coarse_01-albedo.jpg` | `r3-rust_coarse_01-normal.jpg` | `rusty_painted_metal_orm.jpg` |

Names without a directory are under `assets/surfaces/steel/`. The oxide layer borrows roughness from the approved rusty-painted-metal set; it has no metallic contribution. `tools/blender/hatch_scan_finish.py` defines these inputs once, and their bytes are hashed into the delivered sidecar.

The scans supply colour, surface normals and roughness. Layer masks come from geometry AO, curvature, physical sheet relief, chip edges, exported fastener contact positions, downward trails and bottom accumulation. There is no procedural noise colour field. Scan frequency is reduced and pale luminance peaks are compressed without replacing photographic colour ratios. Paint survives on two connected sheets per plate and along worn edges. Fastener runoff extends down the leaf; bottom accumulation and baked contact AO darken recesses. Exposed substrate blends the steel and oxide scans without a neutral wash. Machined shoulders retain photographed steel detail with reduced saturation. Hardware shoulders receive localized steel wear. Raised oxide has localized lower roughness. Warning paint is multiplied over the scan, broken by scan luminance and fastener weathering, and restricted to 52 percent of its unchanged steel carrier. Bare margins retain substrate and contact corrosion.

## Geometry and runtime ownership

The approach-side ring is the fixed silhouette: a 90 mm polygon offset, 20 mm ahead of the wall, with 54 equal-arc-length rivets per face at the unchanged 130 mm nominal pitch. `ShipGeometry.HATCH_RING_WIDTH`, `HATCH_RING_FRONT`, `HATCH_RING_REAR` and `HATCH_CORNER_RADIUS` own the profile. The bead has a rounded outer profile within its shallow depth rather than forming a deep square box. Collar and stop profiles are clipped to that outer contour; supports stop at its curve tangencies. Sloped sealing returns remain. The hidden wall pocket clears the offset hinge sweep without changing the 1.2 by 2.4 m nominal mouth, 1.0 m sill walk width or 80 mm coaming. Ring, lip and throat share their inner curve and adjoining depth runs. Annular cells have shared boundaries without internal radial walls.

`HatchParts.APPROACH_SLAB_DEPTH` is 220 mm and `REVERSE_SLAB_DEPTH` is 40 mm. These solid parts meet at the hinge plane; the front slab alone exceeds Andrew's 160 mm edge-on requirement. A separate exported 4 mm bevel and 2 mm paint recess prevent the heavier steel from enlarging the paint relief. The edge uses the existing machined scan wear. `DoorSpec.leaf_aperture()` sets the leaf to 1.18 by 2.4 m, giving a measured 15 mm front-view edge gap. `hinge_frame()` derives the axis from that slab depth and `HatchParts.HINGE_OUTSET`; the closed front reaches the wall plane, 20 mm behind the ring front. The current hinge assembly puts two 56 mm diameter, 140 mm long moving barrels on the actual vertical hinge axis, at 0.48 and 2.24 m. Their 20 mm caps share that diameter. Only the swing face carries the two 0.22 by 0.22 m, 12 mm thick straps and their orthogonal necks; four bolts follow each strap's centre. The fixed recipe supplies two frame plates, two axial bridges, two 60 mm fixed knuckles and three free-edge keepers. Keeper heights derive directly from the same `HatchParts.DOG_HEIGHTS` stations as the whole latches: 0.40, 1.17 and 1.496046 m, with no vertical contact offset. Closed-position tests cover all three stations, both faces and both hinge signs. The upper latch remains below the label at 1.86 m to preserve its required 30 mm hardware clearance. Historical Round 11 used 60 mm moving barrels, 10 mm caps and straps on both faces; those dimensions are no longer the build recipe. `HatchParts` owns moving dimensions; `ShipGeometry.hatch_fixed_hardware()` owns fixed dimensions; `DoorSpec.hinge_frame()` owns the pivot and swing sign. Fixed hardware contributes sight and clearance geometry but no colliders, per Andrew's Round 11 decision. Tests check every fixed part outside the walk band and within the 300 mm capsule radius of an existing wall/frame collider. The closed total remains 1,013. Services stay outside the leaf's sweep. Seeded rest angles remain 100 to 130 degrees.

Collision assembly uses one inscribed AABB per clipped frame reservation, including the opening adapters. Its XY footprint remains inside the shared outer silhouette while retaining the reservation's depth planes. Each box keeps its stable reservation ID so well slices retain every piece. A shared 2 m spatial broad phase keeps those refined boxes local to movement queries, deduplicates boxes spanning cells and restores insertion-order results before resolution. Tests compare it with a linear reference, including negative coordinates, exact cell boundaries and later insertions. Ladder slices reuse one assembled template per well until selected decks or door revisions change; returned ID arrays and spatial indices remain private to the caller. Render-free tests check the assembled deck set against the unchanged 2 mm outline tolerance.

Collar skins are rounded, sliced along long runs, welded and triangulated with area-balanced diagonals. This avoids needle triangles with undefined tangent bases. Stop roundovers are smaller than their sealing overlap. Both source and actual submitted fixed-frame vertices are tested against the outer outline with the unchanged 2 mm tolerance.

Moving parts remain inside the simulation-owned reservations. Each plate retains two connected paint sheets made from 88 adjoining tiles, with 1.8 mm lifted perimeter edges over a 2.0 mm recessed substrate. Internal tile edges have no raised side walls. Turned small hardware uses eight radial segments; layered hinge straps use four segments per corner. The generated six-fold wheel retains its open rim and spoke holes, with a hub cut and six-sided retention nut seated according to `parts/hub-cut.json`. All three whole latches per face retain their flat-sided arm sections. No lights are added.

Historical primitive hardware used 44 by eight wheel tubes, 12-segment spokes, a 32-segment stepped hub and separately forged dog arms. Those wheel and latch helpers have been removed; their historical fixture tests do not describe the delivered whole objects. Production generated-wheel geometry/tangent probes and whole-latch section tests cover the replacements.

The GLB remains part-local for inspection. Runtime construction merges stationary leaf parts into one surface per face, keeps the two wheels separate and merges all fixed collar/surround faces by room mask. Four shared MultiMeshes carry leaf and fixed rivets. The result is ten imported material submissions per complete hatch, shared across all 123 hatch instances. Services and control panels are outside this imported leaf/frame budget and retain their existing batching.

Merged buffers retain contiguous part ranges and original local transforms. Reservation, sight, clearance, seal-normal and hardware tests read the actual submitted vertices and indices through these ranges. The range checker requires complete, positive, nonoverlapping coverage with each triangle confined to its own part. Negative seal controls remove the actual seal index ranges. No second rendered hatch geometry path is retained.

## Maps and measurements

- `hatch_albedo.png`: sRGB-encoded geometry layer masks: paint, oxide and machined wear, BC7.
- `hatch_normal.png`: linear tangent-space +Y geometry normal, BC5.
- `hatch_orm.png`: linear R=geometry AO, G=grime, B=warning-paint ownership, BC7.
- `hatch_ao.png`, `hatch_height.png`, `hatch_curvature.png`, `hatch_coverage.png`: auxiliary authoring outputs, not runtime samplers.

All seven maps are 2048 by 2048. Runtime albedo and ORM use BC7, the normal uses BC5, and each has eleven mip levels after its base. Each compressed chain occupies 5,592,432 bytes; the shared runtime set occupies 16,777,296 bytes including minimum-size blocks. Delivered triangle counts are 37,365 for variant 0 and 37,689 for variant 1, with ten imported submissions in either case. The older 35,478 / 35,474 counts describe the historical primitive-frame build. Runtime limits are 40,000 triangles and twelve material submissions per complete imported hatch, and 24,000,000 bytes for its shared maps.

The GLB embeds only the three runtime images and one material. Godot resolves them to the same external maps used by `Surfaces`; embedded materials are released on extraction. Keep the existing import precision, compression and UIDs. Sidecar coordinates are Godot X-right/Y-up/Z-back; transform basis arrays are columns. Face normals and tangent handedness are transformed when reflected parts are merged, with triangle winding reversed where required.

## Checks

```sh
godot --headless --path . -s tests/run_tests.gd
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_construction.py
HATCH_SOURCE_JSON=tmp/hatch-model/round10/parts-source.json \
  BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_round3.py
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_finish_construction.py
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_scan_finish.py
```

Replace `BLENDER` with the executable above. The finish probes evaluate actual baked emission for chip colour and warning width, and verify unit tangents at both 2048 and 4096. Automated checks do not establish concept matching. Close and three-quarter captures under both production circuits still require the image-comparer's defect-by-defect assessment.
