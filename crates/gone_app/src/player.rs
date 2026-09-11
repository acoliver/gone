//! First-person mouse look for the normal game (issue #6 slice B).
//!
//! Built by the normal game and by gameplay-content harness runs; the
//! calibration harness lanes never build this plugin, so scripted harness look
//! never passes through here and the calibration cameras stay free of player
//! structure.
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
//! Look integrates the one shared gameplay input plane ([`GameplayInput`]):
//! the device producer converts bevy's per-frame [`AccumulatedMouseMotion`]
//! into the plane's radians, and scripted harness input converges on the same
//! plane, so the integrator cannot tell a human's mouse from the runner. The
//! mapping is linear at a constant sensitivity (radians per pixel) and touches
//! nothing else: no frame-time coupling, no field-of-view coupling, no
//! translation. Pitch is clamped to ±89° as part of the integration, before
//! the value can over-rotate past the vertical.
//!
//! Look is armed only while two gates hold: the cursor is captured (always
//! armed in a windowless run, where no cursor exists to gate it), and the wake
//! phase allows look ([`WakePhase::look_allowed`], true from `AwakeInPod`
//! onward). During the authored wake sequence neither mouse motion nor a
//! captured cursor can rotate the view.
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
use bevy::ecs::schedule::{IntoScheduleConfigs, SystemSet};
use bevy::input::ButtonInput;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::AccumulatedMouseMotion;
use bevy::math::{Quat, Vec2};
use bevy::prelude::Camera3d;
use bevy::transform::components::Transform;
use bevy::window::{CursorGrabMode, CursorOptions, Window, WindowFocused};

use crate::harness::{Button, ButtonEdge, Edge, Key, MoveMotion};
use crate::post::{PostChainAssets, camera_post_components};
use crate::scene::{PlayerSpawn, SimWakePhase};

/// Look rotation per mouse pixel, in radians (≈0.126°/px). Constant by
/// design: the same pixel delta always produces the same rotation.
const LOOK_SENSITIVITY: f32 = 0.0022;

/// Pitch hard stop in each direction, just short of the vertical so the view
/// can never flip through the pole. The scene reads it for the authored
/// spawn pitch (one stop short of the same vertical).
pub(crate) const PITCH_LIMIT: f32 = 89.0_f32.to_radians();

/// Marks the rig's yaw parent (horizontal look only).
#[derive(Component)]
struct PlayerYaw;

/// Marks the rig's pitch camera (vertical look only). Crate-visible so the
/// gameplay harness can find the rig camera (it is the one camera the
/// harness retargets into the capture target).
#[derive(Component)]
pub(crate) struct PlayerPitch;

/// The schedule set the scripted input producer drives. The harness gameplay
/// lane steps its input adapter inside this set; the whole look chain orders
/// after it, so a scripted look offered on tick N integrates on tick N. The
/// set is empty in the normal game, where the ordering is vacuous.
#[derive(SystemSet, Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct ScriptedInput;

/// The schedule set carrying the look application. Consumers that must
/// observe the freshly integrated rig (the gameplay lane's yaw recorder)
/// order against this set.
#[derive(SystemSet, Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) struct LookApplied;

/// The one shared gameplay input plane. Device input (real mouse motion) and
/// scripted input (the harness adapter's step) converge here, and gameplay
/// systems consume from it, so gameplay cannot tell a human from the runner.
///
/// Producers accumulate into the plane during the update; the integrator
/// takes the look delta exactly once. Whatever no consumer took by the end
/// of the frame is dropped by [`clear_gameplay_input`], matching bevy's own
/// per-frame reset of [`AccumulatedMouseMotion`]: input not consumed in its
/// frame is lost, never buffered.
#[derive(Resource, Default, Debug, Clone)]
pub(crate) struct GameplayInput {
    /// Look motion accumulated for this frame, in radians: `x` is the yaw
    /// delta, `y` the pitch delta.
    look: Vec2,
    /// Movement intent accumulated for this frame.
    movement: MoveMotion,
    /// Button edges delivered this frame, consumed in delivery order.
    edges: Vec<ButtonEdge>,
}

