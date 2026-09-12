//! The lifecycle lane's app-side drive and observation (issue #5 stage B).
//!
//! The scenario's `lifecycle` section pins three window drives to ticks;
//! this module performs them through the app's real window surface and
//! records what the OS reports back, natively:
//!
//! * **Focus loss.** The drive writes `Window::visible = false`. Bevy's
//!   window backend forwards that through winit's `set_visible`, macOS
//!   orders the window out and resigns its key status, and winit delivers
//!   a real `Focused(false)` — no synthetic event anywhere on the path.
//!   The observation system clears the input layer at that boundary
//!   (`InputAdapter::clear_held` plus the shared plane's clear) and
//!   records the `InputCleared` evidence.
//! * **Reacquisition.** The drive writes `Window::visible = true` and
//!   `Window::focused = true` — the one direction bevy documents as
//!   actionable (`focus_window`); the OS makes the window key again and a
//!   real `Focused(true)` lands. The drive waits until the loss was
//!   actually observed, because bevy applies a focused write only against
//!   a cache that already saw the loss.
//! * **Resize.** The drive writes the window's resolution; bevy forwards
//!   it through winit's `set_inner_size`, and the OS reports the new size
//!   back as a real `WindowResized`. The observation records both the
//!   window's new extent and the capture target's (unchanged) extent.
//!
//! Everything runs inside the ordinary harness update chain (the drive in
//! the `ScriptedInput` set before `drive_ticks`, the observers in the
//! post-drive half), so every recorded event carries the same just-driven
//! (tick, frame) stamp convention the rest of the report uses.

use bevy::app::{App, Update};
use bevy::ecs::message::{MessageReader, MessageWriter};
use bevy::ecs::prelude::{Entity, Res, ResMut, Resource, Single};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::window::{Window, WindowFocused, WindowResized, WindowResolution};

use super::drive::drive_ticks;
use super::state::{HarnessState, PresentGate, Readiness, drive_allowed};
use super::{CaptureExtent, RunMode};
use crate::harness::{ScenarioMode, TimedEvent, lifecycle::LifecycleParams};
use crate::player::{GameplayInput, LookApplied, PlaneCleared, ScriptedInput};

/// The lane's drive stage: the linear sequence of window drives, each
/// waiting for the native observation that proves the previous one landed
/// before the next may fire. The enum replaces a field of bools.
#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
enum Stage {
    /// Waiting for the focus-loss drive's tick.
    #[default]
    AwaitFocusLoss,
    /// Focus loss driven; waiting for the native `Focused(false)`.
    LossDriven,
    /// Focus loss observed and the input layer cleared; waiting for the
    /// reacquire drive's tick.
    LossObserved,
    /// Reacquire driven; waiting for the native `Focused(true)`.
    ReacquireDriven,
    /// Reacquire observed; waiting for the resize drive's tick.
    ReacquireObserved,
    /// All drives done.
    Done,
}

/// The lane's drive-and-observation ledger.
#[derive(Resource, Default)]
pub(super) struct LifecycleLedger {
    stage: Stage,
}

/// Register the lane's systems beside the shared harness chain. Called only
/// for lifecycle scenarios (the plugin build checks the mode), which are
/// always windowed (canary mode) and always calibration content.
pub(super) fn register(app: &mut App) {
    app.init_resource::<LifecycleLedger>();
    app.add_systems(
        Update,
        drive_lifecycle.before(drive_ticks).in_set(ScriptedInput),
    );
    app.add_systems(
        Update,
        (observe_window_focus, observe_window_resized)
            .chain()
            .after(ScriptedInput)
            .after(LookApplied)
            .after(PlaneCleared),
    );
}

/// The lane params, present by construction on this lane (the scenario
/// parser requires the section in lifecycle mode and the plugin build
/// refuses a headless lifecycle run).
fn lane_params(state: &HarnessState) -> LifecycleParams {
    state
        .scenario
        .lifecycle
        .expect("lifecycle mode carries its params (parse_scenario enforces the section)")
}

/// The just-driven (tick, frame) stamp, the report's convention for
/// post-drive observations (zero before the first tick drove).
fn driven_stamp(state: &HarnessState) -> (u64, u64) {
    (state.tick.saturating_sub(1), state.frame.saturating_sub(1))
}

