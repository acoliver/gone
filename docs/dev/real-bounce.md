# Fixture-driven GI experiment

Keep GI off in the main game. This branch adds opt-in SDFGI and an SSIL comparison, with no default lighting change. Both fail all eight rib/duct face-to-sheet contrast checks against the 0.30 gate. SDFGI leaves the white hall beam's broad underside at display luminance 0.00006787, unchanged from the baseline; SSIL reaches only 0.00007543.

On the native M4 Max/Metal route, SDFGI raises paired median-frame cost by 40.46% under secondary white and 41.26% under emergency lighting. SSIL raises it by 20.21% and 18.30%. Both exceed the +10% budget. Median whole-view display-luminance changes are +0.027%/+0.058% for SDFGI and +0.366%/+0.249% for SSIL, white/emergency respectively. The actual red-to-white source handoff passes in both modes, but usable return on the black faces remains inadequate.

## Run in a separate worktree

Import this worktree before launching it. Do not switch the checkout from which Andrew is running the game.

```sh
godot --headless --editor --path . --import
GONE_REAL_BOUNCE=sdfgi godot --path .
```

Unset `GONE_REAL_BOUNCE` for the original rendering. `GONE_REAL_BOUNCE=ssil` selects the screen-space comparison. SSIL cannot reproduce offscreen return and samples visible emission as well as directly lit surfaces, so it is not a complete source-only transport solution.

SDFGI uses four cascades, 0.1 m minimum cells, occlusion enabled, sky input disabled, and energy 1.0. Bounce feedback stays at the engine default 0.5. Actual source bake modes stay dynamic and indirect energies stay 1.0. Source energy, placement, color, range, falloff, masks, angular profiles, shadows and exposure are not changed. Ambient remains disabled, black and zero-energy. No light nodes, hidden bounce geometry or emissive gain are added.

`app/real_bounce.gd` excludes existing emissive mesh surfaces from SDFGI generation, so the actual Light3D does not acquire a second source through its visible lens. It refreshes source visibility registration after procedural assembly, using deferred node calls so attachment can finish first. The final visible state is unchanged. Initial rooms, prepared connectors and streamed remote rooms use the same setup. SDFGI still has static-geometry limitations: doors do not update voxel occlusion continuously, and nearby streamed geometry can require a cascade rebuild.

## Capture and measure

Use a separate absolute output directory. Before any native rendering on the shared workstation, wait for the other native lane locks to clear, then hold the GI lane lock throughout the run. The task's scratch driver implements that protocol and focuses only its owned window.

```sh
GONE_REAL_BOUNCE= godot --path . -s tools/preview_real_bounce.gd -- /absolute/output/base
GONE_REAL_BOUNCE=sdfgi godot --path . -s tools/preview_real_bounce.gd -- /absolute/output/sdfgi
GONE_REAL_BOUNCE=ssil godot --path . -s tools/preview_real_bounce.gd -- /absolute/output/ssil
python3.14 tools/check_real_bounce.py /absolute/output
```

The tool captures 26 views per mode at 2304 by 1296, MSAA 2x, seed 91 and fixed exposure. Each camera settles for 120 distinct rendered frames. Both circuits include connector bulkhead, duct collar, along connector, hall end, ship end, bay/hall/power beams at 2.5 m and close range, and hall/connector overviews. Close beam cameras are approximately 1 m away and oblique, avoiding the pendant that blocks the straight-up power-room close view.

The baseline generates visibility masks from the actual painted housing triangles, selecting downward broad faces below the glass. The measurement erodes masks by one pixel and excludes edge glints. Masks never contribute to a lit capture. The checker verifies identical camera/owner/circuit/door state, reproduces the issue-105b 0.30 face-to-sheet display-luminance gate, and writes `metrics.json` and a labelled 2304-pixel-wide `compare.jpg`. It also reports whole-view display and linear luminance. Requires the existing Pillow/NumPy tooling.

## Dynamic switching and cost

```sh
GONE_REAL_BOUNCE=sdfgi godot --path . -s tools/check_real_bounce_handoff.gd -- /absolute/output/handoff-sdfgi
GONE_REAL_BOUNCE=sdfgi godot --path . -s tools/perf_real_bounce.gd -- /absolute/output/perf-sdfgi.json
```

The handoff tool presses the actual console, advances the existing fixture bridges at 60 logical steps per second and checks monotonic red-to-white source fades. It saves source energies and frames at 0, 15, 30, 60 and 120. A source fade passing does not by itself prove adequate indirect return.

The performance tool uses a populated production scene, including wires, with fixed seed and disabled automatic sparks in both variants. It measures an uncapped 1152 by 648 hall/connector camera route, MSAA 2x, 120 warmup frames and 300 samples per circuit. Run six separate processes in A/B, B/A, A/B order for each candidate. Report the median paired mean-frame-time ratio and paired frame-median ratio against the +10% budget. Raw per-frame and GPU timing values are saved. This is a controlled rendering route, not a worst-case ship-streaming or gameplay simulation benchmark.

The full investigation report, native logs and contact sheet are in the main checkout's ignored `tmp/gi/` directory. VoxelGI and LightmapGI feasibility, unresolved production transport limitations and renderer controls are recorded there. No PR is part of this experiment.
