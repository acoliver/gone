//! Coverage of the normal-mode wake driver: the real plugin wiring (headless,
//! over the game's own plugin set), the readiness gate's hold, the exact
//! start-at-zero and its idempotence, the authored completion handoff, the
//! drift-free sway projection, and the loud pipeline-failure exit.
//!
//! Honesty note on evidence: the pipeline fixtures below drive *controlled
//! bridge resources* in a rendererless ECS app. That is fixture behavior —
//! NOT native presentation evidence. No test here compiles the eyelid
//! pipeline or composites a GPU frame; the only pipeline-state evidence is
//! the bridge's own contract, and the bridge's render-world half is
//! validated in `wake_pass`. The presentation-gate fixtures likewise drive
//! a windowed app shape (a primary window entity plus injected
//! [`WakePresentReadiness`] acknowledgements): the injected acknowledgement
//! is unit fixture behavior, NOT GPU evidence, and no test here touches a
//! surface. The mirror's render-world half is bevy's own state contract,
//! documented and unit-folded in [`super::present`].

use std::time::Duration;

use bevy::app::{App, AppExit, TaskPoolPlugin, Update};
use bevy::asset::{AssetApp, AssetPlugin};
use bevy::camera::Camera;
use bevy::ecs::message::Messages;
use bevy::ecs::prelude::{Entity, With};
use bevy::image::ImagePlugin;
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::math::Quat;
use bevy::mesh::Mesh;
use bevy::pbr::StandardMaterial;
use bevy::time::{Time, Virtual};
use bevy::transform::components::Transform;
use bevy::window::{PrimaryWindow, Window, WindowFocused};
use gone_sim::{LOGICAL_TICK_SECS, WakePhase, WakeTimeline};

use super::present::WakePresentReadiness;
use super::{GameWakePlugin, LoadingCover, PresentationPacedWake, SimWakeState};
use crate::player::{LookAngles, PlayerPitch, PlayerYaw};
use crate::readiness::{AssetLoad, GameAssets};
use crate::scene::SimWakePhase;
use crate::wake_pass::{
    WakeEyelidMaterial, WakeEyelidPipelineFailure, WakeEyelidPipelineReadiness,
};

/// The ledger name of today's only required game asset (the post chain's
/// metering mask), as the fixtures inject it.
const MASK: &str = crate::post::MASK_ASSET_PATH;

/// The authored timeline, for expected-sample and boundary math. The driver
/// runs this exact instance.
fn authored() -> WakeTimeline {
    WakeTimeline::authored()
}

/// The driver fixture: the real [`GameWakePlugin`] in a rendererless app
/// over a hand-spawned rig (the same yaw-parent/pitch-camera-child pair the
/// look plugin spawns, plus the [`LookAngles`] resource it initializes),
/// controlled gate resources, and a manually advanced virtual clock. The
/// bridge states are written by the tests — fixture behavior, not native
/// presentation evidence.
fn driver_app(assets: &[(&'static str, AssetLoad)]) -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        // The completion handoff removes the render-synced eyelid material,
        // whose component hooks run the entity-sync bookkeeping the real
        // app's render stack provides; this is exactly that piece, headless.
        bevy::render::sync_world::SyncWorldPlugin,
    ));
    app.add_message::<AppExit>();
    app.insert_resource(Time::<Virtual>::default());
    app.init_resource::<LookAngles>();
    app.insert_resource(GameAssets::with_loads(assets));
    app.insert_resource(SimWakePhase::new(WakePhase::Waking));
    spawn_rig(&mut app);
    app.add_plugins(GameWakePlugin);
    app
}

/// The rig the wake driver attaches to and composes sway onto: the look
/// plugin's two-entity shape (yaw parent carrying the pitch camera child),
/// at the identity pose.
fn spawn_rig(app: &mut App) {
    let yaw = app
        .world_mut()
        .spawn((PlayerYaw, Transform::default()))
        .id();
    app.world_mut().spawn((
        PlayerPitch,
        bevy::prelude::Camera3d::default(),
        Transform::default(),
        bevy::ecs::hierarchy::ChildOf(yaw),
    ));
}