impl GameplayInput {
    /// Offer one look delta, in radians. Positive yaw turns left (increasing
    /// yaw), positive pitch looks up (increasing pitch), matching the rig's
    /// rotation conventions.
    pub(crate) fn offer_look(&mut self, yaw_delta_radians: f32, pitch_delta_radians: f32) {
        self.look += Vec2::new(yaw_delta_radians, pitch_delta_radians);
    }

    /// Offer movement intent for this frame.
    pub(crate) fn offer_movement(&mut self, motion: MoveMotion) {
        self.movement.forward += motion.forward;
        self.movement.strafe += motion.strafe;
    }

    /// Offer this frame's button edges, in delivery order.
    pub(crate) fn offer_edges(&mut self, edges: impl IntoIterator<Item = ButtonEdge>) {
        self.edges.extend(edges);
    }

    /// Take the accumulated look delta, zeroing the channel: exactly one
    /// consumer sees each frame's motion.
    pub(crate) fn take_look(&mut self) -> Vec2 {
        let look = self.look;
        self.look = Vec2::ZERO;
        look
    }

    /// Consume any scripted Escape press edge offered this frame, draining it
    /// the way a real key event is consumed once. The cursor state machine is
    /// the game's only edge consumer today; the interaction slices consume
    /// the rest.
    pub(crate) fn take_exit_press(&mut self) -> bool {
        let (exit, rest): (Vec<_>, Vec<_>) =
            self.edges.drain(..).partition(|edge| edge == &EXIT_PRESS);
        self.edges = rest;
        !exit.is_empty()
    }

    /// The movement intent accumulated so far this frame (diagnostic read
    /// for the end-of-frame drop log).
    pub(crate) fn movement(&self) -> MoveMotion {
        self.movement
    }

    /// The edges still undelivered this frame (diagnostic read for the
    /// end-of-frame drop log).
    pub(crate) fn edges(&self) -> &[ButtonEdge] {
        &self.edges
    }

    /// Drop everything unconsumed. Look is taken by the integrator; movement
    /// and edges wait for the locomotion and interaction slices, so until
    /// then their per-frame intent is dropped here and surfaced in the drop
    /// log.
    fn end_frame(&mut self) {
        self.look = Vec2::ZERO;
        self.movement = MoveMotion::zero();
        self.edges = Vec::new();
    }
}

/// The one exit edge the cursor state machine consumes.
const EXIT_PRESS: ButtonEdge = ButtonEdge {
    button: Button::Key(Key::Escape),
    edge: Edge::Press,
};

/// The integrated look angles, in radians. The resource is the single source
/// of truth: mouse deltas accumulate here, and the transforms are projections
/// of it (yaw around Y on the parent, pitch around X on the camera).
/// Crate-visible so the gameplay harness can sample the rig's yaw for the
/// report's yaw events.
#[derive(Resource, Default)]
pub(crate) struct LookAngles {
    yaw: f32,
    pitch: f32,
}

impl LookAngles {
    /// The integrated yaw, in radians, wrapped into (-π, π]. The gameplay
    /// harness reads it for the report's yaw samples.
    pub(crate) fn yaw_radians(&self) -> f32 {
        self.yaw
    }
}

/// Adds first-person mouse look and the player camera rig to the app. The
/// rig's camera carries the post-chain components from the
/// [`crate::post::GamePostChainPlugin`] resource, so both plugins must be
/// added for the game to have a camera.
pub struct PlayerLookPlugin;

impl Plugin for PlayerLookPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<LookAngles>()
            .init_resource::<GameplayInput>()
            .add_systems(Startup, (setup_player_rig, capture_cursor_on_startup))
            .add_systems(
                Update,
                // One chain: cursor transitions, then the device producer
                // offers this frame's real motion, then the integrator takes
                // the whole look channel (device plus scripted), then the
                // frame's leftovers are dropped. The whole chain runs after
                // the scripted input set, so a scripted look offered by the
                // harness adapter on tick N integrates on tick N; the set is
                // empty in the normal game and the ordering is vacuous there.
                (
                    update_cursor_lock,
                    collect_device_look,
                    apply_mouse_look.in_set(LookApplied),
                    clear_gameplay_input,
                )
                    .chain()
                    .after(ScriptedInput),
            );
    }
}

