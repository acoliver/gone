//! Pure swept-capsule resolver (issue #7 stage B).
//!
//! Resolves one tick of first-person movement against the static
//! [`ColliderSet`]. The capsule sweeps its intended displacement with
//! conservative advancement: it only ever advances to its first contact
//! minus [`PENETRATION_TOLERANCE`] and then re-queries, so a displacement
//! far larger than a collider can never tunnel through it — the thin-wall
//! sweep is exact because every collider is axis-aligned.
//!
//! At a contact the resolver slides (removes the into-face component of
//! the remaining motion, keeps the tangential part) or, when the struck
//! face's top is a ledge at most [`STEP_UP_HEIGHT`] above the capsule
//! foot and the raised position is free, steps up and continues. The
//! sweep is bounded by [`SWEEP_ITERATION_BOUND`]; running out of
//! iterations is a hard error naming the bound, never a silent clamp.
//!
//! Units: meters, displacements in meters per tick, up is positive Y. The
//! capsule is the line segment between its two sphere centers inflated by
//! the frozen [`CAPSULE_RADIUS`]. Pure: no Bevy, no clocks, no RNG.

use glam::Vec3;

use crate::colliders::{Aabb, ColliderSet};
use crate::controller::{
    CAPSULE_RADIUS, PENETRATION_TOLERANCE, STEP_UP_HEIGHT, SWEEP_ITERATION_BOUND,
};

/// The player capsule: the line segment between the foot sphere's center
/// and the head sphere's center, inflated by [`CAPSULE_RADIUS`]. For a
/// standing player the segment is vertical with `head.y - foot.y` equal
/// to the standing height minus twice the radius.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Capsule {
    /// Center of the foot (bottom) sphere.
    pub foot: Vec3,
    /// Center of the head (top) sphere.
    pub head: Vec3,
}

/// What one resolved tick did.
#[derive(Clone, Debug, PartialEq)]
pub struct ResolvedMotion {
    /// Displacement actually applied: resolved foot-sphere position minus
    /// the initial one. Never penetrates a collider beyond the tolerance.
    pub displacement: Vec3,
    /// Whether a support face sat within [`PENETRATION_TOLERANCE`] below
    /// the capsule foot at the resolved position.
    pub grounded: bool,
    /// Distinct unit contact normals of every face that constrained the
    /// sweep, in first-hit order. Faces stepped over do not count.
    pub contact_normals: Vec<Vec3>,
}

/// Which sweep input carried a non-finite component.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NonFiniteInput {
    /// The capsule's foot-sphere center.
    CapsuleFoot,
    /// The capsule's head-sphere center.
    CapsuleHead,
    /// The intended displacement.
    Displacement,
}

impl std::fmt::Display for NonFiniteInput {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::CapsuleFoot => write!(f, "capsule foot"),
            Self::CapsuleHead => write!(f, "capsule head"),
            Self::Displacement => write!(f, "displacement"),
        }
    }
}

/// A rejected sweep.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ResolveError {
    /// The sweep could not settle within the per-tick iteration bound
    /// ([`SWEEP_ITERATION_BOUND`] in production). Motion was left
    /// unresolved rather than clamped or skipped.
    SweepBoundExceeded {
        /// The bound that was exceeded.
        bound: u32,
    },
    /// The capsule started embedded deeper than [`PENETRATION_TOLERANCE`]
    /// in the collider at this index. Resolution refuses to guess an exit
    /// direction; the caller must fix the spawn position.
    StartPenetration {
        /// Insertion index of the offending collider.
        index: usize,
    },
    /// A capsule endpoint or the displacement carried a non-finite
    /// component, which would silently poison every comparison.
    NonFiniteInput {
        /// The offending input.
        input: NonFiniteInput,
    },
}

