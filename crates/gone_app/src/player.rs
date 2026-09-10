//! First-person mouse look for the normal game (issue #6 slice B).
//!
//! Game-mode only: the harness lanes never build this plugin, so scripted
//! harness look never passes through here and the harness cameras stay free
//! of player structure.
//!
//! # Structure
//!
//! The rig is two entities. A yaw parent carries the horizontal rotation; the
//! camera is its child and carries only the pitch. Pitching the camera child
//! keeps the yaw axis vertical no matter how far the player looks up or down,
//! which is the whole reason for the split.
//!
//! # Look input
//!
//! Look is integrated from bevy's per-frame [`AccumulatedMouseMotion`] at a
//! constant sensitivity (radians per pixel). The mapping is linear in the
//! pixel delta and touches nothing else: no frame-time coupling, no field-of-
//! view coupling, no translation. Pitch is clamped to ±89° as part of the
//! integration, before the value can over-rotate past the vertical.
//!
//! # Cursor capture
//!
//! The cursor state machine has exactly two authored states: captured
//! (`Locked` + hidden) and released (`None` + visible). The transitions are
//! event-driven, one write per transition: captured when the window gains
//! focus (startup included, via the window's focus flag), released when the
//! player presses Esc, released again when focus is lost, and re-captured as
//! a native observation of the next focus gain. There is no per-frame
//! reconcile loop and no fallback chain. Seeing a grab state this module
//! never authored (`Confined`, which macOS cannot produce and nothing here
//! writes) fails loudly instead of being coerced or fought.
//!
//! Look input is armed only while the cursor is captured, so a released
//! cursor (menu-like state) does not rotate the view.

use bevy::app::{App, Plugin, Startup, Update};
use bevy::camera::ClearColor;
use bevy::camera::visibility::Visibility;
use bevy::color::Color;
use bevy::ecs::message::MessageReader;
use bevy::ecs::prelude::{Commands, Component, Res, ResMut, Resource, Single, With, Without};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::math::{Quat, Vec2, Vec3};
use bevy::prelude::Camera3d;
use bevy::transform::components::Transform;
use bevy::window::{CursorGrabMode, CursorOptions, Window, WindowFocused};

use crate::post::{PostChainAssets, camera_post_components};

/// Look rotation per mouse pixel, in radians (≈0.126°/px). Constant by
/// design: the same pixel delta always produces the same rotation.
const LOOK_SENSITIVITY: f32 = 0.0022;

/// Pitch hard stop in each direction, just short of the vertical so the view
/// can never flip through the pole.
const PITCH_LIMIT: f32 = 89.0_f32.to_radians();

/// The rig spawn point: the eye position for this slice. The walkable capsule
/// and its ground offset arrive with the movement milestone; until then the
/// yaw parent carries the eye point directly.
const SPAWN_POS: Vec3 = Vec3::new(0.0, 0.5, 5.0);

/// Marks the rig's yaw parent (horizontal look only).
#[derive(Component)]
struct PlayerYaw;

/// Marks the rig's pitch camera (vertical look only).
#[derive(Component)]
struct PlayerPitch;

/// The integrated look angles, in radians. The resource is the single source
/// of truth: mouse deltas accumulate here, and the transforms are projections
/// of it (yaw around Y on the parent, pitch around X on the camera).
#[derive(Resource, Default)]
struct LookAngles {
    yaw: f32,
    pitch: f32,
}

/// Adds first-person mouse look and the player camera rig to the app. The
/// rig's camera carries the post-chain components from the
/// [`crate::post::GamePostChainPlugin`] resource, so both plugins must be
/// added for the game to have a camera.
pub struct PlayerLookPlugin;

impl Plugin for PlayerLookPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<LookAngles>()
            .add_systems(Startup, (setup_player_rig, capture_cursor_on_startup))
            .add_systems(Update, (update_cursor_lock, apply_mouse_look).chain());
    }
}