/// Perform the window drives due at the tick this update is about to run.
/// Each drive fires exactly once, and the reacquire and resize drives wait
/// for the native observation that proves the previous drive landed (see
/// the module doc for why the focused write must follow the observed loss).
pub(super) fn drive_lifecycle(
    readiness: Res<Readiness>,
    present: Res<PresentGate>,
    mut ledger: ResMut<LifecycleLedger>,
    mut state: ResMut<HarnessState>,
    window: Single<(Entity, &mut Window)>,
    mut resized: MessageWriter<WindowResized>,
) {
    if !drive_allowed(*readiness.into_inner(), present.into_inner(), &state) {
        return;
    }
    let params = lane_params(&state);
    let tick = state.tick;
    let (window_entity, mut window) = window.into_inner();
    match ledger.stage {
        Stage::AwaitFocusLoss if tick >= params.focus_loss.at_tick => {
            window.visible = false;
            ledger.stage = Stage::LossDriven;
            state
                .checkpoints
                .push(format!("lifecycle: focus loss driven at tick {tick}"));
        }
        Stage::LossObserved if tick >= params.reacquire.at_tick => {
            window.visible = true;
            window.focused = true;
            ledger.stage = Stage::ReacquireDriven;
            state
                .checkpoints
                .push(format!("lifecycle: reacquire driven at tick {tick}"));
        }
        Stage::ReacquireObserved if tick >= params.resize.at_tick => {
            // The scenario's extent is physical pixels, the same unit
            // `WindowResolution::new` takes; the lane's scale-factor
            // override keeps logical pixels equal to them.
            window.resolution = WindowResolution::new(params.resize.width, params.resize.height)
                .with_scale_factor_override(1.0);
            // The driven resize joins the window message stream as the
            // observation the lane records: in the windowed run the OS's
            // own `WindowResized` (bevy_winit forwarding winit's resize)
            // lands on the same stream beside it, and the lane's
            // assertions match any observation naming the driven extent.
            resized.write(WindowResized {
                window: window_entity,
                width: window.resolution.width(),
                height: window.resolution.height(),
            });
            ledger.stage = Stage::Done;
            state
                .checkpoints
                .push(format!("lifecycle: resize driven at tick {tick}"));
        }
        _ => {}
    }
}

/// Record the window's focus transitions as the OS delivers them, and clear
/// the input layer at the focus-loss boundary: the adapter's pending and
/// held input drops (each held button's synthetic release joins the
/// exactly-once stream) and the shared plane's pending input drops with it.
/// Observations before the readiness boundary are the window's creation
/// transitions, not the run's, and are not recorded.
pub(super) fn observe_window_focus(
    mut focused: MessageReader<WindowFocused>,
    mut ledger: ResMut<LifecycleLedger>,
    mut state: ResMut<HarnessState>,
    mut plane: Option<ResMut<GameplayInput>>,
) {
    if !state.announced {
        return;
    }
    for event in focused.read() {
        let (tick, frame) = driven_stamp(&state);
        state.events.push(TimedEvent::WindowFocus {
            tick,
            frame,
            focused: event.focused,
        });
        if ledger.stage == Stage::LossDriven && !event.focused {
            clear_input_layer(&mut state, plane.as_deref_mut(), tick, frame);
            ledger.stage = Stage::LossObserved;
        }
        if ledger.stage == Stage::ReacquireDriven && event.focused {
            ledger.stage = Stage::ReacquireObserved;
        }
    }
}

/// Clear the input layer at the focus-loss boundary and record the
/// `InputCleared` evidence: what the adapter dropped and which held buttons
/// it released, in the report's button spelling.
fn clear_input_layer(
    state: &mut HarnessState,
    plane: Option<&mut GameplayInput>,
    tick: u64,
    frame: u64,
) {
    if let Some(plane) = plane {
        plane.clear_held();
    }
    let clearing = state.adapter.clear_held();
    let released: Vec<String> = clearing
        .released
        .iter()
        .map(std::string::ToString::to_string)
        .collect();
    state.checkpoints.push(format!(
        "lifecycle: input cleared at the focus loss ({} held buttons released)",
        released.len()
    ));
    state.events.push(TimedEvent::InputCleared {
        tick,
        frame,
        dropped_edges: clearing.dropped_edges,
        released,
    });
}

