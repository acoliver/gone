//! Frozen first-person controller specification (issue #7 stage A).
//!
//! These constants are frozen before blockout geometry lands so the
//! controller brief, the scene brief, and the collision acceptance scenarios
//! all build against one set of numbers. The room they are tuned for is a
//! rectangular stasis bay greyboxed from primitives: roughly 12 m by 8 m of
//! floor with a 3.2 m ceiling, seven stasis pods in two rows along the long
//! walls (four and three), a central aisle about 3 m wide, and a single
//! hatch in one short wall. Pods are axis-aligned boxes about 2.2 m long,
//! 0.9 m wide, and 0.8 m tall at the plinth.
//!
//! Units: lengths and distances in meters, times in seconds, speeds in
//! meters per second, up is positive Y. The collision resolver and the walk
//! controller that consume these numbers are built by later briefs on the
//! same issue; nothing here computes, everything here specifies.

/// Radius of the player capsule, in meters.
///
/// 0.30 m is an adult shoulder half-width. It leaves about 1.2 m of free
/// width on each side of a player in the 3 m central aisle, fits the 0.9 m
/// pod opening with the frozen [`POD_EXIT_CLEARANCE`] margin on each jamb,
/// and keeps capsule-versus-box corner cases cheap in the axis-aligned
/// primitive collider set.
pub const CAPSULE_RADIUS: f32 = 0.30;

/// Total capsule height while standing, in meters.
///
/// 1.75 m models crew standing height and puts the eye point near 1.6 m:
/// low enough under the 3.2 m ceiling to keep the torn cable trays and the
/// hanging wire loops in frame, high enough to see across the 0.8 m pod
/// plinths while walking the aisle.
pub const CAPSULE_STANDING_HEIGHT: f32 = 1.75;

/// Maximum ledge height the controller climbs with a step, in meters.
///
/// 0.25 m covers deck plate lips, fallen panels, and flattened cable tray
/// covers on the floor without any jump input. It stays below the roughly
/// 0.4 m knee line, so walking can never step the player onto a pod plinth
/// or a hatch sill.
pub const STEP_UP_HEIGHT: f32 = 0.25;

/// Upper bound on sweep-and-slide iterations per fixed tick.
///
/// The milestone-one collider set is axis-aligned primitives: walls, pod
/// boxes, and the hatch. Slide resolution against that set converges in two
/// to three iterations even where a wall and a pod corner meet. Eight
/// bounds the resolver's worst-case per-tick cost with headroom for
/// three-face corners and keeps a wedged player deterministic instead of
/// spinning unbounded.
pub const SWEEP_ITERATION_BOUND: u32 = 8;

/// Allowed residual penetration after resolution, in meters.
///
/// 5 mm is invisible at first-person camera distances and orders of
/// magnitude above f32 rounding noise at room scale, while remaining far
/// below anything a player could exploit. Collision acceptance against
/// walls, pod faces, pod corners, and the jammed hatch reads as no
/// penetration beyond this tolerance.
pub const PENETRATION_TOLERANCE: f32 = 0.005;

/// Free-space margin required around the capsule at pod exit, in meters.
///
/// The pod opening is 0.9 m wide; the 0.60 m capsule diameter plus this
/// 0.15 m margin on each jamb fills it exactly. The get-up completes to
/// [`crate::WakePhase::Standing`] only with this much clearance along the
/// swept path out of the opening, so the standing capsule never spawns in
/// penetration with its own pod.
pub const POD_EXIT_CLEARANCE: f32 = 0.15;

/// Steady survival walking speed, in meters per second.
///
/// 0.9 m/s is roughly two thirds of an unhurried walk: the documented slow
/// survival pace. It carries the player about 9 m from the seventh pod to
/// the hatch in roughly ten seconds, which paces the door beat without
/// feeling like wading.
pub const SURVIVAL_WALK_SPEED: f32 = 0.9;

/// Walk speed multiplier applied at the first unsteady step after standing.
///
/// 35 percent of [`SURVIVAL_WALK_SPEED`], about 0.32 m/s, reads as legs
/// full of pins and needles per the story beat while still clearing a pod
/// length in a few seconds.
pub const STEADY_INITIAL_SPEED_FACTOR: f32 = 0.35;

/// Exponential steadying time constant, in seconds.
///
/// The speed multiplier recovers toward 1.0 as
/// `1.0 - (1.0 - STEADY_INITIAL_SPEED_FACTOR) * exp(-t /
/// STEADYING_TIME_CONSTANT)`: about 76 percent of survival speed at 1.2 s,
/// 91 percent at 2.4 s, and visually settled inside four seconds. That
/// lands the documented unsteady-start steadying over the first seconds of
/// walking.
pub const STEADYING_TIME_CONSTANT: f32 = 1.2;

/// Input magnitude at which the move vector is normalized.
///
/// Policy: the controller scales the input vector to this length only when
/// its magnitude exceeds it, and leaves shorter vectors untouched. Keyboard
/// diagonals arrive at sqrt(2) and clamp to 1.0, so diagonals are not
/// faster than straight lines; analog sticks report at most 1.0 and keep
/// their partial deflection magnitudes for analog walking speed.
pub const MAX_INPUT_LENGTH: f32 = 1.0;
