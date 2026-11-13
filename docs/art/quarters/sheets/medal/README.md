# Issue 130: pendant concepts, raw shape guide and tunic measurements

## Current generated-medal pipeline

The current medal uses the c01 Hunyuan-generated shape retained under
`tools/blender/quarters/dress_uniform/medal_v3/`. A fitted cage follows the
generated surface. The upper star-tip return is corrected before reduction,
and high and low body depth are scaled together to meet the 2 to 4 mm target
at a 32 mm body diameter. The mounted reverse follows the unchanged wool.
The ring is soldered to the body; a centred bar carries an interlinked loop.
The ribbon wraps over the bar with a soft, rounded bend. The editable mounted
sources are `tunic-working.blend` and `tunic-pilot.blend`, beside the pipeline.
Production GLBs are exported from those saved sources.

The finish uses photo-derived brass, enamel and grosgrain maps, with recess
oxide constrained by geometry. Brass and enamel have separately padded
albedo, ORM and normal maps to prevent cross-material filtering. Enamel has
its own coat-weight map. Star normals have a 0.065 mm rounding footprint;
ribbon roughness combines fine weave with a larger photographic field.
Under the fixed game rig, broad brass-face mean RGB targets are 170/135/73
to 193/157/89 for Remembered and 143/113/61 to 170/135/76 for Present, in
8-bit capture values. These are appearance-calibration targets, not alloy
reflectance measurements. The measured grosgrain pitch is about 0.298 mm.

`medal-budget.json` records 26,290 metal triangles for Remembered and 26,326
for Present, plus a 740-triangle ribbon in each state. The #130 generated
replacement, fitted reverse and soldered attachment raised the earlier
whole-garment ceilings of 22,943 and 28,728. The final ceilings are 39,942
Remembered and 46,515 Present triangles, lowered to measured totals after
the ring and loop tessellation changes. Wool geometry was not reduced to
make room. Support, clearance, performance policy and the maximum 1.5
aged/clean ratio remain unchanged.

The result is not yet photographic in review. The main remaining tells are
the Present enamel perimeter, broad star facets and regular rim rings, and
the ribbon and attachment in wider views. The ingame11 technical checks
pass, including guarded Godot 1019/0, focused Godot 39/0, Python and Blender
regressions, byte-identical saved-source exports and fresh native import
source checks. Those checks do not establish photographic appearance.
Local results and captures are under `tmp/issue130-v3/ingame11/`.

In ingame12, the enamel seam came from the low cage's triangle material cutoff crossing the generated high-surface boundary, so both medal slots now blend isolated PBR maps through an antialiased high-surface mask.
The pass adds bounded photo-derived normal and roughness variation to the repeated star planes and ring response without changing geometry or UVs.
Row-uniform ribbon detail caused molded bands and a hard sheen, so the pass attenuates that component and its normal strength while retaining photographed ribs and raising roughness.

The sections below describe earlier stages, including their previous visual
acceptance, measurements and comparison images. They do not describe the
current generated replacement. The original selected C image and raw guide
remain retained as historical inputs.

The isolated worktree is `tmp/wt-130`, branch `issue-130-tunic-details`, based on
`56a656ba807a477a38503c3b6be0343ebb0b2d4d` (merged PR 118).

## Candidate sources

All PNGs are the unmodified 1024 by 1024 generator outputs. JPEG review copies
are also 1024 by 1024 and live under this worktree's `tmp/issue130-review/`.
The labels describe prompt variations, not observations of the images.

| Candidate | Seed | PNG in this directory | Review JPEG basename |
| --- | --- | --- | --- |
| A: stepped rim | 130101 | `a-stepped-rim-seed130101.png` | `a-stepped-rim-seed130101.jpg` |
| B: shallow scalloped rim | 130202 | `b-scalloped-rim-seed130202.png` | `b-scalloped-rim-seed130202.jpg` |
| C: chamfered rim and recessed channel | 130303 | `c-machined-rim-seed130303.png` | `c-machined-rim-seed130303.jpg` |