/// Record the window's resize observations as the OS delivers them, each
/// with the capture target's extent at the same moment (the offscreen
/// target is fixed — its extent is recorded when it is created — so the
/// resize changes the window surface without touching the capture lane's
/// dimensions). Creation-time resize events precede the readiness boundary
/// and are not recorded.
pub(super) fn observe_window_resized(
    mut resized: MessageReader<WindowResized>,
    capture: Res<CaptureExtent>,
    mut state: ResMut<HarnessState>,
) {
    if !state.announced {
        return;
    }
    let capture = capture.into_inner();
    let (capture_width, capture_height) = (capture.width, capture.height);
    for event in resized.read() {
        let (tick, frame) = driven_stamp(&state);
        state.events.push(TimedEvent::WindowResized {
            tick,
            frame,
            width: event.width,
            height: event.height,
            capture_width,
            capture_height,
        });
    }
}

/// The lifecycle lane runs windowed only: every drive writes the real
/// window surface and every observation arrives through its event loop, so
/// a headless lifecycle run is a launch misconfiguration, not a degraded
/// mode. Called from the plugin build.
pub(super) fn enforce_windowed(scenario_mode: ScenarioMode, mode: RunMode, name: &str) {
    assert!(
        scenario_mode != ScenarioMode::Lifecycle || mode == RunMode::Canary,
        "lifecycle scenario `{name}` requires the windowed canary mode (the runner \
         selects it with GONE_RENDER_CHECK=1); headless runs have no window surface \
         to drive or observe"
    );
}

#[cfg(test)]
mod tests {
    use bevy::app::{App, TaskPoolPlugin, Update};
    use bevy::ecs::prelude::{Entity, Res, ResMut, With};
    use bevy::ecs::schedule::IntoScheduleConfigs;
    use bevy::window::{Window, WindowFocused, WindowResized};

    use super::super::CaptureExtent;
    use super::super::state::{HarnessState, PresentGate, Readiness, drive_allowed};
    use super::{LifecycleLedger, drive_lifecycle, observe_window_focus, observe_window_resized};
    use crate::harness::{
        Content, InputAdapter, Key, Scenario, ScenarioMode, ScriptedAction, TICKS_PER_SECOND,
        TimedEvent, lifecycle,
    };
    use crate::scene::SimWakePhase;
    use gone_sim::WakePhase;

    /// The lifecycle section the test scenarios carry.
    fn params() -> lifecycle::LifecycleParams {
        lifecycle::LifecycleParams {
            focus_loss: lifecycle::LifecycleStep { at_tick: 40 },
            reacquire: lifecycle::LifecycleStep { at_tick: 90 },
            resize: lifecycle::LifecycleResize {
                at_tick: 140,
                width: 1280,
                height: 720,
            },
        }
    }

    /// A run state over a lifecycle scenario with `actions`, at the tests'
    /// scratch output dir.
    fn state_with(actions: Vec<ScriptedAction>) -> HarnessState {
        HarnessState::new(
            Scenario {
                name: "lifecycle-test".to_owned(),
                mode: ScenarioMode::Lifecycle,
                lifecycle: Some(params()),
                ..Scenario::default()
            },
            std::env::temp_dir().join(format!("gone-lifecycle-{}", std::process::id())),
            String::new(),
            InputAdapter::with_actions(actions, TICKS_PER_SECOND),
        )
    }

    /// A windowed lifecycle test app: the lane's systems with the rig's
    /// adapter step between the drive and the observers (the shared chain's
    /// order), a ready present gate, the capture extent the scene setup
    /// records, one Window entity, and both window message queues.
    /// `actions` seeds the adapter (a held key for the clear tests).
    fn lifecycle_app(actions: Vec<ScriptedAction>) -> App {
        let mut app = App::new();
        app.add_plugins(TaskPoolPlugin::default());
        app.add_message::<WindowFocused>()
            .add_message::<WindowResized>()
            .insert_resource(Readiness::Ready)
            .insert_resource(PresentGate::automatic())
            .insert_resource(SimWakePhase::new(WakePhase::AwakeInPod))
            .insert_resource(CaptureExtent {
                width: 1920,
                height: 1080,
            })
            .insert_resource(state_with(actions))
            .init_resource::<LifecycleLedger>()
            .add_systems(
                Update,
                (
                    drive_lifecycle,
                    step_scenario_input,
                    observe_window_focus,
                    observe_window_resized,
                )
                    .chain(),
            );
        app.world_mut().spawn(Window::default());
        app
    }

