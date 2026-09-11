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
//! Look is armed only while two gates hold: the cursor gate and the wake
//! phase gate ([`WakePhase::look_allowed`], true from `AwakeInPod`
//! onward). The cursor gate follows the input pathway's mode
//! ([`LookInputMode`]): in device mode (the normal game) look arms only
//! while the cursor is captured, or while no cursor exists at all (a
//! windowless run, where there is nothing to gate on); in scripted mode (a
//! canary run) the cursor gate is lifted, because the canary's window
//! deliberately never takes focus and an unattended run has no one to
//! capture it. The wake phase gate holds in both modes: during the
//! authored wake sequence neither mouse motion nor a captured cursor can
//! rotate the view.
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
//! Look input is armed only while the cursor is captured in device mode,
//! so a released cursor (menu-like state) does not rotate the view; a
//! scripted canary run arms look through [`LookInputMode`] regardless.

use bevy::app::{App, Plugin, Startup, Update};
use bevy::camera::ClearColor;
use bevy::camera::visibility::Visibility;
use bevy::color::Color;
use bevy::ecs::message::MessageReader;
use bevy::ecs::prelude::{Commands, Component, Res, ResMut, Resource, Single, With, Without};
use bevy::ecs::schedule::{IntoScheduleConfigs, SystemSet};
use bevy::ecs::system::SystemParam;
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

/// Which policy arms the shared gameplay input plane's look channel. One
/// mode per run, decided where the run mode is known: the normal game and
/// headless harness runs keep device mode, and a canary run inserts
/// scripted mode before the look plugin builds.
#[derive(Resource, Default, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum LookInputMode {
    /// The device-cursor policy: look arms only while the cursor is
    /// captured (a released cursor is a menu-like state and must not
    /// rotate the view), or while no cursor exists at all (a windowless
    /// run). The OS focus state matters here: an unfocused window never
    /// captures, so it never arms device look.
    #[default]
    Device,
    /// A scripted canary run: the run is unattended and its window
    /// deliberately never takes focus, so the cursor gate is lifted and
    /// scripted look integrates regardless of cursor or focus state. The
    /// shared plane cannot tell a human's mouse from the runner by design,
    /// so the lift covers the whole channel; the wake phase gate still
    /// applies.
    Scripted,
}

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
            .init_resource::<LookInputMode>()
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

/// The rig's two transform projections, bundled as one system parameter so
/// the look integrator stays inside the workspace's argument limit: the yaw
/// parent (horizontal rotation) and the pitch camera child (vertical), the
/// same disjoint pair the integrator always writes together.
#[derive(SystemParam)]
pub(crate) struct RigTransforms<'w, 's> {
    /// The yaw parent's transform (horizontal look only).
    yaw: Single<'w, 's, &'static mut Transform, (With<PlayerYaw>, Without<PlayerPitch>)>,
    /// The pitch camera child's transform (vertical look only).
    pitch: Single<'w, 's, &'static mut Transform, (With<PlayerPitch>, Without<PlayerYaw>)>,
}

/// Integrate this frame's look delta from the shared gameplay input plane
/// into the look angles and project them onto the rig transforms. The plane
/// carries device motion (offered by [`collect_device_look`]) and scripted
/// harness motion (offered upstream of this chain in the `ScriptedInput`
/// set) in the same units, so the integrator is mode-free. Look is armed
/// per the input pathway's [`LookInputMode`]: in device mode only while the
/// cursor is captured (a released cursor must not rotate the view; a
/// windowless run has no cursor and is always armed), in scripted mode
/// regardless of the cursor, because the canary's unfocused window never
/// captures one. The wake phase gate applies in both modes: only while it
/// allows look (the authored wake sequence owns the camera until it
/// completes). Writes rotation only; nothing in this system can translate
/// the player.
fn apply_mouse_look(
    mut plane: ResMut<GameplayInput>,
    mode: Res<LookInputMode>,
    cursor: Option<Single<&CursorOptions>>,
    phase: Res<SimWakePhase>,
    mut angles: ResMut<LookAngles>,
    mut rig: RigTransforms,
) {
    let cursor_arms = match mode.into_inner() {
        LookInputMode::Scripted => true,
        LookInputMode::Device => {
            cursor.is_none_or(|cursor| cursor.into_inner().grab_mode == CursorGrabMode::Locked)
        }
    };
    let armed = cursor_arms && phase.into_inner().phase().look_allowed();
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
    rig.yaw.rotation = Quat::from_rotation_y(yaw_angle);
    rig.pitch.rotation = Quat::from_rotation_x(pitch_angle);
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
mod tests;
