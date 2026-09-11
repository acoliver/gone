//! Unit tests for the harness run state and its gates: beat request/capture
//! accounting, readiness gating, the canary present gate, capture-lane
//! serialization, immediate failure recording, run-mode selection from the
//! environment, the canary onscreen-capture gate, and the gameplay readiness
//! barrier (a delayed required asset holds the clock until one announcement,
//! a failed one fails the run by name). The accounting methods under test
//! are pure state transitions, so no renderer is involved; only the
//! save-failure and barrier tests touch disk (into the OS temp dir).

use std::path::PathBuf;

use bevy::app::{App, AppExit, TaskPoolPlugin, Update};
use bevy::asset::{AssetApp, AssetPlugin, Assets, RenderAssetUsages};
use bevy::camera::Camera3d;
use bevy::ecs::message::Messages;
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::image::Image;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::render::view::screenshot::ScreenshotCaptured;
use gone_sim::WakePhase;

use super::gameplay::{
    GameCameraBound, advance_wake_at_readiness, poll_required_assets, retarget_gameplay_camera,
};
use super::save_capture;
use super::state::{
    CaptureRequest, HarnessState, PRESENT_BUDGET_FRAMES, PerfSampler, PresentGate, Readiness,
    RunMode, drive_allowed, fail_at_deadline, fail_scenario, onscreen_capture_due,
    onscreen_file_name, select_run_mode,
};
use super::{
    CaptureTarget, ChipSprite, ChipTexture, drive_ticks, finish_scan, on_screenshot_captured,
    readiness_boundary, request_readiness_proof,
};
use crate::harness::{Beat, Content, InputAdapter, Key, Scenario, ScriptedAction, TimedEvent};
use crate::player::{GameplayInput, PlayerPitch};
use crate::readiness::{AssetLoad, GameAssets};
use crate::scene::SimWakePhase;

/// The ledger name of today's only required game asset (the post chain's
/// metering mask), as the failure report must carry it.
const MASK: &str = crate::post::MASK_ASSET_PATH;

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
        InputAdapter::new(),
    )
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
/// pin, land, then drive one step under the real gate.
fn update_pass(state: &mut HarnessState) {
    let gate = PresentGate::automatic();
    spawn_due_capture(state);
    land_capture(state);
    drive_step(state, &gate);
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
fn the_clock_holds_while_a_capture_is_in_flight() {
    // The capture freeze: beat-b's scripted tick (3) arrives while beat-a's
    // readback is still in flight, so the clock holds instead of passing the
    // beat's tick. The pin update's own drive still runs (it paints the
    // pinned numbers); every later step freezes. After the landing beat-b
    // pins exactly its scripted tick, so identical scenarios pin identical
    // (tick, frame) pairs no matter how long the readback takes.
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 3)]);
    state.tick = 2;
    state.frame = 2;
    spawn_due_capture(&mut state);
    assert_eq!(state.requested_beats, 1, "beat-a pinned at tick 2");
    // The pin update's own drive step: it paints the pinned pair and
    // advances the clock to (3, 3).
    let gate = PresentGate::automatic();
    drive_step(&mut state, &gate);
    assert_eq!((state.tick, state.frame), (3, 3), "the pin update drives");
    // Passes with the readback still in flight: the clock freezes at
    // (3, 3) and beat-b waits for the lane.
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
    // The readback lands between updates; the lane frees and beat-b is due
    // at tick 3, so the next pass pins its scripted tick.
    land_capture(&mut state);
    spawn_due_capture(&mut state);
    let b = &state.beats["beat-b"];
    assert_eq!((b.tick, b.frame), (3, 3), "the pin is the scripted tick");
}