/// The device-side producer: convert this frame's accumulated mouse motion
/// into the shared plane's radians and offer it. Runs after the cursor
/// transitions and before the integrator, so a frame's real motion and any
/// scripted motion offered upstream of this chain take in one step: the
/// integrator consumes the whole plane and cannot tell them apart.
fn collect_device_look(motion: Res<AccumulatedMouseMotion>, mut plane: ResMut<GameplayInput>) {
    let delta_px = motion.into_inner().delta;
    if delta_px != Vec2::ZERO {
        let delta = look_delta_from_pixels(delta_px);
        plane.offer_look(delta.x, delta.y);
    }
}

/// Drop whatever no consumer took this frame. Look is taken by the
/// integrator; movement and edges wait for the locomotion and interaction
/// slices, so until those land their per-frame intent is dropped here and
/// surfaced in the drop log, matching bevy's own per-frame reset of
/// [`AccumulatedMouseMotion`]: input not consumed in its frame is lost,
/// never buffered.
fn clear_gameplay_input(mut plane: ResMut<GameplayInput>) {
    let movement = plane.movement();
    let edges = plane.edges().len();
    if movement != MoveMotion::zero() || edges > 0 {
        bevy::log::debug!(
            "gameplay input dropped unused this frame: movement {movement:?}, {edges} edges"
        );
    }
    plane.end_frame();
}

