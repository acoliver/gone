//! Runner-side lifecycle lane (issue #5 stage B): `gone-harness lifecycle`.
//!
//! One windowed child run of the built-in lifecycle scenario (the canary
//! path: every drive writes the real window surface, every observation
//! arrives through the OS event loop), judged runner-side against
//! predeclared assertions over the report's native observations, then the
//! timeout case: a long-planned child killed and reaped at the lane's
//! budget, returning the named timeout failure, well inside the lane's own
//! patience. The assertions are constants of the lane (see
//! [`assertions`]); a live run that contradicts one is a FINDING, and the
//! evidence artifact (`lifecycle-evidence.json` in the run dir) records
//! every assertion's expected-vs-measured outcome beside the run's report.
//!
//! The scenario's shape is the lane's contract: a key held from the first
//! driven tick (never scripted a release), one look before the loss so the
//! input stream carries a motion delivery, the three window drives pinned
//! by the scenario's `lifecycle` section (focus loss, reacquisition,
//! resize), and beats pinned around the drives so the captures prove the
//! phase timeline kept running through them. The timeout scenario reuses
//! the same drives with beats pinned millions of ticks out — a plan the
//! child pursues honestly, so the budget genuinely terminates a healthy
//! mid-run child rather than a stuck one.

mod assertions;

use assertions::HELD_KEY;

pub use assertions::{AssertionOutcome, verify_lifecycle};

use std::path::{Path, PathBuf};
use std::time::Duration;

use serde::Serialize;

use crate::report;
use crate::scenario::TICKS_PER_SECOND;
use crate::{
    Beat, Content, LifecycleParams, LifecycleResize, LifecycleStep, Scenario, ScenarioMode,
    ScriptedAction,
};

/// The clean-close scenario's name (the run dir lives under
/// `tmp/harness/lifecycle/<run-id>/`).
pub const LIFECYCLE_SCENARIO_NAME: &str = "lifecycle";

/// The timeout scenario's name (its own run dir, distinct from the
/// clean-close run's).
pub const LIFECYCLE_TIMEOUT_SCENARIO_NAME: &str = "lifecycle-timeout";

/// The lane's seed for the clean-close scenario (embedded in the run id).
const SEED: u64 = 3407;

/// The timeout scenario's seed, distinct so the two runs' ids never collide
/// even within the same nanosecond.
const TIMEOUT_SEED: u64 = 3408;

/// The held key's press tick: the first driven tick, so the key is held
/// from the run's start and the focus loss has held input to clear.
const HELD_PRESS_TICK: u64 = 0;

/// The pre-loss look tick: one motion delivery inside the run's input
/// stream, so the after-reacquisition quiet-window assertion proves the
/// stream really went quiet rather than having never spoken.
const LOOK_TICK: u64 = 10;

/// The focus-loss drive's tick.
const FOCUS_LOSS_TICK: u64 = 40;

/// The reacquisition drive's tick.
const REACQUIRE_TICK: u64 = 90;

/// The resize drive's tick.
const RESIZE_TICK: u64 = 140;

/// The resize drive's extent in physical pixels (the lane pins the scale
/// factor to 1.0, so logical matches): smaller than the canary window's
/// 1920x1080, so the observation is an actual resize.
const RESIZE_EXTENT: (u32, u32) = (1280, 720);

/// The clean-close scenario's beats, pinned around the drives: before the
/// loss, after it (the clear has landed by then), after the reacquisition,
/// and after the resize.
const BEATS: [(&str, u64); 4] = [
    ("held", 20),
    ("cleared", 60),
    ("refocused", 110),
    ("resized", 160),
];

/// The clean-close scenario's frame deadline: past the last beat plus the
/// capture settle window, so the run closes cleanly right after the last
/// capture instead of idling to a large default.
const MAX_FRAMES: u64 = 240;

/// The timeout scenario's beats: millions of ticks out, so the child
/// pursues them honestly for far longer than the lane's budget — the
/// runner's kill-and-reap path is what ends the run.
const TIMEOUT_BEATS: [(&str, u64); 2] = [("late-1", 1_500_000), ("late-2", 1_600_000)];