/// Point both gate legs at their ready state (every asset loaded, the
/// pipeline bridge reporting `Ready`) and hold the failure mirror empty.
fn open_gate(app: &mut App) {
    app.insert_resource(GameAssets::with_loads(&[(MASK, AssetLoad::Loaded)]));
    app.world_mut()
        .insert_resource(WakeEyelidPipelineReadiness::Ready);
    app.world_mut()
        .insert_resource(WakeEyelidPipelineFailure(None));
}

/// The windowed fixture: [`driver_app`] plus a primary window entity and
/// the windowed game's pacing marker — the exact shape `run` builds for
/// `RunMode::Normal` (the marker is the normal game's own wiring in
/// `lib.rs`, so the fixture must opt in to test the paced contract). The
/// acknowledgement starts at its honest default: nothing has closed until a
/// test injects it.
fn windowed_driver_app(assets: &[(&'static str, AssetLoad)]) -> App {
    let mut app = driver_app(assets);
    app.insert_resource(PresentationPacedWake);
    app.world_mut().spawn((Window::default(), PrimaryWindow));
    app
}

/// Inject the closed-frame acknowledgement (unit fixture behavior, not GPU
/// evidence): the render world has closed frames over the primary window's
/// drawable, and the frame the next update follows did too. The real
/// mirror's render-world half is bevy's own state contract, documented and
/// unit-folded in [`super::present`].
fn ack_drawable_frame(app: &mut App) {
    app.world_mut().insert_resource(WakePresentReadiness {
        closed_with_drawable: true,
        drawable_frame_seen: true,
    });
}

/// Inject a frame without the drawable — the occlusion-shaped update — with
/// the sticky first-frame history intact: a paced run must bank its seconds
/// as nothing.
fn lose_drawable(app: &mut App) {
    app.world_mut().insert_resource(WakePresentReadiness {
        closed_with_drawable: false,
        drawable_frame_seen: true,
    });
}

/// Advance the virtual clock by one logical tick and run one update: the
/// driver consumes exactly one tick per call at the authored rate.
fn feed_tick(app: &mut App) {
    app.world_mut()
        .resource_mut::<Time<Virtual>>()
        .advance_by(Duration::from_secs_f32(LOGICAL_TICK_SECS));
    app.update();
}

/// Feed `ticks` one-tick updates.
fn feed_ticks(app: &mut App, ticks: u64) {
    for _ in 0..ticks {
        feed_tick(app);
    }
}

/// The rig's two entities (yaw parent, pitch camera child), in that order.
fn rig_entities(app: &mut App) -> (Entity, Entity) {
    let mut yaws = app.world_mut().query_filtered::<Entity, With<PlayerYaw>>();
    let yaw = yaws.single(app.world()).expect("the fixture rig yaw");
    let mut cams = app
        .world_mut()
        .query_filtered::<Entity, With<PlayerPitch>>();
    let camera = cams.single(app.world()).expect("the fixture rig camera");
    (yaw, camera)
}

/// The rig camera's rotation, if it still carries the eyelid effect.
fn eyelid(app: &App, camera: Entity) -> Option<WakeEyelidMaterial> {
    app.world().get::<WakeEyelidMaterial>(camera).copied()
}

/// The yaw parent's rotation, read back through the rig.
fn yaw_rotation(app: &App, yaw: Entity) -> Quat {
    app.world()
        .get::<Transform>(yaw)
        .expect("the rig yaw transform")
        .rotation
}

/// The pitch camera child's rotation.
fn pitch_rotation(app: &App, camera: Entity) -> Quat {
    app.world()
        .get::<Transform>(camera)
        .expect("the rig camera transform")
        .rotation
}

/// How many error exits the app's `AppExit` messages carry.
fn error_exits(app: &App) -> usize {
    app.world()
        .resource::<Messages<AppExit>>()
        .iter_current_update_messages()
        .filter(|exit| matches!(exit, AppExit::Error(_)))
        .count()
}

/// The full normal-mode game wiring, headless: the post chain, the scene,
/// the look plugin, the game's real asset ledger, and the wake driver
/// itself. The look plugin's systems read the input state `DefaultPlugins`
/// initializes in the real game; a rendererless test app provides it
/// directly (the same shape the readiness tests use).
fn normal_mode_app() -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        ImagePlugin::default(),
        // The driver ticks the virtual clock; TimePlugin provides the clocks
        // DefaultPlugins would in the real app.
        bevy::time::TimePlugin,
    ));
    app.init_asset::<Mesh>().init_asset::<StandardMaterial>();
    app.add_message::<WindowFocused>()
        .init_resource::<ButtonInput<KeyCode>>()
        .init_resource::<AccumulatedMouseMotion>();
    app.add_plugins((
        crate::post::GamePostChainPlugin,
        crate::scene::StasisScenePlugin,
        crate::player::PlayerLookPlugin,
    ));
    let ledger = {
        let masks = app.world().resource::<crate::post::PostChainAssets>();
        GameAssets::game_required_assets(masks)
    };
    app.insert_resource(ledger);
    app.add_message::<AppExit>();
    app.add_systems(Update, crate::readiness::poll_required_assets_or_exit);
    app.add_plugins(GameWakePlugin);
    app
}