/// One simulated capture-lane run over a two-beat scenario, driven to
/// completion: the pinning, readback, and drive halves run exactly as the
/// real chain does, and each readback lands `landing_delay` passes after its
/// request (the readback latency the observer sees). Returns the drive
/// event stream and the beat pins, so the latency proof can compare a fast
/// lane against a slow one at the accounting layer.
fn simulated_run(landing_delay: u64) -> (Vec<TimedEvent>, Vec<(u64, u64)>) {
    let mut state = state_with_beats(&[("beat-a", 2), ("beat-b", 8)]);
    let gate = PresentGate::automatic();
    let mut events = Vec::new();
    let mut pins = Vec::new();
    let mut flight_remaining: u64 = 0;
    for _ in 0..200 {
        if state.capture_in_flight.is_none()
            && let Some(beat) = state.next_due_beat()
        {
            let (tick, frame) = (state.tick, state.frame);
            let (_, entry) = state.pin_next_beat(tick, frame);
            pins.push((entry.tick, entry.frame));
            state.capture_in_flight = Some(CaptureRequest {
                name: beat.name,
                tick,
                frame,
                request_id: entry.request_id,
            });
            flight_remaining = landing_delay;
        }
        if flight_remaining > 0 {
            flight_remaining -= 1;
            if flight_remaining == 0 {
                land_capture(&mut state);
            }
        }
        if drive_allowed(Readiness::Ready, &gate, &state) {
            events.push(TimedEvent::Input {
                tick: state.tick,
                frame: state.frame,
                what: format!("tick {}", state.tick),
            });
            state.tick += 1;
            state.frame += 1;
        }
        if state.all_beats_captured() && state.frame >= state.last_beat_frame + 2 {
            break;
        }
    }
    (events, pins)
}

#[test]
fn identical_scenarios_report_identically_regardless_of_readback_latency() {
    // The latency proof at the accounting layer: a lane whose readbacks land
    // the pass after their request and a lane whose readbacks land five
    // passes late run the same scenario, and both produce the same beat pins
    // and the same drive event stream. The slow lane only spends more wall
    // time; nothing in its report moves.
    let (fast_events, fast_pins) = simulated_run(1);
    let (slow_events, slow_pins) = simulated_run(5);
    assert_eq!(fast_pins, slow_pins, "both lanes pin the scripted ticks");
    assert_eq!(
        fast_pins,
        vec![(2, 2), (8, 8)],
        "the pins are the beats' own ticks"
    );
    assert_eq!(
        fast_events, slow_events,
        "the drive event stream carries no latency footprint"
    );
    // Both lanes run to completion: beats at ticks 2 and 8, the settle window
    // ending the run at frame 10, so the drive stream is ticks 0..=9.
    assert_eq!(fast_events.len(), 10);
}

#[test]
fn drive_allowed_holds_while_a_capture_is_in_flight() {
    // The freeze is a drive_allowed conjunct like readiness and the present
    // gate: one place, consulted by every driving system. Under an in-flight
    // readback the only drive step it permits is the pin update's own (the
    // counters still equal the pinned pair); once the counters have moved
    // past it, the clock holds.
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
        drive_allowed(Readiness::Ready, &gate, &state),
        "the pin update's own drive paints the pinned numbers"
    );
    state.tick = 6;
    state.frame = 6;
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
    state.adapter = InputAdapter::with_actions(vec![ScriptedAction::press(0, Key::Forward)]);
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
    assert!(!super::capture_proves_present(&zeroed));
    let mut rendered = test_image();
    rendered.data = Some(vec![0, 0, 0, 255]);
    assert!(super::capture_proves_present(&rendered));
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

/// A scratch run directory unique per test invocation, so the readiness
/// proof, the report, and any failure report never collide across tests or
/// across runs of the suite.
fn barrier_out_dir(tag: &str) -> PathBuf {
    std::env::temp_dir().join(format!("gone-barrier-{}-{tag}", std::process::id()))
}

