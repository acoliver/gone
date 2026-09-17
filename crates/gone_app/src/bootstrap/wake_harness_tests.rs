//! Gameplay-lane coverage of the shared production wake driver: the harness
//! runs the windowed game's own `GameWakePlugin` (registered by `wire`), so
//! these tests drive the real plugin through the real protocol chain — the
//! phase handoff at the authored completion tick, the delayed-readiness hold
//! with the first ready sample bitwise closed at logical zero, the scenario
//! clock's 1:1 pacing of the driver's logical ticks (held updates consume
//! nothing), and the chip overlay's independence from the wake effect.
//!
//! Honesty note on evidence: the pipeline bridge is held at controlled
//! fixture states here (a rendererless app cannot compile pipelines). That
//! is fixture behavior, NOT native presentation evidence — the same rule
//! `crate::wake`'s and `wake_pass`'s tests pin. Live presentation runs
//! through the real bridge on the runner's lanes.

use std::path::PathBuf;
use std::time::Duration;

use bevy::app::{App, TaskPoolPlugin};
use bevy::asset::{AssetApp, AssetPlugin};
use bevy::camera::{Camera, Camera3d, CameraOutputMode, ClearColorConfig};
use bevy::ecs::prelude::{Entity, With, Without};
use bevy::image::{Image, ImagePlugin};
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::mesh::Mesh;
use bevy::pbr::StandardMaterial;
use bevy::render::render_resource::BlendState;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::time::{Time, TimePlugin, Virtual};
use bevy::window::WindowFocused;
use gone_sim::{WakePhase, WakeSample, WakeTimeline};

use super::capture::{CaptureDelay, on_screenshot_captured};
use super::gameplay::{GAMEPLAY_OVERLAY_ORDER, register_update_systems, wire};
use super::state::{BeatCapture, HarnessState, PresentGate, Readiness, RunMode, ScenarioTime};
use super::{CaptureTarget, ChipSprite, ChipTexture};
use crate::harness::{Beat, Content, InputAdapter, Key, Scenario, ScriptedAction, TimedEvent};
use crate::player::PlayerPitch;
use crate::readiness::{AssetLoad, GameAssets};
use crate::scene::SimWakePhase;
use crate::wake::SimWakeState;
use crate::wake_pass::{
    WakeEyelidMaterial, WakeEyelidPipelineFailure, WakeEyelidPipelineReadiness,
};

/// The ledger name of today's only required game asset (the post chain's
/// metering mask), as the fixtures inject it.
const MASK: &str = crate::post::MASK_ASSET_PATH;

/// A scratch run directory unique per test invocation, so reports and
/// failure artifacts never collide across tests or suite runs.
fn out_dir(tag: &str) -> PathBuf {
    std::env::temp_dir().join(format!("gone-wake-harness-{}-{tag}", std::process::id()))
}

/// A gameplay capture scenario for the wake tests: the scripted actions and
/// the named beats at the default rate.
fn wake_scenario(name: &str, actions: Vec<ScriptedAction>, beats: Vec<Beat>) -> Scenario {
    Scenario {
        name: name.to_owned(),
        content: Content::Gameplay,
        actions,
        beats,
        ..Scenario::default()
    }
}

/// The real gameplay lane, no renderer: `wire` builds the game for real
/// (post chain, stasis scene, player look and motion, the production wake
/// driver with its pinned virtual clock), the real startup scene runs, and
/// the full update chain registers through [`register_update_systems`], the
/// function `BootstrapPlugin` calls. The bridge starts at `bridge` (a real
/// loading lane's state before its pipeline compiles); assets are injected
/// loaded. The test plays the render world (see [`play_render_world`]).
pub(super) fn wake_harness_app(
    bridge: WakeEyelidPipelineReadiness,
    scenario: Scenario,
    tag: &str,
) -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        ImagePlugin::default(),
        TimePlugin,
        // The completion handoff removes the render-synced eyelid material,
        // whose component hooks run the entity-sync bookkeeping the real
        // app's render stack provides; this is exactly that piece, headless.
        bevy::render::sync_world::SyncWorldPlugin,
    ));
    app.init_asset::<Mesh>().init_asset::<StandardMaterial>();
    app.add_message::<WindowFocused>()
        .init_resource::<ButtonInput<KeyCode>>()
        .init_resource::<AccumulatedMouseMotion>();
    wire(&mut app);
    app.insert_resource(GameAssets::with_loads(&[(MASK, AssetLoad::Loaded)]));
    app.insert_resource(bridge);
    app.insert_resource(WakeEyelidPipelineFailure(None));
    app.init_resource::<Readiness>();
    app.insert_resource(PresentGate::automatic());
    app.insert_resource(RunMode::Headless);
    app.insert_resource(ChipTexture::default());
    app.insert_resource(ChipSprite::default());
    app.init_resource::<CaptureTarget>();
    let adapter = InputAdapter::with_actions(scenario.actions.clone(), scenario.ticks_per_second);
    let tick_rate = scenario.ticks_per_second;
    app.insert_resource(HarnessState::new(
        scenario,
        out_dir(tag),
        String::new(),
        adapter,
    ));
    app.insert_resource(ScenarioTime::new(tick_rate));
    app.insert_resource(CaptureDelay(Duration::ZERO));
    app.add_observer(on_screenshot_captured);
    app.add_systems(bevy::app::Startup, super::gameplay::setup_gameplay_scene);
    register_update_systems(&mut app);
    app
}

