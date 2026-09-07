# gone: technology plan

## Engine decision

**Bevy 0.19** (released 2026-06-19). Rust-native, ECS architecture that
suits our sim/render split, and the first-party renderer already contains
the features this game is built on: clustered forward lighting, baked
lightmaps, volumetric fog volumes, auto exposure, and the post-processing
hooks we need for the wake-up sequence. MSRV is 1.96; our toolchain is
rustc 1.98.0.

Bevy ships breaking releases on a roughly quarterly cadence, so we pin the
version and upgrade deliberately, one release at a time, with the harness
as the regression gate. Alternatives were considered and rejected: Fyrox
1.0 has a built-in editor but a lower rendering ceiling for what we want
(this game leans on lighting and volumetrics), and Godot keeps Rust
second-class and would put core rendering decisions behind GDScript-era
assumptions.

## Platform

Multi-platform is a requirement, not a port: macOS (primary development,
M4 Max, 40-core GPU, Metal) and Windows are first-class targets, Linux is
supported, and all three run the same wgpu stack (Metal, DirectX 12,
Vulkan). Platform discipline: no OS-specific code outside the wgpu/winit
layer; paths through `std::path` with forward-slash relative paths in
artifacts and JSON; filenames stay case-sensitivity-safe; the harness
protocol (child process, input adapter, exit codes, artifact layout) is
OS-portable and designed against the strictest platform, since macOS
imposes winit main-thread rules that Windows and Linux do not; per-backend
capability recording (adapter info, clustered light limits) so rendering
budgets are measured per platform, not assumed portable. The workspace
cargo-checks against Windows and Linux targets from the start. Milestone
1's performance gate is defined on M4 Max; Windows and Linux measurements
land when representative hardware joins the loop.

## Rendering approach: raster first

The core look is multi-state baked global illumination with realtime
clustered dynamic lighting on top.

- **Multi-state baked lightmaps.** The ship is lit by baked lightmaps in
  four power states: dead, emergency, partial, restored. As the player
  repairs systems, states crossfade. Bevy ships the `Lightmap` component,
  irradiance volumes, and reflection probes, plus a `mixed_lighting`
  example with Baked/MixedDirect/MixedIndirect/RealTime modes.   Bevy has
  no first-party baker; bakes happen offline in Blender with The
  Lightmapper addon and land as compressed ktx2 assets. No baked
  lightmaps ship in milestone 1: emergency lighting there is realtime red
  fixtures. The first baked state arrives with the first repair milestone.
- **Realtime clustered dynamic lights.** Flashlight, work lamps, sparks,
  and console glows are realtime lights over Forward+ clustered shading,
  which Bevy 0.19 does on the GPU.
- **Volumetric atmosphere.** FogVolume entities per compartment, driven
  by the atmosphere simulation. Smoke concentrates at the ceiling in the
  opening room because that is where the torn wiring is. FogVolume's
  scalar density factor is uniform within a volume, so the ceiling
  gradient uses the volume's 3D density texture with an authored vertical
  ramp.
- **Post chain.** Auto exposure with a center-weighted metering mask,
  AgX tonemapping, vignette, subtle chromatic aberration, film grain.
  Bevy has lens distortion and vignette as first-party post effects since
  0.19, auto exposure since 0.15. Milestone 1 enables AgX, auto exposure
  (with the metering-mask asset), and vignette; chromatic aberration and
  film grain arrive with the art-pass milestone.
- **Contact shadows** on the flashlight for close-range detail.
- **Eyelid wake-up.** A fullscreen post pass using `FullscreenMaterial`
  (first-party since 0.18): blur, a lid mask, an exposure ramp, and a
  slow camera sway that together stage the blink sequence when the player
  wakes.