Each `.prompt.txt` contains its complete prompt. Each `.metadata.json` is the
unchanged generator sidecar. `generation.json` records exact commands, prompt
text, seeds, timestamps, outputs and environment. The requested cached model
was `filipstrand/Z-Image-Turbo-mflux-4bit`; mflux's sidecars label the underlying
model `Tongyi-MAI/Z-Image-Turbo`. All three commands exited 0. They used mflux
0.17.5, quantization 4, 8 steps, `HF_HOME=/Volumes/XS1000/hf-cache` and
`HF_HUB_OFFLINE=1`, and ran serially.

The shared prompt specifies a single complete metal pendant with a closed
attachment eyelet, warm brass, deep-blue enamel, a raised five-point star,
a roughly 32 mm body diameter and 3 mm depth. It requests a slightly elevated
three-quarter view, visible sidewall and relief, plain light-grey background,
and no fabric ribbon, uniform, person, stand, writing or extra object.
The existing collar insignia and medal both use a five-point star. No rank or
story meaning has been assigned to these variations. The parent source-review
report is `tmp/issue130-review/c-source-review.md`: it describes C as a compact
circular brass/deep-blue enamel pendant with a raised faceted five-point star,
formed rim and top eyelet/bail. It notes that the frontal view does not
establish thickness, backside or attachment construction. A and B remain
unselected; the leaf worker has made no image judgments.

## Measured button gaps

Measurements read `tools/blender/quarters/dress_uniform/tunic-working.blend`
and the accepted `tunic-pilot.blend` without saving either file. The pilot's
button, placket and medal bounds were also checked against
`assets/props/quarters/dress_uniform_aged.glb` outside Blender with trimesh.
The exported multi-material medal has separate metal and ribbon primitives;
this is expected and is not a missing part.

Coordinates below are metres in Blender's native Z-up frame, front toward
-Y. Exported glTF maps `(x, y, z)` to `(x, z, -y)`, with +Y up.
`tunic-measurements.json` records both saved sources. The measurement script
and raw slice segments remain at `tmp/issue130-review/measure_tunic.py` and
`tmp/issue130-review/measurements.json` in this worktree.

The source row has six 14 mm buttons at nominal Z -0.265, -0.365, -0.465,
-0.565, -0.665 and -0.765. Its 28 mm placket spans nominal Z -0.224 to -0.830.
The accepted pose moves these details slightly, including a lateral drift
from X 1.48 mm at the first button to 8.29 mm at the last. Measurements of the
front cloth and placket therefore use a vertical plane fitted to the actual
button centres, rather than assuming every button remains at X zero.

| Accepted pilot measurement | Value |
| --- | ---: |
| Front neckline Z on row plane | -0.158824 |
| Front hem Z on row plane | -0.869793 |
| Placket top Z on row plane | -0.222008 |
| Placket bottom Z on row plane | -0.827865 |
| First button centre Z | -0.262754 |
| Last button centre Z | -0.762898 |
| Neckline to first button centre | 103.93 mm |
| Neckline to first button upper edge | 96.93 mm |
| Last button centre to front hem | 106.90 mm |
| Last button lower edge to front hem | 99.89 mm |
| Placket top to first button upper edge | 33.75 mm |
| Last button lower edge to placket bottom | 57.96 mm |
| Neckline to placket top | 63.18 mm |
| Placket bottom to front hem | 41.93 mm |

These are vertical separations in the accepted pose, not geodesic tape
measurements. The global lowest body vertex is Z -0.977994, in an off-centre
extended hanging part. It is not the front hem beneath the button row.
The collar's global upper bound is Z -0.092292; buttons should terminate below
the neckline, rather than extend onto the standing collar.

### Supported proposal for later implementation

An eight-button row at actual-pose Z -0.180, -0.275714, -0.371429, -0.467143,
-0.562857, -0.658571, -0.754286 and -0.850 keeps approximately the existing
100 mm cadence, with 95.714 mm spacing. A 14 mm button then leaves 14.18 mm
between its upper edge and the neckline, and 12.79 mm between its lower edge
and the local front hem. Keeping six buttons over the same span would increase
spacing to 134 mm.

Every proposed button footprint has front-cloth hits at 181 of 181 samples:
a 1 mm interior lattice plus a 32-point perimeter. The proposed extended
28 mm placket, Z -0.168 to -0.862 following the fitted row, also has front-cloth
hits at 20,155 of 20,155 1 mm grid samples. Both saved blends pass these
support samples. Thus existing cloth supports the proposed extension; the
current placket does not cover the two new endpoints. A later implementation
would need to extend the sewn placket and seat the buttons on that support,
without changing the accepted body cloth.