/// The timeout scenario's frame deadline: past its beats and far past
/// anything the budget could reach, so the app-side deadline never fires
/// before the runner's kill.
const TIMEOUT_MAX_FRAMES: u64 = 2_000_000;

/// The wall-clock budget the timeout case grants its child. It only has to
/// outlast the child's legitimate startup (readiness handshake, the canary
/// present gate, the three window drives land within a few seconds at the
/// 60 Hz canary cadence) and then terminate a healthy mid-plan run; the
/// kill, the reap, and the named failure are the case under test.
pub const TIMEOUT_BUDGET: Duration = Duration::from_secs(8);

/// The built-in lifecycle scenario: windowed lifecycle mode, the held key
/// plus one look, the three drives, and beats pinned around them.
#[must_use]
pub fn lifecycle_scenario() -> Scenario {
    Scenario {
        name: LIFECYCLE_SCENARIO_NAME.to_owned(),
        seed: SEED,
        ticks_per_second: TICKS_PER_SECOND,
        actions: vec![
            // The stuck key: never scripted a release, so it is held input
            // when the focus loss lands. The same constant the assertions
            // expect in the report's released list.
            ScriptedAction::press(HELD_PRESS_TICK, HELD_KEY),
            // One motion delivery before the loss, so the quiet window the
            // reacquisition must leave behind is proven quiet, not mute.
            ScriptedAction::look(LOOK_TICK, 3.0, 0.0),
        ],
        beats: pinned(&BEATS),
        pacing: None,
        max_frames: MAX_FRAMES,
        mode: ScenarioMode::Lifecycle,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Calibration,
        calibration: None,
        lifecycle: Some(drives()),
    }
}

/// The timeout scenario: the same drives and held key, with beats pinned
/// millions of ticks out so the child is still honestly mid-plan when the
/// lane's budget terminates, reaps, and names it.
#[must_use]
pub fn timeout_scenario() -> Scenario {
    Scenario {
        name: LIFECYCLE_TIMEOUT_SCENARIO_NAME.to_owned(),
        seed: TIMEOUT_SEED,
        ticks_per_second: TICKS_PER_SECOND,
        actions: vec![ScriptedAction::press(HELD_PRESS_TICK, HELD_KEY)],
        beats: pinned(&TIMEOUT_BEATS),
        pacing: None,
        max_frames: TIMEOUT_MAX_FRAMES,
        mode: ScenarioMode::Lifecycle,
        warmup_frames: 0,
        sample_frames: 0,
        content: Content::Calibration,
        calibration: None,
        lifecycle: Some(drives()),
    }
}

/// True when a run's error is the runner's timeout verdict — the child was
/// killed and reaped at the budget and the failure was named — as opposed
/// to any other run failure. The timeout case passes only on this shape.
#[must_use]
pub fn is_timeout_failure(error: &str) -> bool {
    error.contains("timed out after")
}

/// The lane's verdict over one finished clean-close run: every assertion's
/// outcome and where the evidence artifact landed.
#[derive(Debug)]
pub struct LifecycleJudgment {
    /// Whether every predeclared assertion held.
    pub passed: bool,
    /// Every assertion's outcome, in lane order.
    pub assertions: Vec<AssertionOutcome>,
    /// The evidence artifact written beside the run's report.
    pub artifact_path: PathBuf,
}

/// Judge one finished clean-close run: read its report, confirm it names
/// this scenario, evaluate the predeclared assertions, and write
/// `lifecycle-evidence.json` into the run dir.
///
/// # Errors
/// A named error when the report is missing or unparseable, names a
/// different scenario, or the artifact write fails.
pub fn judge_run(
    scenario: &Scenario,
    run_dir: &Path,
    run_id: &str,
) -> Result<LifecycleJudgment, String> {
    let report_path = run_dir.join("report.json");
    let report_text = std::fs::read_to_string(&report_path)
        .map_err(|e| format!("failed to read {}: {e}", report_path.display()))?;
    let run_report =
        report::parse_report(&report_text).map_err(|e| format!("report parse (lifecycle): {e}"))?;
    if run_report.scenario != scenario.name {
        return Err(format!(
            "report names scenario `{}` but the lane ran `{}`",
            run_report.scenario, scenario.name
        ));
    }
    let assertions = assertions::evaluate_lifecycle(scenario, &run_report);
    let passed = assertions.iter().all(|outcome| outcome.passed);
    let artifact_path = write_artifact(run_dir, run_id, scenario, &assertions, passed)?;
    Ok(LifecycleJudgment {
        passed,
        assertions,
        artifact_path,
    })
}

