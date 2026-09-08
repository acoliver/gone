# gone harness protocol

This is the contract between `gone_app` (the game) and `gone_harness` (the
runner) at slice A: how a scenario is declared, how the runner drives the app, how
the two hand off readiness, what lands on disk, and what makes a run pass or fail.
Its home is `docs/dev/harness.md`. The one source of truth for the on-wire JSON
and the pixel encoding is `crates/gone_app/src/harness/`; `gone_harness`
re-exports that surface and never defines a type of its own. Several design-doc
details (a real window, a GPU readback, render-to-texture) are not slice A, and
this document describes what the code ships, flagging each difference.

The protocol version both sides embed and compare is `gone_app::harness::PROTOCOL_VERSION`
(currently `1`). A report whose version does not equal the runner's is rejected.

## Two crates, one boundary

- `gone_app` (Bevy 0.19) owns the protocol: `crates/gone_app/src/harness/{scenario,input,beat,frame,report,mod}.rs`.
  It reads a scenario, runs the fixed timeline, writes the report, exits cleanly.
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

Both hashes are real SHA-256 (the runner depends on `sha2 0.10`; the doc
previously said `gone_app` computes hashes itself and the runner never needed them.
The code ships it the other way: the runner computes them and passes them in as
environment.)

The app is child-owned: the runner reaps it (`try_wait` poll on a 10ms
cadence, `DEFAULT_TIMEOUT` 60 seconds), and on drop (including error paths) it
SIGKILLs and `wait`s so no `gone_app` is orphaned. On macOS killing the
child pid is sufficient; Windows kill-tree is deferred to stage B.

## Scenario format

A scenario is a JSON file. Top-level fields (see
`crates/gone_app/src/harness/scenario.rs`):

- `name` — run-directory label and the app's `report.scenario`.
- `seed` — the scenario RNG id (not yet consumed at slice A).
- `ticks_per_second` — the fixed logical clock rate edited (default 60).
- `actions` — a list of `{"tick": N, "action": ...}` scripted inputs.
- `beats` — a list of `{"name": "...", "tick": N}` capture points.
- `pacing` — `FixedVsync` or vsync, used only by compare.
- `max_frames` — longest the timeline may run (default 720).

Actions the adapter understands (`harness/input.rs`): `Look {yaw_deg,pitch_deg}`,
`MoveDelta {forward,strafe}`, `Press`/`Release {button}`, `Wait {ticks}`,
`WaitUntilTick {tick}`. Buttons are `Key::{Forward,Left,Back,Right,Activate,Secondary,Other}`
or `MouseButton::{Primary,Secondary,Middle,None}`.

## Readiness handshake

The app starts in the loading presentation: a dark clear, no authored content. The
bootstrap `readiness_boundary` system prints the exact stdout line

```
GONE_READY 1 <frame>
```

once the render sub-app has run once. That is the tick-zero boundary: the adapter
clock is reset to zero, the tick-zero event is recorded, and no clear room appears
before that line. The runner does not need to parse the line at slice A (it waits
for the process to exit, then verifies the report), but the line is the contract a
delayed-readiness run will assert against.

## Fixed-timestep clock and exactly-once edges

After readiness the app drives *one logical tick per rendered frame* (`drive_ticks`):
the adapter's `step()` returns the edges due on this tick and the accumulated look
motion. The adapter is a pure state machine over the scenario's actions, so an edge
whose tick has been reached is delivered to exactly one fixed update, never twice and
never dropped, no matter how many fixed updates run in a rendered frame or none do.
Each delivered edge becomes a tick-stamped `TimedEvent::Input`.

Note the design doc promises *button edges buffered so every edge is consumed exactly
once regardless of how many fixed updates run per rendered frame*. Slice A literally
runs one tick per frame, so the field only has one ready case; the adapter type is
built for the multiple-updates case, and the beat/clock semantics below preserve
exactly-once beats regardless.

## Frame-code spec (exact)

The frame code is a `24x10` pixel block (`DIGITS=6` digit cells of
`CELL_W=4` horizontal pixels, two bands of `CELL_H=5` vertical pixels) painted in
the top-left corner of the lane image. The top band encodes the *logical tick*, the
bottom band the *rendered frame*, six decimal digits each, most significant first,
zero-padded to 6. Each digit is drawn as a 3x3 on/off lattice (`ROWS=3`,
`COLS=3`) using the seven-segment-style pattern in `frame::digit_pattern`.

Exact palette:

- `ON_COLOR` = `(0x7f, 0xb8, 0xff)` — a lattice cell that is on.
- `OFF_COLOR` = `(0x05, 0x05, 0x06)` — background.
- A pixel counts as on when red, green, and blue all exceed `IS_ON_MIN = 60`.

`frame::chip_pixel(tick, frame, px, py)` is the exact mapping, and
`frame::encode_chip_rgba`/`decode_chip_rgba` roundtrip in tests. The
runner decodes a captured PNG by sampling the top-left block (`chip_origin = (0,0)`),
reading each cell's lattice, and matching to a digit, giving the `(tick, frame)` the
capture claims. The `24x10` lane makes the PNG the exact code with no crop needed.

## Beat capture binding

