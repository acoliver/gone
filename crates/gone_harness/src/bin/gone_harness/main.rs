//! The `gone-harness` runner binary (issue #5 / slice A).
//!
//! Drives the real `gone_app` binary as a child process for one scenario, collects
//! artifacts under `tmp/harness/<scenario>/<run-id>/`, verifies beat
//! expectations against the app's `report.json` (a beat that never happens fails
//! naming the missing beat), decodes the frame-code from each captured PNG and asserts
//! it matches the report's tick/frame, and prints the artifact dir on stdout's last
//! line. Two-stage verdict: exit 0 = "machine checks passed, visual verification
//! pending". The binary is OS-portable: `std::process::Command`, forward-slash
//! relative artifact paths, no OS-specific code (on macOS a SIGKILL to the child
//! process id is sufficient for termination; Windows kill-tree is documented as
//! stage-B).
//!
//! With `--render-check` the runner also selects the app's canary lane
//! (`GONE_RENDER_CHECK=1`): the run opens the unfocused window and saves one
//! onscreen capture at the first beat, which the runner machine-verifies after
//! the run (exactly one `*.onscreen.png` under `beats/`, exactly 1920x1080, not
//! entirely black, chip frame equal to the report's). Canary run dirs carry an
//! `rc` run-id prefix so they are identifiable in `tmp/harness`.
//!
//! `gameplay-smoke` runs the gameplay lane: the scenario's `content` field boots
//! the real game in the child, and the run's report additionally passes the
//! gameplay machine checks (`gone_harness::gameplay`): a stasis-room observation
//! matching the registry's count, and yaw samples proving the scripted look
//! turned the rig by the scripted amount.
//!
//! `gameplay-full` plays the whole opening beat: the activate press starts the
//! authored get-up out of the player pod, a scripted turn aims down the room's
//! long axis, and the steadying walk carries the player toward the jammed
//! hatch. Its checks add the wake-phase progression in order, the standing
//! beat's position at the exit waypoint, and the door beat's position inside
//! the room near the hatch, all derived from the frozen placement and
//! controller constants the app itself builds from.

mod app;
mod compare;
mod error;
mod hash;
mod paths;
mod perf;
mod run;

use gone_harness::scenario::{Scenario, scenario_to_json};
use gone_harness::{Content, ScenarioMode};

use crate::compare::run_compare;
use crate::paths::{load_scenario, repo_root, root_scenario, write_or};
use crate::perf::run_perf;
use crate::run::run_scenario;

/// The canary flag on the runner's own command line: every scenario run this
/// invocation performs goes through the canary lane and its onscreen
/// verification.
const RENDER_CHECK_FLAG: &str = "--render-check";