These samples establish mesh support at finite resolution. They do not prove
continuous nonintersection, material-opacity visibility, final seating or
appearance. No cloth or placket has been changed for this proposal.

A smaller six-button redistribution to nominal Z -0.240 through -0.815 stays
inside the current placket, with full sampled front-cloth support at those
endpoints, but still leaves most of the neckline and hem gap. It would not
extend the row over the full supported garment front.

## Existing medal and ribbon contract

`build.py` creates the pendant at source X 0.108, Z -0.383. The disc measures
32.000 mm in diameter and 0.800 mm maximum depth normal to its own back plane:
a 0.5 mm rim thickness and a further 0.3 mm centre dome. The separate brass
star has 10 mm outer radius, 4.5 mm inner radius and 0.3 mm thickness, placed
0.2 mm above the disc. Tilt makes the disc's world-Y bounds wider than its
actual thickness; those bounds must not be used as depth.

The source `MedalRibbon` is a 20 by 38 mm cloth rectangle, nominal X 0.098 to
0.118, Z -0.366 to -0.328, 0.8 mm thick, offset 0.7 mm from the supporting
surface. The independent sewn `RibbonBar` is 70 by 18 mm, nominal X 0.073 to
0.143, Z -0.329 to -0.311, using the same fabric material with coloured
stripes. The medal ribbon is joined into the `Medal` mesh but retains the
`RibbonFabric` material, while the disc and star use `Brass`.

The accepted pilot disc centre is approximately `(0.110812, -0.055185,
-0.378164)`. Its body top is Z -0.362164 and bottom Z -0.394163. The sewn
medal-ribbon bounds are X 0.099662 to 0.121414, Y -0.057846 to -0.051538,
Z -0.361378 to -0.323091. Its lower edge is about 0.787 mm above the disc's
top in vertical projection. There is no existing modeled suspension loop,
threaded connector or hinge to preserve. The later loop fit must resolve
that junction while retaining the existing sewn ribbon.

The authored attachment record contains 41 disc-back anchors and 35 ribbon
anchors, with `TunicBody` support and nominal offsets 0.5 to 0.7 mm. Aging
bindings separate metal and ribbon into two groups. Metal is fitted rigidly;
the final seating routine treats the ribbon flexibly by paired columns on the
reduced wool and ribbon bar. `RibbonBar` itself is sewn, not rigid. Buttons
seat on `Placket`, while collar stars bind to `Collar`.

The accepted `pilot-seating.json` records metal-base gaps 0.321 to 0.908 mm,
ribbon-base gaps 0.500 to 1.800 mm, and both within the existing 2 mm limit.
Later replacement must preserve the sewn ribbon and its material/vertex-colour
attributes, replace only the metal pendant including its new loop, and update
the metal attachment anchors for the new mesh. The eventual 2 to 4 mm body
must be seated from its back surface; fitting its entire volume to wool would
bury the relief. No replacement or attachment edit has been performed.


## Full Hunyuan raw guide: generated, awaiting shape review

The unmodified guide is
`c-machined-rim-seed130303-hunyuan-full-seed0-oct320-guide.glb` (5,309,036 bytes).
It was generated from the exact selected C PNG, not the JPEG review copy.
SHA256 values are:

- PNG: `900e566387d32661c16274644f23d14b26a1404bc3ee06931a941c6593eaac3a`
- GLB: `cf71dd7144f44bc91e0867ec56f8d23b0289ebf9bf91ec135559f577f4ac26a8`

`mesh-generation.json` records the exact argv and shell command, local model
path, environment, timestamps, exit code and these hashes. The run used
`hunyuan3d-dit-v2-mv` full weights, float16, 30 steps, guidance 5, octree 320,
50,000 decoder chunks, seed 0, background removal and a minimum component size
of 50 faces. `HF_HUB_OFFLINE=1` was set. The generator exited 0 and reported
201.2 seconds of pipeline work and 6.67 GB peak MLX memory. These are observed
run statistics, not a performance benchmark. No components were pruned.
The only other graphics process observed before launch was the headless
Godot import in `wt-129`, which was not modified or interrupted.

