# gone harness protocol (Godot)

This is the contract between the app lane and the runner in the Godot
tree: how a scenario is declared, how the runner drives the app, what
lands on disk, and what makes a run pass or fail. The protocol both sides
embed and compare is `harness/protocol.gd`, `PROTOCOL_VERSION = 4`,
preloaded verbatim by the runner (`harness/run.gd`) and by the app lanes
(`app/harness_mode.gd` for gameplay and perf, `app/calibration_mode.gd`
for calibration). A report whose version does not equal the runner's is
rejected.

## How a run happens

The runner is a headless SceneTree script:

    godot --headless --path . -s harness/run.gd -- <scenario.json> [--out <dir>]

It parses the scenario, computes the identity hashes, creates the run
directory, spawns the app as a separate Godot process (windowed, at
`--resolution 480x270` by default; the perf lane uses the policy's
resolution), and polls every 0.5 s up to a 300 s timeout, killing the app
if the deadline passes. When the app exits, the runner machine-verifies
the run, writes `verdict.txt`, and prints the two-stage verdict. Exit 0
means the machine stage passed.

The environment contract the runner sets and the app echoes:

- `GONE_HARNESS=1`: the app selects the driven lane and refuses to run
  without it.
- `GONE_SCENARIO=<abs path>`: the scenario file.
- `GONE_OUT_DIR=<abs path>`: the run directory the app writes into.
- `GONE_APP_HASH`, `GONE_SCENARIO_HASH`, `GONE_CONFIG_HASH`: lowercase
  sha256 hex identity strings.
- `GONE_PERF_POLICY=<abs path>`: the perf policy file, perf lane only.

The app hashes nothing itself. It echoes the runner's values verbatim, so
a stale pairing fails the hash check.

Hash definitions:

- The scenario hash is sha256 over the scenario file's exact bytes. The
  config hash equals the scenario hash in this port; the Rust runner
  hashed its own config string separately.
- The app hash is sha256 over every `*.gd` file under `app/`, `sim/`, and
  `harness/`, sorted by relative path, each entry hashed as its UTF-8
  relative path, one NUL byte, and the file's exact bytes. An edited
  script cannot masquerade as the tested build.

## Modes

### Gameplay (mode "capture", content "gameplay")

The real game boots in driven mode (`app/harness_mode.gd`). Scripted
input flows through the shared InputPlane via the ScriptedAdapter, the
same plane the real player consumes, so gameplay code is never called
directly. The run crosses a readiness boundary first: the app records the
`ready` event and writes `readiness-proof.png` before any tick or input.
After that the scenario's fixed 60 Hz timeline advances, and due beats are
captured as `beats/<name>.png` with the frame-code chip painted into the
view.

Machine checks after the run: report version and hash echoes; every
declared beat present and decodable, its chip equal to the report's
(tick, frame) and correlated to the scripted tick; per-beat luminance and
channel stats (the eyes-closed beat must be dark, the hall-dark beat
must be dark while the hallway's fixtures hold zero, every other beat
nonblack and red-dominant); the wake progression waking, awake_in_pod,
exiting_pod, standing in order with non-regressing ticks; door-open
evidence at or before the door-opened beat; and hallway light evidence
for the lanes that declare the hall beats.

`scenarios/gameplay-full.json` scripts the whole opening: the wake, the
get-up out of the pod, a 90-degree turn, the steadying walk across the
room, and the interact that opens the door into the hallway, pinning
seven beats (eyes-closed, first-blink, shapes-resolving, standing,
mid-room, at-door, door-opened). `scenarios/hallway.json` continues past
the doorway: the dark crossing of the unlit hall to the far wall, the
switch flip, and the lit settle, pinning door-opened, hall-dark, and
hall-lit.

### Perf (mode "perf")

No beats. The app disables vsync and samples real frame times in the
populated room (pods, preprocessed ceiling smoke, automatic spark bursts)
at the policy's resolution, while a fixed orbit camera routes around the
room one step per rendered frame with no scripted input. The report
carries the raw samples and summary statistics. The runner checks the
run's shape against the frozen policy (`harness/perf-policy.json`, version
`godot-smoke-1152x648-v1`: 60 warmup frames, 300 samples, uncapped,
1152x648, mean at most 25 ms, p95 at most 50 ms), fails on any threshold
breach, and writes `perf-verdict.json` beside the report with the policy
identity and the measured distribution.

### Calibration (mode "calibration")

The calibration-evidence lane (`app/calibration_mode.gd`) renders exactly
what the scenario predeclares: one luminance step on an emissive wall, an
equal-area bright patch under a placement plan, a metering-mask selection,
and the auto-exposure arm. The lane meters a 48x27 SubViewport view of the
scene through the selected mask, adapts exposure in a closed loop when the
arm is on, pins the scenario's beats as captures, and records one
Calibration event with the setup identity (the mask selection and the
sha256 of the mask's pixel bytes, the arm state, the patch plan, the light
levels, the sample ticks) before any sample is pinned.

