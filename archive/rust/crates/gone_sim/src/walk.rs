//! The steadying walk: post-get-up movement out of
//! [`WakePhase::Standing`] (issue #7 walk beat).
//!
//! The story beat, continued: the player has stood up out of the seventh
//! pod and their legs are still full of pins and needles. This module owns
//! the simulation side of the first walk. From a full stop the walk speed
//! ramps from the frozen [`STEADY_INITIAL_SPEED_FACTOR`] share of
//! [`SURVIVAL_WALK_SPEED`] toward full survival pace with the frozen
//! exponential time constant [`STEADYING_TIME_CONSTANT`], and every tick's
//! intended motion is swept through the static [`ColliderSet`] by the
//! landed resolver ([`resolve_motion`]): walking slides along walls, steps
//! ledges within the frozen budget, and never tunnels through geometry.
//!
//! # The steadying ramp (documented and frozen)
//!
//! With `t` the sim seconds consumed by stepped ticks, the speed
//! multiplier is
//!
//! ```text
//! 1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * exp(-t / STEADYING_TIME_CONSTANT)
//! ```
//!
//! and the tick speed is [`SURVIVAL_WALK_SPEED`] times that multiplier.
//! The ramp starts bitwise on the exact frozen product
//! `STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED` (the limit formula
//! rounds one ulp off the frozen factor, and the first step must land on
//! the frozen numbers), sits near 76 percent of survival speed at one
//! time constant, and is within rounding of full speed a few constants
//! later. `t` advances once per consumed tick, by the tick's own sim
//! seconds: the module takes `dt` per call and never reads a wall clock,
//! so the harness drives it from scenario time.
//!
//! The ramp is temporal, not directional, by definition: `t` accumulates
//! on every consumed tick no matter which way the intent points, and a
//! direction change never resets it. The pins-and-needles recovery is a
//! property of time since the get-up, not of where the player is headed;
//! making it directional would hand players a speed reset button. It
//! follows that the ramp is deterministic given the tick sequence: the
//! only ramp state is `t`, summed in tick order, so the same ticks with
//! the same `dt` reproduce the speed curve bitwise.
//!
//! # Tick and intent rule
//!
//! One call to [`WalkState::step`] consumes the tick's intent exactly
//! once. A second step before [`WalkState::end_tick`] closes the tick is
//! the hard error [`WalkError::StepAlreadyTaken`], so a duplicated system
//! call can never double-step the player, and every error leaves the
//! state untouched, so a rejected step never half-applies.
//!
//! Units: meters, seconds, meters per second, up is positive Y, matching
//! [`crate::controller`]. Pure: no Bevy, no clocks, no RNG.

use glam::Vec3;

use crate::colliders::ColliderSet;
use crate::controller::{
    MAX_INPUT_LENGTH, PENETRATION_TOLERANCE, STEADY_INITIAL_SPEED_FACTOR, STEADYING_TIME_CONSTANT,
    SURVIVAL_WALK_SPEED,
};
use crate::phase::WakePhase;
use crate::resolve::{Capsule, ResolveError, resolve_motion};

/// Which look-frame axis carried a non-finite component.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum IntentAxis {
    /// The forward/back component: positive toward the look direction,
    /// negative back.
    Forward,
    /// The strafe component: positive toward the player's right.
    Strafe,
    /// The look yaw the frame is built from.
    Yaw,
}

