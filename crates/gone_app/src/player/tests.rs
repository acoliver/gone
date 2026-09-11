//! First-person look and cursor-policy regressions, asserted against the
//! real plugin chain (no renderer): pose seeding, the input-mode cursor
//! gates, plane consumption, and the pure integration math.

use super::{
    Button, ButtonEdge, CursorTarget, Edge, Key, LOOK_SENSITIVITY, LookAngles, LookInputMode,
    PITCH_LIMIT, PlayerLookPlugin, PlayerPitch, PlayerYaw, apply_cursor_target,
    integrate_look_radians, look_delta_from_pixels, wrap_angle,
};
use crate::harness::{Delta, InputAdapter, ScriptedAction, TICKS_PER_SECOND};
use crate::scene::{PlayerSpawn, PlayerSpawnPose};
use bevy::app::{App, TaskPoolPlugin};
use bevy::asset::AssetPlugin;
use bevy::camera::Hdr;
use bevy::core_pipeline::tonemapping::Tonemapping;
use bevy::ecs::prelude::{ChildOf, With};
use bevy::image::ImagePlugin;
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::math::{Quat, Vec2};
use bevy::post_process::auto_exposure::AutoExposure;
use bevy::post_process::effect_stack::Vignette;
use bevy::prelude::Camera3d;
use bevy::transform::components::Transform;
use bevy::window::{CursorGrabMode, CursorOptions, Window, WindowFocused};

use gone_sim::WakePhase;

use crate::post::{GamePostChainPlugin, PostChainAssets};
use crate::scene::SimWakePhase;

/// The device-channel pure function under test: one pixel delta in, new
/// (yaw, pitch) radians out. Exactly what the device producer offers the
/// shared plane and the integrator applies.
fn integrate_look(yaw: f32, pitch: f32, delta_px: Vec2) -> (f32, f32) {
    integrate_look_radians(yaw, pitch, look_delta_from_pixels(delta_px))
}

#[test]
fn pitch_clamps_before_over_rotation() {
    // Exact float equality, expressed as a sub-ulp distance: one
    // f32::EPSILON is one ulp(1.0), while one pixel rotates ~2e-3 rad, so
    // any real deviation would exceed it by orders of magnitude. A pixel
    // delta that would rotate far past the vertical lands exactly on the
    // stop, in both directions, from any starting pitch.
    let (_, up) = integrate_look(0.0, 0.0, Vec2::new(0.0, -1_000_000.0));
    assert!((up - PITCH_LIMIT).abs() < f32::EPSILON);
    let (_, down) = integrate_look(0.0, 0.0, Vec2::new(0.0, 1_000_000.0));
    assert!((down + PITCH_LIMIT).abs() < f32::EPSILON);
    // An overshoot from just below the stop cannot pass it either.
    let (_, over) = integrate_look(0.0, PITCH_LIMIT - 0.01, Vec2::new(0.0, -1000.0));
    assert!((over - PITCH_LIMIT).abs() < f32::EPSILON);
    // Many small steps accumulate to the stop and stop there.
    let mut pitch = 0.0;
    for _ in 0..10_000 {
        let (_, next) = integrate_look(0.0, pitch, Vec2::new(0.0, -10.0));
        pitch = next;
    }
    assert!((pitch - PITCH_LIMIT).abs() < f32::EPSILON);
}

