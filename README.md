# gone

gone (working title) is a first-person game set on a derelict military
starship. You wake in a stasis pod in a red-lit room, climb out, cross the
floor on unsteady legs, and find the only door jammed. This repository
currently implements that opening beat, which is milestone 1 of the design;
the long-form plan is survival through repair, with the ship's systems as
both the puzzle and the story. Read
[docs/design/concept.md](docs/design/concept.md) for the design pillars and
[docs/design/story.md](docs/design/story.md) for the fiction.

## Requirements

The project targets Godot 4.7.2 stable, standard build; the .NET build is
not used. Rendering goes through the Forward+ method, so you need a GPU
from 2023 or newer, matching the hardware floor stated in the concept doc.

## Installing Godot

Pick one install path per platform.

- **macOS**: `brew install --cask godot`, or download from
  [godotengine.org](https://godotengine.org).
- **Windows**: download `Godot_v4.7.2-stable_win64.exe` from
  [godotengine.org](https://godotengine.org). The `_console.exe` variant of
  the same download prints engine output in the terminal, which the
  command-line sections below rely on.
- **Linux**: download the x86_64 binary from
  [godotengine.org](https://godotengine.org), or install the package your
  distribution ships, as long as it is 4.7.2 standard.

## Running the game

From the repository root on macOS or Linux:

    godot --path .

On Windows, run the downloaded executable with the same flag from a
command prompt:

    Godot_v4.7.2-stable_win64.exe --path .

The first run imports the project's resources before the window opens, so
expect it to take longer than later runs.

## Controls

- **WASD** moves.
- **Mouse** looks.
- **E** interacts: it starts the get-up out of the pod and tries the door.
- **Space** activates.
- Quit by closing the window.

Arrow-key movement and keyboard look are open work, tracked in issues
[#31](https://github.com/acoliver/gone/issues/31) and
[#30](https://github.com/acoliver/gone/issues/30). The controls today are
WASD and mouse.

## Running the tests

The unit suite lives in `tests/` and is auto-discovered by the runner:

    godot --headless --path . -s tests/run_tests.gd

It prints per-failure diagnostics and a `passed=N failed=Y` tally, exits 0
on a full pass, and exits 1 on any failure. The Windows equivalent uses
the console build so output reaches the terminal:

    Godot_v4.7.2-stable_win64_console.exe --headless --path . -s tests/run_tests.gd

## Running harness lanes

A lane plays the game under a scripted scenario and machine-verifies the
captures. Run one by naming its scenario file:

    godot --headless --path . -s harness/run.gd -- scenarios/<name>.json

The shipped lanes are listed below with what each covers.

- `scenarios/gameplay-full.json`: the full opening beat, seven pinned
  beats from eyes-closed to the refused door.
- `scenarios/perf-smoke.json`: frame-time sampling in the populated room
  against the frozen smoke policy.
- `scenarios/calibration-step.json`: the luminance-step calibration cell.
- `scenarios/calibration-move.json`: the patch-move calibration cell.

Two things to expect when you run a lane. The runner itself is headless,
but it spawns the app as a windowed process because the captures need real
rendering, so a small window appears for the duration of the run. Also, the
two negative scenarios under `scenarios/negative/` (`never-beat.json` and
`calibration-no-autoexposure.json`) exit 1 by design; for those a nonzero
exit is the passing outcome.

Each run writes its artifacts under `tmp/harness/<scenario>/run-<id>/`:
`report.json`, the `beats/` PNGs, `verdict.txt`, and a copy of the scenario
bytes. `tmp/` is gitignored, and each run gets its own directory. On
machines where an OS watchdog kills long foreground commands, start long
lanes with `nohup` and poll for completion instead of waiting in the
foreground.

## Repository layout

The tree is split by role.

- `sim/`: the ship simulation, pure GDScript with no engine scene types;
  it runs headless and is unit-tested directly.
- `app/`: the root scene, room geometry, lighting, the wake pass, the
  player rig, and the driven harness lanes.
- `harness/`: the play-testing runner, protocol, perf policy, and
  calibration machinery.
- `scenarios/`: JSON scenario definitions for the lanes, including the
  negative cases under `scenarios/negative/`.
- `tests/`: the unit suite, auto-discovered by `tests/run_tests.gd`.
- `docs/`: design docs under `docs/design/`, dev records under
  `docs/dev/`.
- `archive/rust/`: the frozen Rust/Bevy first implementation, excluded
  from Godot's import scan by `archive/.gdignore`.

## Further reading

The harness contract, including the environment variables, the hash
identity scheme, and the two-stage verdict, is specified in
[docs/dev/harness.md](docs/dev/harness.md). The record of the port from
the archived Rust/Bevy tree, including what moved where and the known
deviations, is in [docs/dev/godot-port.md](docs/dev/godot-port.md).

The `godot` commands above were verified on macOS with Godot 4.7.2.stable.
The Windows and Linux invocations follow Godot's documented CLI
conventions and have not been run by this project.