/// Point the bridge at its ready state (the state a real renderer reaches a
/// few frames in), the driver's gate's render leg.
fn open_bridge(app: &mut App) {
    app.insert_resource(WakeEyelidPipelineReadiness::Ready);
}

/// Play the render world one frame: deliver the readbacks the real pipeline
/// would. An in-flight beat capture lands first (it is what blocks the
/// drive); otherwise a pending readiness proof lands.
pub(super) fn play_render_world(app: &mut App) {
    if let Some(request) = app
        .world()
        .resource::<HarnessState>()
        .capture_in_flight
        .clone()
    {
        let mut beats = app
            .world_mut()
            .query_filtered::<(Entity, &BeatCapture), ()>();
        let entity = beats
            .iter(app.world())
            .find(|(_, capture)| capture.request_id == request.request_id)
            .map(|(entity, _)| entity)
            .expect("the pinned beat's screenshot entity is still queued");
        app.world_mut().trigger(ScreenshotCaptured {
            entity,
            image: test_image(),
        });
        app.world_mut().despawn(entity);
        return;
    }
    if *app.world().resource::<Readiness>() == Readiness::Loading {
        let mut proofs = app
            .world_mut()
            .query_filtered::<Entity, (With<Screenshot>, Without<BeatCapture>)>();
        if let Some(entity) = proofs.iter(app.world()).next() {
            app.world_mut().trigger(ScreenshotCaptured {
                entity,
                image: test_image(),
            });
        }
    }
}

/// Run `updates` app updates, playing the render world after each.
fn run_updates(app: &mut App, updates: usize) {
    for _ in 0..updates {
        app.update();
        play_render_world(app);
    }
}

/// The scenario clock's driven tick count and the machine's logical tick, as
/// one pair: every 1:1 pacing assertion reads it.
fn ticks(app: &App) -> (u64, u64) {
    let scenario = app.world().resource::<HarnessState>().tick;
    let machine = app.world().resource::<SimWakeState>().current_tick();
    (scenario, machine)
}

/// Both clocks' (delta, elapsed) pairs, as the two temporal consumers read
/// them: the generic `Time` first — `bevy_render`'s `Globals` feeds the
/// auto-exposure adaptation from its delta — then the `Time<Virtual>` the
/// wake driver accumulates.
fn clock_state(app: &App) -> ((Duration, Duration), (Duration, Duration)) {
    let generic = app.world().resource::<Time>();
    let virt = app.world().resource::<Time<Virtual>>();
    (
        (generic.delta(), generic.elapsed()),
        (virt.delta(), virt.elapsed()),
    )
}

/// An 8x8 RGBA capture-shaped image; the readback bytes play the render
/// world's delivery (the content is not what these tests assert on).
fn test_image() -> Image {
    Image::new(
        Extent3d {
            width: 8,
            height: 8,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        vec![0; 8 * 8 * 4],
        TextureFormat::Rgba8UnormSrgb,
        bevy::asset::RenderAssetUsages::MAIN_WORLD,
    )
}

/// The rig camera's eyelid uniform, if the effect is still attached.
fn rig_eyelid(app: &mut App) -> Option<WakeEyelidMaterial> {
    let mut cams = app
        .world_mut()
        .query_filtered::<&WakeEyelidMaterial, With<PlayerPitch>>();
    cams.single(app.world()).ok().copied()
}

/// Assert two materials are the same bits: the driver copies the machine's
/// sample verbatim, so any rounding at all is a break.
fn assert_same_bits(actual: WakeEyelidMaterial, expected: WakeEyelidMaterial, label: &str) {
    assert_eq!(actual, expected, "{label}");
}

/// The observed wake-phase names, in report order.
fn observed_phases(app: &App) -> Vec<String> {
    app.world()
        .resource::<HarnessState>()
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::WakePhase { phase, .. } => Some(phase.clone()),
            _ => None,
        })
        .collect()
}

