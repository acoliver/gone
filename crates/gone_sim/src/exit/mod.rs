//! The authored get-up path out of the stasis pod and its tick-driven
//! controller (issue #7 get-up beat).
//!
//! The story beat: the player wakes lying in the seventh pod, pops the
//! restraint, and their body remembers how to swing out and stand despite
//! legs full of pins and needles. This module owns the simulation side of
//! that beat as pure data plus a deterministic controller:
//!
//! * [`ExitPath`] authors the exit as five key capsule poses — lying in the
//!   tray, sitting up, standing in the tray, through the exit aperture
//!   mouth, standing on the room floor at the exit waypoint — with every
//!   number derived from the frozen constants in [`crate::controller`] and
//!   [`crate::pods`]. The pod's placement is an input: the same authored
//!   path serves any pod placement, and the waypoint's room-frame position
//!   is the placement transform of the authored local waypoint, never a
//!   hard-coded room coordinate. The pod cavity's interior floor is an
//!   input too: the sim does not own the tray's interior build, so the
//!   caller passes the plate top the lying capsule rests on.
//! * [`GetUpController`] drives the phase machine from
//!   [`WakePhase::AwakeInPod`] through [`WakePhase::ExitingPod`] to
//!   [`WakePhase::Standing`] while walking the capsule along the path.
//!
//! # Tick and segment rule
//!
//! One call to [`GetUpController::tick`] advances the capsule exactly one
//! authored segment, in authored order, and no further: the pose table is
//! the whole tick budget, so the get-up always takes exactly four ticks.
//! Each segment is either a rigid translation of the whole capsule or a
//! pivot about one sphere. Every tick's motion is swept through the
//! caller's [`ColliderSet`] by the landed resolver ([`resolve_motion`]),
//! and the swept volume requested is a conservative superset of the true
//! authored motion: for a pivot, a quarter turn of the free sphere about
//! the fixed sphere between axis-aligned radius directions, the true
//! swept region is the quarter sector about the fixed sphere inflated by
//! the capsule radius, and that sector stays inside the whole start
//! capsule swept by the free sphere's reached radius vector. A sweep that
//! completes unblocked therefore
//! proves the authored motion clip-free, and a sweep stopped short of the
//! target pose (by more than the pose's tolerance) is a hard
//! [`ExitError::PathBlocked`] — the motivating case being a blocked exit
//! aperture — never a silent clamp and never a pass through geometry.
//!
//! Units: meters, up is positive Y, matching `controller` and `pods`.
//! Pure: no Bevy, no clocks, no RNG.

use glam::Vec3;

use crate::colliders::ColliderSet;
use crate::controller::{
    CAPSULE_RADIUS, CAPSULE_STANDING_HEIGHT, PENETRATION_TOLERANCE, POD_EXIT_CLEARANCE,
};
use crate::phase::{InputEdge, PhaseError, PhaseTransition, WakePhase};
use crate::pods::{POD_HEIGHT, POD_LENGTH, POD_WIDTH, PodPlacement};
use crate::resolve::{Capsule, ResolveError, resolve_motion};

/// Arrival tolerance for one authored pose: twice the resolver's
/// penetration tolerance. A tick that stops within this distance of the
/// authored pose counts as reaching it; anything farther is a blocked
/// path, never a near miss to shrug off.
pub const POSE_TOLERANCE: f32 = 2.0 * PENETRATION_TOLERANCE;

/// The clear width the exit aperture mouth must hold for the path to be
/// walkable: the capsule diameter plus the frozen [`POD_EXIT_CLEARANCE`]
/// on each jamb. The app-side pod builder cuts the mouth to exactly this
/// width across the pod's full footprint, so the path's traversal of the
/// mouth — always centered, never laterally offset — holds the frozen
/// clearance on both sides.
pub const EXIT_MOUTH_WIDTH: f32 = 2.0 * (CAPSULE_RADIUS + POD_EXIT_CLEARANCE);

// The frozen aperture fits the pod width. The decimals fill it exactly;
// their f32 representations sit a fraction of an ulp apart, the same fit
// the app-side pod builder pins.
const _: () = assert!(EXIT_MOUTH_WIDTH <= POD_WIDTH * (1.0 + f32::EPSILON));

/// How many key poses the authored path holds.
pub const EXIT_POSE_COUNT: usize = 5;

