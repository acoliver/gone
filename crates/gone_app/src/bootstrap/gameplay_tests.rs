//! Gameplay-lane protocol tests, driven through the real systems (no
//! renderer): the readiness barrier (a delayed required asset holds the clock
//! until one announcement, a failed one fails the run by name), the
//! post-tick capture contract (a look action on the beat's own tick is inside
//! the reported yaw, sampled from the rig's actual transform), and the
//! latency invariant (the full report, final scenario time, and final rig
//! transform are identical with and without an injected readback delay).

use std::path::PathBuf;
use std::time::Duration;

use bevy::app::{App, AppExit, Startup, TaskPoolPlugin, Update};
use bevy::asset::{AssetApp, AssetPlugin, Assets};
use bevy::camera::Camera3d;
use bevy::ecs::message::Messages;
use bevy::ecs::prelude::{Entity, With, Without};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::image::{Image, ImagePlugin};
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};
use bevy::time::TimePlugin;
use bevy::transform::components::Transform;
use bevy::window::WindowFocused;
use gone_sim::WakePhase;

use super::capture::{CaptureDelay, on_screenshot_captured};
use super::drive::{drive_ticks, readiness_boundary, request_readiness_proof, rig_yaw_radians};
use super::finish::finish_scan;
use super::gameplay::{
    GameCameraBound, advance_wake_at_readiness, poll_required_assets, register_update_systems,
    retarget_gameplay_camera,
};
use super::state::{BeatCapture, HarnessState, PresentGate, Readiness, RunMode, ScenarioTime};
use super::{CaptureTarget, ChipSprite, ChipTexture};
use crate::harness::{
    Beat, Content, InputAdapter, Key, Scenario, ScriptedAction, TimedEvent, parse_report,
};
use crate::player::{GameplayInput, PlayerPitch, PlayerYaw};
use crate::readiness::{AssetLoad, GameAssets};
use crate::scene::{PlayerSpawn, SimWakePhase};

/// The ledger name of today's only required game asset (the post chain's
/// metering mask), as the failure report must carry it.
const MASK: &str = crate::post::MASK_ASSET_PATH;

/// A scratch run directory unique per test invocation, so the readiness
/// proof, the report, and any failure report never collide across tests or
/// across runs of the suite.
fn barrier_out_dir(tag: &str) -> PathBuf {
    std::env::temp_dir().join(format!("gone-barrier-{}-{tag}", std::process::id()))
}

/// The headless gameplay-lane app the barrier tests run: the real protocol
/// chain (rig-camera retarget, required-asset poll, proof request, boundary,
/// wake override, drive, finish) over a gameplay scenario, with the injected
/// required-asset ledger the test controls. The rig camera is spawned by hand
/// instead of through the look plugin, so the shared input plane stays
/// unconsumed and the tests can assert exactly what the adapter offered. No
/// renderer: the test plays the render world by triggering the proof's
/// `ScreenshotCaptured` by hand.
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
    let adapter = InputAdapter::with_actions(scenario.actions.clone(), scenario.ticks_per_second);
    let tick_rate = scenario.ticks_per_second;
    app.insert_resource(HarnessState::new(
        scenario,
        barrier_out_dir(tag),
        String::new(),
        adapter,
    ));
    app.insert_resource(ScenarioTime::new(tick_rate));
    app.insert_resource(CaptureDelay(Duration::ZERO));
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

/// A gameplay capture scenario at the default rate: the named actions and
/// beats, the default `max_frames` deadline.
fn drive_scenario(name: &str, actions: Vec<ScriptedAction>, beats: Vec<Beat>) -> Scenario {
    Scenario {
        name: name.to_owned(),
        content: Content::Gameplay,
        actions,
        beats,
        ..Scenario::default()
    }
}

