# Asset pipeline: Blender to glTF to Godot

Status: proven end to end on 2026-09-18 with the stasis-pod probe for
[issue #45](https://github.com/acoliver/gone/issues/45). The probe is a
parametric capsule pod (off-white composite shell, dark glass canopy
hinged open 55 degrees, padded couch inside) that exercises every hop a
real asset will take: authored build, GLB export, Khronos validation,
Godot import, render, machine pixel gates, and visual review.

## Production pod (#88)

The seven pods now share `assets/props/pod/pod-v3.glb`, built by the same
parametric script as the original probe. Rebuild from the repo root:

```sh
/Volumes/XS1000/acoliver/projects/threedee/branch-1/.tools/Blender-4.5.11.app/Contents/MacOS/Blender \
    --background --factory-startup --python tools/blender/build_pod_probe.py -- \
    --output assets/props/pod/pod-v3.glb
godot --headless --path . --import
godot --headless --path . --import
```

Commit the GLB and its `.glb.import` sidecar. The builder has fixed vertex
order and no random or clock inputs. It bakes the hinge and modifiers,
then fits the assembly to 0.9 m width, 0.8 m height and 2.2 m length.
Vertices export directly in the pod frame: +Z foot, -Z head, +Y up, deck
at zero. `PodMesh.shell_transform()` is identity. No runtime bounding-box
fit or collider change is needed.

The asset has 15,496 triangles: 7,792 shell, 5,904 canopy and 1,800 couch.
Curved panels are welded smooth quad lofts with a solid rim, not separate
flat-shaded triangles. Pads have beveled edges. One mesh carries three
surfaces named `ShellPlastic`, `CanopyGlass` and `CouchFabric`, with no
textures. `app/pod_mesh.gd` assigns one cached material per named surface
and shares the resulting mesh across all seven pods. Plastic is neutral
near-white, roughness 0.12, metallic 0, clearcoat 1 with roughness 0.08.
Glass is dark tinted and opaque to avoid sorting between its two skins,
with roughness 0.06 and metallic 0. Fabric is dark with roughness 0.9.

`Lighting` adds one interior, box-projected bay reflection probe without
ambient fill, lights, shadows or colliders. It captures once at startup
and once when a lighting fade settles, including secondary white power
and an emergency blackout. It does not recapture every frame. The flank
strip waypoints are frozen measurements of triangle intersections at
y 0.580 and 0.310 m, with centers 0.006 m inside the new skin. Tests check
contact between stations as well as at the authored waypoints, and keep
the existing dressing clearances and sit-up corridor limits.

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
   node tmp/pipeline/valtool/validate.cjs tmp/pipeline/pod-probe.glb \
       tmp/pipeline/validate.json
   ```

   The smoke used the official npm validator build (2.0.0-dev.3.10, the
   version threedee pins) through a scratch wrapper under `tmp/`. That
   wrapper is not committed; giving the validator a durable home in this
   repo (vendored wrapper or a reused threedee script) is open tooling
   debt tracked on #45.

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
- Hunyuan3D dressing props stay blocked on weights; the survey and the
  open question for Andrew are on #45.
