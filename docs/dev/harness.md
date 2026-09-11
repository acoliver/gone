# gone harness protocol

This is the contract between `gone_app` (the game) and `gone_harness` (the
runner) at slice A: how a scenario is declared, how the runner drives the app,
how the two hand off readiness, what lands on disk, and what makes a run pass or
fail. Its home is `docs/dev/harness.md`. The one source of truth for the on-wire
JSON and the pixel encoding is `crates/gone_app/src/harness/`; `gone_harness`
re-exports that surface and never defines a type of its own.

The protocol version both sides embed and compare is
`gone_app::harness::PROTOCOL_VERSION` (currently `4`). A report whose version
does not equal the runner's is rejected. Version 2 is the real-capture protocol:
beats are readbacks of an offscreen render target the harness camera draws into,
the frame-code chip is a sprite rendered into the scene, input events carry
their press/release edge, and capture failures are recorded as `Failure` events.
Version 3 adds the performance lane: scenarios gain a `mode` (capture or perf)
with warmup/sample window counts, reports gain the optional `perf` section, and
the scenario `pacing` field is consumed at window creation (canary runs; a
headless run has no window, so pacing is inert there). Version 4 adds the
calibration-evidence lane: scenarios gain the `calibration` mode plus a required
`calibration` section (one luminance step, an equal-area bright-patch placement
plan, a metering-mask selection, and the auto-exposure arm), and reports gain
the `Calibration` event, recorded once before any sample is pinned with the
run's setup evidence (mask selection plus the sha256 of the loaded mask asset's
pixel bytes, the auto-exposure settings in force, the authored exposure, the
patch plan, the light levels, and the pinned sample ticks). The capture and perf
surfaces are unchanged.

## Two crates, one boundary

- `gone_app` (Bevy 0.19) owns the protocol: `crates/gone_app/src/harness/{scenario,input,beat,frame,report,perf,calibration,mod}.rs`.
  It reads a scenario, runs the fixed timeline (headless by default; a real
  unfocused window in the render canary), captures screenshots, writes the
  report, and exits by itself. The app-side lane lives
  in `crates/gone_app/src/bootstrap/`: `mod.rs` is the plugin plus the ECS
  systems, `captures.rs` is the capture I/O half of the screenshot observer,
  `calibration.rs` owns the calibration lane's scene, evidence recording, and
  camera/post-chain reconciliation, `state.rs` is the run-state ledger
  (counters, beat ledgers, readiness gate, failure recording, perf sampler, run
  mode), and `tests.rs`
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
- `GONE_RENDER_CHECK=1` (canary runs only, set by the runner's
  `--render-check` flag: the app opens the unfocused window and saves the one
  onscreen capture at the first beat).