/// The headless gameplay-lane app the barrier tests run: the real protocol
/// chain (rig-camera retarget, required-asset poll, proof request, boundary,
/// wake override, drive, finish) over a gameplay scenario, with the injected
/// required-asset ledger the test controls. No renderer: the test plays the
/// render world by triggering the proof's `ScreenshotCaptured` by hand.
fn gameplay_barrier_app(assets: GameAssets, actions: Vec<ScriptedAction>, tag: &str) -> App {
    let mut app = App::new();
    app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
    app.init_asset::<Image>();
    let target = {
        let mut images = app.world_mut().resource_mut::<Assets<Image>>();
        images.add(test_image())
    };
    app.init_resource::<Readiness>();
    app.insert_resource(PresentGate::automatic());
    app.insert_resource(RunMode::Headless);
    app.insert_resource(ChipTexture::default());
    app.insert_resource(ChipSprite::default());
    app.insert_resource(CaptureTarget(Some(target)));
    app.insert_resource(GameCameraBound::default());
    app.insert_resource(SimWakePhase::new(WakePhase::Waking));
    app.insert_resource(assets);
    app.insert_resource(GameplayInput::default());
    let scenario = Scenario {
        name: "gameplay-barrier".to_owned(),
        content: Content::Gameplay,
        actions,
        ..Scenario::default()
    };
    let adapter = InputAdapter::with_actions(scenario.actions.clone());
    app.insert_resource(HarnessState::new(
        scenario,
        barrier_out_dir(tag),
        String::new(),
        adapter,
    ));
    // The rig camera the retarget binds into the capture target on the first
    // update: the barrier's rendered-game-frame leg.
    app.world_mut().spawn((Camera3d::default(), PlayerPitch));
    app.add_observer(on_screenshot_captured);
    app.add_message::<AppExit>();
    app.add_systems(
        Update,
        (
            retarget_gameplay_camera,
            poll_required_assets,
            request_readiness_proof,
            readiness_boundary,
            advance_wake_at_readiness,
            drive_ticks,
            finish_scan,
        )
            .chain(),
    );
    app
}

/// How many readiness announcements the run has recorded.
fn ready_announcements(state: &HarnessState) -> usize {
    state
        .events
        .iter()
        .filter(|event| matches!(event, TimedEvent::Ready { .. }))
        .count()
}

/// Run `frames` updates on the test app.
fn run_updates(app: &mut App, frames: usize) {
    for _ in 0..frames {
        app.update();
    }
}

/// Assert the loading hold: nothing has announced, the clock and the adapter
/// never moved, no input ran, and the wake machine sits at the authored
/// opening.
fn assert_loading_holds(app: &App) {
    let state = app.world().resource::<HarnessState>();
    assert!(!state.announced, "loading holds the boundary");
    assert_eq!(ready_announcements(state), 0, "nothing announces early");
    assert_eq!(state.tick, 0, "the scenario clock never started");
    assert_eq!(state.adapter.tick(), 0, "the adapter never stepped");
    assert!(
        state
            .events
            .iter()
            .all(|event| !matches!(event, TimedEvent::Input { .. })),
        "no input was consumed while loading"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the authored opening holds while the asset loads"
    );
}

/// Complete the delayed load and land the proof readback the way the render
/// world would: the poll opens the asset leg, the gate requests the proof,
/// and the test triggers its `ScreenshotCaptured`.
fn complete_load_and_land_proof(app: &mut App) {
    app.insert_resource(GameAssets::with_loads(&[(MASK, AssetLoad::Loaded)]));
    app.update();
    let proof_entity = app.world_mut().spawn_empty().id();
    app.world_mut().trigger(ScreenshotCaptured {
        entity: proof_entity,
        image: test_image(),
    });
}

/// Assert the boundary update: exactly one announcement, the held tick-0
/// look ran onto the shared plane in radians, and the wake override advanced.
fn assert_boundary_opened(app: &mut App) {
    {
        let state = app.world().resource::<HarnessState>();
        assert_eq!(
            ready_announcements(state),
            1,
            "exactly one readiness announcement"
        );
        assert_eq!(state.tick, 1, "tick 0 ran on the boundary update");
        assert_eq!(state.adapter.tick(), 1, "the held input ran exactly once");
        let inputs = state
            .events
            .iter()
            .filter(|event| matches!(event, TimedEvent::Input { .. }))
            .count();
        assert_eq!(inputs, 1, "exactly one input event: the tick-0 look");
    }
    let offered = app.world_mut().resource_mut::<GameplayInput>().take_look();
    let expected_yaw = 90.0_f32.to_radians();
    assert!(
        (offered.x - expected_yaw).abs() < f32::EPSILON,
        "the scripted look reached the shared plane in radians: {offered:?}"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the wake override advanced at the boundary"
    );
}