The runner checks that the Calibration event exists and precedes the first
pinned sample, that the mask hash matches the shipped mask's pixels, that
the declared placements and sample ticks match the evidence, and that the
predeclared assertion cells (`harness/calibration_assertions.gd`) pass
over the measured Rec.709 mean linear luminance of each capture. Two cells
ship: cell A (a luminance step, center-weighted mask, auto-exposure on) as
`calibration-step.json`, and cell D (the patch moving center to edge under
a uniform mask) as `calibration-move.json`.

## Negative cases

Two scenarios under `scenarios/negative/` must fail:

- `never-beat.json` declares a beat at tick 600 under `max_frames` 300.
  The app must record the beat as missing, write the report, and exit
  nonzero; the runner then fails the run. A lane that waited past the
  deadline or reported success without the capture would break the
  contract, and this case exists to catch that.
- `calibration-no-autoexposure.json` runs the cell A setup with
  `auto_exposure` false. Without the adaptation loop the cell's assertions
  must fail, so the lane exits nonzero.

Run them the same way as any lane and expect exit 1; a nonzero exit is
the passing outcome for a negative case. They pin the instrument: the
lanes must be able to fail.

## Artifact layout

    tmp/harness/<scenario>/run-<id>/
      report.json           the run report (protocol_version, events,
                            checkpoints, beats, identity, perf on perf runs)
      beats/<name>.png      one PNG per beat, frame-code chip at top-left
      readiness-proof.png   the first provisioned frame, before any tick
      verdict.txt           the two-stage verdict the runner prints
      scenario.json         a copy of the scenario bytes the run used
      perf-verdict.json     perf runs: policy identity, stats, violations

`<run-id>` is `run-<unix-seconds>`. `tmp/` is gitignored, and each run
gets its own directory so concurrent sessions cannot clobber each other.

## The frame-code chip

A 24x10 pixel lattice scaled 4x (each chip pixel paints a 4x4 block so the
lattice survives the viewport), six decimal digit cells per band, two
bands: the logical tick over the rendered frame, high-order digit first. The chip is rendered content, painted into the captured view. The
runner decodes each beat PNG's top-left chip and asserts it equals the
report's (tick, frame) entry, which proves the PNG shows the exact
reported moment.

## Two-stage verdict and the visual protocol

Stage one (machine) is everything the runner verifies above, and it alone
gates gameplay logic. Stage two is visual. The driver agent cannot read
images, so a vision subagent (the Eyes) receives the beat PNGs and an
expectations checklist (red emergency light, smoke densest at the ceiling,
sparks strobing, the hatch at the door) and returns pass or fail per
expectation with quotes of what it sees. The driver aggregates that with
report.json into the run verdict. Missing, malformed, or inconclusive
visual results count as failures, so an absent visual pass is never
recorded as a pass. The machine verdict always ends with `visual: PENDING
(needs Eyes subagent)` in `verdict.txt`; the visual stage's result lands
with the driver, outside the runner.

## Commands

Unit suite (204 tests, headless):

    godot --headless --path . -s tests/run_tests.gd

Lanes (the runner is headless; the spawned app is windowed):

    godot --headless --path . -s harness/run.gd -- scenarios/gameplay-full.json
    godot --headless --path . -s harness/run.gd -- scenarios/perf-smoke.json
    godot --headless --path . -s harness/run.gd -- scenarios/calibration-step.json
    godot --headless --path . -s harness/run.gd -- scenarios/calibration-move.json

Negatives (exit 1 is the passing outcome):

    godot --headless --path . -s harness/run.gd -- scenarios/negative/never-beat.json
    godot --headless --path . -s harness/run.gd -- scenarios/negative/calibration-no-autoexposure.json

Long windowed runs may need `nohup` and polling on this machine; an OS
watchdog kills long foreground commands.

## Archived Rust history

The Rust/Bevy harness this protocol descends from (the offscreen
render-target capture lane, the `GONE_RENDER_CHECK` render canary, the
`BEVY_ASSET_ROOT` asset-root contract, the cargo xtask wiring) lives
unchanged at `archive/rust/` with its own documentation; see
`archive/rust/README.md`. The Godot port keeps the protocol version, the
beat and chip contract, and the two-stage verdict shape. Two transport
differences are worth naming: the Godot runner stays headless while the
app lane runs windowed, and captures read the window's rendered frame
(`root.get_texture().get_image()` after `RenderingServer.frame_post_draw`)
rather than a dedicated offscreen target.