impl std::fmt::Display for ResolveError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::SweepBoundExceeded { bound } => write!(
                f,
                "sweep did not settle within the per-tick iteration bound \
                 SWEEP_ITERATION_BOUND = {bound}; leftover motion is an error, \
                 never a silent clamp"
            ),
            Self::StartPenetration { index } => write!(
                f,
                "capsule starts embedded beyond PENETRATION_TOLERANCE \
                 in collider {index}; fix the spawn position"
            ),
            Self::NonFiniteInput { input } => {
                write!(f, "sweep {input} carried a non-finite component")
            }
        }
    }
}

impl std::error::Error for ResolveError {}

/// Resolve one tick: sweep `capsule` along `displacement` against
/// `colliders` with conservative advancement, sliding along struck faces,
/// stepping up onto ledges within [`STEP_UP_HEIGHT`], and reporting
/// grounding and contact normals at the resolved position.
///
/// # Errors
/// [`ResolveError::SweepBoundExceeded`] when the slide loop cannot settle
/// within [`SWEEP_ITERATION_BOUND`] iterations, [`ResolveError::
/// StartPenetration`] when the capsule starts embedded beyond the
/// tolerance in some collider, and [`ResolveError::NonFiniteInput`] when
/// an input carries a non-finite component.
pub fn resolve_motion(
    capsule: Capsule,
    displacement: Vec3,
    colliders: &ColliderSet,
) -> Result<ResolvedMotion, ResolveError> {
    sweep_with_bound(capsule, displacement, colliders, SWEEP_ITERATION_BOUND)
}

/// The sweep with an explicit iteration bound; `resolve_motion` passes the
/// frozen [`SWEEP_ITERATION_BOUND`]. The parameter exists so the
/// bound-exceeded error path is testable without manufacturing a scenario
/// the production bound cannot settle (axis-aligned slides converge in at
/// most three, one per axis).
fn sweep_with_bound(
    capsule: Capsule,
    displacement: Vec3,
    colliders: &ColliderSet,
    bound: u32,
) -> Result<ResolvedMotion, ResolveError> {
    let mut state = SweepState::validated(capsule, displacement)?;
    let residual = PENETRATION_TOLERANCE * PENETRATION_TOLERANCE;
    for _ in 0..bound {
        if state.remaining.length_squared() <= residual {
            break;
        }
        state.advance(colliders)?;
    }
    if state.remaining.length_squared() > residual {
        return Err(ResolveError::SweepBoundExceeded { bound });
    }
    Ok(ResolvedMotion {
        displacement: state.foot - capsule.foot,
        grounded: is_grounded(state.foot, colliders),
        contact_normals: state.contacts,
    })
}

/// Loop state: current sphere centers, unresolved motion, and the contact
/// normals struck so far.
struct SweepState {
    foot: Vec3,
    head: Vec3,
    remaining: Vec3,
    contacts: Vec<Vec3>,
}

impl SweepState {
    /// Validate the inputs finitely and open the sweep.
    fn validated(capsule: Capsule, displacement: Vec3) -> Result<Self, ResolveError> {
        let input = if !capsule.foot.is_finite() {
            Some(NonFiniteInput::CapsuleFoot)
        } else if !capsule.head.is_finite() {
            Some(NonFiniteInput::CapsuleHead)
        } else if !displacement.is_finite() {
            Some(NonFiniteInput::Displacement)
        } else {
            None
        };
        match input {
            Some(input) => Err(ResolveError::NonFiniteInput { input }),
            None => Ok(Self {
                foot: capsule.foot,
                head: capsule.head,
                remaining: displacement,
                contacts: Vec::new(),
            }),
        }
    }

    /// Advance one sweep iteration: stop at the first contact minus the
    /// tolerance and slide or step, or consume the whole remaining motion
    /// when nothing blocks.
    fn advance(&mut self, colliders: &ColliderSet) -> Result<(), ResolveError> {
        let capsule = capsule_aabb(self.foot, self.head);
        let query = swept_query(&capsule, self.remaining);
        let mut first: Option<Contact> = None;
        for (index, collider) in colliders.overlapping(&query) {
            if embedded_beyond_tolerance(&capsule, collider) {
                return Err(ResolveError::StartPenetration { index });
            }
            let Some(hit) = face_contact(&capsule, collider, self.remaining) else {
                continue;
            };
            // An exact tie between colliders (a symmetric corner) resolves
            // to the later-inserted one, matching the axis tie-break so
            // the reported first-hit order is deterministic.
            if hit.entry > 1.0 || first.as_ref().is_some_and(|best| hit.entry > best.entry) {
                continue;
            }
            first = Some(hit);
        }
        let Some(contact) = first else {
            self.move_by(self.remaining);
            self.remaining = Vec3::ZERO;
            return Ok(());
        };
        self.apply_contact(contact, colliders);
        Ok(())
    }

