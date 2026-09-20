# gone: technology plan

## Engine decision

**Godot 4.7.2 (stable), GDScript, Forward+ renderer.** The project began
on Rust with Bevy 0.19. That tree is archived unchanged at `archive/rust/`
(commit 7617ca7, the merge of the issue-10 emergency lighting work), and
the Godot tree at the repository root is the live implementation. The
Bevy selection rationale in the archived history was written for that
stack and stays there; `archive/rust/README.md` is the record.

The pivot kept the contract and replaced the code: fixed 60 Hz simulation
ticks, seeded RNG, a protocol-shaped harness with beat captures and a
two-stage verdict, and the opening beat from the design docs.

What Godot supplies for this build:

- Forward+ clustered omni lighting carries the red emergency fixtures.
- GPUParticles3D carries sparks and ceiling smoke.
- A canvas shader pass over the finished 3D frame carries the wake eyelid.
- `godot --headless` runs the whole test suite and the harness runner
  without a window, so the sim and the protocol logic are tested with no
  GPU interaction.
- The project's 60 Hz physics tick (`physics_ticks_per_second` in
  `project.godot`) hosts the sim tick through `_physics_process`.

The language is GDScript everywhere. One language keeps the sim pure and
testable in the same runtime the game ships on, with no binding layer
between the sim and the app.

Engine version discipline carries over from the Rust plan: pin the exact
version (4.7.2), upgrade deliberately one step at a time, and treat the
harness lanes as the regression gate for any engine bump.

## Platform

Multi-platform remains a requirement. macOS is the primary development
platform (M4 Max), Windows and Linux remain targets, and the hardware
floor stays 2023-and-newer machines: Apple M3 family onward, NVIDIA RTX 40
(Ada) onward, AMD RDNA 3 onward (RX 7000 discrete and Radeon 700M-class
integrated), and Intel Arc onward. Nothing below that floor is supported.
Quality tiers (baseline, recommended, enhanced) scale within the floor
once there is something to scale.

What is verified today is narrower than the intent. Every measured run so
far (the 204-test suite and the gameplay, perf, and calibration lanes)
executed on the M4 Max machine under Forward+. Windows and Linux
measurements land when representative hardware joins the loop, one card
per major vendor, as in the Rust plan. Until then only the macOS claims
have measurements behind them.

## Rendering approach

The milestone 1 look is a dark greybox stasis room under red emergency
light. How the rendering plan maps onto Godot:

- **Emergency fixtures.** Eight red OmniLight3D fixtures: one wall-mounted
  above each of the seven registry pods plus one over the hatch lintel
  (`app/lighting.gd`). Each fixture carries a lens cuboid, and all lenses
  share one emissive material. The sim's PowerGrid owns power; a
  FixtureFade bridge reads it, retargets only on a sim-side change, and
  settles over 30 logical ticks. Shadows are off, ambient is disabled, fog
  is off, and the room authors no other light source.
- **Sparks and smoke.** Spark bursts are a strobed OmniLight3D flash plus
  a one-shot GPUParticles3D spray at the authored cable-tray spots
  (`app/hazards.gd`). Smoke is a GPUParticles3D emitter whose spawn box
  hugs the ceiling, with slow downward drift and preprocessing so the haze
  exists from the first captured frame. The Rust-era plan used Bevy
  FogVolume entities with a vertical density ramp; Godot's FogVolume would
  need a custom density shader for that gradient, so particles carry the
  ceiling-hugging look instead (a recorded deviation, see
  `docs/dev/godot-port.md`).
- **Exposure.** The room is dim red emitters on black. A CameraAttributes
  exposure multiplier (2.0, `app/lighting.gd`) stands in for the Rust
  slice's EV100 0 and is sized so the red emitters read without washing
  out the black around them.
- **Wake eyelid pass.** `app/wake_eyelid.gdshader` runs on a full-screen
  ColorRect inside a top CanvasLayer (`app/wake_pass.gd`), compositing lid
  openness, blur, and an exposure ramp over the finished 3D frame. This is
  Godot's stock path for a post effect over the 3D view, with no nested
  viewports. The presentation driver (`app/wake_present.gd`) projects the
  sim's wake sample onto the pass every render frame; the sample's sway
  offset moves the camera.
- **Baked lightmaps, later.** The multi-state baked GI plan (dead,
  emergency, partial, restored, crossfaded as systems are repaired) is
  unchanged as intent. Godot ships LightmapGI for it. No baked lightmaps
  ship in milestone 1; milestone 1 lighting is the realtime red fixtures
  above.

## Workspace architecture

Three directories at the repository root, mirroring the archived crate
split:

- `sim/` is the pure GDScript port of `gone_sim`: `colliders`, `resolve`,
  `controller`, `phase`, `pods`, `power`, `intensity`, `walk`, `exit`,
  `wake`, with `sim.gd` as the facade (the shape of `lib.rs`). Every
  module extends RefCounted, and each module header declares the rule: no
  Node, scene, rendering, or input types. The suite runs all of it
  headless, which is the architecture gate in practice: sim state and
  logic must run with no display server and no GPU, and an engine
  reference there breaks that property loudly.