#[test]
fn the_shared_driver_hands_off_at_the_authored_completion_tick() {
    // The harness lane's wake is the production driver's, end to end: the
    // authored timeline plays on the scenario clock, the machine still holds
    // `Waking` one tick before the authored completion, and the completion
    // tick hands `Waking -> AwakeInPod` through the shared boundary exactly
    // once, stripping the effect from the rig camera. A final beat past the
    // completion keeps the run driving through the whole handoff.
    let timeline = WakeTimeline::authored();
    let complete = timeline.complete_tick();
    let scenario = wake_scenario(
        "wake-handoff",
        vec![],
        vec![Beat::new("after-wake", complete + 10)],
    );
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "handoff");

    // Drive to one tick before completion: the driven sample is the authored
    // sample there, the phase is still the authored opening, the effect is
    // attached. (After N updates the run has driven N-1 ticks; the update
    // that drives tick `complete - 1` is the handoff's eve.)
    run_updates(
        &mut app,
        usize::try_from(complete).expect("the authored tick fits usize"),
    );
    let (_, machine_tick) = ticks(&app);
    assert_eq!(machine_tick, complete - 1, "one tick before the completion");
    assert_same_bits(
        rig_eyelid(&mut app).expect("the effect is still attached"),
        WakeEyelidMaterial::from_sample(timeline.sample_at(complete - 1)),
        "the driven sample one tick before completion is the authored sample",
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "one tick before the authored completion the wake still owns the camera"
    );

    // The completion tick hands off exactly once and strips the effect.
    run_updates(&mut app, 1);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the authored completion tick hands off to AwakeInPod"
    );
    assert!(
        app.world().resource::<SimWakeState>().is_complete(),
        "the machine rests at the neutral hold"
    );
    assert!(
        rig_eyelid(&mut app).is_none(),
        "completion removes the effect from the rig camera"
    );
    assert_eq!(
        observed_phases(&app),
        ["waking", "awake_in_pod"],
        "the report observes exactly the driver's progression"
    );

    // Later updates change nothing: one handoff, no repeat.
    run_updates(&mut app, 3);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the handoff fired exactly once"
    );
}

/// The delayed-bridge hold: several updates with the pipeline bridge not yet
/// `Ready` announce nothing, drive nothing, and leave the wake machine
/// unstarted — closed at logical zero, the phase at the authored opening, the
/// rig camera at the closed rest state.
fn assert_bridge_holds_the_lane(app: &mut App) {
    run_updates(app, 5);
    {
        let state = app.world().resource::<HarnessState>();
        assert!(
            !state.announced,
            "the proof waits on the bridge with the other legs"
        );
        assert_eq!(
            state.tick, 0,
            "the scenario clock never starts behind the gate"
        );
    }
    {
        let machine = app.world().resource::<SimWakeState>();
        assert!(
            !machine.is_started(),
            "a compiling pipeline never starts the wake"
        );
        assert_eq!(
            machine.current_tick(),
            0,
            "no logical tick was consumed behind the bridge"
        );
        assert_eq!(
            machine.sample(),
            WakeSample::CLOSED,
            "the sample holds closed"
        );
    }
    assert_eq!(
        rig_eyelid(app),
        Some(WakeEyelidMaterial::CLOSED),
        "the rig camera carries the closed rest state"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the phase holds at the authored opening behind the bridge"
    );
}