/// A rejected walk step or construction.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum WalkError {
    /// [`WalkState::start`] was called while the machine sat in `current`
    /// instead of the `expected` phase. Nothing was constructed.
    WrongPhase {
        /// The phase the call requires.
        expected: WakePhase,
        /// The phase the machine sat in.
        current: WakePhase,
    },
    /// A look-frame axis or the yaw carried a non-finite component,
    /// which would poison every direction computation downstream.
    NonFiniteIntentAxis {
        /// The offending axis.
        axis: IntentAxis,
        /// The offending value.
        got: f32,
    },
    /// The intent's magnitude overflowed to infinity, so the
    /// [`MAX_INPUT_LENGTH`] clamp scale is uncomputable. The intent is
    /// rejected instead of silently collapsing to zero.
    NonFiniteIntentMagnitude {
        /// The offending magnitude.
        got: f32,
    },
    /// The tick's sim seconds were NaN, infinite, or not strictly
    /// positive. A fixed tick always advances sim time; a tick that
    /// advances none of it is a caller bug, not a pause.
    InvalidTickSeconds {
        /// The offending tick seconds.
        got: f32,
    },
    /// A second step was taken within one fixed tick. One call to
    /// [`WalkState::step`] consumes the tick's intent; close the tick
    /// with [`WalkState::end_tick`] before stepping again.
    StepAlreadyTaken,
    /// The starting capsule carried a non-finite endpoint.
    NonFiniteCapsule,
    /// The resolver rejected the sweep outright (embedded start,
    /// non-finite state, or an exhausted iteration bound).
    Resolver(ResolveError),
}

impl std::fmt::Display for WalkError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::WrongPhase { expected, current } => write!(
                f,
                "walk expected phase {expected:?}, found {current:?}: the \
                 call is rejected and nothing moved"
            ),
            Self::NonFiniteIntentAxis { axis, got } => {
                write!(
                    f,
                    "move intent axis {axis:?} carried {got}, which is not finite"
                )
            }
            Self::NonFiniteIntentMagnitude { got } => write!(
                f,
                "move intent magnitude overflowed to {got}; the input cap \
                 scale is uncomputable"
            ),
            Self::InvalidTickSeconds { got } => write!(
                f,
                "tick seconds must be finite and strictly positive, got {got}"
            ),
            Self::StepAlreadyTaken => write!(
                f,
                "one walk step is consumed per fixed tick; close the tick \
                 with end_tick before stepping again"
            ),
            Self::NonFiniteCapsule => {
                write!(f, "the starting capsule carried a non-finite endpoint")
            }
            Self::Resolver(error) => write!(f, "walk sweep rejected by the resolver: {error}"),
        }
    }
}

impl std::error::Error for WalkError {}

/// One tick's movement input, framed in the player's look frame.
///
/// Built only through [`MoveIntent::new`], which validates finiteness
/// and applies the frozen [`MAX_INPUT_LENGTH`] policy, so an intent in
/// existence always resolves to a finite planar direction of length at
/// most one.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct MoveIntent {
    forward: f32,
    strafe: f32,
    yaw: f32,
}

impl MoveIntent {
    /// Frame one tick's movement input in the look frame at `yaw`.
    ///
    /// `forward` is positive toward the look direction and negative
    /// back; `strafe` is positive toward the player's right. With the
    /// yaw measured about +Y, the look axis is `(sin yaw, 0, cos yaw)`
    /// and the right axis is `(cos yaw, 0, -sin yaw)`, matching the
    /// placement transform in [`crate::pods`] and the exit path: local
    /// +Z at yaw 0 is the room's look-forward. Per the frozen
    /// [`MAX_INPUT_LENGTH`] policy, an intent whose magnitude exceeds
    /// the cap is scaled down to it (keyboard diagonals arrive at
    /// sqrt(2) and must not outrun a straight line); shorter intents
    /// keep their magnitude for analog partial deflection.
    ///
    /// # Errors
    /// [`WalkError::NonFiniteIntentAxis`] when an axis or the yaw is
    /// non-finite, and [`WalkError::NonFiniteIntentMagnitude`] when the
    /// magnitude overflows to infinity, where the clamp scale is
    /// uncomputable.
    pub fn new(yaw: f32, forward: f32, strafe: f32) -> Result<Self, WalkError> {
        if !yaw.is_finite() {
            return Err(WalkError::NonFiniteIntentAxis {
                axis: IntentAxis::Yaw,
                got: yaw,
            });
        }
        if !forward.is_finite() {
            return Err(WalkError::NonFiniteIntentAxis {
                axis: IntentAxis::Forward,
                got: forward,
            });
        }
        if !strafe.is_finite() {
            return Err(WalkError::NonFiniteIntentAxis {
                axis: IntentAxis::Strafe,
                got: strafe,
            });
        }
        let magnitude = (forward * forward + strafe * strafe).sqrt();
        if !magnitude.is_finite() {
            return Err(WalkError::NonFiniteIntentMagnitude { got: magnitude });
        }
        let (forward, strafe) = if magnitude > MAX_INPUT_LENGTH {
            let scale = MAX_INPUT_LENGTH / magnitude;
            (forward * scale, strafe * scale)
        } else {
            (forward, strafe)
        };
        Ok(Self {
            forward,
            strafe,
            yaw,
        })
    }

