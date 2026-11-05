# Shared modelled hatch

## Concept-derived painted finish

Leaf and fixed-frame colour uses the driver's selected concept-derived images, replacing the text-only round-seven sources. `art-source/hatch/leaf-front.png` is the unchanged 512 by 896 `round8/gen3/edit-300.png`; `leaf-back.png` is its horizontal mirror, preserving downward runs. `frame.png` is the unchanged 1024 by 960 `round8/gen4/frame-402.png`. No gen4 leaf or Z-Image refinement is used. Hardware, wheel and rivets retain the CC0 scan finish below. Mesh positions and simulation reservations are unchanged.

The input is our own `docs/art/corridors/hatch-concept-rusted.png`. `docs/art/corridors/README.md` records that the concept images were image-model generated. Leaf input crop: `[365,77,875,960]`. Frame input crop: `[285,120,365,900]`; `[400,30,840,77]` was an additional top-band reference only. Coordinates use Pillow's exclusive right and bottom edges. The concept supplies paint imagery, never dimensions.

Generation used [black-forest-labs/FLUX.2-klein-4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), mflux 0.17.5 on local MLX, four steps, 4-bit weights, leaf seed 300 and frame seed 402. Full original recipes, prompts and literal CLI flags are preserved in `art-source/hatch/gen3-recipe.md`, `gen4-recipe.md`, `leaf-prompt.txt`, `frame-prompt.txt` and the per-image `.metadata.json` records. FLUX's original edit sidecars contained JSON null; the recipes preserve the actual commands. `HF_HOME=/Volumes/XS1000/hf-cache`, `HF_HUB_OFFLINE=1`. Generation runs sequentially with `mflux-generate-flux2-edit --model flux2-klein-4b --quantize 4 --steps 4 --width WIDTH --height HEIGHT --seed SEED --image-paths INPUT --prompt-file PROMPT --metadata --output OUTPUT`.

Licence: **Apache-2.0**, including commercial use. The cached weights are revision `e7b7dc27f91deacad38e78976d1f2b499d76a294` under `/Volumes/XS1000/hf-cache/hub/models--black-forest-labs--FLUX.2-klein-4B/`. That snapshot did not contain its model card or licence file. Both were retrieved from the exact revision, rather than inferring the licence from a model name: [model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/e7b7dc27f91deacad38e78976d1f2b499d76a294/README.md), [licence](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/e7b7dc27f91deacad38e78976d1f2b499d76a294/LICENSE.md). Copies are `art-source/hatch/FLUX.2-klein-4B-model-card.md` and `Apache-2.0.txt`. The card declares `license: apache-2.0` and links the Apache terms.

Run `tools/prepare_hatch_paint.py` with Pillow and NumPy before the Blender rebuild. It uses a fractional centre crop `[45.1764705882,0,466.8235294118,896]` and uniform scale `1088/896` for each leaf, yielding separate 512 by 1088 cells. Fractional bounds avoid an integer-width aspect stretch. The frame fills the 1024 by 960 lower cell without resizing. The packed atlas is 1024 by 2048. UV2 and vertex-colour ownership retain the shared material and geometry-derived projections; hardware never selects painted cells.

RGB stores albedo. Alpha separates paint sheets from rust by chroma, representing paint raised 1.5 mm. `paint_height.png`, `paint_normal.png` and `paint_roughness.png` remain derived authoring maps. Runtime differentiates that alpha height in physical space and derives roughness without extra samplers. Baked AO, edge wear, fastener contact/runoff and bottom grime remain geometry-owned. The shader grades the new sources and multiplies those masks into their colour. AO affects ambient illumination only (`AO_LIGHT_AFFECT = 0.0`), preserving the round-seven sill fix.

The upper ring/lip/throat faces are downward outward soffits. They cannot face an above-door key. The ray tests retain outward camera-facing normals and clear key-facing threshold checks. `tests/hatch_soffit_capture.gd` checks ray-identified soffit rows in both production X=30 close captures: every sampled maximum channel exceeds 2/255 and mean linear luminance is below the exposed upper leaf. A white-circuit end bounce at the existing layout-owned position supplies the fill absent after emergency handoff, using 0.12 of regular-strip energy, the white fade and only the hallway fill layer. Emergency keys and fills still extinguish.

The original smart-projected atlas contains subpixel bevel/contour triangles. A white-emission coverage bake found 4,551 centroids with no initial shaded texel, which an eight-pixel margin cannot repair. The bake copy now gives subpixel triangles a conservative three-texel footprint centred on their runtime centroid's texel. Cycles evaluates the actual material there and applies the existing dilation. The delivered UVs, topology, paint projection and vertex positions are untouched. `hatch_coverage.png` is a white-emission authoring mask, not a runtime sampler. Build-time checks and `tests/hatch_bake_coverage_test.gd` require covered centroids for every triangle; zero AO from genuine occlusion remains valid.

The painted BC7 RGBA atlas with full mips occupies 2,796,240 bytes. Total shared hatch GPU payload is 22,719,504 bytes including all detail samplers. Each leaf supplies at least 468.97 texels/metre: 1.248 texels/pixel at the production close camera, 1.199 front and 1.259 reverse at the reused lookdev camera. Delivered variants have 37,095 / 37,135 triangles and ten draw submissions. Limits remain 40,000 triangles, twelve submissions and 24,000,000 bytes. The GLB embeds only the original three runtime maps; `Surfaces` owns the external paint atlas.

## Rebuild

Keep the supplied GLB and PNG `.import` files. From the repository root:

```sh
mkdir -p tmp/hatch-model/round8/run
/Volumes/XS1000/tools/mlximg-venv/bin/python tools/prepare_hatch_paint.py
godot --headless --path . -s tools/export_hatch_parts.gd -- \
  --output tmp/hatch-model/round8/run/parts-source.json
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 --python tools/blender/build_hatch.py -- \
  --input tmp/hatch-model/round8/run/parts-source.json --output assets/props/hatch/hatch.glb \
  --resolution 2048 --samples 8
node tmp/pipeline/valtool/validate.cjs assets/props/hatch/hatch.glb \
  tmp/hatch-model/round8/run/validate.json
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

The ring is the fixed silhouette: a 160 mm polygon offset with 56 equal-arc-length rivets per face. Collar and stop profiles are clipped to that outer contour in the simulation recipe. Original sloped sealing returns remain. Clipping cannot enlarge the original rectangle or raise the authored 80 mm coaming. The rectangular pier overlays are removed. A floor-backed coaming replaces the projecting steps at the unchanged walk height. Ring, lip and throat use the same inner curve and adjoining, nonoverlapping depth runs. Only the ring's outer edge rolls over; the inner reveal has no repeating rolled bands. Annular cells have shared boundaries without internal radial walls.

Collision assembly preserves the clipped sections through adaptive AABB spans, including the opening adapters. It subdivides where an enclosing rectangle would exceed the shared outer silhouette by 1 mm. Each sub-box has a distinct stable ID so well slices retain every piece. A shared 2 m spatial broad phase keeps those refined boxes local to movement queries, deduplicates boxes spanning cells and restores insertion-order results before resolution. Tests compare it with a linear reference, including negative coordinates, exact cell boundaries and later insertions. Ladder slices reuse one assembled template per well until selected decks or door revisions change; returned ID arrays and spatial indices remain private to the caller. Render-free tests check the assembled deck set against the unchanged 2 mm outline tolerance.

Collar skins are rounded, sliced along long runs, welded and triangulated with area-balanced diagonals. This avoids needle triangles with undefined tangent bases. Stop roundovers are smaller than their sealing overlap. Both source and actual submitted fixed-frame vertices are tested against the outer outline with the unchanged 2 mm tolerance.

Moving parts remain inside the simulation-owned reservations. Each plate has two connected sheets made from 88 adjoining tiles, with 1.8 mm lifted perimeter edges over a 2.0 mm recessed substrate. Internal tile edges have no raised side walls. Turned small hardware uses eight radial segments; the stepped hub uses 32. Wheel tubes use 44 by eight segments, spokes use 12 segments and small layered plates use four segments per corner. The hub's front shoulder is moved ahead of the spoke roots, which remain six structural spokes. The open rim, shaft, pin necks and all three forged dogs per face remain modelled.

The GLB remains part-local for inspection. Runtime construction merges stationary leaf parts into one surface per face, keeps the two wheels separate and merges all fixed collar/surround faces by room mask. Four shared MultiMeshes carry leaf and fixed rivets. The result is ten imported material submissions per complete hatch, shared across all 123 hatch instances. Services and control panels are outside this imported leaf/frame budget and retain their existing batching.

Merged buffers retain contiguous part ranges and original local transforms. Reservation, sight, clearance, seal-normal and hardware tests read the actual submitted vertices and indices through these ranges. The range checker requires complete, positive, nonoverlapping coverage with each triangle confined to its own part. Negative seal controls remove the actual seal index ranges. No second rendered hatch geometry path is retained.

## Maps and measurements

- `hatch_albedo.png`: sRGB-encoded geometry layer masks: paint, oxide and machined wear, BC7.
- `hatch_normal.png`: linear tangent-space +Y geometry normal, BC5.
- `hatch_orm.png`: linear R=geometry AO, G=grime, B=warning-paint ownership, BC7.
- `hatch_ao.png`, `hatch_height.png`, `hatch_curvature.png`, `hatch_coverage.png`: auxiliary authoring outputs, not runtime samplers.

All seven maps are 2048 by 2048. Runtime albedo and ORM use BC7, the normal uses BC5, and each has eleven mip levels after its base. Each compressed chain occupies 5,592,432 bytes; the shared runtime set occupies 16,777,296 bytes including minimum-size blocks. Delivered triangle counts are 37,095 for variant 0 and 37,135 for variant 1, with ten imported submissions in either case. Runtime limits are 40,000 triangles and twelve material submissions per complete imported hatch, and 24,000,000 bytes for its shared maps.

The GLB embeds only the three runtime images and one material. Godot resolves them to the same external maps used by `Surfaces`; embedded materials are released on extraction. Keep the existing import precision, compression and UIDs. Sidecar coordinates are Godot X-right/Y-up/Z-back; transform basis arrays are columns. Face normals and tangent handedness are transformed when reflected parts are merged, with triangle winding reversed where required.

## Checks

```sh
godot --headless --path . -s tests/run_tests.gd
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_construction.py
HATCH_SOURCE_JSON=tmp/hatch-model/round8/run/parts-source.json \
  BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_round3.py
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_finish_construction.py
BLENDER --background --factory-startup --python-exit-code 1 --python tools/blender/test_hatch_scan_finish.py
```

Replace `BLENDER` with the executable above. The finish probes evaluate actual baked emission for chip colour and warning width, and verify unit tangents at both 2048 and 4096. Automated checks do not establish concept matching. Close and three-quarter captures under both production circuits still require the image-comparer's defect-by-defect assessment.