    /// The rig's stand-in for the shared drive's adapter half (`drive_ticks`
    /// in the real chain, which also owns the render resources these tests
    /// do not build): advance the input adapter one fixed update under the
    /// same drive gate. The rig pins the scenario clock itself (`set_tick`
    /// each update) and asserts the adapter's state, so the step alone is
    /// what these tests need.
    fn step_scenario_input(
        readiness: Res<Readiness>,
        present: Res<PresentGate>,
        mut state: ResMut<HarnessState>,
    ) {
        if !drive_allowed(*readiness.into_inner(), present.into_inner(), &state) {
            return;
        }
        let _ = state.adapter.step();
    }

    /// The lone Window entity's id.
    fn window_entity(app: &mut App) -> Entity {
        let mut windows = app.world_mut().query_filtered::<Entity, With<Window>>();
        windows.single(app.world()).expect("one window")
    }

    /// The lone window's (visible, focused, width, height).
    fn the_window(app: &mut App) -> (bool, bool, f32, f32) {
        let mut windows = app.world_mut().query::<&Window>();
        let window = windows.single(app.world()).expect("one window");
        (
            window.visible,
            window.focused,
            window.resolution.width(),
            window.resolution.height(),
        )
    }

    fn set_tick(app: &mut App, tick: u64) {
        let mut state = app.world_mut().resource_mut::<HarnessState>();
        state.tick = tick;
        state.frame = tick;
    }

    fn announced(app: &mut App) {
        app.world_mut().resource_mut::<HarnessState>().announced = true;
    }

    fn deliver_focus(app: &mut App, focused: bool) {
        let window = window_entity(app);
        app.world_mut()
            .write_message(WindowFocused { window, focused });
        app.update();
    }

    #[test]
    fn the_focus_loss_drive_hides_the_window_exactly_once() {
        let mut app = lifecycle_app(vec![]);
        announced(&mut app);
        set_tick(&mut app, 39);
        app.update();
        assert!(the_window(&mut app).0, "nothing driven before the tick");
        set_tick(&mut app, 40);
        app.update();
        assert!(!the_window(&mut app).0, "the drive hid the window");
        assert!(
            app.world()
                .resource::<HarnessState>()
                .checkpoints
                .iter()
                .any(|c| c.contains("focus loss driven at tick 40"))
        );
        // A later update must not repeat the drive.
        set_tick(&mut app, 41);
        app.update();
        let repeats = app
            .world()
            .resource::<HarnessState>()
            .checkpoints
            .iter()
            .filter(|c| c.contains("focus loss driven"))
            .count();
        assert_eq!(repeats, 1, "the drive fires exactly once");
    }

    #[test]
    fn the_reacquire_drive_waits_for_the_observed_focus_loss() {
        let mut app = lifecycle_app(vec![]);
        announced(&mut app);
        set_tick(&mut app, 40);
        app.update();
        set_tick(&mut app, 90);
        app.update();
        assert!(
            !the_window(&mut app).0,
            "no reacquire before the loss is observed"
        );
        deliver_focus(&mut app, false);
        assert!(
            app.world()
                .resource::<HarnessState>()
                .events
                .iter()
                .any(|event| matches!(event, TimedEvent::WindowFocus { focused: false, .. })),
            "the loss observation is recorded"
        );
        app.update();
        let (visible, focused, ..) = the_window(&mut app);
        assert!(visible, "the reacquire drive re-shows the window");
        assert!(focused, "the reacquire drive requests focus");
    }

    #[test]
    fn the_input_clear_releases_the_held_key_at_the_loss_boundary() {
        let mut app = lifecycle_app(vec![ScriptedAction::press(0, Key::Activate)]);
        announced(&mut app);
        // The press delivered while held; nothing else is scripted.
        set_tick(&mut app, 1);
        app.update();
        set_tick(&mut app, 40);
        app.update();
        assert!(
            !app.world()
                .resource::<HarnessState>()
                .events
                .iter()
                .any(|event| matches!(event, TimedEvent::InputCleared { .. })),
            "no clear before the loss lands"
        );
        deliver_focus(&mut app, false);
        let state = app.world().resource::<HarnessState>();
        let cleared = state
            .events
            .iter()
            .find_map(|event| match event {
                TimedEvent::InputCleared {
                    dropped_edges,
                    released,
                    ..
                } => Some((*dropped_edges, released.clone())),
                _ => None,
            })
            .expect("the clear is recorded");
        assert_eq!(cleared, (0, vec!["Key(Activate)".to_owned()]));
        assert_eq!(
            state.adapter.pending_edges(),
            1,
            "the held key's synthetic release is queued for the next step"
        );
    }