Solari (Bevy's ray-traced GI path) stays an optional future tier behind a
feature flag; see the next section for why.

## Ray tracing on Apple hardware: the answer

The question: is ray tracing on this machine a hardware limitation, or is
it just not ported to Metal?

**It is not the hardware. It is the software stack.**

- Apple GPUs from the M3 family (and A17 Pro) onward include
  hardware-accelerated ray tracing; Apple lists it among the M3 GPU
  features (https://www.apple.com/newsroom/2023/10/apple-unveils-m3-m3-pro-and-m3-max-the-most-advanced-chips-for-a-personal-computer/),
  and the M4 Max in the dev machine inherits it. Metal has exposed ray
  tracing through the MetalRT APIs (`MTLAccelerationStructure`, ray
  queries, intersection functions) since Metal 3 in 2022
  (https://developer.apple.com/metal/ray-tracing/).
- wgpu's Metal backend did not implement ray tracing until recently.
  The tracking issue is
  https://github.com/gfx-rs/wgpu/issues/7402 (opened March 2025); the
  implementation landed through https://github.com/gfx-rs/wgpu/pull/8071
  (a continuation of #7660), and it remains experimental.
- That port is still shaking out driver-level problems on macOS: example
  test failures tied to the Metal debug layer and headless windows
  (https://github.com/gfx-rs/wgpu/issues/9100), and missing
  synchronisation between acceleration structure builds that was fixed
  with fences in https://github.com/gfx-rs/wgpu/pull/9645 (June 2026),
  with follow-on work in https://github.com/gfx-rs/wgpu/issues/9215.
  Ray-tracing *pipelines* (as opposed to inline ray queries) on Metal are
  still an open design question: https://github.com/gfx-rs/wgpu/issues/8560.
  MoltenVK, the Vulkan-on-Metal translation layer, has no ray tracing
  either (https://github.com/KhronosGroup/MoltenVK/issues/427,
  https://github.com/gfx-rs/wgpu/issues/7660 references it in discussion;
  see also https://github.com/KhronosGroup/MoltenVK/issues/1956).
- Bevy's Solari renderer builds on the Vulkan ray-tracing path and
  NVIDIA-class features (hardware RT requirement:
  https://github.com/bevyengine/bevy/pull/10000 and
  https://github.com/bevyengine/bevy/pull/19058; the unified DI/GI update:
  https://github.com/bevyengine/bevy/pull/24767; DLSS Ray Reconstruction
  work: https://github.com/bevyengine/bevy/pull/25423). Solari is not a
  usable path on macOS today regardless of what wgpu's Metal backend can
  technically do.

**Decision:** the game renders with the raster pipeline described above.
The hardware would allow ray tracing later if wgpu's Metal backend
matures; Solari stays behind a feature flag as a possible tier for
RT-capable targets (Windows/Linux with RT GPUs). Nothing in the art
direction depends on ray tracing: baked multi-state GI plus clustered
dynamics gives the look with far less risk.

## Workspace architecture

Discipline borrowed from the sibling `stranded` reconstruction project:

- Crates: `gone_sim` (headless ship systems simulation: power, atmosphere,
  hull, comms, game state), `gone_app` (Bevy glue: rendering, input,
  audio, UI), `gone_harness` (the play-testing runner, see below), and
  `xtask` (build and quality gates).
- `gone_sim` never depends on Bevy or any render crate. This is enforced,
  not aspirational: a CI check rejects the dependency edge, the same way
  stranded enforces its sim/render separation.
- Data-driven definitions (ship layout, compartments, systems) live in
  data files the sim consumes, so level logic is testable without a GPU.
- WGSL-only shader sources, shipped with the build. Bevy/wgpu creates
  specialized GPU pipelines at runtime by design; a readiness handshake
  guarantees all milestone-1 pipelines and assets are prepared before the
  wake timeline starts, and performance measurement lanes contain no
  pipeline compilation.
- `#![forbid(unsafe_code)]` workspace-wide; clippy pedantic plus the
  thresholds below.

## Build and quality gates: xtask

The build tooling is ported from **jefe** (`/Volumes/XS1000/acoliver/projects/jefe/branch-6`),
which has the most developed version of this among the surveyed projects.
Survey outcome:

- **jefe**: modular Rust xtask (`xtask/src/{cli,clippy_policy,source_size,architecture,toolchain,process,windows_coverage}.rs`)
  with `ci`/`quick`/`fmt`/`lint`/`complexity`/`coverage`/`build`/`test`
  commands, a five-threshold complexity policy in `clippy.toml`, a
  zero-tolerance scanner for clippy `allow`/`expect` suppressions, and a
  source-file-length gate. The line-size gate (`source_size.rs`) is itself
  a documented port of a shell script, `scripts/check-source-file-size.sh`
  (the shell version of the same policy), and the architecture check
  pairs an xtask command with grep-based shell assertions
  (`scripts/check-architecture.sh`). Best fit; we port this.
- **personal-agent**: xtask is a single 628-line `main.rs` focused on
  parsing LLVM coverage data. Not a complexity/line-size tool.
- **uqm (rust part)**: a heavyweight CI orchestration xtask (build
  evidence, reproducibility proofs, mutation testing). Sophisticated but
  aimed at deterministic native archive builds; not the tool we need. Its
  acceptance and capture harness scripts are useful precedent for our
  runner, noted below.
- **llxprt-agent**: no such directory exists at `../../llxprt-agent` (or
  in `~/projects`); excluded from the survey.

What we port from jefe:

1. **Complexity thresholds** in `clippy.toml`, kept in sync in two copies
   (repo root and the CI config dir) so neither can silently drift:
   `cognitive-complexity-threshold = 15`,
   `too-many-lines-threshold = 60` (lines per function),
   `too-many-arguments-threshold = 6`, `max-struct-bools = 3`,
   `type-complexity-threshold = 250`.
2. **Source file length gate** (`cargo xtask check source-size`): warn at
   750 lines, hard-fail at 1000 lines per first-party Rust file, scanning
   `src` and `tests`.
3. **Clippy suppression gate** (`cargo xtask check clippy-allows`):
   zero `#[allow(clippy::..)]`/`expect` in first-party code; suppressions
   must come from threshold changes, not annotations.
4. **Architecture gate** (`cargo xtask check architecture`): at minimum,
   the rule that `gone_sim` never imports render/Bevy crates.
5. **Command surface**: `cargo xtask ci` runs fmt, the policy checks,
   clippy (pedantic + thresholds), locked build, locked tests, and the
   harness smoke scenario, failing fast in that order.

## Incremental compilation: off

Incremental compilation is disabled everywhere:

- `[profile.dev] incremental = false` in the root `Cargo.toml`, and
- `CARGO_INCREMENTAL = "0"` in `.cargo/config.toml` so every invocation
  path (cargo, xtask, IDEs honoring the config) sees it.

Rationale: incremental artifacts grow the target directory continuously
and do not repay that in build speed for this workload (full check/build
times stay comparable while the disk cost keeps mounting). Clean
`target/` semantics also make harness runs and profiling reproducible.

## Harness-based development

The development loop assumes the implementer is an LLM that cannot see
the screen. Therefore the game ships with a runner that lets an agent
play it and produces evidence that vision-capable subagents then verify.

`gone_harness` (driven by `cargo xtask harness <scenario>`) provides:

- **Scripted play.** Scenarios are declared as input scripts (look
  targets, movement, interactions, timing) executed against a fixed
  timestep with a seeded virtual clock, so runs are reproducible. The
  logical timeline defines tick zero, the fixed frequency, the input
  consumption order, and separately seeded RNG streams; button edges are
  buffered so each edge is consumed exactly once regardless of how many
  fixed updates run per rendered frame. Reproducibility scope is the
  same build, configuration, and seed on the target machine;
  pixel-identical GPU output is not promised.
- **Input injection.** The harness feeds synthetic input events the same
  way real devices do, through the app's input layer, never by calling
  gameplay functions directly.
- **Capture.** Screenshots at named beats (eyes-closed, first-blink,
  sparks-visible, standing, mid-room, at-door, door-refused). Temporal
  beats (blinks, spark bursts, the door shake) are short timestamped
  frame sequences covering before/during/after, not single frames. Each
  capture is correlated to the simulation tick and rendered frame; the
  runner starts scenarios only after a pipeline/asset readiness handshake
  and waits for capture completion before reporting success or exiting.
  A structured JSON report (player transform, ship state, event log,
  frame timings) accompanies the captures. Artifacts land under
  `tmp/harness/<scenario>/<run-id>/`, which is gitignored. Paths are
  unique per run so concurrent sessions cannot clobber each other, and
  each run records build, scenario, and checklist identities so stale or
  cherry-picked artifacts cannot satisfy a newer run.
- **Visual verification protocol.** The driver agent cannot read images.
  After a run, a vision-capable subagent receives the beat screenshots
  and an expectations checklist (red light, smoke denser at the ceiling,
  sparks strobing) and returns pass/fail per expectation with quotes of
  what it sees. The driver aggregates that with the JSON report into the
  run verdict. Verdicts are two-stage: machine checks passed (JSON) and
  visual verification passed; missing, malformed, or inconclusive visual
  results count as failures, not passes. No verdict is final on pixel
  checks alone; the JSON evidence gates gameplay logic. The suite keeps
  negative verification cases (spark particles with their light
  disabled, a refusal event with no hatch animation, collision disabled
  during a crossing) that must fail the relevant expectations, so the
  instrument cannot silently drift into reporting success without proof.
- **Performance beats.** The report records wall-clock frame-time
  distributions per beat, measured in the populated room separately from
  capture/readback overhead, so "4K at 60 FPS on this machine" is a
  measured claim, not a hope.

Precedents in the sibling projects: jefe's `scripts/validate-newissue-wrap.sh`
drives the built TUI app in tmux, types input, captures the pane, and
asserts on the capture; uqm's `rust/harness/` scripts drive the game
binary and capture state with screenshot tooling. Our runner is the same
idea upgraded to a 3D game: drive, capture, hand the capture to a
vision-capable verifier.

## Ecosystem pins (verify at integration time)

- **Physics**: Avian 0.7 (active, supports Bevy 0.19) for props, debris,
  and door dynamics. Milestone 1 movement is a kinematic capsule with a
  custom swept-collision resolver against authored static colliders (no
  rigid-body dynamics solver, but real collision work, owned by the
  blockout issue); Avian arrives with interactive objects.
- **Level authoring**: Blender greybox first. bevy_trenchbroom 0.14
  supports Bevy 0.19 but its maintainer states the crate is on life
  support; treat it as optional tooling, not infrastructure.
- **Video playback** (later milestones): no first-party Bevy support
  (https://github.com/bevyengine/bevy/issues/19172); community options
  are bevy_movie_player (ffmpeg-backed) and bevy-ffmpeg. Decide at the
  security-monitor milestone; an image-sequence fallback is always
  available.
- **Particles**: bevy_hanabi 0.19 declares Bevy 0.19 compatibility in its
  published metadata; execution on this machine's Metal backend is still
  verified at milestone 1, with hand-rolled particle systems as the
  fallback for sparks and smoke wisps.

## Performance

Milestone 1 closes only on a measured gate, not a recorded hope: the
populated room (pods, wires, smoke, sparks active) sustains 60 FPS at
physical 3840x2160 with render scale 1.0, in a release build, on M4 Max,
measured wall-clock by the harness over a defined sample window with
warmup, under simultaneous sparks and fog, separately from
capture/readback overhead. The measured frame-time distribution and the
configuration (adapter/backend, present mode, active effects, sample
window) are posted on the epic. Windows and Linux equivalents are
recorded when representative hardware joins the loop. Quality tiers
(baseline/recommended/enhanced, as stranded does) come when there is
something to scale.
