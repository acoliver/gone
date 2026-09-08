# gone harness protocol

This is the contract between `gone_app` (the game) and `gone_harness` (the
runner) at slice A: how a scenario is declared, how the runner drives the app,
how the two hand off readiness, what lands on disk, and what makes a run pass or
fail. Its home is `docs/dev/harness.md`. The one source of truth for the on-wire
JSON and the pixel encoding is `crates/gone_app/src/harness/`; `gone_harness`
re-exports that surface and never defines a type of its own.

The protocol version both sides embed and compare is
`gone_app::harness::PROTOCOL_VERSION` (currently `3`). A report whose version
does not equal the runner's is rejected. Version 2 is the real-capture protocol:
beats are readbacks of an offscreen render target the harness camera draws into,
the frame-code chip is a sprite rendered into the scene, input events carry
their press/release edge, and capture failures are recorded as `Failure` events.
Version 3 adds the performance lane: scenarios gain a `mode` (capture or perf)
with warmup/sample window counts, reports gain the optional `perf` section, and
the scenario `pacing` field is consumed at window creation.

## Two crates, one boundary

- `gone_app` (Bevy 0.19) owns the protocol: `crates/gone_app/src/harness/{scenario,input,beat,frame,report,perf,mod}.rs`.
  It reads a scenario, opens a real window, runs the fixed timeline, captures
  screenshots, writes the report, and exits by itself. The app-side lane lives
  in `crates/gone_app/src/bootstrap/`: `mod.rs` is the plugin plus the ECS
  systems and capture I/O, `state.rs` is the run-state ledger (counters, beat
  ledgers, readiness gate, failure recording, perf sampler), and `tests.rs`
  pins the accounting and readiness regressions.
- `gone_harness` (no Bevy) is the runner: `crates/gone_harness/src/bin/gone_harness.rs`.
  It hashes the build and scenario, spawns the app, waits for it, decodes the
  beat PNGs, checks the report, and prints the two-stage verdict.

The dependency edge is one-way: `gone_harness` depends on `gone_app` (for the
protocol types only), and the app never depends on the runner.

## Child-process lane

The runner spawns `target/debug/gone_app` (the binary it was built with) with:

- `GONE_HARNESS=1` (the app selects the bootstrap plugin).
- `GONE_SCENARIO=<abs path>` (the scenario file the app parses).
- `GONE_OUT_DIR=<abs path>` (the run directory the app writes into).
- `GONE_APP_HASH=<sha256>` (of the app binary bytes; the report echoes it back).
- `GONE_SCENARIO_HASH=<sha256>` (of the scenario file bytes; echoed back).
- `GONE_CONFIG_HASH=<sha256>` (the runner's config string; echoed back).

All three hashes are real SHA-256 computed runner-side from the bytes it actually
spawned and passed; the app echoes them back verbatim.

The app runs as the normal winit app: `WinitPlugin` owns the OS event loop,
which is what opens the 1920x1080 window (scale factor forced to 1.0 so logical
pixels equal physical pixels) and presents frames. The window is presentation
only; captures never come from its swapchain (see the capture lane section for
why). There is no manual update loop anywhere in the harness path. The runner
owns the child lifecycle (`try_wait` poll on a 10ms cadence, `DEFAULT_TIMEOUT`
60 seconds), and on drop (including error paths) it SIGKILLs and `wait`s so no
`gone_app` is orphaned. On macOS killing the child pid is sufficient; Windows
kill-tree is deferred to stage B.

## Capture lane (offscreen render target)

The harness camera renders into a dedicated offscreen `Image` render target
(`RenderTarget::Image` on the `Camera2d`), created at startup as a 1920x1080
`Bgra8UnormSrgb` texture with `RENDER_ATTACHMENT | TEXTURE_BINDING` usage. Every
capture of the run is a bevy `Screenshot::image(target_handle)`: the render
graph blits the camera's frame into a readback buffer and hands the mapped
`Image` to the app's `ScreenshotCaptured` observer.

The harness never captures from the window swapchain. `Screenshot::
primary_window()` works on this machine when the bevy feature set is correct:
an earlier probe's all-black captures were our own feature-selection error,
not a platform property. The probe's minimal feature list omitted
`bevy_sprite_render`, so nothing drew and even clear-only captures read back
zeros; with the corrected feature set the same probe captured correctly (and
it still verifies that the offscreen path renders and reads back). A related
usage error from the same probe: a texture created with
`RenderAssetUsages::MAIN_WORLD` alone never appears in a capture; textures
need `MAIN_WORLD | RENDER_WORLD` (`RenderAssetUsages::default()`).

The harness keeps the offscreen Image capture lane for two real reasons: its
captures are exactly 1920x1080 regardless of window scale or DPI overrides,
and capture timing is decoupled from the swapchain and present. The OS window
presents nothing during harness runs because the only harness camera renders
into the Image; switching captures to `Screenshot::primary_window()` is a
possible future simplification. The winit window stays open so the app runs as
a real windowed app, and the offscreen image is the capture source of truth.

Sprite rendering has its own feature gate in Bevy 0.19: the sprite render pass
lives in `bevy_sprite_render`, separate from the `bevy_sprite` API crate.
Without `bevy_sprite_render` in the app's bevy features, sprites (including the
frame-code chip) never draw anywhere; the feature is enabled.