/// Spawn the player rig (yaw parent, pitch camera child) and the game's clear
/// color.
///
/// # Panics
/// Panics without the [`PostChainAssets`] resource: the rig's camera needs
/// the post-chain components, so a missing resource is a wiring error, not a
/// degraded mode.
fn setup_player_rig(mut commands: Commands, masks: Option<Res<PostChainAssets>>) {
    let masks = masks
        .expect("PlayerLookPlugin requires PostChainAssets (GamePostChainPlugin provides it)")
        .into_inner();
    let camera_bundle = (
        Camera3d::default(),
        Transform::IDENTITY,
        camera_post_components(masks.metering_mask.clone()),
    );
    commands
        .spawn((
            PlayerYaw,
            Transform::from_translation(SPAWN_POS),
            // The camera child inherits visibility (Camera3d requires it);
            // carrying it on the parent too keeps the propagation chain
            // consistent (bevy warning B0004).
            Visibility::default(),
        ))
        .with_children(|parent| {
            parent.spawn((PlayerPitch, camera_bundle));
        });
    commands.insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.02)));
}

/// Apply the initial cursor capture when the window opens already focused.
/// A focus event usually repeats this; the startup pass covers launches where
/// no event fires.
fn capture_cursor_on_startup(window: Single<&Window>, mut cursor: Single<&mut CursorOptions>) {
    if window.into_inner().focused {
        apply_cursor_target(CursorTarget::Capture, &mut cursor);
    }
}

/// The event-driven cursor transitions: focus gain captures, focus loss and
/// Esc release. Runs before [`apply_mouse_look`] so a same-frame Esc stops
/// look input in the same update it releases the cursor.
fn update_cursor_lock(
    mut focused: MessageReader<WindowFocused>,
    keys: Res<ButtonInput<KeyCode>>,
    mut cursor: Single<&mut CursorOptions>,
) {
    let mut target = None;
    for event in focused.read() {
        target = Some(if event.focused {
            CursorTarget::Capture
        } else {
            CursorTarget::Release
        });
    }
    if keys.into_inner().just_pressed(KeyCode::Escape) {
        target = Some(CursorTarget::Release);
    }
    if let Some(target) = target {
        apply_cursor_target(target, &mut cursor);
    }
}

/// The two cursor states this module authors.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum CursorTarget {
    /// Cursor locked to the window center and hidden.
    Capture,
    /// Cursor free and visible.
    Release,
}

/// Write one cursor transition. Total over the authored state machine: every
/// target maps to exactly one option pair, and the pre-state assertion pins
/// the invariant that only this module writes the cursor.
///
/// # Panics
/// Panics when the observed grab mode is `Confined`: this game authors only
/// `Locked` and `None`, macOS cannot produce `Confined` (winit falls back to
/// `None` there), so observing it means a foreign writer, and failing loudly
/// beats silently fighting over the cursor.
fn apply_cursor_target(target: CursorTarget, cursor: &mut CursorOptions) {
    assert!(
        matches!(
            cursor.grab_mode,
            CursorGrabMode::None | CursorGrabMode::Locked
        ),
        "unexpected cursor grab state {:?}: this game authors only Locked and None",
        cursor.grab_mode
    );
    match target {
        CursorTarget::Capture => {
            cursor.grab_mode = CursorGrabMode::Locked;
            cursor.visible = false;
        }
        CursorTarget::Release => {
            cursor.grab_mode = CursorGrabMode::None;
            cursor.visible = true;
        }
    }
}

