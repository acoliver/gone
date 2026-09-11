//! Hermetic coverage of the body-motion wiring (issue #7, app wiring of the
//! sim core): the get-up's numeric path to Standing at the waypoint and its
//! typed wrong-phase rejection, the walk's frozen ramp along the yaw frame,
//! the walk-before-Standing gate, the phase policy's dropped presses, and
//! the scripted Move action driving the walk exactly like device input.
//! No renderer anywhere: the real plugin chain runs headless.

use bevy::app::{App, TaskPoolPlugin};
use bevy::asset::{AssetApp, AssetPlugin};
use bevy::ecs::prelude::With;
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::math::Vec3;
use bevy::transform::components::Transform;
use gone_sim::controller::{
    CAPSULE_RADIUS, CAPSULE_STANDING_HEIGHT, PENETRATION_TOLERANCE, STEADY_INITIAL_SPEED_FACTOR,
    STEADYING_TIME_CONSTANT, SURVIVAL_WALK_SPEED,
};
use gone_sim::exit::{ExitError, ExitPath, ExitPose};
use gone_sim::walk::WalkError;
use gone_sim::{Aabb, Capsule, ColliderSet, WakePhase};

use crate::bootstrap::ScenarioTime;
use crate::harness::{
    Button, ButtonEdge, Edge, InputAdapter, Key, MoveMotion, ScriptedAction, TICKS_PER_SECOND,
};
use crate::post::GamePostChainPlugin;
use crate::scene::{PlayerExitPath, SimColliders, SimWakePhase, StasisScenePlugin};

use super::motion::{
    BodyState, MotionFailure, MotionFailureKind, PlayerMotion, WalkFrame, get_up_eye, standing_eye,
    start_get_up, start_walk, take_walk_step,
};
use super::{
    GameplayInput, LookInputMode, PlayerLookPlugin, PlayerMotionPlugin, PlayerPitch, PlayerYaw,
};

/// The tests' fixed tick: the scenario default's one step, at the house
/// u64-to-f32 conversion the fixed clock uses elsewhere.
fn dt() -> f32 {
    1.0 / f32::from(u16::try_from(TICKS_PER_SECOND).unwrap_or(u16::MAX))
}

/// Per-component closeness at the codebase's position tolerance (the
/// authored path re-derives its poses through a few f32 roundings).
fn assert_close(actual: Vec3, expected: Vec3, label: &str) {
    let drift = (actual - expected).abs();
    assert!(
        drift.x < 1e-5 && drift.y < 1e-5 && drift.z < 1e-5,
        "{label}: expected {expected:?}, got {actual:?}"
    );
}

/// A test app with the real game plugin chain, headless: the post chain,
/// the stasis scene (the sim resources, colliders, exit path, room build),
/// the look plugin (rig spawn, look angles, the shared input plane), and
/// the motion plugin. The phase is overridden after the plugin build so
/// each test starts the machine exactly where it needs it; `ScenarioTime`
/// is inserted so the body advances on driven ticks like a harness lane
/// (the [`drive`] helper plays the drive half). Scripted look mode keeps
/// the look systems armed without a cursor, as on a canary run.
fn motion_app(phase: WakePhase) -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        bevy::image::ImagePlugin::default(),
    ));
    app.init_asset::<bevy::mesh::Mesh>()
        .init_asset::<bevy::pbr::StandardMaterial>();
    app.add_message::<bevy::window::WindowFocused>()
        .init_resource::<ButtonInput<KeyCode>>()
        .init_resource::<AccumulatedMouseMotion>()
        .insert_resource(LookInputMode::Scripted);
    app.add_plugins((
        GamePostChainPlugin,
        StasisScenePlugin,
        PlayerLookPlugin,
        PlayerMotionPlugin,
    ));
    app.insert_resource(SimWakePhase::new(phase));
    app.insert_resource(ScenarioTime::new(TICKS_PER_SECOND));
    app
}

/// One driven update: advance the scenario clock by its fixed step (the
/// drive half's `advance_tick`) and run the update chain — exactly what a
/// harness lane's driven tick does to the body.
fn drive(app: &mut App) {
    app.world_mut()
        .resource_mut::<ScenarioTime>()
        .advance_tick();
    app.update();
}

/// The machine's current phase.
fn phase_of(app: &App) -> WakePhase {
    app.world().resource::<SimWakePhase>().phase()
}

/// The mirror's state and the capsule it currently holds.
fn motion_of(app: &App) -> (BodyState, Option<Capsule>) {
    let motion = app.world().resource::<PlayerMotion>();
    (motion.state(), motion.capsule())
}