The generation log is `tmp/issue130-mesh/generation.log`, with exit marker
`generation.exit` and wrapper `run_generation.py` in that same runtime
directory. Paths here beginning with `tmp/` are relative to `tmp/wt-130`.

### Exported geometry measurements

`guide-metrics.json` records measurements of the actual exported GLB with
trimesh. Exact identical positions were welded only in memory for topology
analysis. The guide file was not edited, repaired, scaled, split or re-exported.

| Raw guide measurement | Value |
| --- | ---: |
| Triangles | 294,904 |
| Stored vertices / unique exact positions | 147,450 / 147,450 |
| Connected components | 1 |
| Watertight / consistent winding / positive volume | true / true / true |
| Boundary / nonmanifold edges / zero-area faces | 0 / 0 / 0 |
| Euler characteristic | -2 |
| Raw X bounds | -0.729898810 to 0.723398507 |
| Raw Y bounds | -0.998964608 to 0.992486358 |
| Raw Z bounds | -0.267774463 to 0.261337876 |
| Raw X / Y / Z spans | 1.453297317 / 1.991450965 / 0.529112339 |
| Adjacent-face angle median / 90th percentile | 0.407 / 7.726 degrees |

All faces belong to the same connected component, so the guide does not
provide a separately movable bail or eyelet. A closed orientable component
with Euler characteristic -2 has genus 2; this topology alone does not locate
or certify either opening as a practical attachment. Self-intersections have
not been tested.

For a sizing estimate only, treat the complete X span as the circular body's
32 mm diameter. That gives 22.018894293 mm per raw unit. Estimate the body's
upper edge as minimum Y plus one diameter, at raw Y 0.454332709, and call
vertices above this cutoff the attachment region. This is an explicit
geometric estimate, not a semantic separation or a fitted production mesh.

| Estimated dimensions at 32 mm body width | Value |
| --- | ---: |
| Complete guide X / Y / Z spans | 32.000 / 43.850 / 11.650 mm |
| Body-region X / Y / Z spans | 32.000 / 31.997 / 4.534 mm |
| Body depth along fitted PCA normal | 4.525 mm |
| Attachment extension above estimated body top | 11.850 mm |
| Attachment-region X / Y / Z spans | 6.427 / 11.845 / 11.650 mm |

The body PCA depth normal is approximately `(0.000031, 0.000585, 1.000000)`.
Its depth span includes relief, rear curvature and scan noise. The body depth
estimate exceeds the later 2 to 4 mm target, while the attachment accounts for
the much larger complete-guide Z span. The frontal source cannot establish
whether those inferred sides and reverse are appropriate. Parent shape review
must assess them before fitting. No dimension has been corrected in this stage.

### Multi-angle evidence for parent image-comparer

All previews live in `tmp/issue130-mesh/`. The existing local
`tests/render_mesh.py` ran twice, with exits 0, using its CPU orthographic
z-buffer and orange Lambertian diagnostic shading. There is no generated
brass/enamel material in these renders. Each angle used the complete guide,
recentered by its bounding box and uniformly normalized in memory. No viewer
was opened. `preview-manifest.json` records commands, image paths, sizes,
angles, renderer hash and the unchanged guide hash before and after rendering.

The assumed axes are +Y up, +Z front and X horizontal. Zero azimuth/elevation
looks from +Z toward the origin with +X to image right. The renderer applies
`R_x(elevation) @ R_y(azimuth)` to the object. Equivalently, its camera position
in original coordinates is proportional to
`(-sin(azimuth)*cos(elevation), sin(elevation), cos(azimuth)*cos(elevation))`.
Thus 90 degrees views from -X, 180 from -Z and 270 from +X. Positive elevation
views from above. Front identity remains for the parent reviewer to confirm.

| Labelled JPEG | Azimuth / elevation |
| --- | --- |
| `guide-front-000.jpg` | 0 / 0 degrees |
| `guide-front-oblique-035.jpg` | 35 / 0 degrees |
| `guide-edge-090.jpg` | 90 / 0 degrees |
| `guide-rear-180.jpg` | 180 / 0 degrees |
| `guide-edge-270.jpg` | 270 / 0 degrees |
| `guide-front-threequarter-035-e20.jpg` | 35 / 20 degrees |
| `guide-rear-threequarter-215-e20.jpg` | 215 / 20 degrees |