/// The evidence artifact: the lane identity, the run it belongs to, every
/// assertion's expected-vs-measured outcome, and the overall verdict.
#[derive(Debug, Serialize)]
struct EvidenceArtifact<'a> {
    lane: &'static str,
    run_id: &'a str,
    scenario: &'a str,
    assertions: &'a [AssertionOutcome],
    passed: bool,
}

/// Write the evidence artifact into the run dir.
///
/// # Errors
/// A named error when serialization or the file write fails.
fn write_artifact(
    run_dir: &Path,
    run_id: &str,
    scenario: &Scenario,
    assertions: &[AssertionOutcome],
    passed: bool,
) -> Result<PathBuf, String> {
    let artifact = EvidenceArtifact {
        lane: "lifecycle-v1",
        run_id,
        scenario: &scenario.name,
        assertions,
        passed,
    };
    let text = serde_json::to_string_pretty(&artifact)
        .map_err(|e| format!("evidence artifact serialize: {e}"))?;
    let path = run_dir.join("lifecycle-evidence.json");
    std::fs::write(&path, text.as_bytes())
        .map_err(|e| format!("failed to write {}: {e}", path.display()))?;
    Ok(path)
}

/// The scenario's `lifecycle` section: the three drives, in the order the
/// app performs them.
fn drives() -> LifecycleParams {
    LifecycleParams {
        focus_loss: LifecycleStep {
            at_tick: FOCUS_LOSS_TICK,
        },
        reacquire: LifecycleStep {
            at_tick: REACQUIRE_TICK,
        },
        resize: LifecycleResize {
            at_tick: RESIZE_TICK,
            width: RESIZE_EXTENT.0,
            height: RESIZE_EXTENT.1,
        },
    }
}