/// The normal-mode wiring, headless over the game's own plugin set: the rig
/// camera carries the closed eyelid from its first frame, the loading cover
/// sits above it, the machine holds at the authored opening, and — honestly
/// named — the bridge reads `NotStarted` because this app has no render
/// sub-app to produce pipeline state. Presentation itself needs a device;
/// this pins the wiring and the hold, not the pixels.
#[test]
fn normal_mode_wiring_attaches_the_closed_eyelid_and_holds_waking() {
    let mut app = normal_mode_app();
    for _ in 0..3 {
        app.update();
    }
    let mut cams = app
        .world_mut()
        .query_filtered::<(&WakeEyelidMaterial, &Camera), With<PlayerPitch>>();
    let (material, rig_camera_order) = cams
        .single(app.world())
        .map(|(material, rig_camera)| (*material, rig_camera.order))
        .expect("the rig camera carries the effect");
    assert_eq!(
        material,
        WakeEyelidMaterial::CLOSED,
        "attached fully closed"
    );
    let mut orders = app
        .world_mut()
        .query_filtered::<&Camera, With<bevy::camera::Camera2d>>();
    let cover_camera = orders
        .single(app.world())
        .expect("the loading cover is the one 2D camera");
    assert!(
        cover_camera.order > rig_camera_order,
        "the cover draws above the game camera"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "no bridge state exists headless, so the machine holds at the opening"
    );
    let state = app.world().resource::<SimWakeState>();
    assert!(!state.is_started(), "the machine never starts unready");
    assert_eq!(
        app.world().resource::<WakeEyelidPipelineReadiness>(),
        &WakeEyelidPipelineReadiness::NotStarted,
        "no render sub-app: the bridge honestly reports no pipeline state"
    );
    assert_eq!(error_exits(&app), 0, "a loading game does not exit");
}

