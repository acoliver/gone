//! Unit tests for the harness run state and its gates: beat request/capture
//! accounting, readiness gating, capture-lane serialization, and immediate
//! failure recording. The accounting methods under test are pure state
//! transitions, so no renderer is involved; only the save-failure test touches
//! disk (into the OS temp dir).

use std::collections::{BTreeMap, BTreeSet};

use bevy::asset::RenderAssetUsages;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

use super::save_capture;
use super::state::{
    CaptureRequest, HarnessState, PerfSampler, Readiness, drive_allowed, fail_at_deadline,
    fail_scenario,
};
use crate::harness::{Beat, InputAdapter, Key, Scenario, ScriptedAction, TimedEvent};

/// A harness state over a scenario with the named beats, no actions, and a
/// scratch output directory (the accounting methods under test never touch
/// disk; only the save-failure test writes, into the OS temp dir).
fn state_with_beats(beats: &[(&str, u64)]) -> HarnessState {
    HarnessState {
        scenario: Scenario {
            name: "accounting-test".to_owned(),
            beats: beats
                .iter()
                .map(|(name, tick)| Beat::new(name, *tick))
                .collect(),
            ..Scenario::default()
        },
        out_dir: std::env::temp_dir(),
        config_hash: String::new(),
        tick: 0,
        frame: 0,
        announced: false,
        adapter: InputAdapter::new(),
        events: Vec::new(),
        checkpoints: Vec::new(),
        beats: BTreeMap::new(),
        next_request_id: 1,
        last_beat_frame: 0,
        requested_beats: 0,
        captured_beats: BTreeSet::new(),
        capture_in_flight: None,
        done: false,
        failed: None,
        sampler: PerfSampler::new(0, 0),
    }
}

/// The `request_beat_captures` half of an update pass: pin and queue the
/// next due beat's capture, unless one is already in flight.
fn spawn_due_capture(state: &mut HarnessState) {
    if state.capture_in_flight.is_some() {
        return;
    }
    if state.next_due_beat().is_none() {
        return;
    }
    let (tick, frame) = (state.tick, state.frame);
    let (name, entry) = state.pin_next_beat(tick, frame);
    state.capture_in_flight = Some(CaptureRequest {
        name,
        tick,
        frame,
        request_id: entry.request_id,
    });
}

/// The `on_screenshot_captured` half: the in-flight capture lands and is
/// recorded against the numbers it was pinned with.
fn land_capture(state: &mut HarnessState) {
    if let Some(request) = state.capture_in_flight.take() {
        state.mark_captured(
            &request.name,
            request.tick,
            request.frame,
            request.request_id,
        );
    }
}

/// A full frame with the readback landing in the same pass (the real app's
/// readback lands one to two frames later; the accounting is identical).
fn update_pass(state: &mut HarnessState) {
    spawn_due_capture(state);
    land_capture(state);
    state.tick += 1;
    state.frame += 1;
}

#[test]
fn captured_early_beat_does_not_skip_a_later_beat() {
    // Regression: the old code advanced the shared `beat_progress` counter
    // on both request and save, so after beat-a's capture the completion
    // scan saw "all beats done" and the app exited before beat-b's tick was
    // ever reached (smoke run failed with `missing beat beat-b`).
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    for _ in 0..=8 {
        update_pass(&mut state);
    }
    assert!(
        state.captured_beats.contains("beat-a"),
        "beat-a must be captured"
    );
    assert!(
        state.captured_beats.contains("beat-b"),
        "beat-b must be requested and captured; capturing beat-a must not \
         advance the request cursor"
    );
    assert!(state.all_beats_captured());
    assert_eq!(
        state.checkpoints,
        vec!["beat beat-a captured", "beat beat-b captured"]
    );
}

#[test]
fn manifest_binds_each_beat_to_its_own_tick() {
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    for _ in 0..=8 {
        update_pass(&mut state);
    }
    let a = &state.beats["beat-a"];
    assert_eq!(a.tick, 2);
    assert_eq!(a.frame, 2);
    assert_eq!(a.request_id, 1);
    let b = &state.beats["beat-b"];
    assert_eq!(b.tick, 8);
    assert_eq!(b.frame, 8);
    assert_eq!(b.request_id, 2);
}

#[test]
fn capturing_the_first_beat_keeps_the_run_incomplete() {
    // The exact old-bug condition: beat-a requested and captured at tick 2
    // while beat-b (tick 8) is still pending must not satisfy completion.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.tick = 2;
    state.frame = 2;
    spawn_due_capture(&mut state);
    assert_eq!(
        state.requested_beats, 1,
        "beat-b must stay unrequested at tick 2"
    );
    assert!(
        state.next_due_beat().is_none(),
        "beat-b is not due at tick 2"
    );
    land_capture(&mut state);
    assert!(
        !state.all_beats_captured(),
        "capturing beat-a must not complete the run while beat-b is pending"
    );
    assert!(state.next_due_beat().is_none(), "nothing else is due yet");
}

