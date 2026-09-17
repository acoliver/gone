# gone: Godot port record

The Rust/Bevy 0.19 workspace is archived unchanged at `archive/rust/`
(commit 7617ca7). The Godot 4.7.2 tree at the repository root reimplements
its behavioral contract: the sim, the opening beat, and the harness
protocol. This file records what moved where, how the port was verified,
and where it deviates from the Rust design on purpose.

## Crate-to-directory mapping

- `gone_sim` became `sim/`: `colliders.gd`, `resolve.gd`, `controller.gd`,
  `phase.gd`, `pods.gd`, `power.gd`, `intensity.gd`, `walk.gd`, `exit.gd`,
  `wake.gd`, with `sim.gd` as the facade in the shape of `lib.rs`. Every
  module is pure RefCounted logic with no Node, scene, rendering, or input
  types, so the whole sim runs headless without a GPU.
- `gone_app` became `app/`: `main.gd` (the root scene script), `game.gd`
  (the 60 Hz sim container, the old StasisScenePlugin contract),
  `room_geometry.gd`, `pods.gd`, `pod_body.gd`, `hatch.gd`, and
  `placement.gd` (the greybox room and placement parity),
  `placement_truth.gd` (placement-derived verification truth),
  `lighting.gd` (the issue-10 emergency lighting bridge), `hazards.gd`
  (sparks and smoke), `wake_pass.gd` with `wake_eyelid.gdshader` and
  `wake_present.gd` (the eyelid pass and its presentation driver),
  `player.gd`, `motion.gd`, `input_plane.gd` (the rig, the motion mirror,
  and the shared input plane with the ScriptedAdapter), and the driven
  lanes `harness_mode.gd` and `calibration_mode.gd`.
- `gone_harness` became `harness/`: `run.gd` (the runner), `protocol.gd`
  (the wire protocol, the frame-code chip, the identity hashes),
  `scenario.gd` and `report.gd` (the types), `perf_policy.gd` with
  `perf-policy.json`, `calibration.gd` with `calibration_assertions.gd`,
  and the metering mask PNGs.
- `xtask` has no Godot equivalent. Its gates (clippy thresholds, source
  line counts, complexity policy) were Rust tooling. The quality gates now
  are the headless test suite, the lanes, and the negative cases; see
  `docs/design/technology.md`.

The `app/capture_*.gd` scripts (`capture_smoke`, `capture_lit`,
`capture_wake`, `capture_gameplay`) are the port's own staged smoke lanes
from bringing the renderer up: windowed, self-terminating, machine-checking
their captures. The protocol lanes superseded them for verification, and
they remain as quick one-shot checks.

## Test mapping

204 tests, all green, auto-discovered by `tests/run_tests.gd` (which loads
every `tests/*_test.gd`, runs each `test_*` method, prints per-failure
diagnostics plus a `passed=N failed=Y` tally, and exits 1 on any failure).
The mission carried two kinds of coverage:

- Sim tests, ported assertion-for-assertion from the Rust suites:
  `colliders_test`, `resolve_test`, `controller_test`, `phase_test`,
  `pods_test`, `power_test`, `intensity_test`, `walk_test`, `exit_test`,
  `wake_test`, and `sim_test` (the facade and standalone construction).
- App and harness parity tests, pinning that the Godot side matches the
  sim's contract and the protocol's shape: `placement_test`,
  `lighting_test`, `player_test`, `wake_present_test`, `harness_test`
  (chip encode/decode, scenario parse, report schema), `perf_test`, and
  `calibration_test`.

## How to run everything

Unit suite (204 tests, headless):

    godot --headless --path . -s tests/run_tests.gd

Lanes (runner headless, spawned app windowed):

    godot --headless --path . -s harness/run.gd -- scenarios/gameplay-full.json
    godot --headless --path . -s harness/run.gd -- scenarios/perf-smoke.json
    godot --headless --path . -s harness/run.gd -- scenarios/calibration-step.json
    godot --headless --path . -s harness/run.gd -- scenarios/calibration-move.json

Negatives (exit 1 is the passing outcome):

    godot --headless --path . -s harness/run.gd -- scenarios/negative/never-beat.json
    godot --headless --path . -s harness/run.gd -- scenarios/negative/calibration-no-autoexposure.json

Long windowed runs may need `nohup` and polling on this machine; an OS
watchdog kills long foreground commands.

## Verification results

The machine stage passed everywhere: 204 of 204 unit tests; the gameplay
lane machine PASS (seven beats plus the readiness proof, hash echo,
tick/frame correlation, wake progression, refusal evidence); the perf lane
machine PASS at the smoke-grade policy (mean 8.33 ms against the 25 ms
budget, p95 9.4 ms against 50 ms, 300 samples, 120 fps cadence); both
calibration cells PASS; both negative cases fail as they must.

The visual stage passed as well. The vision subagent (the Eyes) reviewed
the lane's beat images and passed 8 of 8, finding no rendering defects.
Two observations are recorded and open for a later art pass, neither
blocking: pod forms and smoke are weakly legible in the standing and
mid-room frames, and the hatch covers about a quarter of the frame in the
at-door beat.

## Known deviations from the Rust design

- **Eyelid pass.** The Rust slice used a Bevy FullscreenMaterial post
  pass. The port runs `wake_eyelid.gdshader` on a full-screen ColorRect in
  a top CanvasLayer, Godot's stock path for a post effect over the 3D
  view. The same param triple maps over (lid openness, blur, exposure
  ramp); the sample's sway offset stays camera motion.
- **Smoke.** The Rust-era plan used Bevy FogVolume entities with a
  vertical density ramp. Godot's FogVolume needs a custom density shader
  for that gradient, so smoke is a GPUParticles3D ceiling emitter with
  preprocessing instead.
- **Lighting units.** One line in `lighting.gd` converts the authored
  lumens to OmniLight3D energy: `FIXTURE_LUMENS / (2.0 * TAU)`, so 45 lm
  becomes about 3.58 candela read directly as energy under Godot's
  non-physical omni falloff. An `exposure_multiplier` of 2.0 stands in for
  the Rust slice's EV100 0.
- **Perf policy.** Smoke grade: 1152x648 with 25 ms mean and 50 ms p95
  budgets (`godot-smoke-1152x648-v1`). The milestone 1 gate stays 4K60 on
  M4 Max and has not been measured on this tree.
- **Windowed app lane.** The Rust harness ran the app headless into an
  offscreen render target. The Godot runner stays headless but spawns the
  app windowed (480x270 by default) and captures from the window's
  rendered frame.
- **Config hash.** The Rust runner hashed its own config string; the port
  sets the config hash equal to the scenario hash.