/// Either gate leg pending holds everything: the effect stays closed, the
/// cover stays up, the phase stays `Waking`, and the machine never starts —
/// no matter how long the updates run.
#[test]
fn delayed_readiness_holds_closed_without_phase_advance() {
    let holds: [(WakeEyelidPipelineReadiness, &[(&str, AssetLoad)]); 3] = [
        (
            WakeEyelidPipelineReadiness::NotStarted,
            &[(MASK, AssetLoad::Loaded)],
        ),
        (
            WakeEyelidPipelineReadiness::Compiling,
            &[(MASK, AssetLoad::Loaded)],
        ),
        (
            WakeEyelidPipelineReadiness::Ready,
            &[(MASK, AssetLoad::Pending)],
        ),
    ];
    for (readiness, assets) in holds {
        let mut app = driver_app(assets);
        app.world_mut().insert_resource(readiness);
        for _ in 0..5 {
            app.update();
        }
        let (yaw, camera) = rig_entities(&mut app);
        assert_eq!(
            eyelid(&app, camera),
            Some(WakeEyelidMaterial::CLOSED),
            "{readiness:?}: the effect holds fully closed"
        );
        assert!(
            app.world().get_entity(yaw).is_ok()
                && app
                    .world()
                    .resource::<LoadingCover>()
                    .0
                    .is_some_and(|cover| app.world().get_entity(cover).is_ok()),
            "{readiness:?}: the loading cover stays up"
        );
        assert_eq!(
            app.world().resource::<SimWakePhase>().phase(),
            WakePhase::Waking,
            "{readiness:?}: the phase holds at the authored opening"
        );
        let state = app.world().resource::<SimWakeState>();
        assert!(!state.is_started(), "{readiness:?}: nothing starts");
        assert_eq!(state.0.current_tick(), 0, "{readiness:?}: no ticks pass");
        assert_eq!(error_exits(&app), 0);
    }
}

/// The gate's first holding update starts the machine exactly once, at
/// logical tick zero sampling bitwise-closed; later gate-open updates are
/// the machine's own `AlreadyStarted` no-op: no restart, no ticks, no cover
/// back.
#[test]
fn the_first_ready_update_starts_once_at_tick_zero_and_duplicates_do_nothing() {
    let mut app = driver_app(&[(MASK, AssetLoad::Pending)]);
    app.update();
    let held_cover = app
        .world()
        .resource::<LoadingCover>()
        .0
        .expect("the cover is up while the gate is closed");
    open_gate(&mut app);
    app.update();

    let state = app.world().resource::<SimWakeState>();
    assert!(state.is_started(), "the gate opened the machine");
    assert_eq!(state.0.current_tick(), 0, "the start is tick zero");
    assert_eq!(
        state.sample(),
        gone_sim::WakeSample::CLOSED,
        "tick zero samples the closed rest state"
    );
    let (_, camera) = rig_entities(&mut app);
    assert_eq!(
        eyelid(&app, camera),
        Some(WakeEyelidMaterial::CLOSED),
        "the effect holds the closed sample"
    );
    assert_eq!(
        app.world().resource::<LoadingCover>().0,
        None,
        "the cover resource forgets its entity at the lift"
    );
    assert!(
        app.world().get_entity(held_cover).is_err(),
        "the cover camera is despawned at the start"
    );

    // Duplicates: several more gate-open updates with no time to tick. The
    // machine must not restart (the tick counter cannot go backward or
    // re-zero), the effect must not re-attach, and the cover must stay down.
    for _ in 0..4 {
        app.update();
    }
    let state = app.world().resource::<SimWakeState>();
    assert!(state.is_started());
    assert_eq!(state.0.current_tick(), 0, "no restart, no phantom ticks");
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the machine started but the timeline has not completed"
    );
    assert_eq!(eyelid(&app, camera), Some(WakeEyelidMaterial::CLOSED));
}