/// The built-in smoke scenario constant: empty scene (Camera3d + clear), a couple
/// of scripted actions, two beat captures, clean exit. The beats are spaced far
/// apart so each readback lands well inside the gap between beats; the scenario
/// clock holds under an in-flight readback, so spacing only spreads wall time,
/// it never moves a pin off its scripted tick.
#[must_use]
pub fn smoke_scenario() -> Scenario {
    Scenario {
        name: "smoke".to_owned(),
        seed: 1234,
        ticks_per_second: 60,
        actions: vec![
            gone_harness::ScriptedAction::look(0, 15.0, 0.0),
            gone_harness::ScriptedAction::move_delta(3, 1.0, 0.0),
            gone_harness::ScriptedAction::press(5, gone_harness::Key::Activate),
            gone_harness::ScriptedAction::release(5, gone_harness::Key::Activate),
        ],
        beats: vec![
            gone_harness::Beat::new("beat-a", 2),
            gone_harness::Beat::new("beat-b", 60),
        ],
        pacing: None,
        max_frames: 600,
        mode: ScenarioMode::Capture,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Calibration,
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    std::process::exit(dispatch(&args));
}

/// Route one command line to the smoke, perf, compare, or scenario run. The
/// `--render-check` flag may appear anywhere on the line and applies to every
/// scenario run the invocation performs.
fn dispatch(args: &[String]) -> i32 {
    let render_check = args.iter().any(|arg| arg == RENDER_CHECK_FLAG);
    let positional: Vec<String> = args
        .iter()
        .filter(|arg| arg.as_str() != RENDER_CHECK_FLAG)
        .cloned()
        .collect();
    match positional.get(1).map(String::as_str) {
        // Bare invocation is the default smoke run, matching `cargo xtask
        // harness`.
        None | Some("smoke") => run_smoke(render_check),
        Some("gameplay-smoke") => run_gameplay_smoke(render_check),
        Some("gameplay-full") => run_gameplay_full(render_check),
        Some("--help" | "-h") => {
            eprintln!(
                "usage: gone-harness [--render-check] <smoke | gameplay-smoke | gameplay-full | perf [scenario] | compare <scenario> | <scenario.json>>
  (no command runs the smoke scenario)
  --render-check: canary lane (unfocused window, one onscreen capture machine-verified after the run)"
            );
            0
        }
        Some("perf") => run_perf(&positional, render_check),
        Some("compare") => run_compare(&positional, render_check),
        Some(path) => run_one(path, render_check),
    }
}

fn run_smoke(render_check: bool) -> i32 {
    run_builtin(&smoke_scenario(), "smoke-scenario.json", render_check)
}

/// The gameplay smoke lane: the built-in gameplay scenario through the same
/// run/verify path as smoke, plus the gameplay-specific machine checks
/// hooked into [`run_scenario`] (room presence, scripted-look yaw replay).
fn run_gameplay_smoke(render_check: bool) -> i32 {
    run_builtin(
        &gone_harness::gameplay::gameplay_smoke_scenario(),
        "gameplay-smoke-scenario.json",
        render_check,
    )
}

/// The gameplay-full lane: the built-in whole-opening-beat scenario through
/// the same run/verify path, with the full lane's checks hooked into
/// [`run_scenario`] (wake progression, exit waypoint, door walk) on top of
/// the shared gameplay ones.
fn run_gameplay_full(render_check: bool) -> i32 {
    run_builtin(
        &gone_harness::gameplay::gameplay_full_scenario(),
        "gameplay-full-scenario.json",
        render_check,
    )
}

/// Run one built-in scenario end to end: write its JSON beside the artifacts
/// tree, run it, and print the two-line verdict. The shared body of every
/// built-in lane (smoke, gameplay smoke).
fn run_builtin(scenario: &Scenario, scenario_file: &str, render_check: bool) -> i32 {
    let root = repo_root().expect("root");
    let out_root = root.join("tmp").join("harness");
    let scenario_path = root.join("tmp").join(scenario_file);
    let json = scenario_to_json(scenario).expect("scenario json");
    write_or("built-in scenario", &scenario_path, json.as_bytes()).expect("write");
    match run_scenario(&root, &scenario_path, scenario, &out_root, render_check) {
        Ok(run_dir) => {
            println!(
                "MACHINE PASS: scenario `{}`; machine checks passed, visual verification pending",
                scenario.name
            );
            println!("ARTIFACTS: {}", run_dir.display());
            0
        }
        Err(e) => {
            eprintln!("{e}");
            println!("ARTIFACTS: {}", out_root.join(&scenario.name).display());
            1
        }
    }
}

fn run_one(path: &str, render_check: bool) -> i32 {
    let scenario_path = root_scenario(path).expect("scenario path");
    let scenario = load_scenario(&scenario_path).expect("scenario");
    let root = repo_root().expect("root");
    let out_root = root.join("tmp").join("harness");
    match run_scenario(&root, &scenario_path, &scenario, &out_root, render_check) {
        Ok(run_dir) => {
            println!(
                "MACHINE PASS: scenario `{}`; machine checks passed, visual verification pending",
                scenario.name
            );
            println!("ARTIFACTS: {}", run_dir.display());
            0
        }
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}