Each individual JPEG is 1024 by 1072 including its label; the corresponding
`-raw.png` keeps the full 1024 by 1024 render. `guide-cardinal-raw.png` preserves
the five-view full-resolution strip, and `guide-elevated-raw.png` the two-view
strip. The two labelled sheets are 1280 by 1376, read left-to-right by row:

- `guide-shape-review.jpg`: front 0, oblique 35, edge 90, rear 180.
- `guide-depth-review.jpg`: front 35/elevation 20, rear 215/elevation 20,
  edge 90, edge 270.

Use these against the already reviewed source JPEG at
`tmp/issue130-review/c-machined-rim-seed130303.jpg`. The leaf worker has not
read or judged the images. No shape acceptance, manufacturing-depth approval,
attachment clearance or production readiness is claimed. The accepted cloth,
existing sewn ribbon, button row and production uniform remain unchanged.


## Production fitting, issue #130

**The source, exports and automated fitting checks pass, and image-comparer review passes.** The selected image and full generated guide above remain unchanged. Their SHA256 values are `900e566387d32661c16274644f23d14b26a1404bc3ee06931a941c6593eaac3a` and `cf71dd7144f44bc91e0867ec56f8d23b0289ebf9bf91ec135559f577f4ac26a8` respectively. No additional image, mesh generation or texture-paint run was used for this fitting.

### Shape fitting and editable sources

`tools/blender/quarters/dress_uniform/medal_fit.py` imports the actual guide, scales its body to 32 mm and casts a 40-radius by 60-angle sampling grid. There are 2,366 supported radial samples. A separate 180-spoke probe measures the first raised central region along each spoke; stopping at the enamel field prevents the outer ring from being mistaken for a star tip. Fivefold averages supply the regularized star. Median angular depth profiles locate the inner crest, outer channel and outer crest. The complete samples, constraints and resulting profiles are retained in `medal-fit.json` and on the editable `medal-fitted.blend` scene.

The raw star tip/valley means are 10.957/5.181 mm. The fitted radii are 10.500/5.181 mm with an upright phase of 90 degrees and 0.650 mm central relief above the enamel field. The measured inner crest at 11.626 mm and channel at 14.662 mm drive the clean concentric profile; the channel radius is constrained to 14.400 mm. The minimum star-tip/inner-field margin is 0.576 mm. The fitted outer radial-front departures from the guide are 0.758 mm median, 1.064 mm p95 and 1.210 mm maximum. Those deliberate departures remove the swollen rim and establish the shallow formed profile; they are not claims of scan-surface matching accuracy.

The source cage has 30 angular sectors, analytically fair circular bands and a shared star/enamel boundary. It has no overlapping star-bottom shell and no dense projection back onto scan lumps. `medal-fitted.blend` contains this common editable body before garment fitting. The fully mounted, editable medal and original ribbon are in `tunic-working.blend` and `tunic-pilot.blend`. Both mounted states are derived from that body by `tunic_details.py`; the hidden reverse follows the saved cloth where a flat reverse would exceed the 2 mm support limit. Front relief is retained.

`medal_eyelet.py` measures the existing ribbon and constructs a closed tilted bail with joined straps. A flat rear return across the ribbon's full width could not maintain the existing 0.25 mm metal/wool clearance without moving the ribbon. The fitted rear return therefore closes below the ribbon tip and follows the wool; the front crossbar is 3 mm above the tip. The 0.12 mm rear section, 0.55 mm front section and 0.40 mm vertical section are explicit geometry. Exact Boolean unions produce one connected, watertight metal component. The sewn ribbon is still the original 70 vertices/68 faces, with identical positions, existing UVs and RibbonColours.

### Actual mounted measurements