/// Integrate this frame's mouse motion into the look angles and project them
/// onto the rig transforms. Look is armed only while the cursor is captured:
/// a released cursor must not rotate the view. Writes rotation only; nothing
/// in this system can translate the player.
fn apply_mouse_look(
    motion: Res<AccumulatedMouseMotion>,
    cursor: Single<&CursorOptions>,
    mut angles: ResMut<LookAngles>,
    mut yaw: Single<&mut Transform, (With<PlayerYaw>, Without<PlayerPitch>)>,
    mut pitch: Single<&mut Transform, (With<PlayerPitch>, Without<PlayerYaw>)>,
) {
    if cursor.into_inner().grab_mode != CursorGrabMode::Locked {
        return;
    }
    let (yaw_angle, pitch_angle) =
        integrate_look(angles.yaw, angles.pitch, motion.into_inner().delta);
    angles.yaw = yaw_angle;
    angles.pitch = pitch_angle;
    // Mouse right (positive pixel x) turns right: yaw decreases. Mouse up
    // (negative pixel y) looks up: pitch increases.
    yaw.rotation = Quat::from_rotation_y(yaw_angle);
    pitch.rotation = Quat::from_rotation_x(pitch_angle);
}

/// Pure look integration: one pixel delta in, new (yaw, pitch) radians out.
/// Linear in the delta at a constant [`LOOK_SENSITIVITY`], independent of any
/// frame delta, with pitch clamped to ±[`PITCH_LIMIT`] before the result can
/// over-rotate and yaw wrapped into (-π, π] so long play cannot drift the
/// angle's precision.
fn integrate_look(yaw: f32, pitch: f32, delta_px: Vec2) -> (f32, f32) {
    let yaw = wrap_angle(yaw - delta_px.x * LOOK_SENSITIVITY);
    let pitch = (pitch - delta_px.y * LOOK_SENSITIVITY).clamp(-PITCH_LIMIT, PITCH_LIMIT);
    (yaw, pitch)
}

/// Wrap an angle into (-π, π]. Values already in range pass through
/// unchanged (the common per-frame case, kept bit-exact): routing them
/// through `rem_euclid` would round-trip the value through TAU's magnitude
/// and quantize small angles to ulp(TAU) every frame.
fn wrap_angle(angle: f32) -> f32 {
    if angle.abs() <= core::f32::consts::PI {
        return angle;
    }
    let wrapped = angle.rem_euclid(core::f32::consts::TAU);
    if wrapped > core::f32::consts::PI {
        wrapped - core::f32::consts::TAU
    } else {
        wrapped
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CursorTarget, LOOK_SENSITIVITY, LookAngles, PITCH_LIMIT, PlayerLookPlugin, PlayerPitch,
        PlayerYaw, SPAWN_POS, apply_cursor_target, integrate_look, wrap_angle,
    };
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

    use crate::post::{GamePostChainPlugin, PostChainAssets};

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

    /// A test app with both game plugins built for real: the post-chain
    /// plugin loads its asset handle, the look plugin spawns the rig, and the
    /// camera carries the whole configured chain. The input resources and the
    /// focus message are initialized directly (`InputPlugin` would zero the
    /// accumulated motion each update, which is bevy's reset contract, not
    /// this module's; the tests below insert the accumulated value they want
    /// the look system to see).
    fn game_app() -> App {
        let mut app = App::new();
        app.add_plugins((
            TaskPoolPlugin::default(),
            AssetPlugin::default(),
            ImagePlugin::default(),
        ));
        app.add_message::<WindowFocused>()
            .init_resource::<ButtonInput<KeyCode>>()
            .init_resource::<AccumulatedMouseMotion>();
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
        assert_eq!(yaw.translation, SPAWN_POS);
        assert_eq!(pitch.translation, bevy::math::Vec3::ZERO);
        // The rotations are exactly the pure-integration projection.
        assert_eq!(
            yaw.rotation,
            Quat::from_rotation_y(-120.0 * LOOK_SENSITIVITY)
        );
        assert_eq!(
            pitch.rotation,
            Quat::from_rotation_x(40.0 * LOOK_SENSITIVITY)
        );
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
        // Never captured, so never integrated: the angles are still zero.
        assert!(angles.yaw.abs() < f32::EPSILON);
        assert!(angles.pitch.abs() < f32::EPSILON);
    }
}