#[test]
fn sensitivity_is_constant_across_delta_sizes() {
    // The mapping is exactly linear: doubling the pixel delta doubles the
    // rotation, at every magnitude (powers-of-two scaling is exact in
    // f32, so the distances below are zero).
    let (yaw_a, pitch_a) = integrate_look(0.0, 0.0, Vec2::new(2.0, 2.0));
    let (yaw_b, pitch_b) = integrate_look(0.0, 0.0, Vec2::new(4.0, 4.0));
    assert!((yaw_b - yaw_a * 2.0).abs() < f32::EPSILON);
    assert!((pitch_a - (-2.0 * LOOK_SENSITIVITY)).abs() < f32::EPSILON);
    assert!((pitch_b - pitch_a * 2.0).abs() < f32::EPSILON);
    // Tiny and huge deltas share one coefficient.
    let (small, _) = integrate_look(0.0, 0.0, Vec2::new(1.0, 0.0));
    assert!((small + LOOK_SENSITIVITY).abs() < f32::EPSILON);
    let (large, _) = integrate_look(0.0, 0.0, Vec2::new(100_000.0, 0.0));
    assert!((large - wrap_angle(-100_000.0 * LOOK_SENSITIVITY)).abs() < f32::EPSILON);
}

#[test]
fn yaw_wraps_into_the_half_open_pi_range() {
    // Wrapping subtracts TAU at π-scale magnitudes, so the result may sit
    // one ulp (at the result's magnitude) away from the exact constant;
    // two epsilon is that bound.
    let (yaw, _) = integrate_look(3.0 * core::f32::consts::FRAC_PI_2, 0.0, Vec2::ZERO);
    assert!((yaw + core::f32::consts::FRAC_PI_2).abs() <= 2.0 * f32::EPSILON);
    // Wrapping is idempotent: every wrapped value re-wraps to itself
    // (bit-identical, hence the zero distance).
    for turns in [-5.0, -1.0, 0.0, 1.0, 5.0] {
        let angle = turns * core::f32::consts::TAU + 0.7;
        let once = wrap_angle(angle);
        assert!((wrap_angle(once) - once).abs() < f32::EPSILON);
        assert!(once <= core::f32::consts::PI);
        assert!(once > -core::f32::consts::PI);
    }
}

#[test]
fn mouse_right_turns_right_and_mouse_up_looks_up() {
    let (yaw, pitch) = integrate_look(0.0, 0.0, Vec2::new(50.0, -30.0));
    assert!(yaw < 0.0, "mouse right must decrease yaw (turn right)");
    assert!(pitch > 0.0, "mouse up must increase pitch (look up)");
}

#[test]
fn cursor_capture_locks_and_hides_release_restores() {
    let mut cursor = CursorOptions::default();
    apply_cursor_target(CursorTarget::Capture, &mut cursor);
    assert_eq!(cursor.grab_mode, CursorGrabMode::Locked);
    assert!(!cursor.visible);
    apply_cursor_target(CursorTarget::Release, &mut cursor);
    assert_eq!(cursor.grab_mode, CursorGrabMode::None);
    assert!(cursor.visible);
}

#[test]
#[should_panic(expected = "unexpected cursor grab state")]
fn foreign_confined_state_fails_loud() {
    let mut cursor = CursorOptions {
        grab_mode: CursorGrabMode::Confined,
        ..CursorOptions::default()
    };
    apply_cursor_target(CursorTarget::Release, &mut cursor);
}

/// The authored spawn the test apps insert in place of the scene plugin:
/// a distinct, non-identity pose, so every assertion below proves the rig
/// actually consumes the resource instead of any local default.
fn test_spawn() -> PlayerSpawn {
    PlayerSpawn {
        pose: PlayerSpawnPose {
            eye: bevy::math::Vec3::new(1.5, 0.62, -3.0),
            yaw_radians: 0.7,
            pitch_radians: 1.2,
        },
    }
}

/// A test app with both game plugins built for real: the post-chain
/// plugin loads its asset handle, the look plugin spawns the rig, and the
/// camera carries the whole configured chain. The sim phase sits at
/// `AwakeInPod` (look armed) so the cursor-focused tests below see the
/// look system run; the phase-gate test overrides it per phase. The
/// input resources and the focus message are initialized directly
/// (`InputPlugin` would zero the accumulated motion each update, which is
/// bevy's reset contract, not this module's; the tests below insert the
/// accumulated value they want the look system to see).
fn game_app() -> App {
    let mut app = App::new();
    app.add_plugins((
        TaskPoolPlugin::default(),
        AssetPlugin::default(),
        ImagePlugin::default(),
    ));
    app.add_message::<WindowFocused>()
        .init_resource::<ButtonInput<KeyCode>>()
        .init_resource::<AccumulatedMouseMotion>()
        .insert_resource(SimWakePhase::new(WakePhase::AwakeInPod))
        .insert_resource(test_spawn());
    app.add_plugins((GamePostChainPlugin, PlayerLookPlugin));
    app
}