#[test]
fn a_delayed_bridge_holds_the_lane_and_the_first_driven_update_starts_once() {
    // The readiness hold on the gameplay lane: the pipeline bridge is one of
    // the proof gate's legs, so while it has not reached `Ready` the proof
    // never lands, the lane never announces and never drives — and the wake
    // machine is untouched no matter how many updates pass: closed,
    // unstarted, `Waking`. The bridge's first driven update starts the
    // machine at logical zero and consumes that update's tick, and every
    // later driven update consumes exactly one more: no restart, no phantom
    // ticks, and the authored timeline plays entirely on the scenario clock.
    let scenario = wake_scenario("wake-delay", vec![], vec![Beat::new("late", 8)]);
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Compiling, scenario, "delayed");

    // Loading: nothing announces, nothing drives, the machine never starts.
    assert_bridge_holds_the_lane(&mut app);

    // The gate's first driven update starts the machine once and consumes
    // this update's tick: logical one, bitwise still closed (the authored
    // closed hold eases closed to closed). One update requests the proof, the
    // next opens the boundary and drives tick zero.
    open_bridge(&mut app);
    run_updates(&mut app, 2);
    {
        let state = app.world().resource::<HarnessState>();
        assert!(
            state.announced,
            "the open gate lands the proof and announces"
        );
        assert_eq!(state.tick, 1, "tick zero drove on the boundary update");
        let machine = app.world().resource::<SimWakeState>();
        assert!(machine.is_started(), "the gate opened the machine");
        assert_eq!(
            machine.current_tick(),
            1,
            "the start consumed exactly the first driven update's tick"
        );
        assert_eq!(
            machine.sample(),
            WakeSample::CLOSED,
            "the driven sample inside the closed hold is bitwise closed"
        );
    }

    // Every later driven update consumes exactly one tick and no more, the
    // rig carrying the authored sample of exactly that tick.
    run_updates(&mut app, 2);
    let (_, machine_tick) = ticks(&app);
    assert_eq!(
        machine_tick, 3,
        "exactly one logical tick per driven update"
    );
    assert_same_bits(
        rig_eyelid(&mut app).expect("the effect stays attached mid-wake"),
        WakeEyelidMaterial::from_sample(WakeTimeline::authored().sample_at(machine_tick)),
        "the rig carries the authored sample at the machine's tick",
    );
}

#[test]
fn the_handoff_lands_on_the_derived_tick_and_the_documented_press_starts_the_get_up() {
    // The boundary ordering the runner's schedule is authored against: the
    // production handoff lands on the update that drives scenario tick
    // `complete - 1` (the 1:1 pacing puts the machine's completion tick
    // there), a press on the last wholly-`Waking` tick before it is consumed
    // and dropped by the phase policy, and a press on the runner's documented
    // first-input tick (`handoff + 2`) starts the get-up — the machine
    // observed in `ExitingPod` on exactly that tick.
    let complete = WakeTimeline::authored().complete_tick();
    let handoff = complete - 1;
    let documented_press = handoff + 2;
    let scenario = wake_scenario(
        "wake-press",
        vec![
            ScriptedAction::press(handoff - 1, Key::Activate),
            ScriptedAction::release(handoff - 1, Key::Activate),
            ScriptedAction::press(documented_press, Key::Activate),
            ScriptedAction::release(documented_press, Key::Activate),
        ],
        vec![Beat::new("late", complete + 40)],
    );
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "press");

    // Drive through the handoff and the documented press: the first update
    // lands the readiness proof and every later one drives a tick, so driving
    // through tick `documented_press` takes `documented_press + 2` updates.
    run_updates(
        &mut app,
        usize::try_from(documented_press + 2).expect("the tick count fits usize"),
    );

    let stamps: Vec<(u64, &str)> = app
        .world()
        .resource::<HarnessState>()
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::WakePhase { tick, phase, .. } => Some((*tick, phase.as_str())),
            _ => None,
        })
        .collect();
    assert_eq!(
        stamps,
        [
            (0, "waking"),
            (handoff, "awake_in_pod"),
            (documented_press, "exiting_pod"),
        ],
        "the handoff stamps the derived tick, the early press is dropped, and the \
         documented press starts the get-up on its own tick"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::ExitingPod,
        "the get-up owns the body after the documented press"
    );
}

