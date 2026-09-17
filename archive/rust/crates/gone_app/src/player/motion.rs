//! Player body motion: the sim-driven get-up and steadying walk (issue #7,
//! app wiring of the sim core).
//!
//! The slice owns nothing about *how* the body moves — that is `gone_sim`'s
//! frozen contract ([`gone_sim::exit`]'s authored get-up path and
//! [`gone_sim::walk`]'s steadying ramp). It owns only the wiring:
//!
//! * **One intent pathway.** The device producer and the harness adapter
//!   both feed the shared gameplay input plane ([`GameplayInput`]); this
//!   slice consumes the same plane a human's keys feed, so the body cannot
//!   tell a player from the runner. A fresh activate press (device Space,
//!   scripted `Key::Activate`) starts the get-up; the tick's movement
//!   intent drives the walk.
//! * **One mirror.** [`PlayerMotion`] follows the authoritative
//!   [`SimWakePhase`] machine: `Lying` until the machine is `AwakeInPod`
//!   and the intent arrives, `GetUp` while the machine is `ExitingPod` (one
//!   authored segment per driven tick), `Walk` from `Standing` on. The
//!   gates are the machine's own typed contracts
//!   ([`gone_sim::exit::ExitError::WrongPhase`],
//!   [`gone_sim::walk::WalkError::WrongPhase`]), so a wiring bug that
//!   tries to walk before `Standing` or get up before `AwakeInPod` fails
//!   loudly instead of half-applying.
//! * **One clock.** In a harness lane the body advances only on a driven
//!   tick: the fixed step comes from [`ScenarioTime`]'s driven-tick drain,
//!   so a held update (a beat readback in flight, the canary present gate)
//!   cannot advance the body. The normal game advances on every update's
//!   virtual delta.
//! * **Fail fast.** The first typed sim rejection lands in
//!   [`MotionFailure`] and [`halt_on_motion_failure`] exits the app nonzero
//!   on the same update, naming the rejection. Nothing is retried,
//!   swallowed, or clamped.
//!
//! The rig follows the body: during the get-up the eye rides the capsule's
//! head sphere as the authored path swings it up and out of the pod;
//! standing, the eye sits directly above the foot's ground contact at the
//! controller spec's standing eye height. Look keeps owning the rotations;
//! this slice writes only the yaw parent's translation.

use std::num::NonZeroU8;

use bevy::app::{App, AppExit, Plugin, Update};
use bevy::ecs::message::MessageWriter;
use bevy::ecs::prelude::{Local, Res, ResMut, Resource, Single, With};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::ecs::system::SystemParam;
use bevy::math::Vec3;
use bevy::time::{Time, Virtual};
use bevy::transform::components::Transform;
use gone_sim::controller::CAPSULE_RADIUS;
use gone_sim::exit::{ExitError, ExitPath, GetUpController};
use gone_sim::walk::{MoveIntent, WalkError, WalkState};
use gone_sim::{Capsule, WakePhase};

use crate::bootstrap::ScenarioTime;
use crate::harness::MoveMotion;
use crate::placement_truth::STANDING_EYE_HEIGHT;
use crate::scene::{PlayerExitPath, SimColliders, SimWakePhase};

use super::{GameplayInput, LookAngles, LookApplied, PlaneCleared, PlayerYaw};

/// The player body's mirrored motion state: which sim controller, if any,
/// currently owns the body. The sim phase machine is authoritative; the
/// mirror only ever follows it (the get-up start advances the machine
/// through the controller, the walk starts only at `Standing`), and a
/// disagreement is a recorded failure, never a silent rewrite.
#[derive(Resource, Default)]
pub(crate) struct PlayerMotion {
    body: BodyMotion,
}

impl PlayerMotion {
    /// Which controller, if any, currently owns the body: the mirror's
    /// discriminator for the tick's state dispatch.
    #[must_use]
    pub(crate) fn state(&self) -> BodyState {
        match &self.body {
            BodyMotion::Lying => BodyState::Lying,
            BodyMotion::GetUp(_) => BodyState::GetUp,
            BodyMotion::Walk(_) => BodyState::Walk,
        }
    }