#[test]
fn game_plugin_build_wires_camera_to_the_full_post_chain() {
    let mut app = game_app();
    app.update();
    let masks = app
        .world()
        .get_resource::<PostChainAssets>()
        .expect("the post-chain plugin inserted its asset resource");
    let expected_mask = masks.metering_mask.clone();
    let mut cameras = app.world_mut().query::<(
        &PlayerPitch,
        &Camera3d,
        &Tonemapping,
        &Vignette,
        &AutoExposure,
        &Hdr,
        &ChildOf,
    )>();
    let mut iter = cameras.iter(app.world());
    let (_, _, tonemapping, vignette, exposure, _, child_of) =
        iter.next().expect("the rig camera exists");
    assert!(iter.next().is_none(), "exactly one rig camera");
    assert_eq!(*tonemapping, Tonemapping::AgX);
    assert!((vignette.intensity - 0.35).abs() < f32::EPSILON);
    assert_eq!(exposure.metering_mask, expected_mask);
    // The camera hangs under the yaw parent (auto exposure needs HDR,
    // which the component requirement supplied).
    assert!(
        app.world()
            .get_entity(child_of.parent())
            .expect("parent exists")
            .contains::<PlayerYaw>(),
        "the pitch camera's parent must carry the yaw"
    );
}

/// The rig spawns exactly at the authored pose: eye point and yaw on the
/// parent, pitch on the camera child, and the look angles seeded so the
/// transforms stay projections of the resource from frame one.
#[test]
fn rig_spawns_at_the_authored_spawn_pose() {
    let mut app = game_app();
    app.update();
    let pose = test_spawn().pose;
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    let yaw = *yaws.single(app.world()).expect("yaw parent");
    let mut pitches = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerPitch>>();
    let pitch = *pitches.single(app.world()).expect("pitch camera");
    assert_eq!(yaw.translation, pose.eye);
    assert_eq!(yaw.rotation, Quat::from_rotation_y(pose.yaw_radians));
    assert_eq!(pitch.translation, bevy::math::Vec3::ZERO);
    assert_eq!(pitch.rotation, Quat::from_rotation_x(pose.pitch_radians));
    let angles = app.world().resource::<LookAngles>();
    // The angles carry the pose bit-for-bit (copied, never integrated);
    // expressed as a distance because exact float equality is banned.
    assert!((angles.yaw - pose.yaw_radians).abs() < f32::EPSILON);
    assert!((angles.pitch - pose.pitch_radians).abs() < f32::EPSILON);
}

#[test]
fn look_writes_rotation_and_never_translation() {
    let mut app = game_app();
    // A fake window with the cursor captured: look is armed only then.
    app.world_mut().spawn((
        Window::default(),
        CursorOptions {
            grab_mode: CursorGrabMode::Locked,
            ..CursorOptions::default()
        },
    ));
    app.update();
    app.insert_resource(AccumulatedMouseMotion {
        delta: Vec2::new(120.0, -40.0),
    });
    app.update();
    let pose = test_spawn().pose;
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    let yaw = *yaws.single(app.world()).expect("yaw parent");
    let mut pitches = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerPitch>>();
    let pitch = *pitches.single(app.world()).expect("pitch camera");
    // Translation is untouched: the rig stays at its spawn eye point and
    // the camera child at its local origin.
    assert_eq!(yaw.translation, pose.eye);
    assert_eq!(pitch.translation, bevy::math::Vec3::ZERO);
    // The rotations are exactly the pure-integration projection from the
    // seeded pose angles.
    let (expected_yaw, expected_pitch) = integrate_look(
        pose.yaw_radians,
        pose.pitch_radians,
        Vec2::new(120.0, -40.0),
    );
    assert_eq!(yaw.rotation, Quat::from_rotation_y(expected_yaw));
    assert_eq!(pitch.rotation, Quat::from_rotation_x(expected_pitch));
}