#[test]
fn a_delayed_required_asset_holds_the_clock_until_one_ready_announcement() {
    // The barrier end to end on the gameplay lane: while the required ledger
    // reports pending, nothing runs (no tick, no adapter step, no input, no
    // wake advance, no announcement). Once the ledger reports loaded and the
    // proof readback lands, the boundary announces exactly once and the held
    // tick-0 look runs on that same update, offered onto the shared input
    // plane, with the wake override firing exactly once behind it.
    let mut app = gameplay_barrier_app(
        GameAssets::with_loads(&[(MASK, AssetLoad::Pending)]),
        vec![ScriptedAction::look(0, 90.0, 0.0)],
        "delayed-asset",
    );
    run_updates(&mut app, 3);
    assert_loading_holds(&app);

    complete_load_and_land_proof(&mut app);
    app.update();
    assert_boundary_opened(&mut app);

    // The announcement never repeats, and the completed run then exits
    // cleanly through the report path (no beats, the settle window passed).
    app.update();
    {
        let state = app.world().resource::<HarnessState>();
        assert_eq!(ready_announcements(state), 1, "still exactly one");
        assert_eq!(state.tick, 2, "the clock runs normally after the boundary");
    }
    let exits = app.world().resource::<Messages<AppExit>>();
    assert_eq!(
        exits
            .iter_current_update_messages()
            .filter(|exit| matches!(exit, AppExit::Success))
            .count(),
        1,
        "the completed gameplay run exits cleanly"
    );
    app.update();
    let state = app.world().resource::<HarnessState>();
    assert_eq!(ready_announcements(state), 1, "never a second announcement");
}

#[test]
fn a_failed_required_asset_fails_the_gameplay_run_naming_the_asset() {
    // Fail fast on the gameplay lane: the first poll records the failure
    // naming the asset and the underlying error, the run never announces
    // readiness, never drives a tick or consumes input, never advances the
    // wake, and exits nonzero through the report path. The verdict is
    // sticky: a later update neither recovers nor drives.
    let mut app = gameplay_barrier_app(
        GameAssets::with_loads(&[(MASK, AssetLoad::Failed("missing file".to_owned()))]),
        vec![ScriptedAction::look(0, 90.0, 0.0)],
        "failed-asset",
    );

    app.update();
    {
        let state = app.world().resource::<HarnessState>();
        let what = state
            .failed
            .as_deref()
            .expect("the failed asset fails the run");
        assert!(what.contains(MASK), "the failure names the asset: {what}");
        assert!(
            what.contains("missing file"),
            "the failure names the error: {what}"
        );
        assert!(!state.announced, "a failed run never announces readiness");
        assert_eq!(ready_announcements(state), 0);
        assert_eq!(state.adapter.tick(), 0, "no input was consumed");
        assert_eq!(
            state
                .events
                .iter()
                .filter(|event| matches!(event, TimedEvent::Failure { .. }))
                .count(),
            1,
            "the failure is recorded exactly once"
        );
    }
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the wake never advances on a failed run"
    );
    let exits = app.world().resource::<Messages<AppExit>>();
    assert_eq!(
        exits
            .iter_current_update_messages()
            .filter(|exit| matches!(exit, AppExit::Error(_)))
            .count(),
        1,
        "the failed gameplay run exits nonzero"
    );

    // The failure is sticky: a later update neither recovers nor drives.
    app.update();
    let state = app.world().resource::<HarnessState>();
    assert_eq!(state.adapter.tick(), 0, "still no input");
    assert_eq!(ready_announcements(state), 0, "still no announcement");
}
