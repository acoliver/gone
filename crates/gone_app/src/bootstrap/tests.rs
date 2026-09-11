//! Unit tests for the harness run state and its gates: beat request/capture
//! accounting, readiness gating, the canary present gate, capture-lane
//! serialization, immediate failure recording, run-mode selection from the
//! environment, and the canary onscreen-capture gate. The gameplay-lane
//! protocol tests (the readiness barrier, the post-tick capture contract, the
//! latency invariant) live in `gameplay_tests`. The accounting methods under
//! test are pure state transitions, so no renderer is involved; only the
//! save-failure test touches disk (into the OS temp dir).

use bevy::asset::RenderAssetUsages;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

use super::capture::{capture_proves_present, save_capture};
use super::state::{
    CaptureRequest, HarnessState, PRESENT_BUDGET_FRAMES, PerfSampler, PresentGate, Readiness,
    RunMode, drive_allowed, fail_at_deadline, fail_scenario, onscreen_capture_due,
    onscreen_file_name, select_run_mode,
};
use crate::harness::{
    Beat, InputAdapter, Key, Scenario, ScriptedAction, TICKS_PER_SECOND, TimedEvent,
};

/// A harness state over a scenario with the named beats, no actions, and a
/// scratch output directory (the accounting methods under test never touch
/// disk; only the save-failure test writes, into the OS temp dir).
fn state_with_beats(beats: &[(&str, u64)]) -> HarnessState {
    HarnessState::new(
        Scenario {
            name: "accounting-test".to_owned(),
            beats: beats
                .iter()
                .map(|(name, tick)| Beat::new(name, *tick))
                .collect(),
            ..Scenario::default()
        },
        std::env::temp_dir(),
        String::new(),
        InputAdapter::new(TICKS_PER_SECOND),
    )
}