#[test]
fn look_input_only_rotates_the_view_from_awake_in_pod_onward() {
    // Regression: the look system checked only cursor capture, so a
    // captured cursor rotated the view during the authored wake
    // sequence. The phase gate must hold the camera still through
    // Waking and release it exactly at AwakeInPod.
    for (phase, rotates) in [
        (WakePhase::Waking, false),
        (WakePhase::AwakeInPod, true),
        (WakePhase::ExitingPod, true),
        (WakePhase::Standing, true),
    ] {
        let mut app = game_app();
        app.world_mut().insert_resource(SimWakePhase::new(phase));
        app.world_mut().spawn((
            Window::default(),
            CursorOptions {
                grab_mode: CursorGrabMode::Locked,
                ..CursorOptions::default()
            },
        ));
        app.update();
        app.insert_resource(AccumulatedMouseMotion {
            delta: Vec2::new(120.0, -40.0),
        });
        app.update();
        let pose = test_spawn().pose;
        let mut yaws = app
            .world_mut()
            .query_filtered::<&Transform, With<PlayerYaw>>();
        let yaw = *yaws.single(app.world()).expect("yaw parent");
        let mut pitches = app
            .world_mut()
            .query_filtered::<&Transform, With<PlayerPitch>>();
        let pitch = *pitches.single(app.world()).expect("pitch camera");
        if rotates {
            let (expected_yaw, expected_pitch) = integrate_look(
                pose.yaw_radians,
                pose.pitch_radians,
                Vec2::new(120.0, -40.0),
            );
            assert_eq!(
                yaw.rotation,
                Quat::from_rotation_y(expected_yaw),
                "look must rotate in {phase:?}"
            );
            assert_eq!(
                pitch.rotation,
                Quat::from_rotation_x(expected_pitch),
                "look must pitch in {phase:?}"
            );
        } else {
            assert_eq!(
                yaw.rotation,
                Quat::from_rotation_y(pose.yaw_radians),
                "the wake sequence owns the camera in {phase:?}"
            );
            assert_eq!(
                pitch.rotation,
                Quat::from_rotation_x(pose.pitch_radians),
                "the wake sequence owns the camera in {phase:?}"
            );
        }
    }
}

#[test]
fn released_cursor_disarms_look() {
    let mut app = game_app();
    app.world_mut().spawn((
        Window {
            focused: false,
            ..Window::default()
        },
        CursorOptions::default(),
    ));
    app.update();
    let mut options = app
        .world_mut()
        .query_filtered::<&CursorOptions, With<Window>>();
    let cursor = options
        .single(app.world())
        .expect("window cursor options")
        .clone();
    assert_eq!(cursor.grab_mode, CursorGrabMode::None);
    assert!(cursor.visible, "an unfocused window must not capture");
    // Motion now cannot rotate the never-captured rig.
    app.insert_resource(AccumulatedMouseMotion {
        delta: Vec2::new(500.0, -500.0),
    });
    app.update();
    let angles = app.world().resource::<LookAngles>();
    // Never captured, so never integrated: the angles still hold the
    // seeded authored pose.
    let pose = test_spawn().pose;
    // The angles carry the pose bit-for-bit (copied, never integrated);
    // expressed as a distance because exact float equality is banned.
    assert!((angles.yaw - pose.yaw_radians).abs() < f32::EPSILON);
    assert!((angles.pitch - pose.pitch_radians).abs() < f32::EPSILON);
}