## Readiness handshake (the exact signal)

The app starts in the loading presentation: a dark clear, the harness `Camera2d`
rendering into the offscreen target, no authored content. While loading it
requests a bevy screenshot of the offscreen target every update
(`Screenshot::image`). A request that reaches the render world before the
camera's first rendered frame is skipped or deduplicated there, so the app keeps
requesting until one lands.

The readiness signal is the first `ScreenshotCaptured` for the offscreen target:
the capture is the readback of a frame the render graph actually executed into
the target, so it is direct evidence the renderer built its device resources and
rendered at least one full frame — there is no authored-content or clock state
that could precede it.

On that capture the app writes the proof PNG to the run dir
(`readiness-proof.png`), prints the exact stdout line

```
GONE_READY 3 <frame>
```

(`3` is `PROTOCOL_VERSION`, `<frame>` the rendered frame count at the boundary),
records `TimedEvent::Ready`, and makes the frame-code chip visible. Every later
step (ticks, input edges, beat captures) is gated on the same readiness state by
`drive_allowed`, so the scenario clock starts at zero and the input adapter is
first stepped *after* the boundary — the tick-0 press cannot run before Ready.
No clock reset exists: the adapter is built at startup and never stepped before
Ready, so its clock is simply 0 until then.

The runner does not parse the line at slice A (it waits for the process to exit,
then verifies the report), but the line is the contract a delayed-readiness run
will assert against.

## Fixed-timestep clock and exactly-once edges

After readiness the app drives *one logical tick per rendered frame*
(`drive_ticks`): the adapter's `step()` returns the edges due on this tick and
the accumulated look motion. Each delivered edge becomes a tick-stamped
`TimedEvent::Input` whose `what` names the button *and the edge*:
`Key(Forward) press`, `Key(Forward) release`, `Mouse(Primary) press`,
`move-delta` for movement. Opposite edges of one button are therefore
distinguishable in events, checkpoints, and compare streams.

The adapter is a pure std state machine over the scenario's actions, so an edge
whose tick has been reached is delivered to exactly one fixed update, never
twice and never dropped. Slice A runs one tick per rendered frame, so the
adapter's multi-fixed-update buffering has one ready case; the type is built for
the broader guarantee and the beat/clock semantics below preserve exactly-once
beats regardless.

## Frame-code spec (exact)

The frame code is a `24x10` pixel chip (`DIGITS=6` digit cells of `CELL_W=4`
horizontal pixels, two bands of `CELL_H=5` vertical pixels). The top band
encodes the *logical tick*, the bottom band the *rendered frame*, six decimal
digits each, most significant first, zero-padded. Each digit is drawn as a 3x3
on/off lattice (`ROWS=3`, `COLS=3`) using the pattern in `frame::digit_pattern`.

The chip is *rendered content*, not CPU-composited pixels: at startup the app
creates a `24x10` `Image` texture, repaints it each tick with
`frame::encode_chip_rgba(tick, frame)`, and renders it as a `Sprite` with
MSAA off and `Anchor::TOP_LEFT`, pinned to the capture target's top-left pixel
at spawn (the target is a fixed 1920x1080 image, so a window resize cannot move
the code out of the corner). The sprite is invisible until the readiness
boundary, so nothing authored precedes it.

Exact palette:

- `ON_COLOR` = `(0x7f, 0xb8, 0xff)` — a lattice cell that is on.
- `OFF_COLOR` = `(0x05, 0x05, 0x06)` — background.
- A pixel counts as on when red, green, and blue all exceed `IS_ON_MIN = 60`.