#[test]
fn the_scenario_clock_paces_the_driver_and_a_capture_hold_advances_nothing() {
    // The harness clock contract: one driven scenario tick is one logical
    // wake tick, and a held update — a beat readback in flight — is zero.
    // The machine's tick count therefore equals the scenario tick count
    // through holds and resumes, and the rig's uniform is always the
    // authored sample of exactly that tick.
    let scenario = wake_scenario("wake-pace", vec![], vec![Beat::new("held", 3)]);
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "pace");

    run_updates(&mut app, 8);
    let (scenario_tick, machine_tick) = ticks(&app);
    assert_eq!(
        scenario_tick, machine_tick,
        "one logical tick per driven scenario tick, holds included"
    );
    let state = app.world().resource::<HarnessState>();
    assert!(
        state.last_beat_frame > 0,
        "the beat's readback landed, so the run held at least once"
    );
    assert!(
        state.done,
        "the beat landed and the settle window passed: the run is closed"
    );
    assert_same_bits(
        rig_eyelid(&mut app).expect("attached inside the closed hold"),
        WakeEyelidMaterial::from_sample(WakeSample::CLOSED),
        "the pinned frames inside the closed hold are bitwise closed",
    );
}

#[test]
fn the_driven_step_reaches_both_clocks() {
    // The render clock is the generic `Time` (bevy_render's `Globals` feeds
    // the auto-exposure adaptation from its delta) and the wake driver's
    // clock is `Time<Virtual>`: a driven update must leave both describing
    // the same driven step. Regression for the harness render-clock bug —
    // the drive advanced only the virtual clock, so the renderer read the
    // paused zero TimePlugin's First had already copied in and engine
    // temporal effects never adapted on driven frames.
    let scenario = wake_scenario("clock-driven", vec![], vec![Beat::new("late", 30)]);
    let step = Duration::from_secs_f32(ScenarioTime::new(scenario.ticks_per_second).delta_secs());
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "clock-driven");

    // The first update requests the readiness proof and its readback lands;
    // the next update opens the boundary and drives tick zero.
    run_updates(&mut app, 1);
    app.update();
    assert_eq!(
        app.world().resource::<HarnessState>().tick,
        1,
        "tick zero drove on the boundary update"
    );

    let ((generic_delta, generic_elapsed), (virt_delta, virt_elapsed)) = clock_state(&app);
    assert_eq!(
        virt_delta, step,
        "the virtual clock carries exactly one step"
    );
    assert_eq!(
        generic_delta, virt_delta,
        "the generic clock carries the same driven delta"
    );
    assert_eq!(
        virt_elapsed, step,
        "one driven update is one step of elapsed"
    );
    assert_eq!(
        generic_elapsed, virt_elapsed,
        "the generic elapsed mirrors the virtual elapsed"
    );

    // A second driven update: still exactly one step of delta on both
    // clocks, one more step of elapsed on both.
    app.update();
    let ((generic_delta, generic_elapsed), (virt_delta, virt_elapsed)) = clock_state(&app);
    assert_eq!(virt_delta, step);
    assert_eq!(generic_delta, virt_delta);
    assert_eq!(virt_elapsed, step + step);
    assert_eq!(generic_elapsed, virt_elapsed);
}

#[test]
fn the_readiness_hold_zeroes_both_clocks() {
    // Updates behind the readiness gate drive nothing, and the paused
    // clock's First publish (`*current = virt.as_generic()`) zeroes the
    // delta into the generic clock too: both deltas read zero every held
    // update and both elapsed counters stand at zero — no update has
    // rendered as time on either clock.
    let scenario = wake_scenario("clock-loading", vec![], vec![Beat::new("late", 30)]);
    let mut app = wake_harness_app(
        WakeEyelidPipelineReadiness::Compiling,
        scenario,
        "clock-loading",
    );

    run_updates(&mut app, 4);
    assert!(
        !app.world().resource::<HarnessState>().announced,
        "the lane is still held behind the gate"
    );
    let ((generic_delta, generic_elapsed), (virt_delta, virt_elapsed)) = clock_state(&app);
    assert!(
        virt_delta.is_zero(),
        "the paused clock never accumulates a delta behind the gate"
    );
    assert!(
        generic_delta.is_zero(),
        "the generic clock reads the paused zero"
    );
    assert!(
        virt_elapsed.is_zero() && generic_elapsed.is_zero(),
        "nothing drove, so nothing elapsed on either clock"
    );
}