/// The real gameplay drive lane, no renderer: the game plugins build for real
/// (post chain, stasis scene, player look — `wire` adds exactly what the
/// normal game adds), the real startup scene runs, and the full update chain
/// registers through [`register_update_systems`], the same function
/// `BootstrapPlugin` calls, so drive, look integration, beat pinning, yaw
/// sampling, and the close scan are the shipped systems. The barrier's asset
/// leg is pre-opened with an injected loaded ledger: these tests are about
/// the drive and capture path, not the asset wait. The test plays the render
/// world (see [`play_render_world`]).
fn gameplay_drive_app(scenario: Scenario, out_dir: PathBuf, delay: Duration) -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        ImagePlugin::default(),
        // The engine-clock freeze (bevy's `Time<Virtual>`) is part of the
        // chain under test; TimePlugin provides the clocks DefaultPlugins
        // would in the real app.
        TimePlugin,
    ));
    app.init_asset::<bevy::mesh::Mesh>()
        .init_asset::<bevy::pbr::StandardMaterial>();
    // The look plugin's systems read the input state DefaultPlugins
    // initializes in the real game; a rendererless test app provides it
    // directly.
    app.add_message::<WindowFocused>()
        .init_resource::<ButtonInput<KeyCode>>()
        .init_resource::<AccumulatedMouseMotion>();
    super::gameplay::wire(&mut app);
    app.insert_resource(GameAssets::with_loads(&[(MASK, AssetLoad::Loaded)]));
    app.init_resource::<Readiness>();
    app.insert_resource(PresentGate::automatic());
    app.insert_resource(RunMode::Headless);
    app.insert_resource(ChipTexture::default());
    app.insert_resource(ChipSprite::default());
    app.init_resource::<CaptureTarget>();
    let adapter = InputAdapter::with_actions(scenario.actions.clone(), scenario.ticks_per_second);
    let tick_rate = scenario.ticks_per_second;
    app.insert_resource(HarnessState::new(scenario, out_dir, String::new(), adapter));
    app.insert_resource(ScenarioTime::new(tick_rate));
    app.insert_resource(CaptureDelay(delay));
    app.add_observer(on_screenshot_captured);
    app.add_message::<AppExit>();
    app.add_systems(Startup, super::gameplay::setup_gameplay_scene);
    register_update_systems(&mut app);
    app
}

/// A small RGBA capture-shaped image; the readback bytes play the render
/// world's delivery and the observer writes them as PNGs (the conversion is
/// covered by `crate::capture` tests, the content is not what these tests
/// assert on).
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