/// The run's recorded motion failure, if any.
fn failure_of(app: &App) -> Option<&MotionFailureKind> {
    app.world().resource::<MotionFailure>().kind()
}

/// The authored exit path the scene plugin built from the frozen registry
/// against the tray floor the cavity build constructs — the one
/// construction path, read back through the resource it produced.
fn exit_path_of(app: &App) -> ExitPath {
    app.world().resource::<PlayerExitPath>().0
}

/// The rig yaw parent's translation — the eye point.
fn rig_eye(app: &mut App) -> Vec3 {
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    yaws.single(app.world())
        .expect("the rig's yaw parent exists")
        .translation
}

/// Offer one scripted activate press on the shared plane — the same offer
/// the harness adapter's `Press { Key::Activate }` makes, and the one the
/// device producer makes for a fresh Space press.
fn offer_activate_press(app: &mut App) {
    app.world_mut()
        .resource_mut::<GameplayInput>()
        .offer_edges(core::iter::once(ButtonEdge {
            button: Button::Key(Key::Activate),
            edge: Edge::Press,
        }));
}

/// Press activate and drive the four authored segments to `Standing`.
fn stand_up(app: &mut App) {
    offer_activate_press(app);
    drive(app);
    assert_eq!(
        phase_of(app),
        WakePhase::ExitingPod,
        "the press starts the get-up"
    );
    for _ in 0..4 {
        drive(app);
    }
    assert_eq!(phase_of(app), WakePhase::Standing, "the get-up completed");
}

/// A hermetic world: one floor slab topping out at y = 0.
fn floor_colliders() -> SimColliders {
    let mut set = ColliderSet::new();
    set.insert(
        Aabb::from_min_max(Vec3::new(-10.0, -1.0, -10.0), Vec3::new(10.0, 0.0, 10.0))
            .expect("the floor slab is a valid box"),
    );
    SimColliders::new(set)
}

/// A standing capsule resting on y = 0, clear of everything.
fn standing_capsule(x: f32, z: f32) -> Capsule {
    let segment = CAPSULE_STANDING_HEIGHT - 2.0 * CAPSULE_RADIUS;
    let foot_y = CAPSULE_RADIUS + PENETRATION_TOLERANCE;
    Capsule {
        foot: Vec3::new(x, foot_y, z),
        head: Vec3::new(x, foot_y + segment, z),
    }
}

/// The frozen steadying ramp at `seconds` of accumulated sim time (the
/// formula `gone_sim::walk` froze, restated here so the wiring test pins
/// the numbers, not the implementation).
fn ramp_at(seconds: f32) -> f32 {
    let multiplier =
        1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * (-seconds / STEADYING_TIME_CONSTANT).exp();
    SURVIVAL_WALK_SPEED * multiplier
}

/// The get-up walks the authored path segment by segment — one per driven
/// tick — and lands `Standing` at the waypoint, with the rig's eye on the
/// capsule the whole way (head sphere during the swing, standing height on
/// the floor).
#[test]
fn the_get_up_walks_the_authored_path_to_standing_at_the_waypoint() {
    let mut app = motion_app(WakePhase::AwakeInPod);
    app.update();
    let path = exit_path_of(&app);
    let waypoint = path.waypoint();

    offer_activate_press(&mut app);
    drive(&mut app);
    assert_eq!(phase_of(&app), WakePhase::ExitingPod);
    assert_eq!(motion_of(&app).0, BodyState::GetUp);
    assert!(failure_of(&app).is_none());

    for (index, expected) in path.poses().iter().enumerate().skip(1) {
        drive(&mut app);
        let capsule = motion_of(&app).1.expect("a controller holds the capsule");
        assert_close(capsule.foot, expected.foot(), "segment foot");
        assert_close(capsule.head, expected.head(), "segment head");
        if index == 1 {
            assert_close(
                rig_eye(&mut app),
                get_up_eye(capsule),
                "eye on the head sphere",
            );
        }
        if index + 1 < path.poses().len() {
            assert_eq!(phase_of(&app), WakePhase::ExitingPod, "mid-path");
        }
    }
    assert_eq!(
        phase_of(&app),
        WakePhase::Standing,
        "completion is Standing at the waypoint"
    );
    assert_eq!(motion_of(&app).0, BodyState::Walk);
    let capsule = motion_of(&app).1.expect("the walk holds the capsule");
    assert_close(capsule.foot, waypoint.foot(), "waypoint foot");
    assert_close(capsule.head, waypoint.head(), "waypoint head");
    assert_close(rig_eye(&mut app), standing_eye(capsule), "standing eye");
    assert!(failure_of(&app).is_none());
}