- `BEVY_ASSET_ROOT=<abs path>` (the `gone_app` crate directory whose `assets/`
  subtree holds the game's assets; see the asset root paragraph below).

All three hashes are real SHA-256 computed runner-side from the bytes it actually
spawned and passed; the app echoes them back verbatim.

The runner also passes `BEVY_ASSET_ROOT`, the absolute path of the `gone_app`
crate directory whose `assets/` subtree holds the game's assets, and it fails
the launch by name when that directory is missing. Bevy resolves its asset root
from this variable first and falls back to the inherited `CARGO_MANIFEST_DIR`,
so a child launched without it inherits the runner crate's manifest context and
looks for assets under `crates/gone_harness/assets`, where nothing lives; the
gameplay lane's readiness barrier then correctly reports the required asset as
missing. Direct binary launches (running `target/debug/gone_app` outside `cargo
run`) must set `BEVY_ASSET_ROOT` themselves: a stale `CARGO_MANIFEST_DIR`
inherited from the parent shell points the asset server at the wrong tree just
the same. The app asserts the variable and the required asset under it in both
harness modes before anything loads, and the normal game keeps the readiness
ledger as its enforcement. A regression test pins that the runner's computed
root contains `post/metering_mask.png`.

By default the app runs headless: `WinitPlugin` is disabled, no window is
created, and the schedule runner spins updates. With `GONE_RENDER_CHECK=1` the
app runs the canary lane: `WinitPlugin` owns the OS event loop and opens the
1920x1080 window (scale factor forced to 1.0 so logical pixels equal physical
pixels, `focused: false` so the run never takes the foreground). See the
capture lane section for the two-mode contract. There is no manual update loop
anywhere in the harness path. The runner owns the child lifecycle (the same in
both modes: `try_wait` poll on a 10ms cadence, `DEFAULT_TIMEOUT`
60 seconds), and on drop (including error paths) it SIGKILLs and `wait`s so no
`gone_app` is orphaned. On macOS killing the child pid is sufficient; Windows
kill-tree is deferred to stage B.

## Capture lane (two modes: headless offscreen, plus the render canary)

Harness runs have a run mode (`RunMode` in the app's bootstrap state, derived
from the environment; unknown values panic at launch naming the variable).

The default harness run is headless: no window exists at all (`WinitPlugin`
disabled, `ExitCondition::DontExit` so a windowless app does not exit
immediately, `ScheduleRunnerPlugin` spinning updates). The harness camera
renders into a dedicated offscreen `Image` render target
(`RenderTarget::Image` on the `Camera2d`), created at startup as a 1920x1080
`Bgra8UnormSrgb` texture with `RENDER_ATTACHMENT | TEXTURE_BINDING` usage. Every
capture of the run is a bevy `Screenshot::image(target_handle)`: the render
graph blits the camera's frame into a readback buffer and hands the mapped
`Image` to the app's `ScreenshotCaptured` observer. The offscreen captures are
the single source of truth for readiness and beat decode, and the majority of
runs need nothing else.

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

Headless runs keep the offscreen Image capture lane for two real reasons:
captures are exactly 1920x1080 regardless of window scale or DPI overrides,
and capture timing is decoupled from the swapchain and present. A headless run
has no window and no surface, so nothing is presented at all; the canary below
is the one run that presents to a window and reads one capture back from it.

Sprite rendering has its own feature gate in Bevy 0.19: the sprite render pass
lives in `bevy_sprite_render`, separate from the `bevy_sprite` API crate.
Without `bevy_sprite_render` in the app's bevy features, sprites (including the
frame-code chip) never draw anywhere; the feature is enabled.

### The render canary (GONE_RENDER_CHECK=1 with GONE_HARNESS=1)

The render canary is the one windowed test that answers "does the game
actually render". The app opens a real 1920x1080 window at scale factor 1.0
with `focused: false`, so the run never steals the foreground, and a window
camera (order 0) presents the actual scene alongside the offscreen capture
camera (order 1). At the first beat's request the run captures the primary
window exactly once (`Screenshot::primary_window()`), through the same sync
point as the beat capture, and saves it as `beats/<first-beat>.onscreen.png`
in the run dir. The offscreen captures remain the readiness and beat source
of truth; the window exists to prove the presented path.

The runner selects the canary with `--render-check` (`cargo xtask harness
render-check`; the `ci` step immediately after smoke) and machine-verifies the
artifact after the run, failing fast with named errors: exactly one
`*.onscreen.png` under `beats/` (none names the expected file, more than one
lists them), it decodes as PNG at exactly 1920x1080, it is not entirely black
(every pixel exactly (0,0,0) fails), and its frame-code chip lattice decodes
to the report's frame for that beat (the same decoder as the offscreen beats;
the window renders the same world, chip included). Canary run dirs carry an
`rc` run-id prefix (`rc<unix-nanos>-s<seed>`) under the usual `tmp/harness`
layout.

