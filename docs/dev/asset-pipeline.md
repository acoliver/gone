# Asset pipeline: Blender to glTF to Godot

Status: proven end to end on 2026-09-18 with the stasis-pod probe for
[issue #45](https://github.com/acoliver/gone/issues/45). The probe is a
parametric capsule pod (off-white composite shell, dark glass canopy
hinged open 55 degrees, padded couch inside) that exercises every hop a
real asset will take: authored build, GLB export, Khronos validation,
Godot import, render, machine pixel gates, and visual review.

## Production pod (#88)

The seven pods use `assets/props/pod/pod-v4.glb`, copied from the
Hunyuan-derived clean-cage pass-13 delivery. The editable source and
self-contained export script live in [`tools/blender/pod_v4/`](../../tools/blender/pod_v4/README.md).
This replaces the parametric v3 production pod. `build_pod_probe.py` is
retained for the original #45 probe commands below, not as a production
pod builder.

Rebuild from the repository root using the commands in that README,
then import twice and commit the GLB and its `.glb.import` sidecar.
The five-node hierarchy preserves PodLid's hidden pivot and its WindowPane
child. Closed size is 2.392917 × 0.899940 × 0.895995 m (length, width,
height), with the couch plateau at Y=0.240 m. Coordinates are pod-local
metres: +Y up, +Z foot, -Z head, floor at zero. No mesh fitting transform
is applied. The source has 28,566 triangles. To preserve the existing 20,000-triangle
runtime budget, PodMesh uses the first generated Godot LOD on the two
ShellPlastic surfaces and WindowTint, leaving upholstery and gasket
unchanged. Runtime total is 17,062 triangles. The importer reports maximum
errors of 0.923 mm (base), 0.729 mm (lid), and 0.657 mm (pane); code rejects
an error of 1 mm or more. The full-resolution GLB is retained unchanged.

ShellPlastic is glossy white dielectric plastic, roughness 0.12,
clearcoat 1 and coat roughness 0.08. PodMesh restores clearcoat in code
because Godot drops the glTF extension. WindowTint stays dark and opaque;
CouchFabric, PillowFabric and Gasket retain their source material values.
Sealed lids are closed, empty-open lids rotate -70° about local X, and
the player lid rotates -78° for ceiling clearance (#88). Meshes and
materials are shared across pods.

The 8 m bay retains its reflection probe. Only the bay aisle narrows to
2.9 m; the hallway and ship layout retain their independent 3.0 m width.
The couch height drives the get-up path. The foot wall has no collider,
as before; passing the body capsule through that visible tub wall is an
accepted limitation. At the 78-degree player pose, the three lid proxies
cover the upper panels, leaving the lower lid outside collision so its
AABBs do not block the conservative get-up sweep (#88). Body-to-mesh
collision remains approximate; sealed and empty-open proxies are unchanged.
The eye trajectory is checked separately against
the actual asset. Dense nearest-surface sampling finds a 237.140 mm
minimum on the live rig's straight eye interpolation, at the pillow.
The independent capsule quarter-circle eye arc approaches the raised lid
to 91.897 mm; this arc is not the live camera interpolation. The runtime
mesh test checks the live eye against the unchanged 130 mm requirement.

The player lid opens 78 degrees, reaching Y=3.145976 m with 54.024 mm
clearance below the 3.2 m ceiling (#88). This is the largest whole-degree
opening that retains at least 50 mm clearance: 79 degrees leaves only
37.684 mm. Measurements use the actual pod-v4 lid and pane vertices about
the exported pivot, without changing the room height, pod scale or hinge.
Empty-open remains at 70 degrees and reaches 2.997186 m.

Both red flank tubes remain on the stationary base in every state.
Waypoints are measured at Y=0.280 m (+X) and 0.120 m (-X), 24 mm outward
from the horizontal skin intersection, with a 12 mm tube radius. Full
strip/source triangle checks find no intersections in any state, with a
minimum sampled base gap of 9.362 mm. Existing skin-contact tolerance,
dressing clearance checks and 576-triangle strip budget are retained.

## Original probe chain

All commands run from the repo root. Scratch output lives under
`tmp/pipeline/` (gitignored). Blender 4.5.11 LTS is borrowed from the
threedee project and is not vendored here:

```
BLENDER=/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender
```

1. **Build** (deterministic, parametric, no randomness, no time
   dependence):

   ```
   $BLENDER --background --factory-startup \
       --python tools/blender/build_pod_probe.py -- \
       --output tmp/pipeline/pod-probe.glb \
       [--length 2.2] [--half-width 0.45] [--half-height 0.425] \
       [--lid-angle 55.0] [--rim-angle 55.0]
   ```

   The script prints `TOTAL` mesh stats and a `RISE` line (canopy
   far rim above the shell rim) and exits nonzero if the rise collapses
   below 80 percent of the expected open angle, so a lost transform
   fails the build instead of shipping silently.

2. **Validate** (Khronos glTF-Validator, zero errors required):

   ```
   npm ci --prefix tools/gltf-validator
   node tools/gltf-validator/validate.cjs tmp/pipeline/pod-probe.glb \
       tmp/pipeline/validate.json
   ```

   The tracked wrapper and lockfile in `tools/gltf-validator/` use the
   official npm validator build (2.0.0-dev.3.10). Run `npm ci` after a
   clean checkout; `node_modules/` is ignored by Git and the directory's
   `.gdignore` keeps it out of Godot imports. The output parent must exist.
   Reports record errors and warnings; errors produce a nonzero exit code.
   Scratch output under `tmp/` remains available through direct file I/O,
   but `tmp/.gdignore` excludes it from Godot's editor import scan.

3. **Import**:

   ```
   cp tmp/pipeline/pod-probe.glb assets/props/probe/pod-probe.glb
   godot --headless --path . --import
   ```

   Run the import twice when the GLB is brand new: the first pass
   registers it, the second reports errors honestly. The
   `.glb.import` file is committed with the GLB.

4. **Render and capture** (windowed; headless cannot render):

   ```
   godot --path . --resolution 640x360 -s assets/props/probe/probe_capture.gd
   ```

   Writes two captures of the same framing: `tmp/pipeline/probe-capsule.png`
   (red emergency lane) and `tmp/pipeline/probe-capsule-neutral.png`
   (neutral white material lane), and prints the imported canopy
   transform as a `PROBE` line so node transforms are checkable from the
   log.

5. **Machine check** (headless):

   ```
   godot --headless --path . -s assets/props/probe/probe_check.gd
   ```

   Gates per lane: non-black mean, a pod-sized bright-structure
   fraction, and hue gates (the red lane must be red-dominant; the
   neutral lane must keep bright pixels near-neutral for the off-white
   shell). Exits 0 only when every gate passes.

6. **Eyes review** of both captures against the expectations in #45
   (pod form, open canopy with visible couch, correct hue lanes). The
   driver cannot read images; the image-comparer subagent returns
   per-expectation verdicts.

## Numbers from the smoke

- Mesh: 3 objects (Shell, Canopy, Couch), 2610 verts, 5032 tris,
  3 materials, 3 draw calls, no textures. The budget is 50k tris.
- Validator: 0 errors, 0 warnings, 0 infos.
- Captures: red lane mean 11.22/255 with 8.79 percent bright fraction;
  neutral lane mean 27.29/255 with 12.31 percent bright; hue gates pass.
- Suite: 204 passed, 0 failed (main baseline).

## Lessons that are now rules

- Frame probes from the opening side. The first review read the canopy
  as closed. The camera sat on the hinge side, so the raised wing
  foreshortened into a thin dark band, and near-black glass (albedo
  0.03) over a near-black background (0.01) under one dim light is
  indistinguishable from a closed lid. The transform chain was correct
  at every hop (GLB node quaternion, Blender `matrix_world`, Godot
  import), proven by an A/B render against a `--lid-angle 0` reference.
  The diagnosis order that worked: parse the GLB JSON chunk, print
  `matrix_world` in Blender, walk the imported scene, then A/B.
- Two lighting lanes per probe. The game's red emergency light checks
  mood; a neutral white light checks material hue. A single red lane
  cannot verify an off-white albedo, because everything it lights is
  red.

## Next

- The production mesh currently uses the same open canopy on all seven
  pods. Rendered state variants and occupancy blankets remain separate
  work. Placement and clearance pins must keep holding.
- #35 wall textures ride the same validator and import gates: geometry
  first, then PBR from ambientCG CC0 bases plus locally generated
  decals.
- The local Hunyuan3D-2mv MLX output path supplies the #91 terminal and
  status-panel props. Its license restrictions are recorded below.

## Power-room terminal and status-panel props (#91)

The standing console and separate generated keyboard are in `assets/props/terminal/`; the north-wall status panel and its native/perceived board layers are in `assets/props/status_panel/`. The GLBs embed their images. The console exports `DisplayPlane`, `ScreenSocket` and `KeyboardSocket`; the keyboard's `KeyboardBase` takes its transform from `keyboard-placement.json`. Triangle totals are 48,002 for the console, 28,998 for the keyboard, and 44,972 for the status panel, within the 50,000-triangle budget per GLB. The console body is reduced from the supplied standing-height mesh with a deck-protecting Blender decimation pass. Source images, raw meshes, scripts, provenance and license records are under `art-source/terminal/` and `art-source/status_panel/`.

The active terminal uses the shared console text cache and perception timing. The wall board uses native Naleya and perceived Spanish layers with the same attention memory. The Hunyuan3D-2mv community license excludes the European Union, the United Kingdom and South Korea, and restricts use, distribution and display of outputs outside those territories. These assets must not be treated as unrestricted worldwide content; see the copied license and notice records before distributing them. FLUX.2-klein-4B is Apache-2.0, which does not change Hunyuan's output terms.