    /// Move to the chosen contact minus the tolerance along the path, then
    /// either step onto the struck ledge or slide along the struck face.
    fn apply_contact(&mut self, contact: Contact, colliders: &ColliderSet) {
        let path = self.remaining.length();
        // The tolerance is owed on the struck face's own axis, not along
        // the (possibly diagonal) path: the resting contract reads the
        // per-axis gap, so the slack divides by the axial direction
        // cosine, `axial / path`. `axial` cannot be zero — only an axis
        // with nonzero motion can win the entry.
        let axial = self.remaining.dot(contact.normal).abs();
        let stop = (contact.entry * path - PENETRATION_TOLERANCE * path / axial).clamp(0.0, path);
        let moved = self.remaining * (stop / path);
        self.move_by(moved);
        self.remaining -= moved;
        if contact.normal.y == 0.0
            && let Some(raise) = try_step_up(self.foot, self.head, contact.box_top, colliders)
        {
            self.foot.y += raise;
            self.head.y += raise;
            return;
        }
        self.record(contact.normal);
        let into = self.remaining.dot(contact.normal);
        if into < 0.0 {
            self.remaining -= contact.normal * into;
        }
    }

    /// Translate both sphere centers.
    fn move_by(&mut self, delta: Vec3) {
        self.foot += delta;
        self.head += delta;
    }

    /// Record a contact normal, deduplicating (at most three exist).
    fn record(&mut self, normal: Vec3) {
        if !self.contacts.contains(&normal) {
            self.contacts.push(normal);
        }
    }
}

/// One struck face: the sweep entry fraction, the face's outward unit
/// normal, and the struck box's top height for the step-up probe.
#[derive(Clone, Copy)]
struct Contact {
    entry: f32,
    normal: Vec3,
    box_top: f32,
}

/// One axis's slab outcome for the moving capsule bounds against a static
/// box.
enum AxisSweep {
    /// The boxes stay separated on this axis for the whole motion, or the
    /// box is already behind and opening: it can never be struck.
    Miss,
    /// This axis cannot gate the approach (no motion, or the sweep is
    /// already moving through the slab).
    Open,
    /// First contact at this fraction of the remaining motion.
    Hit(f32),
}

/// Slab test for one axis. `lo`/`hi` are the moving bounds, `box_lo`/
/// `box_hi` the static ones, `motion` the displacement component.
fn axis_sweep(motion: f32, lo: f32, hi: f32, box_lo: f32, box_hi: f32) -> AxisSweep {
    if motion == 0.0 {
        let separated = box_lo - hi > 0.0 || lo - box_hi > 0.0;
        return if separated {
            AxisSweep::Miss
        } else {
            AxisSweep::Open
        };
    }
    let (front_gap, back_gap) = if motion > 0.0 {
        (box_lo - hi, box_hi - lo)
    } else {
        (lo - box_hi, hi - box_lo)
    };
    if back_gap <= 0.0 {
        // At or past the far face and opening: this axis can never close.
        return AxisSweep::Miss;
    }
    if front_gap > PENETRATION_TOLERANCE {
        return AxisSweep::Hit(front_gap / motion.abs());
    }
    if front_gap >= -PENETRATION_TOLERANCE {
        // At the struck face within the tolerance band: immediate contact.
        return AxisSweep::Hit(0.0);
    }
    // Strictly inside the slab, moving through: the face is beside us.
    AxisSweep::Open
}