/// The beats as `Beat` pins, in declared order.
fn pinned(beats: &[(&str, u64)]) -> Vec<Beat> {
    beats
        .iter()
        .map(|&(name, tick)| Beat::new(name, tick))
        .collect()
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use super::{
        BEATS, HELD_PRESS_TICK, LIFECYCLE_SCENARIO_NAME, LIFECYCLE_TIMEOUT_SCENARIO_NAME,
        LOOK_TICK, TIMEOUT_BUDGET, TIMEOUT_MAX_FRAMES, drives, is_timeout_failure, judge_run,
        lifecycle_scenario, timeout_scenario,
    };
    use crate::report::{BeatEntry, Identity, Report, TimedEvent};
    use crate::{Action, PROTOCOL_VERSION, ScenarioMode, parse_scenario, scenario_to_json};

    /// A scratch run dir unique to this test process (the runner's run dirs
    /// live under `tmp/harness`; a unit test needs no repo side effects).
    fn scratch_dir(label: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "gone-harness-lifecycle-{label}-{}",
            std::process::id()
        ))
    }

    #[test]
    fn the_scenario_is_a_valid_windowed_lifecycle_scenario() {
        let scenario = lifecycle_scenario();
        assert_eq!(scenario.name, LIFECYCLE_SCENARIO_NAME);
        assert_eq!(scenario.mode, ScenarioMode::Lifecycle);
        assert_eq!(scenario.lifecycle, Some(drives()));
        assert!(
            scenario.lifecycle.expect("drives").validate().is_ok(),
            "the drives validate"
        );
        // The lane runs windowed: the runner selects the canary path, and
        // the app refuses a headless lifecycle run at plugin build.
        assert_eq!(scenario.content, crate::Content::Calibration);
        let json = scenario_to_json(&scenario).expect("serializes");
        let parsed = parse_scenario(&json).expect("the lane scenario is valid");
        assert_eq!(parsed, scenario);
    }

    #[test]
    fn the_scenario_holds_a_key_across_the_loss_and_speaks_motion_before_it() {
        let scenario = lifecycle_scenario();
        let presses: Vec<_> = scenario
            .actions
            .iter()
            .filter(|action| matches!(action.action, Action::Press { .. }))
            .collect();
        let releases: Vec<_> = scenario
            .actions
            .iter()
            .filter(|action| matches!(action.action, Action::Release { .. }))
            .collect();
        assert_eq!(presses.len(), 1, "exactly the held press");
        assert_eq!(presses[0].tick, HELD_PRESS_TICK);
        assert!(releases.is_empty(), "nothing ever releases the held key");
        let loss_tick = drives().focus_loss.at_tick;
        assert!(
            HELD_PRESS_TICK < loss_tick,
            "the key is already held when the loss lands"
        );
        assert!(
            scenario
                .actions
                .iter()
                .any(|action| action.tick < loss_tick
                    && matches!(action.action, Action::Look { .. })),
            "one motion delivery precedes the loss"
        );
        assert_eq!(
            scenario
                .actions
                .iter()
                .find(|action| matches!(action.action, Action::Look { .. }))
                .map(|action| action.tick),
            Some(LOOK_TICK),
        );
    }

    #[test]
    fn the_beats_pin_around_the_drives() {
        let scenario = lifecycle_scenario();
        let drives = drives();
        let pins: Vec<u64> = scenario.beats.iter().map(|beat| beat.tick).collect();
        assert_eq!(
            pins,
            BEATS.iter().map(|(_, tick)| *tick).collect::<Vec<u64>>()
        );
        let (before_loss, after_loss, after_reacquire, after_resize) =
            (pins[0], pins[1], pins[2], pins[3]);
        assert!(before_loss < drives.focus_loss.at_tick);
        assert!(after_loss > drives.focus_loss.at_tick);
        assert!(after_loss < drives.reacquire.at_tick);
        assert!(after_reacquire > drives.reacquire.at_tick);
        assert!(after_reacquire < drives.resize.at_tick);
        assert!(after_resize > drives.resize.at_tick);
        assert!(
            scenario.max_frames > after_resize,
            "the deadline never lands inside the beat plan"
        );
    }

    #[test]
    fn the_timeout_scenario_plans_a_honest_long_run() {
        let scenario = timeout_scenario();
        assert_eq!(scenario.name, LIFECYCLE_TIMEOUT_SCENARIO_NAME);
        assert_eq!(scenario.mode, ScenarioMode::Lifecycle);
        assert_eq!(scenario.lifecycle, Some(drives()));
        assert_ne!(scenario.seed, lifecycle_scenario().seed);
        let last_beat = scenario.beats.last().expect("beats").tick;
        assert!(
            last_beat > TIMEOUT_MAX_FRAMES / 2,
            "the beats sit deep in a plan the budget cannot reach"
        );
        assert!(
            TIMEOUT_MAX_FRAMES > last_beat,
            "the app-side deadline never fires before the runner's kill"
        );
        assert!(
            TIMEOUT_BUDGET.as_secs() < 60,
            "the budget terminates a healthy child far inside the runner's default timeout"
        );
    }

    #[test]
    fn the_timeout_verdict_is_recognized_by_name_and_others_are_not() {
        assert!(is_timeout_failure(
            "scenario `lifecycle-timeout` timed out after 8s"
        ));
        assert!(!is_timeout_failure(
            "app exited nonzero (exit status: 1) for scenario `lifecycle-timeout`"
        ));
        assert!(!is_timeout_failure("report parse: {e}"));
    }

    /// One input-delivery event at `tick` for `what` (the frame matches the
    /// tick, as the drive's stamps do).
    fn input(tick: u64, what: &str) -> TimedEvent {
        TimedEvent::Input {
            tick,
            frame: tick,
            what: what.to_owned(),
        }
    }

    /// One native observation event at `tick`, focused or resized per the
    /// lane's drive outcomes.
    fn focus(tick: u64, focused: bool) -> TimedEvent {
        TimedEvent::WindowFocus {
            tick,
            frame: tick,
            focused,
        }
    }

    /// The input layer's clear at the loss tick.
    fn cleared(tick: u64) -> TimedEvent {
        TimedEvent::InputCleared {
            tick,
            frame: tick,
            dropped_edges: 0,
            released: vec!["Key(Forward)".to_owned()],
        }
    }

    /// The native resize observation at the scenario's extent, capture
    /// target unchanged.
    fn resized(tick: u64) -> TimedEvent {
        TimedEvent::WindowResized {
            tick,
            frame: tick,
            width: 1280.0,
            height: 720.0,
            capture_width: 1920,
            capture_height: 1080,
        }
    }

    /// A good run's report, in the shape a correct clean-close run writes
    /// (the same one the assertion tests build).
    fn good_report() -> Report {
        let mut report = Report::new(
            PROTOCOL_VERSION,
            LIFECYCLE_SCENARIO_NAME,
            3407,
            Identity {
                app_hash: "a".to_owned(),
                scenario_hash: "s".to_owned(),
                config_hash: "c".to_owned(),
            },
        );
        for (index, (name, tick)) in BEATS.iter().enumerate() {
            report.beats.insert(
                (*name).to_owned(),
                BeatEntry {
                    file: format!("beats/{name}.png"),
                    tick: *tick,
                    frame: *tick,
                    request_id: index as u64 + 1,
                },
            );
        }
        report.events = vec![
            TimedEvent::Ready { frame: 0 },
            input(0, "Key(Forward) press"),
            input(10, "look 3 0"),
            focus(43, false),
            cleared(43),
            input(44, "Key(Forward) release"),
            focus(92, true),
            resized(141),
            TimedEvent::Complete { frame: 162 },
        ];
        report
    }

    #[test]
    fn judge_run_passes_a_correct_report_and_writes_the_evidence_artifact() {
        let run_dir = scratch_dir("judge-pass");
        std::fs::create_dir_all(&run_dir).expect("run dir");
        let report = good_report();
        std::fs::write(
            run_dir.join("report.json"),
            crate::report::report_to_json(&report).expect("json"),
        )
        .expect("write report");
        let judgment = judge_run(&lifecycle_scenario(), &run_dir, "run-1");
        let _ = std::fs::remove_dir_all(&run_dir);
        let judgment = judgment.expect("the correct report passes");
        assert!(judgment.passed, "{:?}", judgment.assertions);
        assert!(
            judgment
                .artifact_path
                .file_name()
                .is_some_and(|name| name == "lifecycle-evidence.json")
        );
    }

    #[test]
    fn judge_run_fails_naming_a_foreign_report() {
        let run_dir = scratch_dir("judge-foreign");
        std::fs::create_dir_all(&run_dir).expect("run dir");
        let mut report = good_report();
        report.scenario = "smoke".to_owned();
        std::fs::write(
            run_dir.join("report.json"),
            crate::report::report_to_json(&report).expect("json"),
        )
        .expect("write report");
        let outcome = judge_run(&lifecycle_scenario(), &run_dir, "run-2");
        let _ = std::fs::remove_dir_all(&run_dir);
        let err = outcome.expect_err("a foreign report must fail");
        assert!(err.contains("smoke"), "{err}");
        assert!(err.contains("lifecycle"), "{err}");
    }

    #[test]
    fn judge_run_fails_naming_a_missing_report() {
        let run_dir = scratch_dir("judge-missing");
        let outcome = judge_run(&lifecycle_scenario(), &run_dir, "run-3");
        let _ = std::fs::remove_dir_all(&run_dir);
        let err = outcome.expect_err("a missing report must fail");
        assert!(err.contains("failed to read"), "{err}");
        assert!(err.contains("report.json"), "{err}");
    }
}