    /// The intent as a world-space planar direction: the look-frame axes
    /// rotated by the intent's yaw. The length is one for an input at or
    /// above the [`MAX_INPUT_LENGTH`] cap and the input's own sub-cap
    /// magnitude otherwise; Y is always zero.
    #[must_use]
    pub fn world_direction(self) -> Vec3 {
        let (sin, cos) = self.yaw.sin_cos();
        let look = Vec3::new(sin, 0.0, cos);
        let right = Vec3::new(cos, 0.0, -sin);
        look * self.forward + right * self.strafe
    }
}

/// How one stepped tick met the world.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WalkContact {
    /// No face constrained the sweep: the full intended motion applied.
    Free,
    /// A face constrained the sweep and the capsule kept tangential
    /// progress: motion slid along the struck geometry.
    Sliding,
    /// A face constrained the sweep and the planar motion was absorbed
    /// into it: the capsule pressed into the face and stopped.
    Stopped,
}

/// What one stepped walk tick did.
#[derive(Clone, Debug, PartialEq)]
pub struct WalkOutcome {
    /// Displacement actually applied: resolved foot-sphere position
    /// minus the prior one.
    pub displacement: Vec3,
    /// How the sweep met the world.
    pub contact: WalkContact,
    /// Distinct unit normals of every face that constrained the sweep,
    /// in first-hit order. Faces stepped over do not count.
    pub contact_normals: Vec<Vec3>,
    /// Whether a support face sat within the tolerance below the
    /// capsule foot at the resolved position.
    pub grounded: bool,
}

/// The steadying walk state: the standing capsule, the steadying clock,
/// and the current tick's consumption budget.
///
/// Built only through [`WalkState::start`], which requires the machine
/// to sit in [`WakePhase::Standing`]: locomotion exists only after the
/// get-up completes, per the phase contract's single locomotion
/// predicate.
#[derive(Clone, Debug, PartialEq)]
pub struct WalkState {
    capsule: Capsule,
    steadied_seconds: f32,
    tick_stepped: bool,
}

impl WalkState {
    /// Take over a standing capsule and open the first tick.
    ///
    /// The capsule is the get-up's waypoint pose: [`WakePhase::Standing`]
    /// is required, mirroring the phase contract's locomotion predicate,
    /// and any earlier phase rejects with [`WalkError::WrongPhase`] and
    /// constructs nothing.
    ///
    /// # Errors
    /// [`WalkError::WrongPhase`] when the machine is not in
    /// [`WakePhase::Standing`], and [`WalkError::NonFiniteCapsule`] when
    /// the capsule carries a non-finite endpoint.
    pub fn start(phase: &WakePhase, capsule: Capsule) -> Result<Self, WalkError> {
        if !phase.in_phase(WakePhase::Standing) {
            return Err(WalkError::WrongPhase {
                expected: WakePhase::Standing,
                current: *phase,
            });
        }
        if !capsule.foot.is_finite() || !capsule.head.is_finite() {
            return Err(WalkError::NonFiniteCapsule);
        }
        Ok(Self {
            capsule,
            steadied_seconds: 0.0,
            tick_stepped: false,
        })
    }

    /// The capsule's current room-frame segment.
    #[must_use]
    pub fn capsule(&self) -> Capsule {
        self.capsule
    }

    /// The current steadied walk speed in meters per second: the speed
    /// the next consumed tick will move at. At a full stop this is the
    /// exact frozen initial product; thereafter the frozen exponential
    /// approach toward [`SURVIVAL_WALK_SPEED`].
    #[must_use]
    pub fn speed(&self) -> f32 {
        steadied_speed(self.steadied_seconds)
    }