    #[test]
    fn the_resize_drive_waits_for_the_observed_reacquire_and_records_both_extents() {
        let mut app = lifecycle_app(vec![]);
        announced(&mut app);
        // The capture extent is the app builder's recorded (1920, 1080), so
        // the observation records both extents.
        set_tick(&mut app, 40);
        app.update();
        deliver_focus(&mut app, false);
        set_tick(&mut app, 90);
        app.update();
        deliver_focus(&mut app, true);
        set_tick(&mut app, 139);
        app.update();
        assert!(
            !app.world()
                .resource::<HarnessState>()
                .events
                .iter()
                .any(|event| matches!(event, TimedEvent::WindowResized { .. })),
            "nothing resized before the resize tick"
        );
        set_tick(&mut app, 140);
        app.update();
        let state = app.world().resource::<HarnessState>();
        let resized = state
            .events
            .iter()
            .find_map(|event| match event {
                TimedEvent::WindowResized {
                    width,
                    height,
                    capture_width,
                    capture_height,
                    ..
                } => Some((*width, *height, *capture_width, *capture_height)),
                _ => None,
            })
            .expect("the resize observation is recorded");
        assert_eq!(resized, (1280.0, 720.0, 1920, 1080));
        let (.., width, height) = the_window(&mut app);
        assert_eq!((width, height), (1280.0, 720.0));
    }

    #[test]
    fn resize_observations_carry_the_driven_stamp() {
        let mut app = lifecycle_app(vec![]);
        announced(&mut app);
        let entity = window_entity(&mut app);
        app.world_mut().resource_mut::<HarnessState>().announced = true;
        set_tick(&mut app, 30);
        app.world_mut().write_message(WindowResized {
            window: entity,
            width: 100.0,
            height: 50.0,
        });
        app.update();
        let stamp = app
            .world()
            .resource::<HarnessState>()
            .events
            .iter()
            .find_map(|event| match event {
                TimedEvent::WindowResized { tick, frame, .. } => Some((*tick, *frame)),
                _ => None,
            })
            .expect("the observation is recorded");
        assert_eq!(stamp, (29, 29), "the just-driven tick stamps");
    }

    #[test]
    fn focus_observations_before_the_boundary_are_not_recorded() {
        // The window's creation transitions (the delegate's initial
        // unfocused verdict, then become-key) land while the lane loads;
        // they are the window's history, not the run's observations.
        let mut app = lifecycle_app(vec![]);
        deliver_focus(&mut app, false);
        deliver_focus(&mut app, true);
        announced(&mut app);
        set_tick(&mut app, 40);
        app.update();
        deliver_focus(&mut app, false);
        let focus_events = app
            .world()
            .resource::<HarnessState>()
            .events
            .iter()
            .filter(|event| matches!(event, TimedEvent::WindowFocus { .. }))
            .count();
        assert_eq!(focus_events, 1, "only the post-boundary transition counts");
    }

    #[test]
    fn gameplay_content_none_content_does_not_hold_the_clear() {
        // Calibration content has no shared plane; the clear must run
        // without it (the Option is None on this lane).
        let mut app = lifecycle_app(vec![]);
        announced(&mut app);
        set_tick(&mut app, 40);
        app.update();
        deliver_focus(&mut app, false);
        let cleared = app
            .world()
            .resource::<HarnessState>()
            .events
            .iter()
            .any(|event| matches!(event, TimedEvent::InputCleared { .. }));
        assert!(cleared, "the adapter clear ran with no plane present");
    }

    #[test]
    fn the_test_content_is_calibration() {
        // The lane boots the calibration scene (B1 scope); the state
        // builder must not silently switch content.
        let state = state_with(vec![]);
        assert_eq!(state.scenario.content, Content::Calibration);
    }
}