/// The timeline runs to the authored completion tick — not a frame-count
/// guess — and the completion frame hands off exactly once: `Waking ->
/// AwakeInPod` through the shared boundary, the neutral pose projected, the
/// effect removed. Before the boundary the machine is still `Waking`; after
/// it, further updates change nothing.
#[test]
fn completion_lands_at_the_authored_tick_and_hands_off_once() {
    let timeline = authored();
    let complete = timeline.complete_tick();
    let mut app = driver_app(&[(MASK, AssetLoad::Pending)]);
    open_gate(&mut app);
    app.update();
    let (yaw, camera) = rig_entities(&mut app);

    feed_ticks(&mut app, complete - 1);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "one tick before the authored completion the wake still owns the camera"
    );
    assert!(
        eyelid(&app, camera).is_some(),
        "the effect is still attached before completion"
    );

    feed_tick(&mut app);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the authored completion tick hands off to AwakeInPod"
    );
    let state = app.world().resource::<SimWakeState>();
    assert!(state.is_complete(), "the machine rests at the neutral hold");
    assert_eq!(
        eyelid(&app, camera),
        None,
        "completion removes the effect from the camera"
    );
    // The completion frame projected the plain authored pose (look has not
    // moved the angles, sway is done): the rig reads exactly the identity
    // pose the fixture spawned.
    assert_eq!(yaw_rotation(&app, yaw), Quat::IDENTITY);
    assert_eq!(pitch_rotation(&app, camera), Quat::IDENTITY);

    feed_ticks(&mut app, 3);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the handoff fires exactly once; later updates change nothing"
    );
    assert_eq!(eyelid(&app, camera), None, "the effect stays removed");
    assert_eq!(error_exits(&app), 0);
}

/// The driver runs the authored timeline at its authored pace: at an
/// authored boundary tick the camera's uniform is exactly the timeline's
/// sample there — the production duration conversion, sampled through the
/// real driver, not a parallel implementation.
#[test]
fn the_driven_timeline_matches_the_authored_samples_at_their_boundaries() {
    let timeline = authored();
    let boundaries = WakeTimeline::authored_boundaries();
    let mut app = driver_app(&[(MASK, AssetLoad::Pending)]);
    open_gate(&mut app);
    app.update();
    let (_, camera) = rig_entities(&mut app);

    let mut fed = 0u64;
    for boundary in [
        boundaries.first_opening_start,
        boundaries.first_blink_start,
        boundaries.second_opening_start,
        boundaries.second_blink_start,
        boundaries.final_opening_start,
    ] {
        feed_ticks(&mut app, boundary - fed);
        fed = boundary;
        let expected = WakeEyelidMaterial::from_sample(timeline.sample_at(boundary));
        assert_eq!(
            eyelid(&app, camera),
            Some(expected),
            "at authored boundary tick {boundary} the effect carries the authored sample"
        );
    }
}

/// The sway projection is drift-free: reaching the same logical tick through
/// different update batchings lands the rig on the same rotation bits, and
/// those bits are the pure projection of the (constant) look angles plus the
/// tick's authored sway — never an accumulation of past frames.
#[test]
fn sway_composes_to_the_same_pose_regardless_of_tick_batching() {
    let timeline = authored();
    let at = WakeTimeline::authored_boundaries().second_opening_start + 7;
    let expected_sway = timeline.sample_at(at).sway_offset;

    // Batching A: one tick per update, all the way to `at`.
    let mut small_steps = driver_app(&[(MASK, AssetLoad::Pending)]);
    open_gate(&mut small_steps);
    small_steps.update();
    feed_ticks(&mut small_steps, at);

    // Batching B: three ticks per update. Deltas near a tick boundary are
    // the interesting case; three ticks is far enough from one to differ.
    let mut chunked = driver_app(&[(MASK, AssetLoad::Pending)]);
    open_gate(&mut chunked);
    chunked.update();
    for _ in 0..at / 3 {
        chunked
            .world_mut()
            .resource_mut::<Time<Virtual>>()
            .advance_by(Duration::from_secs_f32(3.0 * LOGICAL_TICK_SECS));
        chunked.update();
    }
    feed_ticks(&mut chunked, at % 3);

    for app in [&mut small_steps, &mut chunked] {
        let state = app.world().resource::<SimWakeState>();
        assert_eq!(
            state.0.current_tick(),
            at,
            "both batchings consumed exactly the authored tick count"
        );
    }
    let (small_yaw, small_cam) = rig_entities(&mut small_steps);
    let (chunk_yaw, chunk_cam) = rig_entities(&mut chunked);
    // Bitwise: a projection recomputed from the same inputs, not two paths
    // that merely agree to an epsilon.
    let bits = |quat: Quat| {
        [
            quat.x.to_bits(),
            quat.y.to_bits(),
            quat.z.to_bits(),
            quat.w.to_bits(),
        ]
    };
    assert_eq!(
        bits(yaw_rotation(&small_steps, small_yaw)),
        bits(yaw_rotation(&chunked, chunk_yaw)),
        "yaw sway identical across batchings"
    );
    assert_eq!(
        bits(pitch_rotation(&small_steps, small_cam)),
        bits(pitch_rotation(&chunked, chunk_cam)),
        "pitch sway identical across batchings"
    );
    // And the value is the projection, not an accumulation: yaw rotation is
    // from_rotation_y(0 + sway.x) with the fixture's zero look angles, so a
    // drifting sum would have walked off the authored offset within `at`
    // ticks of writes.
    let expected_yaw = Quat::from_rotation_y(expected_sway.x);
    assert_eq!(
        bits(yaw_rotation(&small_steps, small_yaw)),
        bits(expected_yaw),
        "the pose is the authored sway projection at this tick"
    );
}