/// How many authored segments connect the key poses.
const EXIT_SEGMENT_COUNT: usize = EXIT_POSE_COUNT - 1;

/// A rejected exit-path construction.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum ExitPathError {
    /// The pod placement carried a non-finite center coordinate or yaw.
    NonFinitePlacement,
    /// The tray floor height was non-finite.
    NonFiniteTrayFloor,
    /// The tray floor sat below the room floor, so the lying capsule would
    /// rest under the deck.
    TrayFloorBelowRoom {
        /// The rejected floor height.
        got: f32,
    },
    /// The tray floor sat so high the lying capsule cannot fit under the
    /// tray walls (the capsule top would pass the pod body's top line).
    TrayFloorTooHigh {
        /// The highest floor height the lying capsule fits under.
        max: f32,
        /// The rejected floor height.
        got: f32,
    },
    /// The frozen pose table stopped being connected by rigid moves and
    /// pivots, which the conservative sweep cannot cover. This is a
    /// build-time invariant of the authored table, surfaced at
    /// construction so a bad edit fails loudly instead of mid-sweep.
    AuthoredPathDisconnected {
        /// The index of the first disconnected segment.
        index: usize,
    },
}

impl std::fmt::Display for ExitPathError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NonFinitePlacement => {
                write!(f, "pod placement carried a non-finite coordinate or yaw")
            }
            Self::NonFiniteTrayFloor => write!(f, "tray floor height was non-finite"),
            Self::TrayFloorBelowRoom { got } => {
                write!(f, "tray floor {got} m sits below the room floor")
            }
            Self::TrayFloorTooHigh { max, got } => write!(
                f,
                "tray floor {got} m exceeds the {max} m ceiling the lying \
                 capsule fits under"
            ),
            Self::AuthoredPathDisconnected { index } => write!(
                f,
                "authored exit pose {index} is not connected to the previous \
                 pose by a rigid move or a pivot"
            ),
        }
    }
}

impl std::error::Error for ExitPathError {}

/// A rejected get-up step.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum ExitError {
    /// The machine was not in the phase the call requires. Nothing moved.
    WrongPhase {
        /// The phase the call requires.
        expected: WakePhase,
        /// The phase the machine sat in.
        current: WakePhase,
    },
    /// The sweep was stopped short of the authored pose: the path is
    /// blocked, the motivating case being a blocked exit aperture. The
    /// capsule sits where the resolver stopped it (rigid segments) or at
    /// the previous pose (pivots); nothing passed through geometry.
    PathBlocked {
        /// Index of the pose the sweep failed to reach.
        pose_index: usize,
        /// How far the capsule fell short of the pose, in meters.
        shortfall: f32,
    },
    /// The resolver rejected the sweep outright (embedded start,
    /// non-finite input, or an exhausted iteration bound).
    Resolver(ResolveError),
    /// The get-up already reached the waypoint; the controller is spent
    /// and cannot be re-run even if the machine is reset to
    /// [`WakePhase::ExitingPod`].
    GetUpAlreadyComplete,
}

impl std::fmt::Display for ExitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::WrongPhase { expected, current } => write!(
                f,
                "get-up expected phase {expected:?}, found {current:?}: the \
                 call is rejected and nothing moved"
            ),
            Self::PathBlocked {
                pose_index,
                shortfall,
            } => write!(
                f,
                "get-up sweep toward pose {pose_index} was stopped {shortfall} \
                 m short: the authored path is blocked"
            ),
            Self::Resolver(error) => {
                write!(f, "get-up sweep rejected by the resolver: {error}")
            }
            Self::GetUpAlreadyComplete => {
                write!(f, "the get-up already reached the waypoint")
            }
        }
    }
}

impl std::error::Error for ExitError {}

/// One authored key pose: a capsule segment position plus the arrival
/// tolerance, in room coordinates.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ExitPose {
    foot: Vec3,
    head: Vec3,
    tolerance: f32,
}

impl ExitPose {
    /// The foot (bottom) sphere center.
    #[must_use]
    pub fn foot(self) -> Vec3 {
        self.foot
    }

    /// The head (top) sphere center.
    #[must_use]
    pub fn head(self) -> Vec3 {
        self.head
    }

    /// The arrival tolerance: how far a sweep may stop short of this pose
    /// and still count as reaching it.
    #[must_use]
    pub fn tolerance(self) -> f32 {
        self.tolerance
    }