`frame::chip_pixel(tick, frame, px, py)` is the exact mapping;
`frame::encode_chip_rgba`/`decode_chip_rgba` roundtrip in tests, and
`frame::decode_chip_from_rgb` crops the top-left block (`chip_origin = (0,0)`)
out of a decoded capture. The runner decodes each beat PNG through that shared
decoder and asserts the result equals the report's `(tick, frame)`.

## Beat capture binding (real GPU screenshots)

A beat's capture is one bevy `Screenshot::image` of the offscreen render target.
On the first update at or after the beat's tick where the capture lane is free,
`request_beat_captures` does one atomic step: it pins the beat's manifest entry
`{file, tick, frame, request_id}` to the frame that update is about to render,
spawns the screenshot entity carrying that binding, and marks the lane busy.
Pinning at spawn (not at tick arrival) is what makes the report trustworthy:
one capture is in flight at a time (bevy captures at most one screenshot per
render target per frame), so a beat whose tick passed while the lane was busy is
pinned to the frame it actually renders, and the PNG's decoded code always
equals the report's entry. Scenario beats spaced further apart than the readback
latency (one to two frames) pin at exactly their scenario tick.

When the capture lands, the observer matches it to the in-flight request by
request id, converts the GPU image (the target's `Bgra8UnormSrgb` bytes) to PNG
with `capture_to_png`, and writes `beats/<name>.png` in the run dir. The capture
event and checkpoint record the pinned numbers.

A readback conversion or file write failure is terminal: the app records a
`Failure` event naming the beat and the underlying error, writes the report, and
exits nonzero immediately. There is no retry loop and no settle wait. The runner
propagates a nonzero app exit, a missing file, and a frame-code mismatch as hard
failures.

The run completes only when every scenario beat's PNG is on disk (the captured
set, not the request cursor, drives completion) plus a two-frame settle after
the last capture; then the app writes `report.json`, prints `REPORT <path>`, and
exits 0 via `AppExit::Success`.

The scenario's `max_frames` is the deadline on that wait, not extra patience: it
counts rendered frames after the readiness boundary, and when the count reaches
it with beats still uncaptured, the app records every uncaptured beat as
missing (a `Failure` event naming each in the runner's
``missing beat `<name>` (expected tick <n>)`` shape), writes the report, prints
`REPORT <path>`, and exits nonzero. A beat scripted past the deadline is a
failed scenario, never a hang; there is no waiting past the deadline.

## Artwork layout

```
tmp/harness/<scenario>/<run-id>/
  readiness-proof.png   the first capture of the offscreen target (dark, no chip)
  beats/<name>.png      one PNG per beat: the rendered frame, chip at top-left
  report.json           the run report
  scenario.json         a copy of the scenario bytes the run used
```

`<run-id>` is `<unix-nanos>-s<seed>` so concurrent sessions cannot clobber each
other. `tmp/` is gitignored.

## report.json schema

Written by the app at finish (`harness/report.rs`), keyed to `PROTOCOL_VERSION`:

- `protocol_version` — must equal the runner's.
- `scenario`, `seed` — the scenario's name and RNG id.
- `events` — tick-stamped timeline: `Ready {frame}`, `Input {tick,frame,what}`,
  `Beat {name,tick,frame,request_id}`, `Complete {frame}`, and
  `Failure {frame, what}` (a capture or report error, terminal, no retry).
- `checkpoints` — strings like `ready at frame N`, `beat <name> captured`,
  `failed: beat `x` capture failed: <error>`.
- `frame_stats` — `{frames, mean_us, p95_us, median_us}` (defaults at slice A).
- `beats` — name -> `{file, tick, frame, request_id}`; the pinned rendered
  moment the PNG shows.
- `perf` — the perf-lane section, present only on perf-mode runs (`null` on
  the capture lane): `{warmup_frames, sample_frames, presentation, resolution,
  samples_ms, stats}` — raw wall-clock samples in ms plus the summary
  statistics over them (see the performance lane below).
- `identity` — `{app_hash, scenario_hash, config_hash}` (sha2-256 hex).

The runner re-verifies `identity.app_hash`/`identity.config_hash` match what it
computed before spawning the child.

## Frame stats and identity

`FrameStats` is emitted empty at slice A: the app does not measure present
timestamps into it. The fields exist so a real statistics lane can fill them
(deferred). The perf lane reports its own `perf` section instead of
`frame_stats`; the seeded struct stays untouched on both lanes.

## Two-stage verdict and exit code