/// Earliest contact between the capsule bounds and one box along
/// `remaining`, or `None` when this motion cannot strike the box. The
/// entry fraction is the slab maximum over axes — the standard
/// no-tunneling sweep for axis-aligned boxes — and an exact tie between
/// axes resolves to the later axis, which pins the first-hit order when a
/// symmetric corner is struck on two faces at once.
fn face_contact(capsule: &Aabb, collider: &Aabb, remaining: Vec3) -> Option<Contact> {
    let (cmin, cmax) = (capsule.min(), capsule.max());
    let (bmin, bmax) = (collider.min(), collider.max());
    let axes = [
        (remaining.x, cmin.x, cmax.x, bmin.x, bmax.x),
        (remaining.y, cmin.y, cmax.y, bmin.y, bmax.y),
        (remaining.z, cmin.z, cmax.z, bmin.z, bmax.z),
    ];
    let mut entry: Option<(f32, usize)> = None;
    for (axis, &(motion, lo, hi, box_lo, box_hi)) in axes.iter().enumerate() {
        match axis_sweep(motion, lo, hi, box_lo, box_hi) {
            AxisSweep::Miss => return None,
            AxisSweep::Open => {}
            AxisSweep::Hit(hit) => {
                if entry.is_none_or(|(best, _)| hit >= best) {
                    entry = Some((hit, axis));
                }
            }
        }
    }
    let (entry, struck) = entry?;
    let sign = if axes[struck].0 > 0.0 { -1.0 } else { 1.0 };
    let normal = match struck {
        0 => Vec3::X * sign,
        1 => Vec3::Y * sign,
        _ => Vec3::Z * sign,
    };
    Some(Contact {
        entry,
        normal,
        box_top: bmax.y,
    })
}

/// Whether the capsule is inside the box beyond [`PENETRATION_TOLERANCE`]
/// on every axis: genuinely embedded, not resting or grazing. Deeper
/// overlap is a caller bug and fails loudly instead of guessing an exit.
fn embedded_beyond_tolerance(capsule: &Aabb, collider: &Aabb) -> bool {
    let (cmin, cmax) = (capsule.min(), capsule.max());
    let (bmin, bmax) = (collider.min(), collider.max());
    cmin.x < bmax.x - PENETRATION_TOLERANCE
        && cmax.x > bmin.x + PENETRATION_TOLERANCE
        && cmin.y < bmax.y - PENETRATION_TOLERANCE
        && cmax.y > bmin.y + PENETRATION_TOLERANCE
        && cmin.z < bmax.z - PENETRATION_TOLERANCE
        && cmax.z > bmin.z + PENETRATION_TOLERANCE
}

/// The capsule's axis-aligned bounds: the segment hull grown by the
/// frozen radius on every axis.
fn capsule_aabb(foot: Vec3, head: Vec3) -> Aabb {
    let min = foot.min(head) - Vec3::splat(CAPSULE_RADIUS);
    let max = foot.max(head) + Vec3::splat(CAPSULE_RADIUS);
    Aabb::from_parts((min + max) * 0.5, (max - min) * 0.5)
}

/// Broad-phase query: the capsule bounds swept over the remaining motion
/// (the hull of the start and end bounds). Any box the motion can strike
/// must intersect this hull, so nothing tunnelable is left out.
fn swept_query(capsule: &Aabb, remaining: Vec3) -> Aabb {
    let min = capsule.min().min(capsule.min() + remaining);
    let max = capsule.max().max(capsule.max() + remaining);
    Aabb::from_parts((min + max) * 0.5, (max - min) * 0.5)
}

/// Attempt a step onto the struck ledge: allowed when its top sits at or
/// below [`STEP_UP_HEIGHT`] above the capsule foot (within the tolerance)
/// and the raised capsule is free of every collider. Returns the raise in
/// meters, landing the foot one tolerance above the ledge top so the
/// resting contract matches every other resolved stop.
fn try_step_up(foot: Vec3, head: Vec3, ledge_top: f32, colliders: &ColliderSet) -> Option<f32> {
    let capsule_foot = foot.y - CAPSULE_RADIUS;
    let ledge = ledge_top - capsule_foot;
    if ledge <= 0.0 || ledge > STEP_UP_HEIGHT + PENETRATION_TOLERANCE {
        return None;
    }
    let raise = ledge_top + PENETRATION_TOLERANCE - capsule_foot;
    let raised = capsule_aabb(foot + Vec3::Y * raise, head + Vec3::Y * raise);
    colliders
        .overlapping(&raised)
        .next()
        .is_none()
        .then_some(raise)
}