    /// The pose as a capsule for the resolver.
    fn capsule(self) -> Capsule {
        Capsule {
            foot: self.foot,
            head: self.head,
        }
    }
}

/// How one authored segment moves the capsule, and the single resolver
/// displacement whose sweep conservatively covers it.
///
/// A rigid segment sweeps its own translation. A pivot is a quarter turn
/// of the free sphere about the fixed sphere between axis-aligned radius
/// directions, and sweeps the whole capsule by the free sphere's reached
/// radius vector: the true swept region is the quarter sector about the
/// fixed sphere inflated by the capsule radius, which stays inside the
/// rectangle spanned by the two radius vectors, exactly the region the
/// start capsule's straight sweep covers.
#[derive(Clone, Copy, Debug, PartialEq)]
enum SegmentMove {
    /// Rigid translation of the whole capsule.
    Rigid(Vec3),
    /// The foot sphere stays put; the vector is the head sphere's reached
    /// radius from the foot.
    PivotAboutFoot(Vec3),
    /// The head sphere stays put; the vector is the foot sphere's reached
    /// radius from the head.
    PivotAboutHead(Vec3),
}

impl SegmentMove {
    /// The displacement to sweep the whole capsule by.
    fn vector(self) -> Vec3 {
        match self {
            Self::Rigid(displacement)
            | Self::PivotAboutFoot(displacement)
            | Self::PivotAboutHead(displacement) => displacement,
        }
    }

    /// The capsule state once the segment is reached.
    ///
    /// A rigid segment applies the resolver's own displacement, so a stop
    /// inside the tolerance band leaves the capsule where the sweep put
    /// it. A pivot keeps its fixed sphere put and places the free sphere
    /// at its reached radius: the sweep proved the quarter sector free,
    /// and the pivot's true end state lies inside the swept volume that
    /// was proved.
    fn visited(self, current: Capsule, swept: Vec3) -> Capsule {
        match self {
            Self::Rigid(_) => translate(current, swept),
            Self::PivotAboutFoot(radius) => Capsule {
                foot: current.foot,
                head: current.foot + radius,
            },
            Self::PivotAboutHead(radius) => Capsule {
                foot: current.head + radius,
                head: current.head,
            },
        }
    }
}

/// Slack for classifying an authored segment as rigid. The pose table's
/// rigid deltas are formed per sphere through independent f32 adds, so
/// equal-by-construction deltas can disagree in the last ulp (about 1e-7
/// at room scale). The band sits orders of magnitude above that rounding
/// noise and below the pose tolerance, so a genuinely non-rigid segment
/// still classifies as a pivot or fails the connectivity check.
const RIGID_SLACK: f32 = 1e-5;

/// Slack for authored-pivot geometry checks. The pose table's radius
/// vectors are formed through the placement transform, so an axis-aligned
/// radius can carry a cross-axis term of a few ulps (about 1e-7 at room
/// scale). The band sits orders of magnitude above that rounding noise
/// and far below any authored pivot dimension.
const PIVOT_SLACK: f32 = 1e-4;

/// Classify one authored segment, or `None` when the conservative sweep
/// cannot cover it: both spheres moving by different displacements, or a
/// pivot that is not a quarter turn between axis-aligned radius
/// directions.
fn segment_move(from: &ExitPose, to: &ExitPose) -> Option<SegmentMove> {
    let by_foot = to.foot - from.foot;
    let by_head = to.head - from.head;
    if (by_head - by_foot).length() <= RIGID_SLACK {
        return Some(SegmentMove::Rigid(by_foot));
    }
    if by_foot == Vec3::ZERO {
        return Some(SegmentMove::PivotAboutFoot(pivot_radius(
            from.foot, from.head, to.head,
        )?));
    }
    if by_head == Vec3::ZERO {
        return Some(SegmentMove::PivotAboutHead(pivot_radius(
            from.head, from.foot, to.foot,
        )?));
    }
    None
}

/// The free sphere's reached radius about the fixed sphere, when the
/// authored pivot is a quarter turn between axis-aligned radius
/// directions of one length. Only that shape's quarter sector stays
/// inside the straight whole-capsule sweep of the reached radius vector;
/// anything else cannot be covered and disconnects the path.
fn pivot_radius(fixed: Vec3, free_start: Vec3, free_end: Vec3) -> Option<Vec3> {
    let start = free_start - fixed;
    let end = free_end - fixed;
    let length = start.length();
    if (end.length() - length).abs() > PIVOT_SLACK {
        return None;
    }
    let start_axis = radius_axis(start, length)?;
    let end_axis = radius_axis(end, length)?;
    if start_axis == end_axis {
        return None;
    }
    Some(end)
}