A run has two verdict stages. Stage 1 (this slice) is the machine layer: the
report parsed, the protocol version matched, identity matched, every scenario
beat in the manifest, every beat PNG present and its frame-code decode equal to
the report. Stage 2 is the vision layer (deferred): a vision-capable subagent
looks at the beats. Machine decoding only here; visual judgments use GPT or
Opus, never Zai.

- Exit 0 = machine checks passed, visual verification pending.
- Nonzero = a machine check failed (nonzero app exit, mismatch, timeout, missing
  file, capture I/O error).

`cargo xtask harness smoke` prints `MACHINE PASS: ... machine checks passed,
visual verification pending` and `ARTIFACTS: <dir>` on success.

## Input-adapter boundary

Scripts never touch gameplay internals. The adapter is a pure std state machine
(`harness/input.rs`) that feeds scripted inputs *through the same input layer*
the game reads; gameplay has no "test mode" that skips its own code. Growing the
button enum is a harness change, not an app change. This satisfies "the runner
feeds synthetic input events the same way real devices do". The boundary is
machine-enforced, not just documented: `cargo xtask check architecture` fails
when `gone_harness` declares a direct `gone_sim` dependency or when any file in
`crates/gone_app/src/harness/` references `gone_sim` in source, with the pinning
tests in `crates/xtask/src/architecture.rs` and `crates/xtask/src/protocol_surface.rs`.

## Compare mode

`gone_harness compare <scenario>` runs the scenario twice from the same seed into
two run dirs, then diffs the two reports' event streams tick by tick. Equal
streams print `COMPARE PASS: two runs identical (N events)` and exit 0. The
first differing event prints `COMPARE DIVERGENCE at event i` and exits 1. Input
edges compare distinctly because `what` carries the press/release word.

The report's event list is written in a total order (tick, then frame, ready
first, terminal events last, stable append order as the tie-break) precisely
because capture completion is asynchronous: a beat's readback can land several
ticks after the tick the capture shows, so wall-clock append order is not
reproducible across runs.

Beat capture events carry the pinned tick/frame; for scenarios whose beats are
spaced further apart than the capture readback latency (one to two rendered
frames), both runs pin identical values and the streams match.

## Performance lane

The perf lane measures wall-clock frame times of the calibration scene and
judges them against a versioned, checked-in policy. It is the third runner mode
beside `smoke` and `compare`:

    gone_harness perf [scenario.json]
    cargo xtask harness perf [scenario.json]

With no argument the runner derives the calibration scenario from the policy:
the bootstrap scene (dark clear plus the frame-code chip sprite, 1920x1080,
scale factor 1.0) with no scripted actions and no beats. A scenario argument
must be a perf-mode scenario (`"mode": "perf"`); a capture scenario in the perf
lane is a caller error.

### Policy (location, schema, versioning)

The policy lives at `crates/gone_harness/perf-policy.json` and ships with the
repo. Its schema (`PerfPolicy`) lives with the rest of the protocol in
`crates/gone_app/src/harness/perf.rs`: the version string, the warmup frame
count, the sample window frame count, the presentation pacing (`Uncapped` —
wall-clock frame times must not be quantized by vsync; the app configures the
window with `PresentMode::AutoNoVsync` for an uncapped run), the camera route
description (static on the calibration scene; recorded, never simulated), the
concurrent effects (none in the calibration scene), the physical resolution,
the statistics the lane reports (count, mean, min, max, p50, p95, p99 of frame
time in ms), and the thresholds the runner enforces on those statistics (mean
and p95 ceilings).

The `calibration-v1` thresholds are calibration-scene placeholders: generous
but real (a 25 ms mean / 50 ms p95 ceiling catches gross stalls and a stalled
or throttled clock) and deliberately machine-tolerant. They are superseded by
the populated-room 60 FPS policy that arrives with issues #2/#10; that change
is a new `policy_version`, never an edit in place.

The policy is frozen before measurement: the runner parses and hashes the exact
file bytes before spawning the app, and the policy identity (version string +
sha2-256) travels into the run artifacts, so a verdict always names the policy
it was decided by.

### What the app does (capture-free by design)

The perf run is capture-free by design. The app waits for readiness exactly as
the capture lane does (loading presentation, readiness proof readback,
`GONE_READY`), then runs the policy's warmup frames unrecorded, then records
`sample_frames` per-frame wall-clock deltas from Bevy's real `Time` delta — no
beats, no screenshots, no decode after the readiness proof. The raw samples
plus the summary statistics go into the report's `perf` section, the app prints
`REPORT <path>`, and exits 0.

