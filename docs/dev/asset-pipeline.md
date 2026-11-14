# Asset pipeline: Blender to glTF to Godot

Production props retain an editable source, an exporter, the GLB and any external textures. Export from the retained source when reproducing a shipped asset. Reconstructing generation or cloth simulation is a separate operation and may require local intermediates.

## Production sources

| Asset family | Editable source and build guide | Runtime output |
| --- | --- | --- |
| Stasis pod | [Pod v4](../../tools/blender/pod_v4/README.md) | `assets/props/pod/pod-v4.glb` |
| Quarters | [Quarters art](../art/quarters/README.md) | `assets/props/quarters/` |
| Stasis wiring and seat | [Installed wiring](../art/stasis-wiring-production-installation.md), [seat](../art/seat-production-integration.md) | `assets/props/stasis-wiring/` |
| Power-room console and keyboard | `art-source/terminal/`, including `export_game_console.py` and the retained generated assembly | `assets/props/terminal/` |
| Power-room status panel | `art-source/status_panel/build_panel.py` and `decimate_panel.py` | `assets/props/status_panel/` |

The pod source has tagged glass regions, a hinged lid, couch and pillow. Runtime restores shell clearcoat and binds the pane to `app/pod_glass.gdshader`. `sim/pod_geometry.gd` owns its production opening angle. Consult the pod source guide for current geometry, optical diagnostics and limitations rather than reusing dimensions from the original probe.

The terminal exports `DisplayPlane`, `ScreenSocket` and `KeyboardSocket`. Keyboard placement comes from its placement JSON. The active console and status board use the shared Naleya/Spanish perception system. Console screen fit is checked against the reduced housing rather than inferred from its bounding box.

## Export and import

Quarters builders use Blender-native +Z up, front -Y and `export_yup=True`, giving glTF +Y up and front +Z. Other retained sources can use their own documented frame; the pod source is already Y-up. Check the exported asset's orientation and bounds outside Blender.

For example, export the current pod with Blender 4.5.11 LTS:

```sh
"$BLENDER" --background --factory-startup --python-exit-code 1 --python tools/blender/pod_v4/build.py -- --output assets/props/pod/pod-v4.glb
godot --headless --editor --path . --import
```

Set `BLENDER` to the executable. The project keeps `.glb.import` sidecars with source assets. A new asset may need another import after registration. Before capture, verify that Godot's native imported resource corresponds to the current source; stale native caches can render an earlier mesh or texture despite a changed GLB.

## Verification

Run the source-specific exported-mesh checks in the guides above. They cover geometry, named parts, supports, materials, UVs and repeat exports. Test the runtime imports as well:

```sh
godot --headless --path . -s tests/run_tests.gd
```

Relevant suites include `tests/pod_mesh_test.gd`, `tests/pod_glass_test.gd`, `tests/console_screen_fit_test.gd`, `tests/quarters_props_test.gd` and the family-specific tests listed in each guide. Native rendering is required to assess glass, fine fabric, dust and lighting. Keep a neutral-light view for material colour alongside the actual game-light view.

An optional Khronos validation wrapper is tracked at `tools/gltf-validator/validate.cjs`. When its locked dependency is already available, run:

```sh
mkdir -p art-output
node tools/gltf-validator/validate.cjs assets/props/pod/pod-v4.glb art-output/pod-validation.json
```

The wrapper exits nonzero on validation errors. This is separate from game-space contact, optical and visual checks.

## Original probe

`tools/blender/build_pod_probe.py` and `assets/props/probe/` retain a small parametric capsule for testing the Blender-to-Godot path. It is not the production pod builder. Its capture/check scripts use their own fixed output locations. Use production source guides when changing game assets.

## Known limitations

Some fitting and simulation reconstruction paths depend on untracked intermediates; saved-source exports are retained for those assets. Pod optical and collision approximations have open limitations documented with its source. Numerical validation does not establish visual quality or appearance under every camera and light.