| Measurement | Remembered | Present |
|---|---:|---:|
| Button count / nominal diameter | 8 / 14 mm | 8 / 14 mm |
| Actual posed vertical pitch | 95.714286 mm | 95.714286 mm |
| Button-edge gap to front neckline | 15.209 mm | 14.978 mm |
| Button-edge gap to front hem | 15.168 mm | 12.798 mm |
| Maximum button-base support distance | 1.019 mm | 1.166 mm |
| Placket support samples | 20,155/20,155 | 20,155/20,155 |
| Medal body diameter | 32.000 mm | 32.000 mm |
| Actual formed body-envelope depth | 3.971 mm | 2.888 mm |
| Raised star relief | 0.650 mm | 0.650 mm |
| Metal reverse-base distances | 0.315 to 1.743 mm | 0.325 to 0.868 mm |
| Ribbon reverse-base distances | 0.700 to 0.700 mm | 0.500 to 1.800 mm |
| Continuous metal/wool clearance | 0.250 mm | 0.250 mm |
| Bail opening width | 22.703 mm | 22.499 mm |
| Bail opening depth range | 0.600 to 1.335 mm | 0.749 to 0.851 mm |
| Actual exported metal/ribbon minimum separation | 0.096 mm | 0.096 mm |
| Strict detail self/body crossings | 0 / 0 | 0 / 0 |
| Medal assembly triangles, including ribbon | 982 | 850 |
| Metal / ribbon triangles | 846 / 136 | 714 / 136 |
| Complete garment export triangles | 13,894 | 20,299 |

The opening follows each fixed ribbon pose, which accounts for its different station count and metal topology between states. Both retain one metal component and one ribbon component. The fixed clean triangle limit remains below 15,000, the aged ceiling remains 20,652 and the aged/clean ratio remains below 1.5. There are 31 retained metal reverse anchors and 35 original ribbon anchors; all eight buttons retain 25 back anchors each. Actual triangle/triangle separation includes vertex/face and interior edge/edge minima.

Brass, navy enamel and woven ribbon remain three separate exported PBR slots. The brass uses the existing deterministic brown-tarnish process. Enamel is dielectric: it has zero metallic factor, clean roughness 0.22, aged roughness 0.38 and its own aged navy colour. The runtime explicitly excludes it from wool colour calibration. The Present state represents 1000 years in dry sterile storage; no biological growth or water drips were added. All unrelated materials and embedded texture payloads match the baseline exports.

### Reproduction and verification

The production route is a saved-source export, without another cloth solve:

```sh
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
PYTHON=/Volumes/XS1000/acoliver/projects/3dlocal/hunyuan3d/.venv/bin/python
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/build.py -- --output tmp/issue130-fit/repeats/dress_uniform.glb
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/build.py -- --aged --output tmp/issue130-fit/repeats/dress_uniform_aged.glb
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/quarters/dress_uniform/test_issue130_details.py
"$PYTHON" tools/blender/quarters/dress_uniform/verify_details_export.py --exports assets/props/quarters --baseline tmp/issue130-fit/baseline --repeats tmp/issue130-fit/repeats --output tmp/issue130-fit/export-verification.json
```

Create the output directory before using these export commands. Both saved-source results are byte-identical to the installed production GLBs. `publish_pilot.py --export-only <path>` remains the equivalent aged export entry point. The historical `--assemble` route has been wired to apply the generated detail fitting, but was not rerun; it requires its original saved sleeve intermediate. The production exports above do not depend on that intermediate.

To repeat the fitting itself, use `tunic_details.py --source-directory tmp/issue130-fit/baseline --output-directory <scratch-output>` after Blender's `--` separator. That source directory must contain the two preserved, pre-fitting six-button blends from baseline commit `56a656b`. The builder checks for an already-fitted medal and fails instead of refitting it silently. It verifies frozen non-detail mesh hashes. `verify_details.py --sources <directory> --baseline tmp/issue130-fit/baseline --output <measurements.json>` checks both states, exact ribbon geometry/UV/colour preservation, actual row endpoints, all placket samples, strict contacts, body depth and fixed budgets. Source records `issue130-details.json`, `construction.json`, `verify.json`, `pilot-gates.json` and `pilot-seating.json` record the final measured source contracts.

Source and independent GLB checks pass, including +Y-up/+Z-front orientation, origin, node pivots, dimensions, material routing, normalized UVs, metal topology, exact unrelated material/texture preservation and saved-source repeat bytes. The original six-button regression failed before implementation. The final regression passes. The retained clean-garment verifier also passes its thickness, collider, crossing, seating, orientation, dimension and repeat-export checks.

### Windowed game captures and limits