/// A fatal pipeline failure exits the game nonzero, naming bevy's own error
/// text — never a silent hold on a pass that will never run.
#[test]
fn a_failed_pipeline_exits_naming_the_actual_error() {
    let mut app = driver_app(&[(MASK, AssetLoad::Loaded)]);
    app.world_mut()
        .insert_resource(WakeEyelidPipelineReadiness::Errored);
    app.world_mut()
        .insert_resource(WakeEyelidPipelineFailure(Some(
            "Could not create shader module: the wgsl was rejected".to_owned(),
        )));
    app.update();
    assert_eq!(
        error_exits(&app),
        1,
        "the failed pipeline is a hard error, exactly one exit"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the machine never starts on a failed pipeline"
    );
}

/// Assets and pipeline fully ready, a primary window present, and no
/// drawable frame for longer than the entire authored sequence: the machine
/// stays unstarted at logical zero, the phase at the authored opening, the
/// sample closed — the issue #27 gap (the whole wake playing invisibly into
/// a window that never presents) cannot run the timeline, and the held
/// seconds bank nothing.
#[test]
fn a_windowed_gate_without_a_drawable_frame_holds_the_whole_machine() {
    let mut app = windowed_driver_app(&[(MASK, AssetLoad::Loaded)]);
    open_gate(&mut app);
    feed_ticks(&mut app, authored().complete_tick() + 10);
    let state = app.world().resource::<SimWakeState>();
    assert!(!state.is_started(), "no drawable frame: nothing starts");
    assert_eq!(state.0.current_tick(), 0, "no ticks and no banked seconds");
    assert_eq!(
        state.sample(),
        gone_sim::WakeSample::CLOSED,
        "the sample holds the closed rest state"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the phase holds at the authored opening"
    );
    let (_, camera) = rig_entities(&mut app);
    assert_eq!(eyelid(&app, camera), Some(WakeEyelidMaterial::CLOSED));
    assert_eq!(error_exits(&app), 0);
}

/// The first acknowledged closed frame starts the machine once, at logical
/// tick zero, spending no wake delta on the start update; the timeline's
/// first tick lands on the next acknowledged update, exactly one.
#[test]
fn the_first_acknowledged_frame_starts_once_at_tick_zero_without_spending_delta() {
    let mut app = windowed_driver_app(&[(MASK, AssetLoad::Loaded)]);
    open_gate(&mut app);
    app.update();
    let held_cover = app
        .world()
        .resource::<LoadingCover>()
        .0
        .expect("the cover is still up behind the presentation leg");
    assert!(
        !app.world().resource::<SimWakeState>().is_started(),
        "the windowed gate holds before the first closed frame"
    );

    ack_drawable_frame(&mut app);
    feed_tick(&mut app);
    let state = app.world().resource::<SimWakeState>();
    assert!(
        state.is_started(),
        "the first closed frame starts the machine"
    );
    assert_eq!(state.0.current_tick(), 0, "the start spends no wake delta");
    assert_eq!(
        state.sample(),
        gone_sim::WakeSample::CLOSED,
        "tick zero samples the closed rest state"
    );
    assert_eq!(app.world().resource::<LoadingCover>().0, None);
    assert!(
        app.world().get_entity(held_cover).is_err(),
        "the cover lifted with the acknowledged start"
    );

    feed_tick(&mut app);
    assert_eq!(
        app.world().resource::<SimWakeState>().0.current_tick(),
        1,
        "the first timeline tick lands on the next acknowledged update, exactly one"
    );
}