/// Rounding slack for the grounding probe: the sweep's stop position
/// accumulates a few ulps of f32 error across the entry-fraction math, so
/// a support face at exactly the tolerance distance can land a hair
/// outside a closed window and even drop out of the probe's broad-phase
/// query. A fiftieth of the tolerance is orders above that noise and far
/// below any semantic band.
const GROUND_PROBE_SLACK: f32 = 1e-4;

/// Whether a support face sits within [`PENETRATION_TOLERANCE`] of the
/// capsule foot height and underlaps the foot sphere: standing or resting
/// reads grounded, mid-air does not.
fn is_grounded(foot: Vec3, colliders: &ColliderSet) -> bool {
    let foot_y = foot.y - CAPSULE_RADIUS;
    let band = PENETRATION_TOLERANCE + GROUND_PROBE_SLACK;
    let query = Aabb::from_parts(
        Vec3::new(foot.x, foot_y, foot.z),
        Vec3::new(CAPSULE_RADIUS, band, CAPSULE_RADIUS),
    );
    for (_, collider) in colliders.overlapping(&query) {
        let top = collider.max().y;
        if top < foot_y - band || top > foot_y + band {
            continue;
        }
        let (bmin, bmax) = (collider.min(), collider.max());
        let over = bmin.x <= foot.x + CAPSULE_RADIUS
            && foot.x - CAPSULE_RADIUS <= bmax.x
            && bmin.z <= foot.z + CAPSULE_RADIUS
            && foot.z - CAPSULE_RADIUS <= bmax.z;
        if over {
            return true;
        }
    }
    false
}

/// Coverage of the resolver contract: head-on stops, corner slides, step
/// ups and refusals, thin-wall no-tunneling, the bound error, grounding,
/// and the fail-fast inputs.
#[cfg(test)]
mod tests {
    use super::{
        Capsule, NonFiniteInput, PENETRATION_TOLERANCE, ResolveError, ResolvedMotion,
        STEP_UP_HEIGHT, SWEEP_ITERATION_BOUND, resolve_motion,
    };
    use crate::colliders::{Aabb, ColliderSet};
    use crate::controller::{CAPSULE_RADIUS, CAPSULE_STANDING_HEIGHT};
    use glam::Vec3;

    /// Asserts stop precision for exactly-representable expectations.
    fn assert_close(actual: Vec3, expected: Vec3, label: &str) {
        let drift = (actual - expected).abs();
        assert!(
            drift.x < 1e-3 && drift.y < 1e-3 && drift.z < 1e-3,
            "{label}: expected {expected:?}, resolved {actual:?}"
        );
    }

    /// A standing capsule whose foot sphere rests at height `foot_y`.
    fn standing(x: f32, foot_y: f32, z: f32) -> Capsule {
        let segment = CAPSULE_STANDING_HEIGHT - 2.0 * CAPSULE_RADIUS;
        Capsule {
            foot: Vec3::new(x, foot_y + CAPSULE_RADIUS, z),
            head: Vec3::new(x, foot_y + CAPSULE_RADIUS + segment, z),
        }
    }

    /// A box spanning the given min and max corners.
    fn box_between(min: (f32, f32, f32), max: (f32, f32, f32)) -> Aabb {
        Aabb::from_min_max(Vec3::from(min), Vec3::from(max)).expect("test box is valid")
    }

    /// A scene: a floor slab topping out at y = 0 plus the given boxes.
    fn scene(extra: &[Aabb]) -> ColliderSet {
        let mut set = ColliderSet::new();
        set.insert(box_between((-10.0, -1.0, -10.0), (10.0, 0.0, 10.0)));
        for aabb in extra {
            set.insert(*aabb);
        }
        set
    }