    /// The capsule the sim currently owns, if a controller holds one.
    #[must_use]
    pub(crate) fn capsule(&self) -> Option<Capsule> {
        match &self.body {
            BodyMotion::Lying => None,
            BodyMotion::GetUp(controller) => Some(controller.capsule()),
            BodyMotion::Walk(walk) => Some(walk.capsule()),
        }
    }
}

/// Which controller currently owns the body: the mirror's discriminator.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum BodyState {
    /// No controller: lying in the pod (`Waking` or `AwakeInPod`).
    Lying,
    /// The authored get-up owns the body (`ExitingPod`).
    GetUp,
    /// The steadying walk owns the capsule (`Standing`).
    Walk,
}

/// The body's controller payload: nothing until the get-up intent starts
/// the exit controller, then the walk once the waypoint lands. The
/// controller rides in a box: it is built once per run at a phase boundary,
/// and unboxed the walk variant (an order of magnitude smaller) would make
/// every `Lying` entity carry the get-up's whole authored pose table.
#[derive(Default)]
enum BodyMotion {
    /// No controller: lying in the pod.
    #[default]
    Lying,
    /// The authored get-up owns the body (the machine is in `ExitingPod`).
    GetUp(Box<GetUpController>),
    /// The steadying walk owns the capsule (the machine is in `Standing`).
    Walk(WalkState),
}

/// One typed sim rejection, or a mirror disagreement: exactly what the app
/// offered that the sim refused. The `Display` is the halt message.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum MotionFailureKind {
    /// The get-up controller rejected a start or a segment tick.
    GetUp(ExitError),
    /// The walk rejected a start or a step.
    Walk(WalkError),
    /// The mirrored motion state disagreed with the sim phase: a wiring
    /// bug, never a gameplay input (the machine never moves backward, so a
    /// mismatch means the mirror or the phase resource was rewritten
    /// around the controllers).
    PhaseMirror {
        /// The phase the machine sat in.
        phase: WakePhase,
        /// The motion state that disagreed with it ("get-up" or "walk").
        state: &'static str,
    },
}

impl std::fmt::Display for MotionFailureKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::GetUp(error) => write!(f, "get-up rejected: {error}"),
            Self::Walk(error) => write!(f, "walk rejected: {error}"),
            Self::PhaseMirror { phase, state } => write!(
                f,
                "the player motion state `{state}` disagrees with the sim \
                 phase {phase:?}"
            ),
        }
    }
}

/// The run's first typed motion failure. Recorded fail-fast —
/// [`halt_on_motion_failure`] exits the app nonzero on the same update —
/// and never cleared: the first rejection is the run's verdict.
#[derive(Resource, Default)]
pub(crate) struct MotionFailure(Option<MotionFailureKind>);

impl MotionFailure {
    /// Record the first failure; later ones are dropped because the first
    /// already names the verdict. Logs once, loudly.
    fn record(&mut self, kind: MotionFailureKind) {
        if self.0.is_none() {
            bevy::log::error!("player motion failed: {kind}");
            self.0 = Some(kind);
        }
    }

    /// The recorded failure, if any.
    #[must_use]
    pub(crate) fn kind(&self) -> Option<&MotionFailureKind> {
        self.0.as_ref()
    }
}

/// Start the authored get-up: run the exit intent through the machine's own
/// contract ([`GetUpController::start`]), which consumes the fresh press in
/// `AwakeInPod`, advances the machine to `ExitingPod`, and takes the
/// capsule onto the path's first pose.
///
/// # Errors
/// [`MotionFailureKind::GetUp`] with the machine's
/// [`ExitError::WrongPhase`] when the machine is not in `AwakeInPod`: the
/// app's own gate ([`begin_get_up_if_pressed`]) never starts the get-up in
/// a phase whose policy drops exit intent, so a rejection here is a wiring
/// bug and fails fast.
pub(crate) fn start_get_up(
    phase: &mut SimWakePhase,
    exit_path: &ExitPath,
) -> Result<GetUpController, MotionFailureKind> {
    GetUpController::start(phase.machine_mut(), *exit_path).map_err(MotionFailureKind::GetUp)
}