`tools/capture_tunic_details.gd` instantiates the actual game, uses the unchanged wardrobe camera and room lights, and captures Remembered/Present wardrobe, buttons and medal views. `tmp/issue130-fit/before/` preserves the baseline; `after/` contains the final game captures. Their camera manifests match exactly. Under `tmp/issue130-fit/review/`, `remembered-wardrobe-before-after.jpg`, `present-wardrobe-before-after.jpg`, `remembered-buttons-before-after.jpg`, `present-buttons-before-after.jpg`, `remembered-medal-before-after.jpg` and `present-medal-before-after.jpg` place before on the left and after on the right. The corresponding filenames without `-before-after` are the larger single-state detail views. JPGs are at most 1400 px per edge and only the existing 40 px protocol band is cropped from presentation images.

A fresh editor import precedes capture. `verify_native_import.py` reads each exact `.glb.import` native path and checks its native `source_md5` against the current GLB; `tmp/issue130-fit/native-import.json` retains the result. GPU process snapshots and capture logs are in the same scratch directory. The windowed capture exits, with the same renderer teardown leak diagnostics observed in the baseline. No performance claim is made. No `gltf-validator` command was available on PATH; the independent glTF/trimesh checks above were run instead. OCR review skipped per Andrew 2026-10-09. The completed image-comparer reviews and corrected capture provenance are recorded below.


### Final automated test results

The final guarded full Godot suite passes **1010 tests, zero failures**, with no script errors or guard violations. All **26 asset-verification commands** in `tmp/issue130-fix-bake/checks.json` exited 0, including **18 tunic/attachment regression scripts**. The separate aging package passes **89 tests**. Portable aging units pass **66 tests** and Blender-hosted aging units pass **10 tests**, totaling **76 units**; the mask-baker fixtures also pass. Final logs remain under `tmp/issue130-fix-bake/`: `godot-full.log`, `test-*.log`, `aging-package-unit.log`, `aging-unit.log`, `aging-blender-unit.log`, `aging-mask-fixture.log`, `verification-source.log`, `verification-export.log` and `clean-surface.log`. The earlier focused runtime cohort passes **51/0**, including all 11 fixture-aging cases, in `tmp/issue130-fit/godot-focused.log`. Godot's existing resource/ObjectDB/allocator teardown diagnostics remain.

### Final review and comparison images

Technical acceptance is **PASS**, with no remaining in-scope defects, in
`tmp/issue130-fix-bake/acceptance-verification.md`. Image-comparer reports PASS
for the medal, row placement and wardrobe preservation in
`tmp/issue130-fit/review/medal-visual-review.md`,
`buttons-visual-review.md` and `wardrobe-visual-review.md`. The final Present
row/material/context review is PASS in
`tmp/issue130-fix-bake/review/final-visual-review.md`. These report paths are
relative to the worktree and remain local; the comparison JPGs below are
committed byte-for-byte copies of the reviewed images.

| Committed comparison, baseline left / current right | Original reviewed file |
| --- | --- |
| [Remembered buttons](remembered-buttons-before-after.jpg) | `tmp/issue130-fit/review/remembered-buttons-before-after.jpg` |
| [Remembered medal](remembered-medal-before-after.jpg) | `tmp/issue130-fit/review/remembered-medal-before-after.jpg` |
| [Remembered wardrobe](remembered-wardrobe-before-after.jpg) | `tmp/issue130-fit/review/remembered-wardrobe-before-after.jpg` |
| [Present buttons](present-buttons-before-after.jpg) | `tmp/issue130-fix-bake/review/present-buttons-before-after.jpg` |
| [Present medal](present-medal-before-after.jpg) | `tmp/issue130-fit/review/present-medal-before-after.jpg` |
| [Present wardrobe](present-wardrobe-before-after.jpg) | `tmp/issue130-fix-bake/review/present-wardrobe-before-after.jpg` |

The copies retain the existing comparison layout, 40 px protocol-band crop
and 1400 px maximum edge. No new render, image generation or recompression was
used. The row bake correction changes neither the clean source/export nor
the medal's geometry, materials or texture payloads, so the earlier medal
and Remembered reviews still apply.