Frame times are wall-clock and inherently non-deterministic. The perf lane is
excluded from the harness's compare/determinism claims: raw samples differ run
to run by design, and the statistics are judged against policy thresholds,
never against a second run. The event timeline the perf report carries is only
the ready/complete skeleton — nothing about it is a determinism sample either.

### Verdict and artifacts

The runner reads the report, verifies the run's shape matches the policy
(window counts, presentation, resolution — identity checks, not thresholds),
and evaluates the recorded statistics against the policy thresholds. It prints
one verdict line — `PERF PASS` or `PERF FAIL`, the policy identity, and on a
fail each violated statistic with its observed value and ceiling — plus a
distribution summary over the policy's reported statistics, writes
`perf-verdict.json` (verdict, policy identity, violations, stats) beside
`report.json`, and exits 0 on pass, 1 on fail or on any runner error. A perf
run dir holds `scenario.json`, `readiness-proof.png`, `report.json`, and
`perf-verdict.json`.

`ci`'s harness step stays on the smoke lane: the perf verdict measures
wall-clock on real GPU present, so it is a local gate, not a deterministic CI
step.

## Deferred (stage B)

Not in slice A, per the plan:

- Vision checklist plus vision verification (the two-stage model's second
  verdict; machine decode only in this slice).
- Negative verification cases (a scenario that must fail naming why).
- Lifecycle scenarios (delayed readiness, the no-content-before-ready assertion
  on the GONE_READY line).
- The milestone performance gate: the populated room at 4K, 60 FPS (issues
  #2/#10). The calibration lane's policy and reporting are its substrate; the
  calibration thresholds are placeholders for that milestone's policy.
- Windows kill-tree for the child process.

## Known limits (honest notes)

1. A bevy-internal readback failure that never produces `ScreenshotCaptured`
   (device loss, driver hang) leaves the lane waiting; the app cannot observe
   it, so the run ends in the runner's timeout naming the scenario. I/O failures
   inside the app's own convert/save path are the immediate-failure path above.
2. Beats closer together than the readback latency serialize (one capture in
   flight); a beat whose tick passed while the lane was busy is captured at the
   first later frame and its manifest entry pins that later frame. The PNG and
   the report always agree; only the beat's scenario tick and its captured frame
   may differ in that case.
3. `FrameStats` is empty; the perf lane reports the `perf` section instead (the
   seeded struct is untouched on both lanes).
4. The `pacing` scenario field is consumed at window creation (Uncapped sets
   `PresentMode::AutoNoVsync`). Compare scenarios leave it unset and run the
   default vsync presentation; `max_frames` is consumed as the clean-close
   deadline described under beat capture binding (inert on the perf lane,
   which has no beats to miss).

## Cross-target verification

`cargo check --locked --workspace --all-targets` cross checks from this macOS
host (aarch64-apple-darwin; log: `tmp/issue15-fix/cross-target-after.log`):

- Host target: the full gate set passes (build, `fmt --check`, clippy
  `-D warnings`, 112 workspace tests, harness smoke exit 0).
- `--target x86_64-unknown-linux-gnu`: `gone_app`'s bevy feature list includes
  `x11` and `wayland`, bevy's own linux platform defaults. `bevy_winit` builds
  `winit` with `default-features = false`, so without them winit aborts with
  its "The platform you're compiling for is not supported" compile_error on
  linux (they are no-ops on macOS). With them, compilation reaches
  `wayland-sys v0.31.11`, whose build script panics: "pkg-config has not been
  configured to support cross-compilation. Install a sysroot for the target
  platform and configure it via PKG_CONFIG_SYSROOT_DIR and PKG_CONFIG_PATH, or
  install a cross-compiling wrapper for pkg-config and set it via the
  PKG_CONFIG environment variable." A linux-gnu cross check therefore requires
  a linux-gnu sysroot whose wayland client library is reachable through
  pkg-config.
- `--target x86_64-pc-windows-msvc`: fails in `blake3 v1.8.7`'s custom build
  script (reached through the `bevy_asset` dependency chain): cc-rs reports
  "failed to find tool \"ml64.exe\": No such file or directory" — the MSVC x64
  assembler is absent on this host. A windows-msvc cross check requires an
  MSVC cross toolchain that provides `ml64.exe` and the Windows SDK headers
  and libraries (e.g. cargo-xwin), which is not installed here.