- `app/` is the Godot game. `main.gd` is the root scene script; `game.gd`
  is the 60 Hz sim container (registry, colliders, phase machine, power
  grid, wake state, exit path, ticked from `_physics_process`); the
  greybox room, pods, hatch, and hazards build procedurally at runtime
  from the authored placement data; the player rig, motion mirror, and
  shared input plane live in `player.gd`, `motion.gd`, `input_plane.gd`;
  the harness-driven lanes are `harness_mode.gd` (gameplay and perf) and
  `calibration_mode.gd`.
- `harness/` is the runner and protocol: `protocol.gd` (the shared wire
  surface, `PROTOCOL_VERSION = 4`), `scenario.gd` and `report.gd` (the
  types), `run.gd` (the runner), `perf_policy.gd` with
  `perf-policy.json`, and `calibration.gd` with
  `calibration_assertions.gd`.

Two rules carry over from the Rust workspace. First, the sim is
authoritative: app nodes read sim state through bridges and never write
ahead of the controllers that own it. Second, the scene is procedural
from authored placement: room envelope, pods, hatch, cable trays, and
colliders derive from the frozen pod registry and placement data, and the
gameplay lane verifies runs against placement-derived truth
(`app/placement_truth.gd`) rather than literals, so the game and its
verifier cannot drift apart silently.

## Harness protocol summary

The development loop assumes the implementer is an LLM that cannot see
the screen. The runner (`harness/run.gd`) drives the real game and
produces evidence that a vision-capable subagent then verifies. The full
contract lives in `docs/dev/harness.md`; the shape:

- **Env contract.** The runner spawns the app with `GONE_HARNESS=1`,
  `GONE_SCENARIO`, `GONE_OUT_DIR`, `GONE_APP_HASH`,
  `GONE_SCENARIO_HASH`, `GONE_CONFIG_HASH`, and `GONE_PERF_POLICY` on the
  perf lane. The app echoes the hashes verbatim and hashes nothing
  itself, so a stale pairing fails.
- **Hashes.** The scenario and config hashes are sha256 over the scenario
  file's exact bytes. The app hash is sha256 over every `*.gd` file under
  `app/`, `sim/`, and `harness/`, sorted by relative path, each entry
  hashed as its UTF-8 relative path, one NUL byte, and its exact file
  bytes. An edited script cannot masquerade as the tested build.
- **Beats.** Scenarios pin named captures (`beats/<name>.png`) carrying a
  rendered frame-code chip that encodes the logical tick and the rendered
  frame. The runner decodes each PNG and checks it against the report, so
  a beat that happened between rendered frames cannot be fabricated.
- **Two-stage verdict.** Stage one is machine: report version, hash echo,
  beat decode and tick correlation, luminance and red-dominance stats,
  wake progression, door-open evidence, perf thresholds, calibration
  assertions. Stage two is visual: a vision subagent receives the beat
  PNGs and an expectations checklist; missing or inconclusive visual
  results count as failures.

## Quality gates

- **Unit suite.** `godot --headless --path . -s tests/run_tests.gd` runs
  204 auto-discovered tests from `tests/*_test.gd` and exits 1 on any
  failure.
- **Gameplay lane.** The runner on `scenarios/gameplay-full.json` drives
  the whole opening beat with seven captures (eyes-closed, first-blink,
  shapes-resolving, standing, mid-room, at-door, door-opened), a
  readiness proof, hash echo, and tick/frame correlation.
- **Perf lane.** The same runner on `scenarios/perf-smoke.json` judges
  frame times against the smoke-grade policy.
- **Calibration lanes.** The runner on `scenarios/calibration-step.json`
  and `scenarios/calibration-move.json` verifies the auto-exposure
  evidence cells.
- **Negatives.** `scenarios/negative/never-beat.json` and
  `scenarios/negative/calibration-no-autoexposure.json` must FAIL (runner
  exit nonzero). A negative case that passes means the instrument is
  broken.

The lanes spawn a windowed app even though the runner itself is headless.
Long windowed runs on this machine may need `nohup` plus polling; an OS
watchdog kills long foreground commands.

## Performance

The smoke-grade gate is met. The policy (`harness/perf-policy.json`,
version `godot-smoke-1152x648-v1`) fixes 60 warmup frames, 300 samples,
uncapped presentation, 1152x648 resolution, and thresholds of 25 ms mean
and 50 ms p95, measured in the populated room (pods, preprocessed ceiling
smoke, automatic spark bursts active). Measured on M4 Max: mean 8.33 ms,
p95 9.4 ms, 300 samples at a 120 fps cadence. Machine PASS, with the
distribution recorded in the run's `perf-verdict.json`.

The milestone 1 gate is unchanged from the Rust plan and has not been
measured on the Godot tree: the populated room sustains 60 FPS at physical
3840x2160 with render scale 1.0, in a release build, on M4 Max, measured
wall-clock by the harness over a defined sample window with warmup, under
simultaneous sparks and smoke, separately from capture overhead. The smoke
policy exists to catch regressions cheaply; closing milestone 1 requires
the 4K gate. Windows and Linux equivalents are recorded per GPU vendor
(one representative 2023+ NVIDIA, AMD, and Intel card) when hardware joins
the loop.