    /// Head-on into a wall stops one tolerance short of the face, keeps
    /// the vertical, and names the wall's inward normal.
    #[test]
    fn head_on_motion_stops_at_the_wall() {
        let wall = box_between((2.0, 0.0, -4.0), (2.2, 3.2, 4.0));
        let set = scene(&[wall]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(5.0, 0.0, 0.0), &set)
            .expect("head-on stop resolves");
        let expected = 2.0 - CAPSULE_RADIUS - PENETRATION_TOLERANCE;
        assert_close(
            resolved.displacement,
            Vec3::new(expected, 0.0, 0.0),
            "head-on",
        );
        assert!(resolved.grounded, "standing on the floor");
        assert_eq!(resolved.contact_normals, vec![Vec3::new(-1.0, 0.0, 0.0)]);
    }

    /// A diagonal move into a wall slides along its face around a corner
    /// in one tick: the wall-parallel axis runs free, the wall-normal axis
    /// stops with a gap inside the tolerance band, and only the wall's
    /// normal is reported.
    #[test]
    fn diagonal_motion_slides_along_a_face_around_a_corner() {
        let wall = box_between((-10.0, 0.0, 2.0), (10.0, 3.2, 2.2));
        let set = scene(&[wall]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(10.0, 0.0, 3.0), &set)
            .expect("corner slide resolves");
        assert_close(
            resolved.displacement,
            Vec3::new(10.0, 0.0, 1.695),
            "corner slide",
        );
        let gap = 2.0 - (resolved.displacement.z + CAPSULE_RADIUS);
        assert!(
            (0.0..=PENETRATION_TOLERANCE + 1e-6).contains(&gap),
            "normal-axis gap {gap} must sit inside the tolerance band"
        );
        assert_eq!(resolved.contact_normals, vec![Vec3::new(0.0, 0.0, -1.0)]);
    }

    /// Two perpendicular walls wedge a diagonal move against both faces
    /// in one tick, reporting both normals and settling inside the
    /// production iteration bound.
    #[test]
    fn a_corner_wedge_reports_both_face_normals() {
        let wall_x = box_between((2.0, 0.0, -10.0), (2.2, 3.2, 10.0));
        let wall_z = box_between((-10.0, 0.0, 2.0), (10.0, 3.2, 2.2));
        let set = scene(&[wall_x, wall_z]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(5.0, 0.0, 5.0), &set)
            .expect("wedge resolves within the production bound");
        let x_gap = 2.0 - (resolved.displacement.x + CAPSULE_RADIUS);
        let z_gap = 2.0 - (resolved.displacement.z + CAPSULE_RADIUS);
        for gap in [x_gap, z_gap] {
            assert!(
                (0.0..=PENETRATION_TOLERANCE + 1e-6).contains(&gap),
                "wedge gap {gap} must sit inside the tolerance band"
            );
        }
        assert_eq!(
            resolved.contact_normals,
            vec![Vec3::new(0.0, 0.0, -1.0), Vec3::new(-1.0, 0.0, 0.0)]
        );
    }

    /// A 0.2 m ledge is inside the frozen step budget: the capsule rises
    /// onto it, walks over, and reads grounded on the ledge top.
    #[test]
    fn step_up_onto_a_0p2_ledge_carries_the_capsule() {
        let ledge = box_between((3.0, 0.0, -4.0), (6.0, 0.2, 4.0));
        let set = scene(&[ledge]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(3.5, 0.0, 0.0), &set)
            .expect("0.2 step resolves");
        let raise = 0.2 + PENETRATION_TOLERANCE;
        assert_close(
            resolved.displacement,
            Vec3::new(3.5, raise, 0.0),
            "0.2 step",
        );
        assert!(resolved.grounded, "standing on the ledge top");
        assert!(
            resolved.contact_normals.is_empty(),
            "a stepped-over ledge is not a contact"
        );
    }

