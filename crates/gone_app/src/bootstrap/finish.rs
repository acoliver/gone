//! The run's close: the completion scan, the `max_frames` deadline check, and
//! the report write. Split out of `super` for size; the module doc there
//! describes the close contract (failure exits immediately, the capture lane
//! wants every beat on disk plus a settle window, the perf lane wants its
//! sample window full, then one report and one exit request).

use std::num::NonZeroU8;
use std::path::PathBuf;

use bevy::app::AppExit;
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Res, ResMut};

use super::state::{HarnessState, ScenarioTime, fail_at_deadline};
use crate::harness::{
    FrameSampleStats, Identity, Pacing, PerfResolution, PerfRun, ScenarioMode, TimedEvent, report,
};

/// How many frames the run settles after the last beat capture before closing.
const SETTLE_FRAMES: u64 = 2;

/// Close the run: a recorded failure exits nonzero immediately (no settle
/// window). On the lanes with beats (capture and calibration), the
/// `max_frames` deadline with beats still uncaptured records that failure
/// and exits nonzero in the same pass, and otherwise every beat must be
/// captured to disk plus a two-frame settle before the report is written.
/// On the perf lane the report waits for the sample window to fill instead
/// (the deadline scan does not apply: a perf scenario has no beats to
/// miss). The close checkpoint carries the final scenario time, so the
/// report artifact itself records the fixed-step contract the run drove.
/// Then the report is written and `AppExit::Success` requested (nonzero on
/// a recorded failure).
pub(super) fn finish_scan(
    mut state: ResMut<HarnessState>,
    scenario_time: Res<ScenarioTime>,
    mut exits: MessageWriter<AppExit>,
) {
    if state.done {
        return;
    }
    if state.scenario.mode != ScenarioMode::Perf {
        fail_at_deadline(&mut state);
    }
    let failed = state.failed.clone();
    if failed.is_none() && !run_complete(&state) {
        return;
    }
    let elapsed = scenario_time.into_inner().elapsed_secs();
    state
        .checkpoints
        .push(format!("closed at scenario time {elapsed:.6}s"));
    if failed.is_none() {
        let frame = state.frame;
        state.events.push(TimedEvent::Complete { frame });
    }
    let perf_run = perf_report_run(&state);
    let path = write_report(&state, perf_run);
    println!("REPORT {}", path.display());
    exits.write(if failed.is_some() {
        exit_failure()
    } else {
        AppExit::Success
    });
    state.done = true;
}

/// The lane's completion test: the perf lane wants the sample window full;
/// the lanes with beats want every beat's PNG on disk and the settle window
/// after the last capture to have passed (calibration and lifecycle behave
/// exactly like the capture lane: their beats are the pinned moments).
fn run_complete(state: &HarnessState) -> bool {
    match state.scenario.mode {
        ScenarioMode::Perf => state.sampler.is_complete(),
        ScenarioMode::Capture | ScenarioMode::Calibration | ScenarioMode::Lifecycle => {
            state.all_beats_captured() && state.frame >= state.last_beat_frame + SETTLE_FRAMES
        }
    }
}

/// The report's perf section for a perf run (`None` on the capture lane).
/// The resolution is the run's actual capture-target extent; the pacing is
/// what the scenario told the window to use.
fn perf_report_run(state: &HarnessState) -> Option<PerfRun> {
    if state.scenario.mode != ScenarioMode::Perf {
        return None;
    }
    let window_stats = FrameSampleStats::from_samples(state.sampler.samples_ms())?;
    Some(PerfRun {
        warmup_frames: state.scenario.warmup_frames,
        sample_frames: state.scenario.sample_frames,
        presentation: state.scenario.pacing.unwrap_or(Pacing::FixedVsync),
        resolution: PerfResolution::new(super::CAPTURE_W, super::CAPTURE_H),
        samples_ms: state.sampler.samples_ms().to_vec(),
        stats: window_stats,
    })
}

/// Serialize and write `report.json` into the run directory; returns its path.
/// Panics when the report cannot be written: the runner treats a missing or
/// unparsable report as a failed run either way.
fn write_report(state: &HarnessState, perf_run: Option<PerfRun>) -> PathBuf {
    if let Err(err) = std::fs::create_dir_all(&state.out_dir) {
        panic!("cannot create run dir {}: {err}", state.out_dir.display());
    }
    let identity = Identity {
        app_hash: app_hash(),
        scenario_hash: scenario_hash(),
        config_hash: state.config_hash.clone(),
    };
    // Capture completion is asynchronous (a beat's readback lands one or more
    // frames after the frame it captured), so `state.events` is in wall-clock
    // completion order, which two identical runs can differ in. The report is
    // written in the protocol's canonical order instead.
    let mut events = state.events.clone();
    report::sort_events(&mut events);
    let report = report::Report {
        protocol_version: crate::harness::PROTOCOL_VERSION,
        scenario: state.scenario.name.clone(),
        seed: state.scenario.seed,
        events,
        checkpoints: state.checkpoints.clone(),
        frame_stats: crate::harness::FrameStats::default(),
        beats: state.beats.clone(),
        perf: perf_run,
        identity,
    };
    let text = report::report_to_json(&report).expect("report json");
    let path = state.out_dir.join("report.json");
    std::fs::write(&path, text).expect("write report");
    path
}

/// The nonzero `AppExit` used when the scenario failed.
fn exit_failure() -> AppExit {
    AppExit::Error(NonZeroU8::new(1).expect("one is nonzero"))
}

fn app_hash() -> String {
    std::env::var("GONE_APP_HASH").unwrap_or_default()
}

fn scenario_hash() -> String {
    std::env::var("GONE_SCENARIO_HASH").unwrap_or_default()
}