/// The `request_beat_captures` half of an update pass: pin and queue the
/// next due beat's capture from the post-tick state, unless one is already
/// in flight. The pin names the tick this pass just drove, exactly as the
/// real system pins `state.tick - 1` after the drive half ran.
fn spawn_due_capture(state: &mut HarnessState) {
    if state.capture_in_flight.is_some() {
        return;
    }
    let Some(beat) = state.next_due_beat() else {
        return;
    };
    let (tick, frame) = (state.tick - 1, state.frame - 1);
    let (_, entry) = state.pin_next_beat(tick, frame);
    state.capture_in_flight = Some(CaptureRequest {
        name: beat.name,
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

/// The `drive_ticks` half of an update pass: one tick and one frame when
/// [`drive_allowed`] opens the clock, nothing while it holds the clock (a
/// readback in flight). The same gate the real drive system consults.
fn drive_step(state: &mut HarnessState, gate: &PresentGate) {
    if drive_allowed(Readiness::Ready, gate, state) {
        state.tick += 1;
        state.frame += 1;
    }
}

/// A full frame with the readback landing in the same pass (a fast readback):
/// land, drive one step under the real gate, then pin from the post-tick
/// state — the update order of the real chain halves.
fn update_pass(state: &mut HarnessState) {
    let gate = PresentGate::automatic();
    land_capture(state);
    drive_step(state, &gate);
    spawn_due_capture(state);
}

#[test]
fn captured_early_beat_does_not_skip_a_later_beat() {
    // Regression: the old code advanced the shared `beat_progress` counter
    // on both request and save, so after beat-a's capture the completion
    // scan saw "all beats done" and the app exited before beat-b's tick was
    // ever reached (smoke run failed with `missing beat beat-b`). The pass
    // count: ticks 0..=8 drive across the first nine passes, beat-b pins on
    // the ninth (its tick just drove), and its readback lands on the tenth.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    for _ in 0..=9 {
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
    state.tick = 3;
    state.frame = 3;
    spawn_due_capture(&mut state);
    assert_eq!(
        state.requested_beats, 1,
        "beat-a pins from the post-tick state of tick 2"
    );
    let a = &state.beats["beat-a"];
    assert_eq!((a.tick, a.frame), (2, 2), "the pin is the scripted tick");
    assert!(
        state.next_due_beat().is_none(),
        "beat-b is not due while only ticks 0..=2 have driven"
    );
    land_capture(&mut state);
    assert!(
        !state.all_beats_captured(),
        "capturing beat-a must not complete the run while beat-b is pending"
    );
}

#[test]
fn pins_alone_never_complete_the_run() {
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.tick = 3;
    state.frame = 3;
    spawn_due_capture(&mut state);
    land_capture(&mut state);
    state.tick = 9;
    state.frame = 9;
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
fn the_clock_holds_while_a_capture_is_in_flight() {
    // The capture freeze: beat-a's scripted tick (2) drives, the pass pins
    // beat-a from the post-tick state, and every later pass freezes — no
    // tick, no frame, no further pin — until the readback lands. Beat-b
    // (tick 3) cannot even drive its tick while the lane is busy, so when
    // the lane frees it pins exactly its scripted tick, and identical
    // scenarios pin identical (tick, frame) pairs no matter how long the
    // readback takes.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 3)]);
    let gate = PresentGate::automatic();
    for _ in 0..2 {
        update_pass(&mut state);
    }
    assert_eq!((state.tick, state.frame), (2, 2), "ticks 0 and 1 drove");
    assert_eq!(
        state.requested_beats, 0,
        "beat-a is not due until its tick has driven"
    );
    // The pass that drives tick 2 pins beat-a at the post-tick numbers.
    update_pass(&mut state);
    assert_eq!((state.tick, state.frame), (3, 3), "the pin update drives");
    assert_eq!(state.requested_beats, 1, "beat-a pinned after its tick");
    let a = &state.beats["beat-a"];
    assert_eq!((a.tick, a.frame), (2, 2), "the pin is the scripted tick");
    // Passes with the readback still in flight: the clock freezes at (3, 3)
    // and beat-b waits — its tick cannot drive while the lane is busy.
    for _ in 0..5 {
        spawn_due_capture(&mut state);
        drive_step(&mut state, &gate);
        assert_eq!(
            (state.tick, state.frame),
            (3, 3),
            "the scenario clock is frozen under a readback"
        );
        assert_eq!(state.requested_beats, 1, "beat-b waits for the lane");
    }
    // The readback lands between updates; tick 3 drives and beat-b pins at
    // its own scripted tick.
    land_capture(&mut state);
    update_pass(&mut state);
    let b = &state.beats["beat-b"];
    assert_eq!((b.tick, b.frame), (3, 3), "the pin is the scripted tick");
}

#[test]
fn drive_allowed_holds_while_a_capture_is_in_flight() {
    // The freeze is a drive_allowed conjunct like readiness and the present
    // gate: one place, consulted by every driving system. Under an in-flight
    // readback nothing drives — the beat request is the post-drive half of
    // the chain, so there is no pin-update exception: the pinned tick has
    // already driven, and the clock holds until the readback lands.
    let mut state = state_with_beats(&[]);
    let gate = PresentGate::automatic();
    assert!(drive_allowed(Readiness::Ready, &gate, &state));
    state.capture_in_flight = Some(CaptureRequest {
        name: "beat-a".to_owned(),
        tick: 5,
        frame: 5,
        request_id: 1,
    });
    state.tick = 5;
    state.frame = 5;
    assert!(
        !drive_allowed(Readiness::Ready, &gate, &state),
        "the clock holds while a readback is in flight"
    );
    state.capture_in_flight = None;
    assert!(drive_allowed(Readiness::Ready, &gate, &state));
}

#[test]
fn drive_never_consumes_input_before_readiness() {
    // Regression (issue #15): drive_ticks used to run on the first update
    // and consumed tick-0 input before the readiness boundary. The gate
    // must refuse to drive until the renderer has presented, and stop on
    // completion or failure.
    let mut state = state_with_beats(&[]);
    state.adapter = InputAdapter::with_actions(
        vec![ScriptedAction::press(0, Key::Forward)],
        TICKS_PER_SECOND,
    );
    let gate = PresentGate::automatic();
    // While loading: no drive, so the adapter never steps and tick-0 input
    // stays queued for the post-boundary tick.
    assert!(!drive_allowed(Readiness::Loading, &gate, &state));
    if drive_allowed(Readiness::Loading, &gate, &state) {
        let _ = state.adapter.step();
    }
    assert_eq!(state.adapter.tick(), 0, "the adapter clock never moved");
    assert_eq!(state.events.len(), 0, "no input recorded before ready");
    // Ready: exactly one drive consumes exactly the tick-0 edge.
    assert!(drive_allowed(Readiness::Ready, &gate, &state));
    let step = state.adapter.step();
    assert_eq!(step.edges.len(), 1, "the queued tick-0 press survives");
    state.tick += 1;
    state.frame += 1;
    assert_eq!(state.tick, 1, "one tick advanced after ready");
    // Failure or completion closes the lane.
    state.failed = Some("beat `x` capture failed: boom".to_owned());
    assert!(!drive_allowed(Readiness::Ready, &gate, &state));
    state.failed = None;
    state.done = true;
    assert!(!drive_allowed(Readiness::Ready, &gate, &state));
}

#[test]
fn the_canary_gate_holds_the_drive_until_the_first_present() {
    // The canary's scenario clock may not start until the window's first
    // capturable frame: with presents unproven the gate refuses, declined
    // frames only count, and the first rendered probe capture releases it.
    let state = state_with_beats(&[]);
    let mut gate = PresentGate::canary();
    assert!(!gate.presenting());
    assert!(!drive_allowed(Readiness::Ready, &gate, &state));
    gate.record_declined();
    assert_eq!(gate.declined_frames(), 1);
    assert!(
        gate.awaiting_first_present(),
        "one decline is not the budget"
    );
    assert!(!drive_allowed(Readiness::Ready, &gate, &state));
    gate.record_presented();
    assert!(gate.presenting(), "the first present is sticky");
    assert!(!gate.awaiting_first_present());
    assert!(drive_allowed(Readiness::Ready, &gate, &state));
}

#[test]
fn the_probe_lane_issues_one_probe_at_a_time() {
    // The probe lane's single slot, the beat lane's one-in-flight
    // discipline: a request takes the gate's slot, a further request waits
    // while it is out, and only the verdict — declined or rendered — frees
    // it. Two probes in flight would double-count declined frames against
    // the present budget.
    let mut gate = PresentGate::canary();
    assert!(!gate.probe_in_flight(), "a fresh gate has no probe out");
    gate.request_probe();
    assert!(gate.probe_in_flight(), "the request takes the slot");
    gate.record_declined();
    assert!(
        !gate.probe_in_flight(),
        "the declined verdict frees the slot"
    );
    gate.request_probe();
    gate.record_presented();
    assert!(
        !gate.probe_in_flight(),
        "the rendered verdict frees the slot too"
    );
    assert!(gate.presenting(), "the first present is sticky");
}

#[test]
fn headless_gate_never_holds_the_drive() {
    // No window, no presents to wait for: the gate starts satisfied and
    // only the readiness conjunct can refuse the drive.
    let state = state_with_beats(&[]);
    let gate = PresentGate::automatic();
    assert!(gate.presenting());
    assert!(drive_allowed(Readiness::Ready, &gate, &state));
    assert!(!drive_allowed(Readiness::Loading, &gate, &state));
}

#[test]
fn exhausting_the_present_budget_closes_the_probe_window() {
    // Declined frames count one by one; at the budget the probe window
    // closes so the run fails by name instead of waiting on the compositor
    // forever. Exhaustion is a failure state, never a present.
    let mut gate = PresentGate::canary();
    for _ in 0..PRESENT_BUDGET_FRAMES - 1 {
        gate.record_declined();
        assert!(gate.awaiting_first_present(), "still within the budget");
    }
    gate.record_declined();
    assert!(!gate.awaiting_first_present(), "the budget is exhausted");
    assert!(!gate.presenting());
    assert_eq!(gate.declined_frames(), PRESENT_BUDGET_FRAMES);
}

#[test]
fn a_zeroed_capture_never_proves_a_present_and_a_rendered_one_does() {
    // The zeroed capture is bevy's skip signature on a frame whose drawable
    // the compositor declined; a presented frame always renders a nonzero
    // byte (the canary cameras clear to a nonzero color before any content).
    let zeroed = test_image();
    assert!(!capture_proves_present(&zeroed));
    let mut rendered = test_image();
    rendered.data = Some(vec![0, 0, 0, 255]);
    assert!(capture_proves_present(&rendered));
}

#[test]
fn captures_are_serialized_one_in_flight() {
    // bevy captures at most one screenshot per render target per frame, so
    // the runner-side queue must hand out one request at a time.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    state.tick = 3;
    state.frame = 3;
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
    state.tick = 9;
    state.frame = 9;
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

#[test]
fn without_harness_env_the_app_is_the_normal_game() {
    // No harness vars: the plain windowed game, byte-for-byte unchanged.
    assert_eq!(select_run_mode(None, None), Ok(RunMode::Normal));
    // An empty value counts as unset (the pre-5a `== "1"` check treated it
    // as off).
    assert_eq!(select_run_mode(Some(""), None), Ok(RunMode::Normal));
    assert_eq!(select_run_mode(Some(""), Some("")), Ok(RunMode::Normal));
}

#[test]
fn harness_env_defaults_to_headless() {
    // The default harness lane has no window: offscreen capture only, no
    // onscreen capture, no onscreen file.
    assert_eq!(select_run_mode(Some("1"), None), Ok(RunMode::Headless));
    assert_eq!(select_run_mode(Some("1"), Some("")), Ok(RunMode::Headless));
}

#[test]
fn render_check_selects_the_canary() {
    assert_eq!(select_run_mode(Some("1"), Some("1")), Ok(RunMode::Canary));
}

#[test]
fn unknown_harness_env_values_fail_loudly() {
    let err = select_run_mode(Some("0"), None).expect_err("GONE_HARNESS=0 is not a mode");
    assert!(err.contains("GONE_HARNESS"), "names the variable: {err}");
    assert!(err.contains('0'), "carries the value: {err}");
}

#[test]
fn unknown_render_check_values_fail_loudly() {
    let err =
        select_run_mode(Some("1"), Some("yes")).expect_err("GONE_RENDER_CHECK=yes is not a mode");
    assert!(
        err.contains("GONE_RENDER_CHECK"),
        "names the variable: {err}"
    );
    assert!(err.contains("yes"), "carries the value: {err}");
}

#[test]
fn render_check_without_harness_fails_loudly() {
    // A canary run is a harness run; a dangling GONE_RENDER_CHECK is a
    // misconfiguration, not a mode to fall back from.
    let err = select_run_mode(None, Some("1")).expect_err("canary requires harness mode");
    assert!(
        err.contains("GONE_HARNESS"),
        "points at the missing variable: {err}"
    );
}

#[test]
fn onscreen_capture_saves_next_to_the_beat_png() {
    // Same run directory's beats/ folder, `.onscreen` infix before the
    // extension so the two files of a beat never collide.
    assert_eq!(onscreen_file_name("beat-a"), "beats/beat-a.onscreen.png");
}

#[test]
fn headless_mode_has_no_onscreen_capture_path() {
    // Whatever the beat schedule, headless never captures the (nonexistent)
    // window: no onscreen request, no onscreen file.
    assert!(!onscreen_capture_due(RunMode::Headless, true));
    assert!(!onscreen_capture_due(RunMode::Headless, false));
}

#[test]
fn canary_mode_captures_the_window_once_at_the_first_beat() {
    assert!(onscreen_capture_due(RunMode::Canary, true));
    assert!(
        !onscreen_capture_due(RunMode::Canary, false),
        "exactly one onscreen capture per run"
    );
    // The normal game never builds the harness plugin; the gate stays total.
    assert!(!onscreen_capture_due(RunMode::Normal, true));
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