#[test]
fn windowless_runs_arm_scripted_look_through_the_shared_plane() {
    // The headless harness has no Window entity, so no cursor state
    // exists: look must stay armed (no cursor to gate it) and a scripted
    // plane delta in radians must integrate exactly as the pixel-level
    // pure function projects it.
    let mut app = game_app();
    let mut plane = super::GameplayInput::default();
    plane.offer_look(0.2, -0.1);
    app.insert_resource(plane);
    app.update();
    let pose = test_spawn().pose;
    let (expected_yaw, expected_pitch) =
        integrate_look_radians(pose.yaw_radians, pose.pitch_radians, Vec2::new(0.2, -0.1));
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    let yaw = *yaws.single(app.world()).expect("yaw parent");
    let mut pitches = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerPitch>>();
    let pitch = *pitches.single(app.world()).expect("pitch camera");
    assert_eq!(yaw.rotation, Quat::from_rotation_y(expected_yaw));
    assert_eq!(pitch.rotation, Quat::from_rotation_x(expected_pitch));
}

#[test]
fn scripted_canary_look_arms_on_an_unfocused_released_window() {
    // Regression: the canary opens a real window that never takes
    // focus, so its cursor is never captured, and the device-cursor
    // policy silently dropped the scripted turn on an unattended
    // gameplay-smoke render check unless an external focus event
    // happened. Scripted mode lifts the cursor gate: the full scripted
    // chain (scenario look action -> adapter step -> shared input
    // plane -> the real look systems) turns the rig on an unfocused,
    // cursor-released window.
    let mut app = game_app();
    app.world_mut().spawn((
        Window {
            focused: false,
            ..Window::default()
        },
        CursorOptions::default(),
    ));
    app.insert_resource(LookInputMode::Scripted);
    app.update();
    let mut options = app
        .world_mut()
        .query_filtered::<&CursorOptions, With<Window>>();
    let cursor = options
        .single(app.world())
        .expect("window cursor options")
        .clone();
    assert_eq!(cursor.grab_mode, CursorGrabMode::None, "never captured");
    assert!(cursor.visible, "an unfocused window must not capture");
    // The same offer `drive_ticks` makes: one scripted look action
    // through the adapter's step, offered onto the shared plane in
    // radians.
    let mut adapter =
        InputAdapter::with_actions(vec![ScriptedAction::look(0, 90.0, -10.0)], TICKS_PER_SECOND);
    let step = adapter.step();
    assert_eq!(step.motion, Delta { x: 90.0, y: -10.0 });
    let mut plane = super::GameplayInput::default();
    plane.offer_look(step.motion.x.to_radians(), step.motion.y.to_radians());
    app.insert_resource(plane);
    app.update();
    let pose = test_spawn().pose;
    let (expected_yaw, expected_pitch) = integrate_look_radians(
        pose.yaw_radians,
        pose.pitch_radians,
        Vec2::new(90.0_f32.to_radians(), (-10.0_f32).to_radians()),
    );
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    let yaw = *yaws.single(app.world()).expect("yaw parent");
    let mut pitches = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerPitch>>();
    let pitch = *pitches.single(app.world()).expect("pitch camera");
    assert_eq!(yaw.rotation, Quat::from_rotation_y(expected_yaw));
    assert_eq!(pitch.rotation, Quat::from_rotation_x(expected_pitch));
    let angles = app.world().resource::<LookAngles>();
    assert!(
        (angles.yaw_radians() - expected_yaw).abs() < f32::EPSILON,
        "the turn landed in the look angles"
    );
}