The canary's scenario clock waits for the window's first capturable frame
before it starts. The window is unfocused by design, and macOS does not hand a
freshly created unfocused window its swapchain drawable until the compositor
has composited it once. On such a frame bevy skips the window screenshot's
composite into the swapchain and its readback copy but still fires the capture
event, so the app receives the zero-initialized transfer buffer and would
write an entirely black PNG; the offscreen beats of the same run are immune
because they read back their own render target and never touch the swapchain.
The app therefore holds the drive until a present probe proves the window
presents: while the gate is unresolved it requests one primary-window probe
capture per rendered frame, a capture with a rendered byte proves presents and
releases the clock, and a zeroed capture counts one declined frame against a
300-frame present budget that fails the run by name when exhausted. Probes are
frame keyed, every declined frame is counted and logged, and the budget is
hard, so the barrier is never a silent retry loop; the same-sync-point pairing
of the onscreen capture with the first beat's PNG is unchanged.

Visual inspection of the onscreen PNG by the visual model agent is the
follow-up judgment step, outside CI: the runner's machine checks prove the
frame rendered, and the visual pass judges what it looks like. The canary is
the practical use of the corrected `primary_window()` knowledge above.

## The gameplay lanes (gameplay-smoke, gameplay-full)

    gone_harness gameplay-smoke
    gone_harness gameplay-full
    cargo xtask harness gameplay-smoke
    cargo xtask harness gameplay-full

Both lanes boot the real game in the child (the scenario's
`content: "gameplay"` field): the post chain, the stasis-room scene, and the
player rig build exactly as the normal game builds them, behind the extended
readiness barrier described above (required assets loaded, rig camera bound
to the capture target). The frame-code chip renders as a corner overlay on
the gameplay camera's view, so beat captures keep the same decode contract
and every capture still decodes to the report's tick and frame.

`gameplay-smoke` scripts a 30 degree look between two pinned beats and proves
two things machine-side: the room observation matches the registry's pod
count, and the rig's beat-pinned yaw samples show exactly the scripted look
delta (compared modulo a full turn, within a stated tolerance). A run whose
player systems never integrated scripted look, or whose scene failed to
build, fails here.