/// The machine's own typed contract rejects a get-up outside `AwakeInPod`
/// and leaves the machine unchanged: the app's gate never starts one in a
/// dropped phase, so this path can only mean a wiring bug, and it fails
/// fast. The path under test is the scene plugin's own build.
#[test]
fn a_get_up_outside_awake_in_pod_is_a_typed_rejection() {
    let app = motion_app(WakePhase::Waking);
    let exit_path = exit_path_of(&app);
    let mut phase = SimWakePhase::new(WakePhase::Waking);
    let failure = start_get_up(&mut phase, &exit_path).expect_err("a get-up in Waking is rejected");
    assert_eq!(
        failure,
        MotionFailureKind::GetUp(ExitError::WrongPhase {
            expected: WakePhase::AwakeInPod,
            current: WakePhase::Waking,
        })
    );
    assert_eq!(
        phase.phase(),
        WakePhase::Waking,
        "the rejection leaves the machine unchanged"
    );
}

/// The first walk steps land exactly on the frozen ramp values, along the
/// yaw frame the intent was framed in: forward runs the look axis
/// `(sin yaw, 0, cos yaw)`, strafe the right axis `(cos yaw, 0, -sin yaw)`,
/// first step at the frozen initial product, the next at the exponential
/// ramp.
#[test]
fn the_first_walk_steps_follow_the_frozen_ramp_along_the_yaw_frame() {
    let colliders = floor_colliders();
    let phase = SimWakePhase::new(WakePhase::Standing);
    let start = standing_capsule(0.0, 0.0);
    let mut walk = start_walk(phase.phase(), start).expect("Standing starts the walk");
    let yaw: f32 = 1.234;
    let (sin, cos) = yaw.sin_cos();

    take_walk_step(
        &mut walk,
        WalkFrame {
            yaw,
            dt: dt(),
            colliders: &colliders,
        },
        MoveMotion {
            forward: 1.0,
            strafe: 0.0,
        },
    )
    .expect("the first step sweeps free");
    let first = STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED * dt();
    assert_close(
        walk.capsule().foot,
        start.foot + Vec3::new(sin, 0.0, cos) * first,
        "the first step follows the look axis at the frozen initial speed",
    );
    assert!(
        (walk.speed() - ramp_at(dt())).abs() < 1e-6,
        "the ramp advanced by one tick: {} vs {}",
        walk.speed(),
        ramp_at(dt())
    );

    take_walk_step(
        &mut walk,
        WalkFrame {
            yaw,
            dt: dt(),
            colliders: &colliders,
        },
        MoveMotion {
            forward: 0.0,
            strafe: 1.0,
        },
    )
    .expect("the second step sweeps free");
    let second = ramp_at(dt()) * dt();
    assert_close(
        walk.capsule().foot,
        start.foot + Vec3::new(sin, 0.0, cos) * first + Vec3::new(cos, 0.0, -sin) * second,
        "strafe follows the right axis at the ramped speed",
    );
}

/// Walking before `Standing` is the machine's typed rejection, not a
/// fallback or a clamp.
#[test]
fn a_walk_before_standing_is_a_typed_rejection() {
    let phase = SimWakePhase::new(WakePhase::AwakeInPod);
    let failure = start_walk(phase.phase(), standing_capsule(0.0, 0.0))
        .expect_err("walking before Standing is rejected");
    assert_eq!(
        failure,
        MotionFailureKind::Walk(WalkError::WrongPhase {
            expected: WakePhase::Standing,
            current: WakePhase::AwakeInPod,
        })
    );
}

/// A get-up press in `Waking` is dropped under the phase policy — not
/// buffered, not a failure — and it does not fire once the machine later
/// reaches `AwakeInPod`: the player presses again to leave the pod.
#[test]
fn a_get_up_press_in_waking_is_dropped_not_buffered() {
    let mut app = motion_app(WakePhase::Waking);
    app.update();
    offer_activate_press(&mut app);
    drive(&mut app);
    assert_eq!(phase_of(&app), WakePhase::Waking, "the wake holds the body");
    assert_eq!(motion_of(&app).0, BodyState::Lying);
    assert!(
        failure_of(&app).is_none(),
        "a dropped press is not a failure"
    );

    app.world_mut()
        .insert_resource(SimWakePhase::new(WakePhase::AwakeInPod));
    drive(&mut app);
    assert_eq!(
        phase_of(&app),
        WakePhase::AwakeInPod,
        "the dropped press never fires late"
    );
    assert_eq!(motion_of(&app).0, BodyState::Lying);
}