/// Duplicate acknowledgements never restart, re-zero, or re-cover the
/// machine: the sticky mirror latching again is the machine's own
/// `AlreadyStarted` no-op.
#[test]
fn duplicate_acknowledgements_never_restart_or_rezero_the_machine() {
    let mut app = windowed_driver_app(&[(MASK, AssetLoad::Loaded)]);
    open_gate(&mut app);
    app.update();
    ack_drawable_frame(&mut app);
    app.update();
    let (_, camera) = rig_entities(&mut app);
    for _ in 0..4 {
        ack_drawable_frame(&mut app);
        app.update();
    }
    let state = app.world().resource::<SimWakeState>();
    assert!(state.is_started(), "the machine stays started");
    assert_eq!(state.0.current_tick(), 0, "no restart, no phantom ticks");
    assert_eq!(eyelid(&app, camera), Some(WakeEyelidMaterial::CLOSED));
    assert_eq!(
        app.world().resource::<LoadingCover>().0,
        None,
        "the cover never comes back"
    );
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "the timeline has started but not completed"
    );
}

/// A frame without the drawable banks no time mid-wake: occlusion-shaped
/// updates hold the tick exactly where it is, and the next acknowledged
/// update consumes exactly one tick — no catch-up on seconds the window
/// never presented.
#[test]
fn a_frame_without_the_drawable_banks_no_time_mid_wake() {
    let mut app = windowed_driver_app(&[(MASK, AssetLoad::Loaded)]);
    open_gate(&mut app);
    app.update();
    ack_drawable_frame(&mut app);
    app.update();
    feed_ticks(&mut app, 5);
    assert_eq!(
        app.world().resource::<SimWakeState>().0.current_tick(),
        5,
        "the acknowledged updates drive the timeline"
    );

    lose_drawable(&mut app);
    feed_ticks(&mut app, 3);
    assert_eq!(
        app.world().resource::<SimWakeState>().0.current_tick(),
        5,
        "the un-presented updates bank nothing"
    );

    ack_drawable_frame(&mut app);
    feed_tick(&mut app);
    assert_eq!(
        app.world().resource::<SimWakeState>().0.current_tick(),
        6,
        "the resume consumes exactly one tick, no catch-up"
    );
}

/// Completion in a windowed run still requires driven acknowledged
/// progression: `AwakeInPod` lands exactly at the authored completion tick
/// once the acknowledged updates have driven the machine there, and later
/// acknowledged updates change nothing.
#[test]
fn completion_requires_driven_acknowledged_progression() {
    let complete = authored().complete_tick();
    let mut app = windowed_driver_app(&[(MASK, AssetLoad::Loaded)]);
    open_gate(&mut app);
    app.update();
    ack_drawable_frame(&mut app);
    app.update();
    feed_ticks(&mut app, complete - 1);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::Waking,
        "one acknowledged tick before the authored completion the wake still owns the camera"
    );
    feed_tick(&mut app);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the authored completion tick hands off exactly at its tick"
    );
    feed_ticks(&mut app, 3);
    assert_eq!(
        app.world().resource::<SimWakePhase>().phase(),
        WakePhase::AwakeInPod,
        "the handoff fired exactly once"
    );
    assert_eq!(error_exits(&app), 0);
}