/// Take over the standing capsule once the machine reached `Standing`.
///
/// # Errors
/// [`MotionFailureKind::Walk`] with the machine's
/// [`WalkError::WrongPhase`] when the machine is not in `Standing` — the
/// get-up only lands there at the waypoint, so a rejection is a wiring bug
/// and fails fast.
pub(crate) fn start_walk(
    current: WakePhase,
    capsule: Capsule,
) -> Result<WalkState, MotionFailureKind> {
    WalkState::start(&current, capsule).map_err(MotionFailureKind::Walk)
}

/// The `Lying` tick: a fresh activate press starts the get-up, but only in
/// `AwakeInPod`. The phase policy drops exit intent in every other phase
/// (`Waking` holds the wake sequence, `ExitingPod` and `Standing` own the
/// body), so there the edge is consumed and dropped — never buffered,
/// never a failure — and a later press in `AwakeInPod` is the one that
/// fires. Movement intent offered the same tick is left for the end-of-frame
/// clear: the get-up owns the body from this tick on.
fn begin_get_up_if_pressed(
    plane: &mut GameplayInput,
    phase: &mut SimWakePhase,
    exit_path: &ExitPath,
    motion: &mut PlayerMotion,
    failure: &mut MotionFailure,
) {
    if !plane.take_activate_press() || phase.phase() != WakePhase::AwakeInPod {
        return;
    }
    match start_get_up(phase, exit_path) {
        Ok(controller) => motion.body = BodyMotion::GetUp(Box::new(controller)),
        Err(kind) => failure.record(kind),
    }
}

/// One tick's walk context: the look yaw the intent frame is built from,
/// the sim seconds the tick advances, and the collider set the sweep
/// resolves against.
#[derive(Clone, Copy)]
pub(crate) struct WalkFrame<'a> {
    /// The integrated look yaw, in radians.
    pub(crate) yaw: f32,
    /// The tick's sim seconds (the scenario step or the virtual delta).
    pub(crate) dt: f32,
    /// The static collider set the sweep resolves against.
    pub(crate) colliders: &'a SimColliders,
}

/// Consume the tick's movement intent: frame it in the look frame at the
/// tick's yaw, sweep it through the resolver at the walk's current speed,
/// close the tick, and land the capsule at the resolved stop.
///
/// # Errors
/// [`MotionFailureKind::Walk`] for a non-finite intent or tick, a double
/// step, or a resolver rejection: typed, never clamped.
pub(crate) fn take_walk_step(
    walk: &mut WalkState,
    frame: WalkFrame,
    intent: MoveMotion,
) -> Result<(), MotionFailureKind> {
    let intent = MoveIntent::new(frame.yaw, intent.forward, intent.strafe)
        .map_err(MotionFailureKind::Walk)?;
    walk.step(intent, frame.dt, frame.colliders.set())
        .map_err(MotionFailureKind::Walk)?;
    walk.end_tick();
    Ok(())
}

/// The `GetUp` tick: drive the authored path exactly one segment through
/// the machine and the collider set. Reaching the final pose delivers the
/// machine's get-up-complete signal (the controller does it) and hands the
/// standing capsule to the walk — completion is `Standing` at the waypoint.
fn advance_get_up(
    motion: &mut PlayerMotion,
    phase: &mut SimWakePhase,
    colliders: &SimColliders,
    failure: &mut MotionFailure,
) {
    let BodyMotion::GetUp(controller) = &mut motion.body else {
        failure.record(MotionFailureKind::PhaseMirror {
            phase: phase.phase(),
            state: "get-up",
        });
        return;
    };
    let mut controller = **controller;
    match controller.tick(phase.machine_mut(), colliders.set()) {
        Ok(progress) => {
            if progress.at_waypoint {
                match start_walk(phase.phase(), controller.capsule()) {
                    Ok(walk) => motion.body = BodyMotion::Walk(walk),
                    Err(kind) => failure.record(kind),
                }
            } else {
                motion.body = BodyMotion::GetUp(Box::new(controller));
            }
        }
        Err(error) => failure.record(MotionFailureKind::GetUp(error)),
    }
}