/// Movement intent before `Standing` moves nothing and starts no get-up:
/// the walk gate holds until the waypoint lands.
#[test]
fn movement_intent_before_standing_moves_nothing() {
    let mut app = motion_app(WakePhase::AwakeInPod);
    app.update();
    let before = rig_eye(&mut app);

    app.world_mut()
        .resource_mut::<GameplayInput>()
        .offer_movement(MoveMotion {
            forward: 1.0,
            strafe: 0.0,
        });
    drive(&mut app);

    assert_eq!(
        phase_of(&app),
        WakePhase::AwakeInPod,
        "movement is not get-up intent"
    );
    assert_eq!(motion_of(&app).0, BodyState::Lying);
    assert_eq!(
        rig_eye(&mut app),
        before,
        "nothing translates the lying player"
    );
    assert!(failure_of(&app).is_none());
}

/// A scripted `MoveDelta` action drives the walk to exactly the capsule a
/// held device key produces: both channels are offers on the same shared
/// plane, so the body cannot tell the runner from a human.
#[test]
fn a_scripted_move_drives_the_walk_exactly_like_device_input() {
    let forward = 0.8;
    let steps = 10_usize;

    let mut device = motion_app(WakePhase::AwakeInPod);
    device.update();
    stand_up(&mut device);
    let start = motion_of(&device).1.expect("the walk holds the capsule");
    for _ in 0..steps {
        // The device producer's per-frame held-key offer.
        device
            .world_mut()
            .resource_mut::<GameplayInput>()
            .offer_movement(MoveMotion {
                forward,
                strafe: 0.0,
            });
        drive(&mut device);
    }

    let mut scripted = motion_app(WakePhase::AwakeInPod);
    scripted.update();
    stand_up(&mut scripted);
    let actions: Vec<ScriptedAction> = (0..steps as u64)
        .map(|tick| ScriptedAction::move_delta(tick, forward, 0.0))
        .collect();
    let mut adapter = InputAdapter::with_actions(actions, TICKS_PER_SECOND);
    for _ in 0..steps {
        // Exactly the offer `drive_ticks` makes: the tick's step movement.
        let step = adapter.step();
        scripted
            .world_mut()
            .resource_mut::<GameplayInput>()
            .offer_movement(step.movement);
        drive(&mut scripted);
    }

    assert_eq!(motion_of(&device).0, BodyState::Walk);
    assert_eq!(motion_of(&scripted).0, BodyState::Walk);
    let device_capsule = motion_of(&device)
        .1
        .expect("the device walk holds the capsule");
    let scripted_capsule = motion_of(&scripted)
        .1
        .expect("the scripted walk holds the capsule");
    assert_eq!(
        device_capsule, scripted_capsule,
        "the two channels are one pathway"
    );
    let walked = (device_capsule.foot - start.foot).length();
    assert!(
        walked > 0.01,
        "the walk actually moved: {walked} m in {steps} steps"
    );
    assert!(failure_of(&device).is_none());
    assert!(failure_of(&scripted).is_none());
}

/// The rig's pitch camera never carries a translation: the eye lives on the
/// yaw parent alone, so look keeps owning the rotations while the motion
/// slice owns the position.
#[test]
fn the_pitch_camera_stays_at_its_local_origin_while_the_body_moves() {
    let mut app = motion_app(WakePhase::AwakeInPod);
    app.update();
    stand_up(&mut app);
    let mut pitches = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerPitch>>();
    let pitch = *pitches
        .single(app.world())
        .expect("the rig's pitch camera exists");
    assert_eq!(
        pitch.translation,
        Vec3::ZERO,
        "the camera child keeps its local origin"
    );
}

/// The waypoint pose is a standing capsule on the room floor (the authored
/// standing height), so the standing eye derivation and the walk start from
/// grounded geometry. The path under test is the scene plugin's own build.
#[test]
fn the_authored_waypoint_stands_on_the_room_floor() {
    let app = motion_app(WakePhase::Waking);
    let waypoint: ExitPose = exit_path_of(&app).waypoint();
    let segment = CAPSULE_STANDING_HEIGHT - 2.0 * CAPSULE_RADIUS;
    assert!(
        (waypoint.foot().y - (CAPSULE_RADIUS + PENETRATION_TOLERANCE)).abs() < 1e-5,
        "the foot rests one tolerance above the floor"
    );
    assert!(
        (waypoint.head().y - waypoint.foot().y - segment).abs() < 1e-5,
        "the capsule stands at the frozen height"
    );
}