#[test]
fn a_capture_hold_zeroes_both_clocks_and_the_resume_steps_both_once() {
    // The held frame under a beat readback renders with zero delta on both
    // clocks and both elapsed counters standing, and the resume drives
    // exactly one step into both — not zero, not the accumulated hold, not
    // a double step.
    let scenario = wake_scenario("clock-hold", vec![], vec![Beat::new("held", 2)]);
    let step = Duration::from_secs_f32(ScenarioTime::new(scenario.ticks_per_second).delta_secs());
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "clock-hold");

    // The first update requests and lands the proof, the next two drive
    // ticks zero and one, and the third driven update drives tick two and
    // pins the beat (its readback is now in flight).
    run_updates(&mut app, 3);
    app.update();
    assert_eq!(
        app.world().resource::<HarnessState>().tick,
        3,
        "three ticks drove before the hold"
    );
    assert!(
        app.world()
            .resource::<HarnessState>()
            .capture_in_flight
            .is_some(),
        "the beat's readback is in flight"
    );

    // The held update: the drive gate holds, and First's paused publish
    // zeroes both deltas while both elapsed counters stand at the three
    // driven steps.
    app.update();
    let ((generic_delta, generic_elapsed), (virt_delta, virt_elapsed)) = clock_state(&app);
    assert!(virt_delta.is_zero(), "the hold advances no virtual delta");
    assert!(
        generic_delta.is_zero(),
        "the hold renders a zero generic delta"
    );
    assert_eq!(
        virt_elapsed,
        step + step + step,
        "the hold preserves elapsed"
    );
    assert_eq!(
        generic_elapsed, virt_elapsed,
        "both clocks hold the same elapsed"
    );

    // The readback lands and the resume update drives exactly one step into
    // both clocks, with the machine consuming exactly that tick.
    play_render_world(&mut app);
    app.update();
    let ((generic_delta, generic_elapsed), (virt_delta, virt_elapsed)) = clock_state(&app);
    assert_eq!(virt_delta, step, "the resume drives exactly one step");
    assert_eq!(
        generic_delta, virt_delta,
        "the generic clock carries the same resumed step"
    );
    assert_eq!(virt_elapsed, 4 * step, "the hold elapsed for nothing");
    assert_eq!(
        generic_elapsed, virt_elapsed,
        "both clocks end the resume at the same elapsed"
    );
    let (scenario_tick, machine_tick) = ticks(&app);
    assert_eq!(scenario_tick, 4, "the resume drove one scenario tick");
    assert_eq!(
        machine_tick, 4,
        "the machine consumed exactly the resumed tick, holds included"
    );
}

#[test]
fn the_wake_effect_lives_on_game_cameras_and_never_on_the_chip_overlay() {
    // Capture-overlay independence: the wake eyelid attaches to the game's
    // cameras only. The chip overlay camera keeps its exact blend contract
    // (no clears, an alpha-blended final write) and carries no eyelid
    // material, so the corner chip decodes over whatever the wake renders —
    // the overlay's ALPHA_BLENDING is untouched by the wake migration.
    let scenario = wake_scenario("wake-overlay", vec![], vec![Beat::new("beat", 5)]);
    let mut app = wake_harness_app(WakeEyelidPipelineReadiness::Ready, scenario, "overlay");
    run_updates(&mut app, 4);

    let mut overlays = app
        .world_mut()
        .query_filtered::<&Camera, Without<PlayerPitch>>();
    let mut found_overlay = false;
    for camera in overlays.iter(app.world()) {
        if camera.order != GAMEPLAY_OVERLAY_ORDER {
            continue;
        }
        found_overlay = true;
        assert!(
            matches!(camera.clear_color, ClearColorConfig::None),
            "the overlay never clears: {camera:?}"
        );
        let CameraOutputMode::Write {
            blend_state,
            clear_color,
        } = camera.output_mode
        else {
            panic!("the overlay must write (blend) its output, not skip it");
        };
        assert_eq!(blend_state, Some(BlendState::ALPHA_BLENDING));
        assert!(matches!(clear_color, ClearColorConfig::None));
    }
    assert!(found_overlay, "the gameplay overlay camera is present");

    let material_entities: Vec<(Entity, WakeEyelidMaterial)> = {
        let mut materials = app.world_mut().query::<(Entity, &WakeEyelidMaterial)>();
        materials
            .iter(app.world())
            .map(|(entity, material)| (entity, *material))
            .collect()
    };
    let mut rig = app
        .world_mut()
        .query_filtered::<&Camera3d, With<PlayerPitch>>();
    for (entity, _) in material_entities {
        assert!(
            rig.get(app.world(), entity).is_ok(),
            "only game cameras carry the wake effect"
        );
    }
    assert!(
        rig_eyelid(&mut app).is_some(),
        "the rig camera carries the effect"
    );
}