/// Spawn the player rig (yaw parent, pitch camera child) and the game's clear
/// color, at the authored spawn pose (`scene::PlayerSpawn`, derived from the
/// pod registry): lying in the player pod, aimed up at the ceiling.
///
/// # Panics
/// Panics without the [`PostChainAssets`] resource: the rig's camera needs
/// the post-chain components, so a missing resource is a wiring error, not a
/// degraded mode. Panics symmetrically without the [`PlayerSpawn`] resource:
/// the rig needs its authored spawn, and game mode always provides both.
fn setup_player_rig(
    mut commands: Commands,
    masks: Option<Res<PostChainAssets>>,
    spawn: Option<Res<PlayerSpawn>>,
    mut angles: ResMut<LookAngles>,
) {
    let masks = masks
        .expect("PlayerLookPlugin requires PostChainAssets (GamePostChainPlugin provides it)")
        .into_inner();
    let pose = spawn
        .expect("PlayerLookPlugin requires PlayerSpawn (StasisScenePlugin provides it)")
        .into_inner()
        .pose;
    // The look angles are the single source of truth and the rig transforms
    // are projections of them, so the authored pose enters through the
    // angles, not by writing the transforms alone.
    angles.yaw = pose.yaw_radians;
    angles.pitch = pose.pitch_radians;
    let camera_bundle = (
        Camera3d::default(),
        Transform::from_rotation(Quat::from_rotation_x(pose.pitch_radians)),
        camera_post_components(masks.metering_mask.clone()),
    );
    commands
        .spawn((
            PlayerYaw,
            Transform::from_translation(pose.eye)
                .with_rotation(Quat::from_rotation_y(pose.yaw_radians)),
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
/// no event fires. A windowless run (headless harness) has no cursor to
/// capture and does nothing.
fn capture_cursor_on_startup(
    window: Option<Single<&Window>>,
    cursor: Option<Single<&mut CursorOptions>>,
) {
    if let (Some(window), Some(mut cursor)) = (window, cursor)
        && window.into_inner().focused
    {
        apply_cursor_target(CursorTarget::Capture, &mut cursor);
    }
}

/// The event-driven cursor transitions: focus gain captures, focus loss and
/// Esc (physical or scripted) release. Runs before [`apply_mouse_look`] so a
/// same-frame Esc stops look input in the same update it releases the cursor.
/// A scripted Escape press edge offered on the shared input plane releases
/// exactly like the physical key: the harness scripts the exit through the
/// same plane a human's key press travels. Windowless runs have no cursor
/// state to write and only drain the plane's exit edge.
fn update_cursor_lock(
    mut focused: MessageReader<WindowFocused>,
    keys: Res<ButtonInput<KeyCode>>,
    mut plane: ResMut<GameplayInput>,
    cursor: Option<Single<&mut CursorOptions>>,
) {
    let mut target = None;
    for event in focused.read() {
        target = Some(if event.focused {
            CursorTarget::Capture
        } else {
            CursorTarget::Release
        });
    }
    if keys.into_inner().just_pressed(KeyCode::Escape) || plane.take_exit_press() {
        target = Some(CursorTarget::Release);
    }
    if let (Some(target), Some(mut cursor)) = (target, cursor) {
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

/// Integrate this frame's look delta from the shared gameplay input plane
/// into the look angles and project them onto the rig transforms. The plane
/// carries device motion (offered by [`collect_device_look`]) and scripted
/// harness motion (offered upstream of this chain in the `ScriptedInput`
/// set) in the same units, so the integrator is mode-free. Look is armed
/// only while the cursor is captured (a released cursor must not rotate the
/// view; a windowless run has no cursor and is always armed) and only while
/// the wake phase allows look (the authored wake sequence owns the camera
/// until it completes). Writes rotation only; nothing in this system can
/// translate the player.
fn apply_mouse_look(
    mut plane: ResMut<GameplayInput>,
    cursor: Option<Single<&CursorOptions>>,
    phase: Res<SimWakePhase>,
    mut angles: ResMut<LookAngles>,
    mut yaw: Single<&mut Transform, (With<PlayerYaw>, Without<PlayerPitch>)>,
    mut pitch: Single<&mut Transform, (With<PlayerPitch>, Without<PlayerYaw>)>,
) {
    let armed = cursor.is_none_or(|cursor| cursor.into_inner().grab_mode == CursorGrabMode::Locked)
        && phase.into_inner().phase().look_allowed();
    if !armed {
        return;
    }
    let delta = plane.take_look();
    let (yaw_angle, pitch_angle) = integrate_look_radians(angles.yaw, angles.pitch, delta);
    angles.yaw = yaw_angle;
    angles.pitch = pitch_angle;
    // The plane's positive yaw turns left (increasing yaw), positive pitch
    // looks up (increasing pitch); the device producer already negated the
    // pixel axes into that convention.
    yaw.rotation = Quat::from_rotation_y(yaw_angle);
    pitch.rotation = Quat::from_rotation_x(pitch_angle);
}

/// Pure look integration over a plane delta in radians: new (yaw, pitch)
/// radians out. Pitch is clamped to ±[`PITCH_LIMIT`] before the result can
/// over-rotate and yaw is wrapped into (-π, π] so long play cannot drift the
/// angle's precision.
fn integrate_look_radians(yaw: f32, pitch: f32, delta: Vec2) -> (f32, f32) {
    let yaw = wrap_angle(yaw + delta.x);
    let pitch = (pitch + delta.y).clamp(-PITCH_LIMIT, PITCH_LIMIT);
    (yaw, pitch)
}

/// Convert bevy's accumulated pixel delta into the plane's radians: mouse
/// right (positive pixel x) turns right, so yaw decreases; mouse up
/// (negative pixel y) looks up, so pitch increases.
fn look_delta_from_pixels(delta_px: Vec2) -> Vec2 {
    Vec2::new(
        -delta_px.x * LOOK_SENSITIVITY,
        -delta_px.y * LOOK_SENSITIVITY,
    )
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
        Button, ButtonEdge, CursorTarget, Edge, Key, LOOK_SENSITIVITY, LookAngles, PITCH_LIMIT,
        PlayerLookPlugin, PlayerPitch, PlayerYaw, apply_cursor_target, integrate_look_radians,
        look_delta_from_pixels, wrap_angle,
    };
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
}