A beat is *requested* the frame its tick is reached (`request_available_beats`
records the manifest entry and the tick/frame) and *captured* on a later frame by
`capture_beats`, which advances the clock to exactly the requested (tick, frame),
repaints the lane to that moment, and writes `beats/<name>.png`. The runner then
decodes each PNG and asserts it equals the report's `(tick, frame)`, so a beat
that happened entirely between rendered frames cannot be fabricated and a beat that never
happens fails naming the missing beat.

The design doc said "one request per target per rendered frame; completion means the
file was written, with save failures propagated as failures". Slice A code treats a
save failure as a logged error, not a run failure (a `report.json` without a beat
PNG still fails the runner's missing-file check). The runner does propagate missing files
and a frame-code mismatch as hard failures.

## Artwork layout

```
tmp/harness/<scenario>/<run-id>/
  beats/<name>.png      one PNG per beat, code pixels at (tick, frame)
  report.json           the run report
  scenario.json        a copy of the scenario bytes the run used
```

`<run-id>` is `<unix-nanos>-s<seed>` so concurrent sessions cannot clobber each
other. `tmp/` is gitignored.

## report.json schema

Written by the app at finish (`harness/report.rs`), keyed to `PROTOCOL_VERSION`:

- `protocol_version` — must equal the runner's.
- `scenario`, `seed` — the scenario's name and RNG id.
- `events` — tick-stamped timeline: `Ready {frame}`, `Input {tick,frame,what}`,
  `Beat {name,tick,frame,request_id}`, `Complete {frame}`.
- `checkpoints` — strings like `ready at frame N` and `beat <name> captured`.
- `frame_stats` — `{frames, mean_us, p95_us, median_us}` (defaults at slice A).
- `beats` — name -> `{file, tick, frame, request_id}`.
- `identity` — `{app_hash, scenario_hash, config_hash}` (sha2-256 hex of the app
  binary bytes, the scenario file bytes, and the config string the runner passed). No
  placeholder hashes anywhere.

The runner re-verifies `identity.app_hash`/`identity.config_hash` match what it
computed before spawning the child.

## Frame stats and identity

`FrameStats` is emitted empty at slice A: the app does not measure present
timestamps yet. The fields exist so a real statistics lane can fill them (deferred).

## Two-stage verdict and exit code

A run has two verdict stages. Stage 1 (this slice) is the machine layer: the
report parsed, the protocol version matched, identity matched, every scenario beat in the
manifest, every beat PNG present and its frame-code decode equal to the report. Stage 2
is the vision layer (deferred): a vision-capable subagent looks at the beats.

- Exit 0 = machine checks passed, visual verification pending.
- Nonzero = a machine check failed (nonzero app exit, mismatch, timeout, missing file).

`cargo xtask harness smoke` prints `MACHINE PASS: ... machine checks passed, visual
verification pending` and `ARTIFACTS: <dir>` on success.

## Input-adapter boundary

Scripts never touch gameplay internals. The adapter is a pure std state machine
(`harness/input.rs`) that feeds scripted inputs *through the same input layer* the
game reads; gameplay has no "test mode" that skips its own code. Growing the button
enum is a harness change, not an app change. This satisfies "the runner feeds
synthetic input events the same way real devices do".

## Compare mode

`gone_harness compare <scenario>` runs the scenario twice from the same seed into two run
dirs, then diffs the two reports' event streams tick by tick. Equal streams print
`COMPARE PASS: two runs identical (N events)` and exit 0. The first differing
event prints `COMPARE DIVERGENCE at event i: A vs B` and exits 1, naming the
first divergence.

## Deferred (stage B)

Not in slice A, per the plan:

- Vision checklist plus vision verification (the two-stage model's second verdict).
- Negative verification cases (a scenario that must fail naming why).
- Lifecycle scenarios (delayed readiness, a run that must not leave an unchanged app
  window open, the no-content-before-readyhouse assertion on the GONE_READY line).
- Performance lane (frame-time sampling in a populated room; the fixed frame stats and
  the "runtime_frames wall-clock" field are its seeds).
- Windows kill-tree for the child process.

## Where code and design doc differ

1. The design doc says hashes are content hashes "the runner computes". Earlier
   `gone_app` was described as "never needs sha2" and there is no sha2 in the app;
   the implementation follows the runner-computes rule. Correct in code.
2. The design doc promises "pixel-identical GPU output is not promised" and the
   capture is "the rendered image read back from the GPU". Slice A ships no GPU
   readback: the lane is an off-window CPU image where slice A painted only the frame
   code. That cage becomes a real render target when PBR ships.
3. The design doc says "the window shows the loading/closed presentation until the
   renderer is ready; the first ready fully-closed frame is captured separately, and a
   delayed-readiness run proves the timeline starts exactly once". Slice A only prints
   `GONE_READY` and starts the clock; the separate first-frame capture and the
   delayed-readiness scenario are stage B.
4. The design doc's button-edge exactly-once guarantee is broader (edges buffered
   across rendered frames) than slice A's one-tick-per-frame drive. The adapter
   type implements the broader guarantee; the drive loop at slice A is the simple case.
5. The design doc says "save failures propagated as failures". The app logs a save
   failure but still exits success; the runner's missing-file check catches the
   downstream result.