/// Which axis an authored radius runs along, when it runs along exactly
/// one: the axis index, or `None` for a radius with off-axis components.
fn radius_axis(radius: Vec3, length: f32) -> Option<usize> {
    let abs = radius.abs();
    let on_axis = |component: f32| (component - length).abs() <= PIVOT_SLACK;
    let off_axis = |component: f32| component <= PIVOT_SLACK;
    if on_axis(abs.x) && off_axis(abs.y) && off_axis(abs.z) {
        Some(0)
    } else if off_axis(abs.x) && on_axis(abs.y) && off_axis(abs.z) {
        Some(1)
    } else if off_axis(abs.x) && off_axis(abs.y) && on_axis(abs.z) {
        Some(2)
    } else {
        None
    }
}

/// The authored exit from the pod: five key capsule poses in room
/// coordinates plus the per-segment movement table. Built only through
/// [`ExitPath::try_new`], which validates the inputs and the authored
/// table's connectivity.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ExitPath {
    poses: [ExitPose; EXIT_POSE_COUNT],
    moves: [SegmentMove; EXIT_SEGMENT_COUNT],
}

impl ExitPath {
    /// Author the exit path for one pod placement.
    ///
    /// `placement` carries the pod's room-frame pose: every key pose is
    /// authored in the pod's local frame (opening facing local +Z, head at
    /// local -Z) and transformed through it, so the waypoint's room-frame
    /// position is exactly the placement transform of the authored local
    /// waypoint. `tray_floor_y` is the room-frame height of the pod's
    /// interior floor — the cavity plate top the lying capsule rests on.
    ///
    /// The authored local table, for the frozen constants:
    /// lying centered in the pod on the tray floor, sitting up (pivot
    /// about the foot sphere), standing in the tray just inside the
    /// aperture line, crossing the mouth at tray height (the base slab
    /// spans the whole footprint, so the drop happens only once the
    /// capsule clears the pod's foot face by its own radius), and
    /// standing on the room floor at the waypoint.
    ///
    /// # Errors
    /// [`ExitPathError::NonFinitePlacement`] for a non-finite placement,
    /// [`ExitPathError::NonFiniteTrayFloor`] for a non-finite floor,
    /// [`ExitPathError::TrayFloorBelowRoom`] when the floor sits below the
    /// room floor, [`ExitPathError::TrayFloorTooHigh`] when the lying
    /// capsule cannot fit under the tray walls, and
    /// [`ExitPathError::AuthoredPathDisconnected`] when the pose table
    /// stops being connected by rigid moves and pivots.
    pub fn try_new(placement: PodPlacement, tray_floor_y: f32) -> Result<Self, ExitPathError> {
        if !placement.center.0.is_finite()
            || !placement.center.1.is_finite()
            || !placement.yaw_radians.is_finite()
        {
            return Err(ExitPathError::NonFinitePlacement);
        }
        if !tray_floor_y.is_finite() {
            return Err(ExitPathError::NonFiniteTrayFloor);
        }
        if tray_floor_y < 0.0 {
            return Err(ExitPathError::TrayFloorBelowRoom { got: tray_floor_y });
        }
        let max_floor = POD_HEIGHT - 2.0 * CAPSULE_RADIUS;
        if tray_floor_y > max_floor {
            return Err(ExitPathError::TrayFloorTooHigh {
                max: max_floor,
                got: tray_floor_y,
            });
        }
        let poses = authored_poses(placement, tray_floor_y);
        let mut moves = [SegmentMove::Rigid(Vec3::ZERO); EXIT_SEGMENT_COUNT];
        for index in 0..EXIT_SEGMENT_COUNT {
            moves[index] = segment_move(&poses[index], &poses[index + 1])
                .ok_or(ExitPathError::AuthoredPathDisconnected { index })?;
        }
        Ok(Self { poses, moves })
    }

    /// The authored poses, in walk order.
    #[must_use]
    pub fn poses(&self) -> &[ExitPose; EXIT_POSE_COUNT] {
        &self.poses
    }