#[test]
fn device_mode_still_disarms_scripted_look_on_an_unfocused_window() {
    // The other side of the fix: the default device mode keeps the
    // cursor policy exactly as it was, so the same unfocused,
    // cursor-released window still holds the camera still.
    let mut app = game_app();
    app.world_mut().spawn((
        Window {
            focused: false,
            ..Window::default()
        },
        CursorOptions::default(),
    ));
    let mut adapter =
        InputAdapter::with_actions(vec![ScriptedAction::look(0, 90.0, -10.0)], TICKS_PER_SECOND);
    let step = adapter.step();
    let mut plane = super::GameplayInput::default();
    plane.offer_look(step.motion.x.to_radians(), step.motion.y.to_radians());
    app.insert_resource(plane);
    app.update();
    let angles = app.world().resource::<LookAngles>();
    let pose = test_spawn().pose;
    assert!(
        (angles.yaw_radians() - pose.yaw_radians).abs() < f32::EPSILON,
        "the angles still hold the seeded pose"
    );
    // The rig transforms project the angles: the yaw parent never moved.
    let mut yaws = app
        .world_mut()
        .query_filtered::<&Transform, With<PlayerYaw>>();
    let yaw = *yaws.single(app.world()).expect("yaw parent");
    assert_eq!(yaw.rotation, Quat::from_rotation_y(pose.yaw_radians));
}

#[test]
fn plane_look_is_consumed_exactly_once() {
    // The integrator takes the whole plane channel; whatever it took is
    // gone, so device and scripted motion can never be integrated twice.
    let mut plane = super::GameplayInput::default();
    plane.offer_look(0.5, 0.25);
    plane.offer_look(0.25, -0.25);
    assert_eq!(plane.take_look(), Vec2::new(0.75, 0.0));
    assert_eq!(plane.take_look(), Vec2::ZERO);
}

#[test]
fn device_pixels_convert_to_the_plane_convention() {
    // Mouse right (positive x) must decrease yaw (turn right); mouse up
    // (negative y) must increase pitch (look up). The negation lives in
    // the device producer so the plane's convention is one-way positive.
    let right = look_delta_from_pixels(Vec2::new(50.0, 0.0));
    let up = look_delta_from_pixels(Vec2::new(0.0, -30.0));
    assert!(right.x < 0.0);
    assert!(up.y > 0.0);
    // The pixel-level pure function is exactly the radian integrator
    // over the converted delta (same ops, same order, bit-identical).
    let (yaw_px, pitch_px) = integrate_look(1.0, 1.0, Vec2::new(4.0, -2.0));
    let (yaw_rad, pitch_rad) =
        integrate_look_radians(1.0, 1.0, look_delta_from_pixels(Vec2::new(4.0, -2.0)));
    assert_eq!((yaw_px, pitch_px), (yaw_rad, pitch_rad));
}

#[test]
fn scripted_exit_edge_releases_and_disarms_like_the_physical_key() {
    // A scripted Escape press offered on the shared plane is consumed by
    // the cursor state machine and releases the (windowed) cursor in the
    // same update, so the same frame's look is disarmed.
    let mut app = game_app();
    app.world_mut().spawn((
        Window::default(),
        CursorOptions {
            grab_mode: CursorGrabMode::Locked,
            ..CursorOptions::default()
        },
    ));
    app.update();
    let mut plane = super::GameplayInput::default();
    plane.offer_edges(core::iter::once(ButtonEdge {
        button: Button::Key(Key::Escape),
        edge: Edge::Press,
    }));
    app.insert_resource(plane);
    app.insert_resource(AccumulatedMouseMotion {
        delta: Vec2::new(500.0, 0.0),
    });
    app.update();
    let mut options = app
        .world_mut()
        .query_filtered::<&CursorOptions, With<Window>>();
    let cursor = options
        .single(app.world())
        .expect("window cursor options")
        .clone();
    assert_eq!(cursor.grab_mode, CursorGrabMode::None);
    assert!(cursor.visible, "a scripted exit releases the cursor");
    // Released this frame, so this frame's motion must not rotate.
    let angles = app.world().resource::<LookAngles>();
    let pose = test_spawn().pose;
    assert!((angles.yaw - pose.yaw_radians).abs() < f32::EPSILON);
}
