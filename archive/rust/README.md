# Archived Rust/Bevy implementation

The Rust workspace (`gone_sim`, `gone_app`, `gone_harness`, `xtask`; Bevy
0.19) was the original implementation of `gone`. Development pivoted to
Godot (4.7.2) and the Rust tree was archived unchanged at
commit 7617ca7 (merge of issue-10 emergency lighting).

Everything here is frozen reference material:

- `crates/gone_sim` — headless ship simulation: phases, wake timeline,
  pods, power grid, fixture intensity fades, walk steadying, exit/door
  refusal, swept-capsule collision resolver, controller.
- `crates/gone_app` — Bevy app: stasis room scene, emergency lighting
  bridge, eyelid wake post pass, player motion, harness lanes
  (gameplay/calibration/perf) and the wire protocol.
- `crates/gone_harness` — the runner: spawns the app, decodes captures,
  computes the two-stage verdict.
- `crates/xtask` — build and quality gates.
- `.cargo/`, `Cargo.toml`, `Cargo.lock`, `clippy.toml`,
  `clippy-config/` — workspace configuration.

The behavioral contract this tree established (fixed 60 Hz ticks, seeded
RNG, protocol-shaped harness with beat captures and two-stage verdicts,
the opening beat from the design docs) is being reimplemented in Godot
at the repository root. Do not build from this directory; it is kept for
design archaeology and fallback.