/// The `Walk` tick: the machine must still be in `Standing` (the mirror's
/// invariant; nothing in this slice leaves it), then the tick's movement
/// intent steps the capsule through the resolver.
fn advance_walk(
    motion: &mut PlayerMotion,
    plane: &mut GameplayInput,
    phase: &SimWakePhase,
    failure: &mut MotionFailure,
    frame: WalkFrame,
) {
    if phase.phase() != WakePhase::Standing {
        failure.record(MotionFailureKind::PhaseMirror {
            phase: phase.phase(),
            state: "walk",
        });
        return;
    }
    let BodyMotion::Walk(walk) = &mut motion.body else {
        failure.record(MotionFailureKind::PhaseMirror {
            phase: phase.phase(),
            state: "walk",
        });
        return;
    };
    let intent = plane.take_movement();
    if let Err(kind) = take_walk_step(walk, frame, intent) {
        failure.record(kind);
    }
}

/// The standing rig's eye point: directly above the capsule foot's ground
/// contact, at the controller spec's standing eye height.
#[must_use]
pub(crate) fn standing_eye(capsule: Capsule) -> Vec3 {
    Vec3::new(
        capsule.foot.x,
        capsule.foot.y - CAPSULE_RADIUS + STANDING_EYE_HEIGHT,
        capsule.foot.z,
    )
}

/// The get-up rig's eye point: the capsule's head sphere, so the camera
/// rides the head as the authored path swings the body up and out of the
/// pod. The handoff to [`standing_eye`] at the waypoint is one short
/// authored step onto the standing eye height.
#[must_use]
pub(crate) fn get_up_eye(capsule: Capsule) -> Vec3 {
    capsule.head
}

/// The tick's body-advance context: the intent plane, the authoritative
/// sim phase, the static colliders, the authored exit path, the look yaw,
/// the mirror, and the failure ledger. One [`SystemParam`] keeps the
/// system inside the workspace's argument limit.
#[derive(SystemParam)]
pub(crate) struct MotionSim<'w> {
    /// The shared gameplay input plane (device and scripted intent).
    plane: ResMut<'w, GameplayInput>,
    /// The authoritative sim phase machine.
    phase: ResMut<'w, SimWakePhase>,
    /// The static collider set the sweeps resolve against.
    colliders: Res<'w, SimColliders>,
    /// The authored get-up path out of the player pod.
    exit: Res<'w, PlayerExitPath>,
    /// The integrated look yaw the walk frame is built from.
    look: Res<'w, LookAngles>,
    /// The body's mirrored motion state.
    motion: ResMut<'w, PlayerMotion>,
    /// The run's first typed motion failure, if any.
    failure: ResMut<'w, MotionFailure>,
}

/// The tick's clock: the driven scenario step in a harness lane (where the
/// resource exists) or bevy's virtual delta in the normal game. Only the
/// harness path can say "this update drove nothing".
#[derive(SystemParam)]
pub(crate) struct MotionClock<'w> {
    /// The landed scenario clock (harness lanes only).
    scenario: Option<ResMut<'w, ScenarioTime>>,
    /// bevy's virtual clock (the normal game's dt source).
    virtual_time: Option<Res<'w, Time<Virtual>>>,
}