    /// A 0.4 m ledge exceeds the frozen step budget: the face blocks, the
    /// capsule stays on the floor, and the wall normal is reported.
    #[test]
    fn step_up_onto_a_0p4_ledge_is_refused() {
        let ledge = box_between((3.0, 0.0, -4.0), (6.0, 0.4, 4.0));
        let set = scene(&[ledge]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(5.0, 0.0, 0.0), &set)
            .expect("0.4 refusal resolves");
        let expected = 3.0 - CAPSULE_RADIUS - PENETRATION_TOLERANCE;
        assert_close(
            resolved.displacement,
            Vec3::new(expected, 0.0, 0.0),
            "0.4 refusal",
        );
        assert!(resolved.grounded, "still standing on the floor");
        assert_eq!(resolved.contact_normals, vec![Vec3::new(-1.0, 0.0, 0.0)]);
        const {
            assert!(
                STEP_UP_HEIGHT < 0.4,
                "the refusal must come from the frozen budget, not the geometry"
            );
        }
    }

    /// A displacement ten times a thin wall's thickness stops dead at the
    /// near face: the slab sweep is exact, so nothing passes through.
    #[test]
    fn thin_walls_do_not_tunnel_under_oversized_displacement() {
        let wall = box_between((5.0, 0.0, -4.0), (5.1, 3.2, 4.0));
        let set = scene(&[wall]);
        let resolved = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::new(50.0, 0.0, 0.0), &set)
            .expect("thin wall resolves");
        let expected = 5.0 - CAPSULE_RADIUS - PENETRATION_TOLERANCE;
        assert_close(
            resolved.displacement,
            Vec3::new(expected, 0.0, 0.0),
            "thin wall",
        );
        let face = resolved.displacement.x + CAPSULE_RADIUS;
        assert!(
            face < 5.0,
            "capsule face {face} must stay short of the wall"
        );
    }

    /// A wedged corner needs more than one blocking iteration: bound one
    /// errors naming the bound, the production bound resolves the same
    /// tick, and an exhausted sweep never clamps silently.
    #[test]
    fn exceeding_the_iteration_bound_is_a_hard_error() {
        let wall_x = box_between((2.0, 0.0, -10.0), (2.2, 3.2, 10.0));
        let wall_z = box_between((-10.0, 0.0, 2.0), (10.0, 3.2, 2.2));
        let mut set = ColliderSet::new();
        set.insert(wall_x);
        set.insert(wall_z);
        let capsule = standing(0.0, 0.0, 0.0);
        let displacement = Vec3::new(5.0, 0.0, 5.0);
        let bounded = super::sweep_with_bound(capsule, displacement, &set, 1);
        assert_eq!(
            bounded,
            Err(ResolveError::SweepBoundExceeded { bound: 1 }),
            "one blocking iteration cannot settle a two-face wedge"
        );
        assert!(bounded.unwrap_err().to_string().contains("bound"));
        let settled = super::sweep_with_bound(capsule, displacement, &set, SWEEP_ITERATION_BOUND)
            .expect("production bound settles the wedge");
        assert!(settled.displacement.x > 0.0 && settled.displacement.z > 0.0);
        let zero_bound = super::sweep_with_bound(capsule, displacement, &set, 0);
        assert_eq!(
            zero_bound,
            Err(ResolveError::SweepBoundExceeded { bound: 0 })
        );
    }

    /// Standing still on the floor reads grounded with no contacts; the
    /// same capsule mid-air, or over an empty world, reads ungrounded.
    #[test]
    fn grounding_follows_the_support_face() {
        let set = scene(&[]);
        let on_floor =
            resolve_motion(standing(0.0, 0.0, 0.0), Vec3::ZERO, &set).expect("at-rest resolve");
        assert_eq!(on_floor.displacement, Vec3::ZERO);
        assert!(on_floor.grounded);
        assert!(on_floor.contact_normals.is_empty());
        let mid_air =
            resolve_motion(standing(0.0, 3.0, 0.0), Vec3::ZERO, &set).expect("mid-air resolve");
        assert!(!mid_air.grounded);
        let empty = ColliderSet::new();
        let nowhere = resolve_motion(standing(0.0, 0.0, 0.0), Vec3::ZERO, &empty)
            .expect("empty world resolve");
        assert!(!nowhere.grounded);
    }

    /// A fall lands one tolerance above the floor, reports the upward
    /// contact normal, and reads grounded.
    #[test]
    fn falling_lands_tolerance_short_and_reads_grounded() {
        let set = scene(&[]);
        let resolved = resolve_motion(standing(0.0, 3.0, 0.0), Vec3::new(0.0, -5.0, 0.0), &set)
            .expect("landing resolves");
        assert_close(
            resolved.displacement,
            Vec3::new(0.0, -(3.0 - PENETRATION_TOLERANCE), 0.0),
            "landing",
        );
        assert_eq!(resolved.contact_normals, vec![Vec3::Y]);
        assert!(resolved.grounded);
    }

    /// A capsule authored deeper than the tolerance inside a collider is
    /// rejected, naming the collider index, instead of guessing an exit.
    #[test]
    fn start_penetration_is_an_error_naming_the_collider() {
        let block = box_between((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0));
        let mut set = ColliderSet::new();
        set.insert(box_between((-5.0, -5.0, -5.0), (-4.0, -4.0, -4.0)));
        set.insert(block);
        let embedded = Capsule {
            foot: Vec3::ZERO,
            head: Vec3::new(0.0, 1.15, 0.0),
        };
        assert_eq!(
            resolve_motion(embedded, Vec3::new(1.0, 0.0, 0.0), &set),
            Err(ResolveError::StartPenetration { index: 1 })
        );
    }

    /// Non-finite capsule endpoints and displacements are rejected,
    /// naming the input, before any comparison can be poisoned.
    #[test]
    fn non_finite_inputs_are_rejected() {
        let set = ColliderSet::new();
        let capsule = standing(0.0, 0.0, 0.0);
        let nan = f32::NAN;
        let bad_foot = resolve_motion(
            Capsule {
                foot: Vec3::new(nan, 0.0, 0.0),
                head: capsule.head,
            },
            Vec3::ZERO,
            &set,
        );
        assert_eq!(
            bad_foot,
            Err(ResolveError::NonFiniteInput {
                input: NonFiniteInput::CapsuleFoot
            })
        );
        let bad_head = resolve_motion(
            Capsule {
                foot: capsule.foot,
                head: Vec3::new(0.0, f32::INFINITY, 0.0),
            },
            Vec3::ZERO,
            &set,
        );
        assert_eq!(
            bad_head,
            Err(ResolveError::NonFiniteInput {
                input: NonFiniteInput::CapsuleHead
            })
        );
        let bad_move = resolve_motion(capsule, Vec3::new(1.0, nan, 0.0), &set);
        assert_eq!(
            bad_move,
            Err(ResolveError::NonFiniteInput {
                input: NonFiniteInput::Displacement
            })
        );
    }

    /// The resolved contract reports displacement against the initial
    /// foot position, so a resolved tick composes with the next one.
    #[test]
    fn resolved_displacement_reaches_the_final_foot_position() {
        let wall = box_between((2.0, 0.0, -4.0), (2.2, 3.2, 4.0));
        let set = scene(&[wall]);
        let capsule = standing(0.0, 0.0, 0.0);
        let resolved: ResolvedMotion =
            resolve_motion(capsule, Vec3::new(5.0, 0.0, 0.0), &set).expect("resolves");
        let expected = 2.0 - CAPSULE_RADIUS - PENETRATION_TOLERANCE;
        assert_close(
            resolved.displacement,
            Vec3::new(expected, 0.0, 0.0),
            "delta",
        );
        let follow_up = resolve_motion(
            Capsule {
                foot: capsule.foot + resolved.displacement,
                head: capsule.head + resolved.displacement,
            },
            Vec3::new(5.0, 0.0, 0.0),
            &set,
        )
        .expect("second tick resolves");
        assert_close(follow_up.displacement, Vec3::ZERO, "held against the wall");
    }
}