    /// Consume the tick: sweep the intent's displacement —
    /// `intent.world_direction() * self.speed() * dt` — through
    /// `colliders` with the landed resolver, land the capsule at the
    /// resolved position, and advance the steadying clock by `dt`.
    ///
    /// The tick moves at the speed the ramp held when the call arrived;
    /// the clock advances after the sweep, so the first step after
    /// standing moves at the frozen initial product. The tick's intent
    /// is consumed exactly once: a second call before
    /// [`WalkState::end_tick`] is [`WalkError::StepAlreadyTaken`].
    /// Errors never mutate: a rejected step leaves the capsule, the
    /// ramp, and the tick budget exactly as they were.
    ///
    /// # Errors
    /// [`WalkError::StepAlreadyTaken`] when the tick is already stepped,
    /// [`WalkError::InvalidTickSeconds`] when `dt` is NaN, infinite, or
    /// not strictly positive, and [`WalkError::Resolver`] when the
    /// resolver rejects the sweep.
    pub fn step(
        &mut self,
        intent: MoveIntent,
        dt: f32,
        colliders: &ColliderSet,
    ) -> Result<WalkOutcome, WalkError> {
        if self.tick_stepped {
            return Err(WalkError::StepAlreadyTaken);
        }
        if !dt.is_finite() || dt <= 0.0 {
            return Err(WalkError::InvalidTickSeconds { got: dt });
        }
        let direction = intent.world_direction();
        let intended = direction * (self.speed() * dt);
        let resolved =
            resolve_motion(self.capsule, intended, colliders).map_err(WalkError::Resolver)?;
        let contact = classify_contact(resolved.displacement, direction, &resolved.contact_normals);
        self.capsule.foot += resolved.displacement;
        self.capsule.head += resolved.displacement;
        self.steadied_seconds += dt;
        self.tick_stepped = true;
        Ok(WalkOutcome {
            displacement: resolved.displacement,
            contact,
            contact_normals: resolved.contact_normals,
            grounded: resolved.grounded,
        })
    }

    /// Close the fixed tick: the next [`WalkState::step`] belongs to a
    /// fresh tick and may consume its intent. Idempotent and infallible;
    /// the harness tick loop calls this once per tick after stepping.
    pub fn end_tick(&mut self) {
        self.tick_stepped = false;
    }
}

/// Classify the tick's contact from the resolver's report: free when no
/// face constrained the sweep; otherwise sliding when tangential
/// progress survived the contact, stopped when the planar motion was
/// absorbed into the struck face. Tangential progress within the
/// penetration tolerance counts as none: the tolerance is the house
/// semantic band for touching.
fn classify_contact(applied: Vec3, direction: Vec3, normals: &[Vec3]) -> WalkContact {
    if normals.is_empty() {
        return WalkContact::Free;
    }
    // A contact report implies a moving sweep: speed and dt are strictly
    // positive and a zero intent cannot strike anything, so the planar
    // direction normalizes here.
    let planar = Vec3::new(direction.x, 0.0, direction.z);
    let ahead = planar / planar.length();
    let aside = Vec3::new(-ahead.z, 0.0, ahead.x);
    let planar_applied = Vec3::new(applied.x, 0.0, applied.z);
    if planar_applied.dot(aside).abs() > PENETRATION_TOLERANCE {
        WalkContact::Sliding
    } else {
        WalkContact::Stopped
    }
}

/// The steadying ramp at `seconds` of accumulated sim time. At zero the
/// frozen initial product is returned bitwise: the limit formula rounds
/// one ulp off the frozen factor, and the ramp must start exactly on the
/// numbers the controller brief froze.
fn steadied_speed(seconds: f32) -> f32 {
    if seconds == 0.0 {
        return STEADY_INITIAL_SPEED_FACTOR * SURVIVAL_WALK_SPEED;
    }
    let multiplier =
        1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * (-seconds / STEADYING_TIME_CONSTANT).exp();
    SURVIVAL_WALK_SPEED * multiplier
}

#[cfg(test)]
mod tests;