#[test]
fn pins_alone_never_complete_the_run() {
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.tick = 8;
    state.frame = 8;
    spawn_due_capture(&mut state);
    land_capture(&mut state);
    spawn_due_capture(&mut state);
    assert_eq!(state.requested_beats, 2, "both beats were pinned");
    assert!(
        !state.all_beats_captured(),
        "a request is not a capture; completion waits for written files"
    );
    land_capture(&mut state);
    assert!(state.all_beats_captured());
}

#[test]
fn entry_pins_the_frame_the_capture_renders_even_when_spawn_lags_the_tick() {
    // beat-b's tick arrives while beat-a's readback is still in flight; the
    // pin waits and lands on the frame actually rendered, so the PNG always
    // decodes to exactly the report's numbers.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 3)]);
    state.tick = 2;
    state.frame = 2;
    spawn_due_capture(&mut state);
    assert_eq!(state.beats["beat-a"].frame, 2);
    state.tick = 3;
    state.frame = 3;
    spawn_due_capture(&mut state);
    assert_eq!(state.requested_beats, 1, "the lane is still busy");
    state.tick = 5;
    state.frame = 5;
    land_capture(&mut state);
    spawn_due_capture(&mut state);
    let b = &state.beats["beat-b"];
    assert_eq!(
        (b.tick, b.frame),
        (5, 5),
        "the pin names the rendered frame, not the scenario tick"
    );
    land_capture(&mut state);
    assert!(state.all_beats_captured());
}

#[test]
fn drive_never_consumes_input_before_readiness() {
    // Regression (issue #15): drive_ticks used to run on the first update
    // and consumed tick-0 input before the readiness boundary. The gate
    // must refuse to drive until the renderer has presented, and stop on
    // completion or failure.
    let mut state = state_with_beats(&[]);
    state.adapter = InputAdapter::with_actions(vec![ScriptedAction::press(0, Key::Forward)]);
    // While loading: no drive, so the adapter never steps and tick-0 input
    // stays queued for the post-boundary tick.
    assert!(!drive_allowed(Readiness::Loading, &state));
    if drive_allowed(Readiness::Loading, &state) {
        let _ = state.adapter.step();
    }
    assert_eq!(state.adapter.tick(), 0, "the adapter clock never moved");
    assert_eq!(state.events.len(), 0, "no input recorded before ready");
    // Ready: exactly one drive consumes exactly the tick-0 edge.
    assert!(drive_allowed(Readiness::Ready, &state));
    let step = state.adapter.step();
    assert_eq!(step.edges.len(), 1, "the queued tick-0 press survives");
    state.tick += 1;
    state.frame += 1;
    assert_eq!(state.tick, 1, "one tick advanced after ready");
    // Failure or completion closes the lane.
    state.failed = Some("beat `x` capture failed: boom".to_owned());
    assert!(!drive_allowed(Readiness::Ready, &state));
    state.failed = None;
    state.done = true;
    assert!(!drive_allowed(Readiness::Ready, &state));
}

#[test]
fn captures_are_serialized_one_in_flight() {
    // bevy captures at most one screenshot per render target per frame, so
    // the runner-side queue must hand out one request at a time.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.tick = 2;
    state.frame = 2;
    spawn_due_capture(&mut state);
    let first = state.capture_in_flight.clone().expect("beat-a is due");
    assert_eq!(first.name, "beat-a");
    assert_eq!((first.tick, first.frame, first.request_id), (2, 2, 1));
    spawn_due_capture(&mut state);
    assert_eq!(
        state.requested_beats, 1,
        "nothing else pins while a capture is in flight"
    );
    land_capture(&mut state);
    assert!(state.capture_in_flight.is_none());
    state.tick = 8;
    state.frame = 8;
    spawn_due_capture(&mut state);
    let b = &state.beats["beat-b"];
    assert_eq!((b.tick, b.frame, b.request_id), (8, 8, 2));
}

#[test]
fn capture_save_failure_fails_the_scenario_immediately() {
    // Regression (issue #15): a failed save used to be retried every frame
    // until the runner timeout. Now the first error is terminal and lands
    // in the report as a Failure event naming the artifact.
    let mut state = state_with_beats(&[("beat-a", 0)]);
    // A regular file where the run directory should be forces the save to
    // fail immediately.
    let blocker = std::env::temp_dir().join(format!("gone-beat-block-{}", std::process::id()));
    std::fs::write(&blocker, b"not a directory").expect("write blocker file");
    state.out_dir = blocker.clone();
    spawn_due_capture(&mut state);
    let image = test_image();
    let err = save_capture(&state.out_dir, "beats/beat-a.png", &image)
        .expect_err("the blocked save must fail");
    assert!(
        err.contains("beats/beat-a.png"),
        "the error names the artifact: {err}"
    );
    fail_scenario(&mut state, format!("beat `beat-a` capture failed: {err}"));
    assert!(
        !state.all_beats_captured(),
        "a failed save is not a capture"
    );
    let what = state
        .events
        .iter()
        .find_map(|event| match event {
            TimedEvent::Failure { what, .. } => Some(what.clone()),
            _ => None,
        })
        .expect("the failure is recorded as a Failure event");
    assert!(
        what.contains("beat-a"),
        "the failure names the beat: {what}"
    );
    assert!(
        state.checkpoints.iter().any(|c| c.starts_with("failed: ")),
        "the failure lands in the checkpoints: {:?}",
        state.checkpoints
    );
    std::fs::remove_file(&blocker).expect("remove blocker file");
}

