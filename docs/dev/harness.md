# gone harness protocol

This is the contract between `gone_app` (the game) and `gone_harness` (the
runner) at slice A: how a scenario is declared, how the runner drives the app,
how the two hand off readiness, what lands on disk, and what makes a run pass or
fail. Its home is `docs/dev/harness.md`. The one source of truth for the on-wire
JSON and the pixel encoding is `crates/gone_app/src/harness/`; `gone_harness`
re-exports that surface and never defines a type of its own.

The protocol version both sides embed and compare is
`gone_app::harness::PROTOCOL_VERSION` (currently `2`). A report whose version
does not equal the runner's is rejected. Version 2 is the real-capture protocol:
beats are readbacks of an offscreen render target the harness camera draws into,
the frame-code chip is a sprite rendered into the scene, input events carry
their press/release edge, and capture failures are recorded as `Failure` events.

## Two crates, one boundary

- `gone_app` (Bevy 0.19) owns the protocol: `crates/gone_app/src/harness/{scenario,input,beat,frame,report,mod}.rs`.
  It reads a scenario, opens a real window, runs the fixed timeline, captures
  screenshots, writes the report, and exits by itself. The app-side lane lives
  in `crates/gone_app/src/bootstrap/`: `mod.rs` is the plugin plus the ECS
  systems and capture I/O, `state.rs` is the run-state ledger (counters, beat
  ledgers, readiness gate, failure recording), and `tests.rs` pins the
  accounting and readiness regressions.
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
only; captures never come from its swapchain (see the readiness section for
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

The harness never captures from the window swapchain: on this platform config
(M4 Max / Bevy 0.19.1 / Metal), `Screenshot::primary_window()` returns a fully
black image regardless of content, timing, or clear color — proven by a minimal
probe that also proved the offscreen path renders and reads back correctly. The
winit window stays open so the app runs as a real windowed app, but the
offscreen image is the capture source of truth.

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
GONE_READY 2 <frame>
```

(`2` is `PROTOCOL_VERSION`, `<frame>` the rendered frame count at the boundary),
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
- `identity` — `{app_hash, scenario_hash, config_hash}` (sha2-256 hex).

The runner re-verifies `identity.app_hash`/`identity.config_hash` match what it
computed before spawning the child.

## Frame stats and identity

`FrameStats` is emitted empty at slice A: the app does not measure present
timestamps yet. The fields exist so a real statistics lane can fill them
(deferred).

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
feeds synthetic input events the same way real devices do".

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

## Deferred (stage B)

Not in slice A, per the plan:

- Vision checklist plus vision verification (the two-stage model's second
  verdict; machine decode only in this slice).
- Negative verification cases (a scenario that must fail naming why).
- Lifecycle scenarios (delayed readiness, the no-content-before-ready assertion
  on the GONE_READY line).
- Performance lane (frame-time sampling in a populated room; the empty
  `FrameStats` is its seed).
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
3. `FrameStats` is empty; the clock is tick-per-frame with no duration
   measurement yet.
4. The `pacing` scenario field is parsed but not yet consumed by the app
   (compare uses default vsync pacing). `max_frames` is consumed as the
   clean-close deadline described under beat capture binding.

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