/// Play the render world one frame: deliver the readbacks the real pipeline
/// would. An in-flight beat capture lands first (it is what blocks the
/// drive), matched to the in-flight request by id and despawned on landing
/// like the real one-shot screenshot request; otherwise a pending readiness
/// proof lands (a bare screenshot entity is the proof request).
fn play_render_world(app: &mut App) {
    if app
        .world()
        .resource::<HarnessState>()
        .capture_in_flight
        .is_some()
    {
        let request = app
            .world()
            .resource::<HarnessState>()
            .capture_in_flight
            .clone()
            .expect("checked above");
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

/// Drive the app until the run completes, playing the render world after
/// every update. Bounded: a regression that wedges the lane fails the test
/// instead of hanging it.
fn drive_to_completion(app: &mut App, max_updates: usize) {
    for _ in 0..max_updates {
        app.update();
        play_render_world(app);
        if app.world().resource::<HarnessState>().done {
            return;
        }
    }
    panic!("the scenario never completed within {max_updates} updates");
}

/// The rig yaw parent's transform, read from the world — the rendered pose.
fn rig_yaw_transform(app: &mut App) -> Transform {
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    *yaws.single(app.world()).expect("the rig yaw parent exists")
}

/// Wrap radians into (-pi, pi], the range the look integrator keeps and the
/// rig transform's derived angle carries.
fn wrap_radians(angle: f32) -> f32 {
    let wrapped = angle.rem_euclid(core::f32::consts::TAU);
    if wrapped > core::f32::consts::PI {
        wrapped - core::f32::consts::TAU
    } else {
        wrapped
    }
}

#[test]
fn the_beat_yaw_reports_the_post_turn_rig_transform() {
    // Captures are post-tick state: the look action scripted on the beat's
    // own tick must be inside the reported yaw. The sample is read from the
    // rig's actual transform (the rendered pose), so the event proves the
    // rig itself turned, not just that the look bookkeeping moved. The
    // sample's (tick, frame) is exactly the beat's pinned moment.
    let scenario = drive_scenario(
        "post-tick-yaw",
        vec![ScriptedAction::look(0, 90.0, 0.0)],
        vec![Beat::new("first", 0)],
    );
    let mut app = gameplay_drive_app(scenario, barrier_out_dir("post-tick-yaw"), Duration::ZERO);
    drive_to_completion(&mut app, 64);
    // The rig's transform at run's end is the pose the capture sampled: the
    // scenario's only look is the beat tick's own 90-degree turn, and nothing
    // turns the rig afterward.
    let rig = rig_yaw_transform(&mut app);
    {
        let state = app.world().resource::<HarnessState>();
        assert!(state.failed.is_none(), "the run completes cleanly");
        let beat = &state.beats["first"];
        assert_eq!(
            (beat.tick, beat.frame),
            (0, 0),
            "the beat pins its scripted tick"
        );
        let (tick, frame, reported) = state
            .events
            .iter()
            .find_map(|event| match event {
                TimedEvent::PlayerYaw {
                    tick,
                    frame,
                    yaw_degrees,
                } => Some((*tick, *frame, *yaw_degrees)),
                _ => None,
            })
            .expect("the beat's pin carries a yaw sample");
        assert_eq!(
            (tick, frame),
            (beat.tick, beat.frame),
            "the sample is the pinned moment"
        );
        // The atan2 extraction quantizes at roughly 1e-6 rad, so a
        // millidegree bound is far above the noise and far below any real
        // coupling.
        let transform_yaw = rig_yaw_radians(&rig).to_degrees();
        assert!(
            (reported - transform_yaw).abs() < 1e-3,
            "the sample must be the rig transform's angle: {reported} vs {transform_yaw}"
        );
    }
    // And it is the post-turn angle: 90 degrees past the authored spawn yaw,
    // wrapped into the integrator's range.
    let spawn_yaw = app.world().resource::<PlayerSpawn>().pose.yaw_radians;
    let expected = wrap_radians(spawn_yaw + 90.0_f32.to_radians()).to_degrees();
    let reported = app
        .world()
        .resource::<HarnessState>()
        .events
        .iter()
        .find_map(|event| match event {
            TimedEvent::PlayerYaw { yaw_degrees, .. } => Some(*yaw_degrees),
            _ => None,
        })
        .expect("checked above");
    assert!(
        (reported - expected).abs() < 1e-3,
        "the sample is the post-turn angle: {reported} vs {expected}"
    );
}

#[test]
fn the_beat_pin_samples_the_rig_position_at_its_moment() {
    // The gameplay-full lane's position assertions ride this sample: every
    // gameplay beat pin carries the rig's eye point at the pinned (tick,
    // frame), read from the rig's actual transform exactly like the yaw
    // sample. Nothing translates the player in this scenario, so the sample
    // is the authored lying spawn pose, and the run's end pose is the pose
    // the beat sampled.
    let scenario = drive_scenario(
        "post-tick-position",
        vec![ScriptedAction::look(0, 90.0, 0.0)],
        vec![Beat::new("first", 0)],
    );
    let mut app = gameplay_drive_app(
        scenario,
        barrier_out_dir("post-tick-position"),
        Duration::ZERO,
    );
    drive_to_completion(&mut app, 64);
    let rig = rig_yaw_transform(&mut app);
    let state = app.world().resource::<HarnessState>();
    assert!(state.failed.is_none(), "the run completes cleanly");
    let beat = &state.beats["first"];
    let positions: Vec<(u64, u64, f32, f32, f32)> = state
        .events
        .iter()
        .filter_map(|event| match event {
            TimedEvent::PlayerPosition {
                tick,
                frame,
                x,
                y,
                z,
            } => Some((*tick, *frame, *x, *y, *z)),
            _ => None,
        })
        .collect();
    assert_eq!(
        positions.len(),
        1,
        "exactly one beat pin carries one position sample"
    );
    let (tick, frame, x, y, z) = positions[0];
    assert_eq!((tick, frame), (beat.tick, beat.frame));
    let eye = rig.translation;
    assert!((x - eye.x).abs() < 1e-6, "x: {x} vs {}", eye.x);
    assert!((y - eye.y).abs() < 1e-6, "y: {y} vs {}", eye.y);
    assert!((z - eye.z).abs() < 1e-6, "z: {z} vs {}", eye.z);
    // The spawn pose lies in the player pod: the eye is inside the pod's
    // footprint at the lying eye height, under the lid line.
    let spawn = app.world().resource::<PlayerSpawn>().pose;
    assert!((y - spawn.eye.y).abs() < 1e-6, "the lying eye height holds");
    assert!((x - spawn.eye.x).abs() < 1e-6 && (z - spawn.eye.z).abs() < 1e-6);
}

#[test]
fn the_latency_invariant_holds_with_and_without_capture_delay() {
    // The protocol's latency proof, on the app's real drive path: the same
    // gameplay scenario runs twice through the real adapters — a scripted
    // look and a press feed the shared plane, two beats pin and land through
    // the real capture observer — once with a zero readback delay and once
    // with the observer sleeping an injected delay on every landing. The
    // capture freeze holds the scenario clock for the whole artificial
    // delay, so both runs must end with byte-identical reports, the same
    // final simulation time, and the same rig transform. Bounded: each drive
    // loop gives up at 64 updates.
    let scenario = drive_scenario(
        "latency-proof",
        vec![
            ScriptedAction::look(0, 90.0, 0.0),
            ScriptedAction::press(3, Key::Forward),
        ],
        vec![Beat::new("early", 0), Beat::new("late", 5)],
    );
    let mut ontime = gameplay_drive_app(
        scenario.clone(),
        barrier_out_dir("latency-ontime"),
        Duration::ZERO,
    );
    let mut delayed = gameplay_drive_app(
        scenario,
        barrier_out_dir("latency-delayed"),
        Duration::from_millis(25),
    );
    drive_to_completion(&mut ontime, 64);
    drive_to_completion(&mut delayed, 64);

    let report_text = |tag| {
        std::fs::read_to_string(barrier_out_dir(tag).join("report.json"))
            .expect("the run wrote its report")
    };
    let ontime_text = report_text("latency-ontime");
    let delayed_text = report_text("latency-delayed");
    // The full reports agree on everything: the same pins at the scripted
    // ticks, the same events, the same completion frame. Nothing in the
    // protocol carries the readback latency.
    assert_eq!(
        ontime_text, delayed_text,
        "readback latency must not move the timeline"
    );

    // The report is complete: one announcement, one completion, both beats
    // at their scripted ticks, a yaw sample pinned at every beat's moment.
    assert_report_shape(&ontime_text);

    // Both runs end at the same simulation time, which is exactly the driven
    // ticks' fixed steps, and at the same rig pose bit for bit: the freeze
    // held both clocks identically regardless of the landing delay.
    let ontime_rig = rig_yaw_transform(&mut ontime);
    let delayed_rig = rig_yaw_transform(&mut delayed);
    let ontime_time = ontime.world().resource::<ScenarioTime>().elapsed_secs();
    let delayed_time = delayed.world().resource::<ScenarioTime>().elapsed_secs();
    assert!(
        (ontime_time - delayed_time).abs() < f32::EPSILON,
        "final simulation time matches: {ontime_time} vs {delayed_time}"
    );
    let tick = ontime.world().resource::<HarnessState>().tick;
    let step = ontime.world().resource::<ScenarioTime>().delta_secs();
    let expected = f32::from(u16::try_from(tick).unwrap_or(u16::MAX)) * step;
    assert!(
        (ontime_time - expected).abs() < f32::EPSILON,
        "elapsed simulation time is exactly the driven ticks' fixed steps"
    );
    assert_eq!(
        ontime_rig.rotation, delayed_rig.rotation,
        "the final rig transform matches bit for bit"
    );
}

/// The report's shape, asserted in full: one announcement, one completion,
/// both beats pinned at their scripted ticks, and a yaw sample at every
/// beat's tick. The latency proof must show this shape on the delayed run
/// too — its full text is already asserted equal to the on-time run's.
fn assert_report_shape(report_text: &str) {
    let report = parse_report(report_text).expect("the report parses");
    assert!(report.perf.is_none(), "a capture run has no perf section");
    let mut beat_pins = Vec::new();
    let mut yaw_ticks = Vec::new();
    let mut ready = 0;
    let mut complete = 0;
    for event in &report.events {
        match event {
            TimedEvent::Beat { name, tick, .. } => beat_pins.push((name.clone(), *tick)),
            TimedEvent::PlayerYaw { tick, .. } => yaw_ticks.push(*tick),
            TimedEvent::Ready { .. } => ready += 1,
            TimedEvent::Complete { .. } => complete += 1,
            _ => {}
        }
    }
    assert_eq!(ready, 1, "exactly one announcement");
    assert_eq!(complete, 1, "exactly one completion");
    assert_eq!(
        beat_pins,
        vec![("early".to_owned(), 0), ("late".to_owned(), 5)],
        "both beats pin exactly their scripted ticks"
    );
    assert_eq!(
        yaw_ticks,
        vec![0, 5],
        "every beat pins a yaw sample at its own tick"
    );
}