#[test]
fn only_the_first_failure_is_recorded() {
    let mut state = state_with_beats(&[]);
    fail_scenario(&mut state, "beat `a` capture failed: first".to_owned());
    fail_scenario(&mut state, "beat `b` capture failed: second".to_owned());
    let failures: Vec<_> = state
        .events
        .iter()
        .filter(|event| matches!(event, TimedEvent::Failure { .. }))
        .collect();
    assert_eq!(failures.len(), 1, "later failures do not overwrite");
    assert!(state.failed.as_deref().is_some_and(|f| f.contains("first")));
}

#[test]
fn max_frames_deadline_fails_the_run_naming_missing_beats() {
    // Regression: a beat scheduled past max_frames (tick 9000, max 60) hung
    // the app until the runner's timeout killed it. The deadline is the
    // deadline: reaching it with the beat uncaptured records the failure in
    // the runner's `missing beat` shape, and only once.
    let mut state = state_with_beats(&[("beat-never", 9000)]);
    state.scenario.max_frames = 60;
    for _ in 0..60 {
        state.tick += 1;
        state.frame += 1;
        fail_at_deadline(&mut state);
    }
    assert_eq!(state.frame, 60);
    let what = state
        .events
        .iter()
        .find_map(|event| match event {
            TimedEvent::Failure { what, .. } => Some(what.clone()),
            _ => None,
        })
        .expect("the deadline records a Failure event");
    assert!(
        what.contains("beat-never"),
        "the failure names the beat: {what}"
    );
    assert!(
        what.contains("9000"),
        "the failure carries the expected tick: {what}"
    );
    assert!(
        state.checkpoints.iter().any(|c| c.starts_with("failed: ")),
        "the failure lands in the checkpoints: {:?}",
        state.checkpoints
    );
    // Driving past the deadline records nothing further: one failure, once.
    state.tick += 1;
    state.frame += 1;
    fail_at_deadline(&mut state);
    let failures = state
        .events
        .iter()
        .filter(|event| matches!(event, TimedEvent::Failure { .. }))
        .count();
    assert_eq!(failures, 1, "the deadline fires exactly once");
    assert!(state.failed.is_some());
}

#[test]
fn max_frames_deadline_spares_captured_and_pre_deadline_runs() {
    // All beats captured before the deadline: the deadline stays silent so the
    // settle-then-succeed path is untouched. And a run below the deadline does
    // not fail early.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.scenario.max_frames = 60;
    for _ in 0..=8 {
        update_pass(&mut state);
        fail_at_deadline(&mut state);
    }
    assert!(
        state.failed.is_none(),
        "a fully captured run never deadline-fails"
    );
    let mut state = state_with_beats(&[("beat-never", 9000)]);
    state.scenario.max_frames = 60;
    state.tick = 59;
    state.frame = 59;
    fail_at_deadline(&mut state);
    assert!(state.failed.is_none(), "frame 59 of 60 is not the deadline");
}

/// A small RGBA capture-shaped image; only its existence matters here (the
/// conversion itself is covered by `crate::capture` tests).
fn test_image() -> bevy::image::Image {
    bevy::image::Image::new(
        Extent3d {
            width: 8,
            height: 8,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        vec![0; 8 * 8 * 4],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::MAIN_WORLD,
    )
}

/// The in-flight request type round-trips through its fields (used by both
/// the spawner and the observer).
#[test]
fn capture_request_binds_manifest_numbers() {
    let request = CaptureRequest {
        name: "beat-a".to_owned(),
        tick: 3,
        frame: 4,
        request_id: 9,
    };
    assert_eq!(request.tick, 3);
    assert_eq!(request.frame, 4);
    assert_eq!(request.request_id, 9);
}

#[test]
fn perf_sampler_skips_warmup_then_fills_the_window() {
    let mut sampler = PerfSampler::new(2, 3);
    sampler.record(99.0);
    sampler.record(98.0);
    assert!(sampler.samples_ms().is_empty(), "warmup is unrecorded");
    assert!(!sampler.is_complete());
    sampler.record(1.0);
    sampler.record(2.0);
    assert_eq!(sampler.samples_ms(), [1.0, 2.0]);
    assert!(!sampler.is_complete());
    sampler.record(3.0);
    assert_eq!(sampler.samples_ms(), [1.0, 2.0, 3.0]);
    assert!(sampler.is_complete());
    // A record past the target is ignored: completion ends the run that frame.
    sampler.record(4.0);
    assert_eq!(sampler.samples_ms(), [1.0, 2.0, 3.0]);
}

#[test]
fn perf_sampler_with_no_warmup_samples_from_the_first_frame() {
    let mut sampler = PerfSampler::new(0, 2);
    sampler.record(16.6);
    assert_eq!(sampler.samples_ms(), [16.6]);
    sampler.record(16.7);
    assert!(sampler.is_complete());
    assert_eq!(sampler.samples_ms(), [16.6, 16.7]);
}