    /// The final pose: standing on the room floor at the exit waypoint.
    #[must_use]
    pub fn waypoint(&self) -> ExitPose {
        self.poses[EXIT_POSE_COUNT - 1]
    }
}

/// The authored pose table for one placement and tray floor. Pod-local
/// numbers are commented; `to_world` maps them through the placement.
fn authored_poses(placement: PodPlacement, tray_floor_y: f32) -> [ExitPose; EXIT_POSE_COUNT] {
    let tolerance = POSE_TOLERANCE;
    let segment = CAPSULE_STANDING_HEIGHT - 2.0 * CAPSULE_RADIUS;
    let lying_y = tray_floor_y + CAPSULE_RADIUS + PENETRATION_TOLERANCE;
    // The lying capsule is centered in the pod: its 1.75 m total extent
    // leaves equal margin to both pod ends for any cavity wall build.
    let half_segment = segment / 2.0;
    // Standing just inside the tray, then fully past the pod's foot face:
    // the crossing runs at tray height because the base slab spans the
    // whole footprint, and the drop to the room floor happens once the
    // capsule clears the face by its own radius.
    let inside_face = POD_LENGTH / 2.0 - CAPSULE_RADIUS - 2.0 * PENETRATION_TOLERANCE;
    let past_face = POD_LENGTH / 2.0 + CAPSULE_RADIUS + 2.0 * PENETRATION_TOLERANCE;
    let standing_y = CAPSULE_RADIUS + PENETRATION_TOLERANCE;
    let local: [(Vec3, Vec3); EXIT_POSE_COUNT] = [
        // Lying in the tray, head toward the pod's head wall.
        (
            Vec3::new(0.0, lying_y, half_segment),
            Vec3::new(0.0, lying_y, -half_segment),
        ),
        // Sitting up: the sit-up pivots the capsule about its foot sphere.
        (
            Vec3::new(0.0, lying_y, half_segment),
            Vec3::new(0.0, lying_y + segment, half_segment),
        ),
        // Standing in the tray, just inside the aperture line.
        (
            Vec3::new(0.0, lying_y, inside_face),
            Vec3::new(0.0, lying_y + segment, inside_face),
        ),
        // Through the aperture mouth, feet still at tray height.
        (
            Vec3::new(0.0, lying_y, past_face),
            Vec3::new(0.0, lying_y + segment, past_face),
        ),
        // The exit waypoint: standing on the room floor in front of the pod.
        (
            Vec3::new(0.0, standing_y, past_face),
            Vec3::new(0.0, standing_y + segment, past_face),
        ),
    ];
    std::array::from_fn(|index| {
        let (foot, head) = local[index];
        ExitPose {
            foot: to_world(placement, foot),
            head: to_world(placement, head),
            tolerance,
        }
    })
}

/// Map a pod-local point into the room frame through `placement`: the yaw
/// about +Y rotates local +Z onto the opening's world direction, matching
/// `pods` and the app-side pod group transform.
fn to_world(placement: PodPlacement, local: Vec3) -> Vec3 {
    let (sin, cos) = placement.yaw_radians.sin_cos();
    Vec3::new(
        placement.center.0 + local.x * cos + local.z * sin,
        local.y,
        placement.center.1 - local.x * sin + local.z * cos,
    )
}

/// Translate the whole capsule by `by`.
fn translate(capsule: Capsule, by: Vec3) -> Capsule {
    Capsule {
        foot: capsule.foot + by,
        head: capsule.head + by,
    }
}

/// What one get-up tick did.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GetUpProgress {
    /// Index of the authored pose the capsule reached this tick.
    pub pose_index: usize,
    /// Whether that pose is the exit waypoint and the machine advanced to
    /// [`WakePhase::Standing`].
    pub at_waypoint: bool,
}

/// The tick-driven get-up controller: one authored segment per tick, every
/// motion swept through the caller's colliders by the landed resolver.
///
/// Built only through [`GetUpController::start`], which consumes the
/// explicit exit command in [`WakePhase::AwakeInPod`] and advances the
/// machine to [`WakePhase::ExitingPod`]. The controller owns the capsule
/// from the path's first authored pose; read it back with
/// [`GetUpController::capsule`].
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct GetUpController {
    path: ExitPath,
    capsule: Capsule,
    segment: usize,
}