impl MotionClock<'_> {
    /// The sim seconds this update advances the body by, or `None` when the
    /// body must hold still: harness lanes advance only on a driven tick,
    /// so a held update (loading, the canary present gate, a beat readback
    /// in flight) cannot double-advance the body, and the normal game
    /// advances on every update's virtual delta.
    fn body_step(&mut self) -> Option<f32> {
        if let Some(scenario) = self.scenario.as_deref_mut() {
            return scenario.drain_driven_delta();
        }
        self.virtual_time
            .as_deref()
            .map(Time::<Virtual>::delta_secs)
    }
}

/// The rig's eye carrier: the yaw parent's transform. The pitch camera
/// child stays at its local origin, so the parent's translation is the eye
/// point; look owns the rotations, this slice only the translation.
#[derive(SystemParam)]
pub(crate) struct RigEye<'w, 's> {
    /// The yaw parent's transform (translation only is written).
    yaw: Single<'w, 's, &'static mut Transform, With<PlayerYaw>>,
}

/// Advance the mirrored motion state by one driven step: consume the tick's
/// get-up edge or movement intent from the shared plane, drive the sim
/// controller it owns, then project the body's capsule onto the rig — the
/// eye rides the head sphere while a controller owns the body (the get-up's
/// start pose included) and stands at the standing eye height once the walk
/// owns it. Systems order between [`LookApplied`] and the input clear
/// ([`PlaneCleared`]), so a scripted input offered by the drive half on
/// tick N drives the body on tick N and nothing is dropped early.
fn advance_player_motion(mut sim: MotionSim, mut clock: MotionClock, mut rig: RigEye) {
    let Some(dt) = clock.body_step() else {
        return;
    };
    let frame = WalkFrame {
        yaw: sim.look.yaw,
        dt,
        colliders: &sim.colliders,
    };
    match sim.motion.state() {
        BodyState::Lying => begin_get_up_if_pressed(
            &mut sim.plane,
            &mut sim.phase,
            &sim.exit.0,
            &mut sim.motion,
            &mut sim.failure,
        ),
        BodyState::GetUp => advance_get_up(
            &mut sim.motion,
            &mut sim.phase,
            frame.colliders,
            &mut sim.failure,
        ),
        BodyState::Walk => advance_walk(
            &mut sim.motion,
            &mut sim.plane,
            &sim.phase,
            &mut sim.failure,
            frame,
        ),
    }
    if sim.motion.state() != BodyState::Lying {
        let capsule = sim
            .motion
            .capsule()
            .expect("a controller that owns the body holds its capsule");
        let eye = match sim.motion.state() {
            BodyState::GetUp => get_up_eye(capsule),
            BodyState::Walk => standing_eye(capsule),
            BodyState::Lying => unreachable!("excluded by the guard above"),
        };
        rig.yaw.translation = eye;
    }
}

/// Exit the app nonzero on the tick's first motion failure, naming the
/// typed rejection. Exactly one exit per failure (the once-flag; bevy stops
/// on the first exit anyway) and no path back: a sim rejection is the run's
/// verdict, never a retryable state.
fn halt_on_motion_failure(
    failure: Res<MotionFailure>,
    mut exits: MessageWriter<AppExit>,
    mut halted: Local<bool>,
) {
    let failure = failure.into_inner();
    if *halted || failure.kind().is_none() {
        return;
    }
    *halted = true;
    bevy::log::error!(
        "halting on player motion failure: {}",
        failure.kind().expect("checked above")
    );
    exits.write(AppExit::Error(NonZeroU8::new(1).expect("one is nonzero")));
}

/// Adds the player body motion slice: the get-up and the steadying walk,
/// driven from the shared gameplay input plane against the sim's phase
/// machine, collider set, and authored exit path. Requires the look plugin
/// (the rig and the look angles) and the stasis scene (the sim resources);
/// their absence is a wiring error the systems fail on loudly.
pub struct PlayerMotionPlugin;

impl Plugin for PlayerMotionPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<PlayerMotion>()
            .init_resource::<MotionFailure>()
            .add_systems(
                Update,
                (advance_player_motion, halt_on_motion_failure)
                    .chain()
                    .after(LookApplied)
                    .before(PlaneCleared),
            );
    }
}