The early button review's before-count estimate was uncertain. Fresh native
imports and actual runtime mesh inventories establish **six baseline buttons
and eight current buttons** in both states. Every historical before crop is
pixel-identical to the fresh six-button baseline, with MAE 0.0 in all six
views. The evidence does not support a stale-before explanation. Camera
manifests match exactly. `tmp/issue130-fix-bake/before/provenance.json`,
`after/provenance.json`, `historical-pixel-comparison.json` and
`final-native-import.json` retain the source/native checks and runtime counts.

The corrected Present placket and buttons are baked from their final surfaces
with explicit `BakeUV` bindings. `test_detail_bakes.py` checks expected pixels,
source/export position-UV correspondence, selected material coordinate sets
and exact embedded PNG bytes. Both use `TEXCOORD_1`; four historical defects
are independently rejected in `negative-controls.json`. Source/export
preservation and byte-identical repeats are recorded in
`source-preservation.json`, `export-verification.json` and `final-status.json`,
all under `tmp/issue130-fix-bake/`. The diagnostic-only placket mask/control
PNGs remain local and are not production dependencies.

Both current production GLBs match repeated saved-source exports byte for byte.
Their current source MD5s, also recorded in the fresh native imports, are
`e6ad66eb0f8dbcd84e54b3c83f3f8922` clean and
`25a5cb23c18ea0e95cf91389102cc629` aged. The historical `--assemble` route still
lacks its original saved sleeve intermediate; saved-source production export
is verified. Khronos CLI validation is unavailable on this machine. Godot
teardown diagnostics remain. The still-image reviews do not establish hidden
mechanical strength or behavior across all lighting and viewing angles.

## Present brass finish

The integrated and individual raw medal captures were byte-identical. This
adjustment addresses the existing Present finish, with no integration-render
repair or geometry change. The formed star's folded planes, 32 mm body,
2.888224 mm Present envelope and 0.650 mm relief remain unchanged.

Only `Medal_DullBrownBrass` changes: metallic 0.15 to 0.55, roughness 0.94 to
0.58. Specular stays 0.12. The existing brown-tarnish albedo, its UV binding
and every embedded image remain exact. The finish retains a rough satin
response rather than the clean brass's metallic 0.80 / roughness 0.30.
The change aims to expose the existing rim and facet response under the same
room light without brightening pigment, adding emission or changing normals.
It applies to the medal's brass rim, star and attachment only; blue enamel,
ribbon, buttons, collar insignia and all other surfaces are unchanged.

`baked_age_colour.aged_brass()` applies this finish only when authoring `Medal`.
The saved `tunic-pilot.blend` carries those same two values; saved-source export
is through `publish_pilot.py --export-only`. No runtime override was added.
The new Present GLB has source MD5 `6d73618fbd6a758bec84929df867324a`
and SHA256 `d99dff8265bc1420f01c9e2f4ae29b95323ce125f8978910e55e5622150ef533`.
Its saved-source repeat has identical bytes. The editor import's native source
MD5 matches; earlier MD5 values above describe the preserved prior export.
The common `medal-fitted.blend`, Remembered source/export and the source
concept/generated guide remain byte-identical. The earlier row bake repair
and its regression assertions are retained.

New baseline comparisons preserve the earlier reviewed JPGs at their original
paths. The following files show baseline `56a656b` on the left and the new
finish on the right:

- [Present medal](present-medal-metal-finish-baseline-before-after.jpg).
- [Present wardrobe](present-wardrobe-metal-finish-baseline-before-after.jpg).

The current-finish versus new-finish comparison is
`tmp/issue130-metal-finish/review/present-medal-finish-before-after.jpg`.
Single medal and wardrobe JPGs, full raw PNGs, camera/native/runtime records
and verification logs are in that same scratch root. Packaging uses the
original individual-capture bicubic resize, quality 93 and 4:4:4 sampling.
The original game capture helper, cameras, lighting and 40 px protocol crop
are unchanged. Final visual QA passed in
`tmp/issue130-metal-finish/review/visual-review.md`: the rim highlight and folded
star response are clearer while the brass remains aged and subdued. The review
requires no further finish adjustment. The wardrobe review establishes no visible
unintended change; exact raw-pixel checks separately establish preservation.
Technical verification records 29 passing asset commands, guarded Godot 1010/0,
focused runtime 51/0, aging package 89/0 and fixture weather 11/0 under
`tmp/issue130-metal-finish/`. No merge is implied.
