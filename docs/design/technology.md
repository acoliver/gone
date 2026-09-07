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

Primary development target is macOS on Apple Silicon (M4 Max, 40-core
GPU, Metal). wgpu, Bevy's rendering backend, runs on Metal on this
machine. Windows and Linux are future targets through the same wgpu
stack; nothing in the design assumes macOS-specific APIs.

## Rendering approach: raster first

The core look is multi-state baked global illumination with realtime
clustered dynamic lighting on top.

- **Multi-state baked lightmaps.** The ship is lit by baked lightmaps in
  four power states: dead, emergency, partial, restored. As the player
  repairs systems, states crossfade. Bevy ships the `Lightmap` component,
  irradiance volumes, and reflection probes, plus a `mixed_lighting`
  example with Baked/MixedDirect/MixedIndirect/RealTime modes. Bevy has
  no first-party baker; bakes happen offline in Blender with The
  Lightmapper addon and land as compressed ktx2 assets.
- **Realtime clustered dynamic lights.** Flashlight, work lamps, sparks,
  and console glows are realtime lights over Forward+ clustered shading,
  which Bevy 0.19 does on the GPU.
- **Volumetric atmosphere.** FogVolume entities per compartment, driven
  by the atmosphere simulation. Smoke concentrates at the ceiling in the
  opening room because that is where the torn wiring is.
- **Post chain.** Auto exposure with a center-weighted metering mask,
  AgX tonemapping, vignette, subtle chromatic aberration, film grain.
  Bevy has lens distortion and vignette as first-party post effects since
  0.19, auto exposure since 0.15.
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
- WGSL-only shaders; no runtime shader compilation in release builds.
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
  timestep with a seeded virtual clock, so runs are reproducible.
- **Input injection.** The harness feeds synthetic input events the same
  way real devices do, through the app's input layer, never by calling
  gameplay functions directly.
- **Capture.** Screenshots at named beats (for example: eyes-closed,
  first-blink, sparks-visible, standing, at-door, door-refused) plus a
  structured JSON report (player transform, ship state, event log, frame
  timings). Artifacts land under `tmp/harness/<scenario>/<run-id>/`,
  which is gitignored. Paths are unique per run so concurrent sessions
  cannot clobber each other.
- **Visual verification protocol.** The driver agent cannot read images.
  After a run, a vision-capable subagent receives the beat screenshots
  and an expectations checklist (red emergency light, smoke denser at the
  ceiling, sparks strobing) and returns pass/fail per expectation with
  quotes of what it sees. The driver aggregates that with the JSON report
  into the run verdict. No verdict is final on pixel checks alone; the
  JSON evidence gates gameplay logic.
- **Performance beats.** The report records frame statistics per beat so
  "4K at 60 FPS on this machine" is a measured claim, not a hope.

Precedents in the sibling projects: jefe's `scripts/validate-newissue-wrap.sh`
drives the built TUI app in tmux, types input, captures the pane, and
asserts on the capture; uqm's `rust/harness/` scripts drive the game
binary and capture state with screenshot tooling. Our runner is the same
idea upgraded to a 3D game: drive, capture, hand the capture to a
vision-capable verifier.

## Ecosystem pins (verify at integration time)

- **Physics**: Avian 0.7 (active, supports Bevy 0.19) for props, debris,
  and door dynamics. Milestone 1 movement is a kinematic capsule and
  needs no solver; Avian arrives with interactive objects.
- **Level authoring**: Blender greybox first. bevy_trenchbroom 0.14
  supports Bevy 0.19 but its maintainer states the crate is on life
  support; treat it as optional tooling, not infrastructure.
- **Video playback** (later milestones): no first-party Bevy support
  (https://github.com/bevyengine/bevy/issues/19172); community options
  are bevy_movie_player (ffmpeg-backed) and bevy-ffmpeg. Decide at the
  security-monitor milestone; an image-sequence fallback is always
  available.
- **Particles**: bevy_hanabi's Bevy 0.19 pairing is unverified as of this
  writing; milestone 1 checks it, with hand-rolled particle systems as
  the fallback for sparks and smoke wisps.

## Performance

Target: 4K, 60 FPS, on M4 Max, in the milestone 1 room, with the full
post chain and volumetrics on. The harness report is the measurement
instrument. Quality tiers (baseline/recommended/enhanced, as stranded
does) come when there is something to scale.