impl GetUpController {
    /// Begin the authored get-up: consume the explicit exit command in
    /// [`WakePhase::AwakeInPod`] and start the capsule on the path's first
    /// pose.
    ///
    /// The command runs through the phase machine's own contract
    /// ([`WakePhase::request_pod_exit`] with a fresh press edge), so a
    /// machine in any other phase rejects the start with
    /// [`ExitError::WrongPhase`] and is left unchanged.
    ///
    /// # Errors
    /// [`ExitError::WrongPhase`] when the machine is not in
    /// [`WakePhase::AwakeInPod`].
    pub fn start(phase: &mut WakePhase, path: ExitPath) -> Result<Self, ExitError> {
        match phase.request_pod_exit(InputEdge::Rising) {
            PhaseTransition::Advanced {
                from: WakePhase::AwakeInPod,
                to: WakePhase::ExitingPod,
            } => {}
            _ => {
                return Err(ExitError::WrongPhase {
                    expected: WakePhase::AwakeInPod,
                    current: *phase,
                });
            }
        }
        Ok(Self {
            capsule: path.poses[0].capsule(),
            path,
            segment: 1,
        })
    }

    /// The capsule's current room-frame segment.
    #[must_use]
    pub fn capsule(&self) -> Capsule {
        self.capsule
    }

    /// Advance the authored get-up by exactly one segment.
    ///
    /// The tick sweeps the segment's conservative displacement through
    /// `colliders` with the landed resolver and moves the capsule to the
    /// resolved stop: the whole authored motion when nothing blocks, a
    /// partial motion (rigid segments) or none (pivots) when the sweep is
    /// stopped, which is a hard [`ExitError::PathBlocked`] unless the stop
    /// landed within the target pose's tolerance. Reaching the final pose
    /// delivers the get-up-complete signal, advancing the machine to
    /// [`WakePhase::Standing`].
    ///
    /// # Errors
    /// [`ExitError::GetUpAlreadyComplete`] when the path is already
    /// walked, [`ExitError::WrongPhase`] when the machine is not in
    /// [`WakePhase::ExitingPod`], [`ExitError::Resolver`] when the
    /// resolver rejects the sweep, and [`ExitError::PathBlocked`] when the
    /// sweep is stopped short of the target pose.
    pub fn tick(
        &mut self,
        phase: &mut WakePhase,
        colliders: &ColliderSet,
    ) -> Result<GetUpProgress, ExitError> {
        if self.segment == EXIT_POSE_COUNT {
            return Err(ExitError::GetUpAlreadyComplete);
        }
        if !phase.in_phase(WakePhase::ExitingPod) {
            return Err(ExitError::WrongPhase {
                expected: WakePhase::ExitingPod,
                current: *phase,
            });
        }
        let pose_index = self.segment;
        let pose = self.path.poses[pose_index];
        let movement = self.path.moves[pose_index - 1];
        let swept = resolve_motion(self.capsule, movement.vector(), colliders)
            .map_err(ExitError::Resolver)?;
        let shortfall = (movement.vector() - swept.displacement).length();
        if shortfall > pose.tolerance {
            // A stopped rigid segment keeps the resolver's partial motion;
            // a stopped pivot keeps the previous pose, because the
            // conservative sweep stopped, not the authored swing.
            if let SegmentMove::Rigid(_) = movement {
                self.capsule = translate(self.capsule, swept.displacement);
            }
            return Err(ExitError::PathBlocked {
                pose_index,
                shortfall,
            });
        }
        self.capsule = movement.visited(self.capsule, swept.displacement);
        self.segment += 1;
        let at_waypoint = pose_index + 1 == EXIT_POSE_COUNT;
        if at_waypoint {
            finish_get_up(phase)?;
        }
        Ok(GetUpProgress {
            pose_index,
            at_waypoint,
        })
    }
}

/// Deliver the get-up-complete boundary signal at the waypoint. The tick
/// entry check already pinned the machine to [`WakePhase::ExitingPod`],
/// where the signal cannot be a rejected skip; the error arm exists
/// because the machine's contract is typed, not assumed.
fn finish_get_up(phase: &mut WakePhase) -> Result<(), ExitError> {
    phase
        .get_up_complete()
        .map(|_| ())
        .map_err(
            |PhaseError::GetUpBeforeExitingPod { current }| ExitError::WrongPhase {
                expected: WakePhase::ExitingPod,
                current,
            },
        )
}

#[cfg(test)]
mod tests;