`gameplay-full` scripts the whole opening beat and verifies it numerically.
The scenario presses activate, so the authored get-up carries the capsule out
of the player pod along the authored exit path; then it turns 90 degrees and
walks forward toward the hatch wall with the steadying walk. The runner
derives every expectation from the same frozen truth the app builds from
(the exit path and standing eye height from `gone_app::placement_truth`, the
controller constants, the room envelope, and the hatch placement through the
app's `gone_sim` re-export), never from literals:

- the report's wake-phase observations read exactly `waking`, `awake_in_pod`,
  `exiting_pod`, `standing`, in order;
- the `standing` beat's position sample equals the standing eye point the
  authored exit path's waypoint projects to, within the sim's own pose
  arrival tolerance;
- the `door` beat's position sits inside the room envelope at the standing
  eye height, its displacement from the standing beat matches the frozen
  steadying ramp consumed exactly as the sim consumes it (the ramp clock
  advances on every walked tick, movement or not), and its distance to the
  frozen hatch placement is bounded by that same walk model, each within a
  stated tolerance.

The lane's negative proofs are unit-tested on the verifier itself: a report
whose standing beat drifts off the waypoint, whose phase sequence drops or
reorders a phase, or whose door beat shows a player that never walked (or
left the room, or lost its eye sample) fails with a named error. What the
lane proves: the phase machine, the get-up controller, the steadying walk,
the collider set, and the placement data all agree with each other and with
the report, end to end, in a real build of the game.

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
rendered at least one full frame. No authored-content or clock state could
precede it, and the calibration loading scene has none to precede.

Gameplay content extends the proof with the game readiness barrier, and the
proof request waits on two more legs before it asks for the readback. Every
required game asset must have loaded (the `readiness` ledger, polled first in
the gameplay update chain), and the player rig's camera must be bound to the
offscreen target, so the capture that opens the scenario clock is a fully
provisioned game frame with its pipelines compiled, never the chip overlay
alone. While a required asset is still loading, nothing runs: no tick, no
input, no phase advance, and the loading presentation stays up. The hold is
bounded by the same known limits as any capture wait; there is no separate
polling budget. A required asset whose load fails is a terminal failure that
names the asset and the underlying error and exits nonzero, on the lane and in
the normal game alike; a run never renders an engine placeholder in a required
asset's place.

The normal game runs the same ledger every update. A pending load keeps the
scene in its authored `Waking` opening, and the wake progression (the issue #8
wake pass, and today the gameplay lane's wake-complete override) may not drive
the phase machine until the ledger reports ready. The gameplay lane moves its
wake-complete signal behind the boundary, so the machine lands in
`AwakeInPod` on the same update the clock opens and the once-only override
never repeats.

On that capture the app writes the proof PNG to the run dir
(`readiness-proof.png`), prints the exact stdout line

```
GONE_READY 4 <frame>
```

(`4` is `PROTOCOL_VERSION`, `<frame>` the rendered frame count at the boundary),
records `TimedEvent::Ready`, and makes the frame-code chip visible. Every later
step (ticks, input edges, beat captures) is gated on the same readiness state by
`drive_allowed`, so the scenario clock starts at zero and the input adapter is
first stepped *after* the boundary — the tick-0 press cannot run before Ready.
No clock reset exists: the adapter is built at startup and never stepped before
Ready, so its clock is simply 0 until then.

The runner does not parse the line at slice A (it waits for the process to exit,
then verifies the report), but the line is the contract a delayed-readiness run
will assert against.

## The scenario clock (fixed timestep)

The scenario clock is the fixed timeline the app simulates against. One clock
step is a tick. The scenario's `ticks_per_second` is the clock's rate: one
tick is worth `1 / ticks_per_second` seconds of simulation time, and gameplay
systems consume simulation time from the clock, never wall time. (The wake
phase machine consumes no time today; the frozen controller constants are
specified against this fixed tick.) The rate is validated at parse time: a
`ticks_per_second` below 1 is a scenario error on both sides, because the app
and the runner share one parser, so a rateless scenario cannot start a run.

The advance rule is frame anchored, and both lanes use it. After the readiness
boundary the drive advances exactly one tick per scenario frame, and the tick
counter equals the scenario frame counter. No wall-clock accumulator decides
tick boundaries: a wall-clock rule would land a given tick on a
jitter-dependent frame, and two identical runs would then stamp different
frames onto the same events. The frame anchored rule is what makes the compare
lane and the latency invariant below hold.

Wall pacing differs by lane, and the difference is presentational only:

- Headless capture lane: the schedule runner waits one tick's duration
  between updates, so the simulation runs at the scenario's declared rate
  against the wall clock, modulo render cost and sleep granularity.
- Perf lane: the runner wait is zero. The lane samples real frame times, so
  it must not be paced. It has no beats, so no capture can hold its clock,
  and its samples stay pure wall-clock.
- Canary lane: winit owns the loop and the display paces presents. The clock
  rule is the same one tick per scenario frame; the wall rate is the display's
  present rate, so a scenario whose rate exceeds it runs slower in wall time
  than scripted. Simulation time per tick is unaffected.

`drive_ticks` steps the input adapter once per tick; the adapter's `step()`
returns the edges due on this tick and the accumulated look motion. Each
delivered edge becomes a tick-stamped `TimedEvent::Input` whose `what` names
the button *and the edge*: `Key(Forward) press`, `Key(Forward) release`,
`Mouse(Primary) press`, `move-delta` for movement. Opposite edges of one
button are therefore distinguishable in events, checkpoints, and compare
streams.

The adapter is a pure std state machine over the scenario's actions, so an
edge whose tick has been reached is delivered to exactly one fixed update,
never twice and never dropped. The harness runs one tick per scenario frame,
so the adapter's multi-fixed-update buffering has one ready case; the type is
built for the broader guarantee and the capture binding below preserves
exactly-once beats regardless.

### Capture binding and the latency invariant

While a beat readback is in flight, the scenario clock holds: no tick, no
frame, no adapter step, and the renderer keeps presenting the held frame, so
the in-flight capture reads back exactly the pinned (tick, frame) pair. The
clock can never pass a beat's tick while the lane is busy, so every beat pins
exactly its scripted tick on every run, regardless of readback latency, and
identical scenarios pin identical (tick, frame) pairs. The hold is bounded by
the existing failure paths: a readback that errors fails the run immediately,
and a readback that never lands ends in the runner's process timeout (the
known limit below, unchanged).

The invariant has a proof knob: the app's capture observer honors
`GONE_TEST_CAPTURE_DELAY_MS` (milliseconds). The runner passes its own
environment through to the app, so a delayed run is a normal runner invocation
with the variable set; unset or empty means no delay, and a value that does
not parse fails the run naming the variable. The proof: run one scenario
twice, once with the delay and once without, and the two `report.json` files
must be byte identical, beat (tick, frame) pairs included. The freeze holds
the clock for the whole artificial delay, so the delayed run differs only in
wall time. The perf lane never reads the variable into its samples: its
sampling system records the real frame delta and never waits on a capture.

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
On the update that reaches the beat's scenario tick with the capture lane free,
`request_beat_captures` does one atomic step: it pins the beat's manifest entry
`{file, tick, frame, request_id}` to the frame that update is about to render,
spawns the screenshot entity carrying that binding, and marks the lane busy.
While a readback is in flight the scenario clock holds (see the scenario clock
section above): the renderer keeps presenting the held frame, so the capture
always shows the pinned numbers, and the PNG's decoded code always equals the
report's entry. Because the clock can never pass a beat's tick while the lane
is busy, every beat pins exactly its scripted tick on every run, regardless of
readback latency.

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
counts scenario frames (drive steps after the readiness boundary; frames the
clock spends held under a readback never consume it), and when the count reaches
it with beats still uncaptured, the app records every uncaptured beat as
missing (a `Failure` event naming each in the runner's
``missing beat `<name>` (expected tick <n>)`` shape), writes the report, prints
`REPORT <path>`, and exits nonzero. A beat scripted past the deadline is a
failed scenario, never a hang; there is no waiting past the deadline.

## Calibration-evidence lane (protocol v4)

The fourth lane (`"mode": "calibration"`) produces capture-based evidence
about auto-exposure behavior. It reuses the capture lane's entire surface —
readiness, ticks, the frame-code chip, beat requests, PNG decode, the report —
and adds exactly two things: a required `calibration` scenario section, and
one `Calibration` event recorded before any sample is pinned.

(The name overlaps the perf lane's "calibration scene", which is the plain
bootstrap scene — dark clear plus the chip. The perf lane does not build this
lane's scene or post chain; only the calibration lane does.)

### Scenario surface

The `calibration` section predeclares everything the lane renders, so the
report's evidence and the runner's measurements are judged against one
declared setup:

```json
{
  "initial_level": 0.18,
  "step": {"tick": 30, "level": 0.36},
  "patch_area_fraction": 0.02,
  "patch": {"center_then_edge": {"at_tick": 60}},
  "mask": "center_weighted",
  "auto_exposure": true
}
```

- `initial_level` / `step.level` — the wall's linear radiance before and from
  the step tick; finite, positive, at most `LEVEL_MAX` (100.0). The step lands
  at tick 1 or later (the initial level is sampled first).
- `patch_area_fraction` — the bright patch's area as a fraction of the frame
  area at the wall plane, identical in both placements; positive and below
  `PATCH_AREA_FRACTION_MAX` (0.03, the largest equal-area patch that stays
  fully on screen in the edge slot at the lane's pinned camera geometry).
- `patch` — the placement plan: `fixed_center`, `fixed_edge`, or
  `center_then_edge` with a move tick of 1 or later.
- `mask` — which metering-mask asset the camera binds: `center_weighted` (the
  game camera's radial mask) or `uniform` (the control that removes the
  center/edge metering difference).
- `auto_exposure` — whether the camera's `AutoExposure` component is bound at
  all (the component's presence is bevy's only switch for computed exposure).

Cross-field invariants enforced by `parse_scenario`: the section is required
exactly when the mode is `calibration` and forbidden on the other lanes; a
calibration scenario carries at least one beat (the beats are the pinned
sample ticks) and no scripted actions (the scene is a closed lane; nothing
reads input).

### Scene and capture path (app side)

The lane renders a 3D scene through the game's REAL post chain into the same
offscreen capture target the capture lane reads back: a wall quad whose
linear radiance is the current level (emissive-only `StandardMaterial`; the
scene has no lights, so emissive is the whole signal), an equal-area bright
patch that radiates a fixed multiple (10x) of the wall level, and a camera at
the origin with a pinned 45-degree vertical FOV at distance 5, authored
exposure `Exposure::ev100 = 0.0`, HDR on in both arms, and the post chain the
game camera carries — AgX tonemapping, the authored vignette, and auto
exposure metering through the selected mask exactly when the arm is on. The
frame-code chip is Core2d (sprites never render in a 3d view), so a second,
plain 2d camera (`ClearColorConfig::None`, higher camera order) draws the
chip over the 3d output into the same target. The histogram pass reads the 3d
view's HDR main texture, which the chip never enters: metering sees only the
wall and the patch. Captures stay the executed post-chain output plus the
chip — the same contract as every other lane. Dynamics apply per logical tick
in the same update the chip is painted for that tick, so a capture pinned at
tick T shows tick T's level, slot, and chip code together. Canary runs mirror
the same camera pair onto the window, so the onscreen capture decodes.

The metering masks are checked-in assets
(`crates/gone_app/assets/post/metering_mask.png` and
`metering_mask_uniform.png`), 64x64 single-channel (8-bit gray) PNGs whose
pixel bytes are the construction `crates/gone_app/src/post.rs` documents and
tests: a radial center-weighted falloff quantized to the shader's 16 levels,
and the all-white uniform control. The generators that serialize the
constructions are `cargo test -p gone_app --lib generate_ -- --ignored`.

### The Calibration evidence event

Once the readiness boundary has passed AND the selected mask asset has
actually loaded (a failed load fails the run naming the mask path; a
still-loading mask keeps waiting under the same `max_frames` deadline as any
beat), the app records exactly one `TimedEvent::Calibration`:

```json
{"kind": "Calibration", "at": {"tick": 0, "frame": 5, "evidence": {"...": "..."}}}
```

`evidence` carries: the mask selection and `mask_sha256`, the sha2-256 of the
loaded asset's pixel bytes (what the GPU histogram samples, not the file
path); the auto-exposure arm (an `enabled` flag plus `settings` — the range,
filter, and adaptation speeds as bound on the camera — present exactly when
enabled); `authored_exposure_ev100`; `patch_area_fraction` and
`patch_placements` (the plan in tick order); `initial_level`, `step_tick`,
`step_level`; and `sample_ticks`, the scenario's beat ticks ascending — the
pinned samples the capture lane is about to take.

The beat requester refuses to pin a capture before that event is recorded
(`bootstrap::state::beat_requests_allowed`), so every capture the runner
measures postdates the setup event. On this lane the readiness-proof PNG
shows the calibration scene's wall instead of the empty dark clear; the
boundary's meaning is unchanged (first readback of a frame the render graph
executed).

The app never measures luminance. The runner measures the capture PNGs
against this predeclared setup; the app's job is to make the captures
possible and report the setup identity honestly.

## Artwork layout

```
tmp/harness/<scenario>/<run-id>/
  readiness-proof.png   the first capture of the offscreen target (the dark
                        loading scene on calibration content, the first
                        provisioned game frame on gameplay content)
  beats/<name>.png      one PNG per beat: the rendered frame, chip at top-left
  beats/<name>.onscreen.png  canary runs only: the single onscreen capture, at the first beat
  report.json           the run report
  scenario.json         a copy of the scenario bytes the run used
```

`<run-id>` is `<unix-nanos>-s<seed>` so concurrent sessions cannot clobber each
other, prefixed `rc` on render-check (canary) runs. `tmp/` is gitignored.

## report.json schema

Written by the app at finish (`harness/report.rs`), keyed to `PROTOCOL_VERSION`:

- `protocol_version` — must equal the runner's.
- `scenario`, `seed` — the scenario's name and RNG id.
- `events` — tick-stamped timeline: `Ready {frame}`, `Input {tick,frame,what}`,
  `Beat {name,tick,frame,request_id}`, `Complete {frame}`, and
  `Failure {frame, what}` (a capture or report error, terminal, no retry).
  Calibration runs add `Calibration {tick, frame, evidence}` — the setup
  evidence recorded once before any sample is pinned (see the
  calibration-evidence lane section).
- `checkpoints` — strings like `ready at frame N`, `beat <name> captured`,
  `failed: beat `x` capture failed: <error>`, and on calibration runs
  `calibration evidence recorded`.
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
the report. A `--render-check` run extends stage 1 with the onscreen artifact
checks (exactly one capture under `beats/`, 1920x1080, not entirely black,
chip frame equal to the report). Stage 2 is the vision layer (deferred): a
vision-capable subagent looks at the beats, and for a canary run the onscreen
PNG joins them in that visual pass. Machine decoding only here; visual
judgments use GPT or Opus, never Zai.

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

Beat capture events carry the pinned tick/frame. The scenario clock holds
under an in-flight readback, so both runs pin exactly the scripted ticks and
the streams match for any beat spacing.

The terminal `Complete` frame is normalized away before diffing. Under the
capture freeze the completion frame is itself deterministic (the clock does
not advance under a readback), so the normalization is redundant today; it
stays so the line shape is stable. Every tick-scoped event (inputs, beats
with their pinned numbers) compares exactly.

## Performance lane

The perf lane measures wall-clock frame times of the bootstrap scene (dark
clear plus the frame-code chip; not the calibration lane's scene) and judges
them against a versioned, checked-in policy. It is the third runner mode
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

`ci`'s harness steps stay on the smoke and render-canary lanes: the perf
verdict measures wall-clock on the real GPU, so it is a local gate, not a
deterministic CI step.

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
   flight). The scenario clock holds meanwhile, so the second beat pins its
   own scripted tick; same-tick beats capture in order and show the same
   (tick, frame) code with distinct request ids. The PNG and the report
   always agree.
3. `FrameStats` is empty; the perf lane reports the `perf` section instead (the
   seeded struct is untouched on both lanes).
4. The `pacing` scenario field is consumed at window creation (Uncapped sets
   `PresentMode::AutoNoVsync`), which now means canary runs only: a headless
   run has no window and no surface, so no present mode applies and pacing no
   longer perturbs reports there. Compare scenarios leave it unset and run the
   default presentation; `max_frames` is consumed as the clean-close deadline
   described under beat capture binding (inert on the perf lane,
   which has no beats to miss).
5. The headless capture lane paces updates at the scenario tick rate, and the
   scenario clock holds under an in-flight readback, so the drive's frame
   counts carry no latency footprint and completion lands at a deterministic
   frame. The compare lane still normalizes the terminal `Complete` frame
   (see compare mode); the normalization is redundant today and kept for
   line-shape stability.

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
