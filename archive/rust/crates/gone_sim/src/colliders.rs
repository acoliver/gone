//! Static-world collider set (issue #7 stage B).
//!
//! The milestone-one greybox world is tens of axis-aligned boxes (room
//! shell, pod boxes, hatch), so the set is a small `Vec` with a linear
//! broad-phase: [`ColliderSet::overlapping`] filters inserted boxes by
//! inclusive AABB overlap, and no spatial index is warranted at this
//! scale.
//!
//! Every [`Aabb`] is validated at construction, so a box in existence
//! always has finite coordinates, non-negative half extents, and a min
//! corner at or below its max corner on every axis. Nothing downstream
//! (the swept resolver in [`crate::resolve`]) can observe a degenerate or
//! non-finite box.
//!
//! Units: meters, up is positive Y, matching `controller` and `pods`.
//! Pure simulation data: no Bevy types, a boundary the workspace
//! architecture gate enforces mechanically.

use std::cmp::Ordering;

use glam::Vec3;

/// One axis-aligned bounding box: a center plus non-negative half extents.
///
/// Construct through [`Aabb::try_new`] or [`Aabb::from_min_max`]; the
/// fields are private so only validated boxes can exist.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Aabb {
    center: Vec3,
    half_extents: Vec3,
}

/// A rejected collider construction.
///
/// Payloads echo the rejected input back to the caller; equality compares
/// those payloads by total order, so a NaN payload still matches itself
/// (derived equality would compare it with IEEE `==` and never hold).
#[derive(Clone, Copy, Debug)]
pub enum ColliderError {
    /// A coordinate was not finite (NaN or infinite).
    NonFinite {
        /// The offending vector.
        value: Vec3,
    },
    /// A half extent component was negative.
    NegativeHalfExtent {
        /// The offending half extents.
        half_extents: Vec3,
    },
    /// A min corner exceeded the max corner on some axis.
    MinAboveMax {
        /// The rejected min corner.
        min: Vec3,
        /// The rejected max corner.
        max: Vec3,
    },
}

impl std::fmt::Display for ColliderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NonFinite { value } => {
                write!(f, "collider coordinates must be finite, got {value:?}")
            }
            Self::NegativeHalfExtent { half_extents } => write!(
                f,
                "collider half extents must be non-negative, got {half_extents:?}"
            ),
            Self::MinAboveMax { min, max } => write!(
                f,
                "collider min corner {min:?} exceeds max corner {max:?} on some axis"
            ),
        }
    }
}

impl PartialEq for ColliderError {
    fn eq(&self, other: &Self) -> bool {
        /// Total-order component comparison: a payload is the offending
        /// input echoed back, so a NaN payload must still match itself,
        /// which IEEE equality cannot express.
        fn same_vector(a: Vec3, b: Vec3) -> bool {
            a.x.total_cmp(&b.x) == Ordering::Equal
                && a.y.total_cmp(&b.y) == Ordering::Equal
                && a.z.total_cmp(&b.z) == Ordering::Equal
        }
        match (self, other) {
            (Self::NonFinite { value: a }, Self::NonFinite { value: b })
            | (
                Self::NegativeHalfExtent {
                    half_extents: a, ..
                },
                Self::NegativeHalfExtent {
                    half_extents: b, ..
                },
            ) => same_vector(*a, *b),
            (
                Self::MinAboveMax { min: a, max: a_max },
                Self::MinAboveMax { min: b, max: b_max },
            ) => same_vector(*a, *b) && same_vector(*a_max, *b_max),
            _ => false,
        }
    }
}

impl std::error::Error for ColliderError {}

impl Aabb {
    /// Build a box from its center and half extents, rejecting non-finite
    /// coordinates and negative half extents.
    ///
    /// # Errors
    /// [`ColliderError::NonFinite`] for non-finite coordinates and
    /// [`ColliderError::NegativeHalfExtent`] for a negative half extent.
    pub fn try_new(center: Vec3, half_extents: Vec3) -> Result<Self, ColliderError> {
        if !center.is_finite() {
            return Err(ColliderError::NonFinite { value: center });
        }
        if !half_extents.is_finite() {
            return Err(ColliderError::NonFinite {
                value: half_extents,
            });
        }
        if half_extents.x < 0.0 || half_extents.y < 0.0 || half_extents.z < 0.0 {
            return Err(ColliderError::NegativeHalfExtent { half_extents });
        }
        Ok(Self::from_parts(center, half_extents))
    }

    /// Build a box from its min and max corners.
    ///
    /// # Errors
    /// [`ColliderError::NonFinite`] for non-finite corners and
    /// [`ColliderError::MinAboveMax`] when `min` exceeds `max` on some
    /// axis.
    pub fn from_min_max(min: Vec3, max: Vec3) -> Result<Self, ColliderError> {
        if !min.is_finite() {
            return Err(ColliderError::NonFinite { value: min });
        }
        if !max.is_finite() {
            return Err(ColliderError::NonFinite { value: max });
        }
        if min.x > max.x || min.y > max.y || min.z > max.z {
            return Err(ColliderError::MinAboveMax { min, max });
        }
        Ok(Self::from_parts((min + max) * 0.5, (max - min) * 0.5))
    }

    /// The box center.
    #[must_use]
    pub fn center(self) -> Vec3 {
        self.center
    }

    /// The non-negative half extents.
    #[must_use]
    pub fn half_extents(self) -> Vec3 {
        self.half_extents
    }

    /// The min corner.
    #[must_use]
    pub fn min(self) -> Vec3 {
        self.center - self.half_extents
    }

    /// The max corner.
    #[must_use]
    pub fn max(self) -> Vec3 {
        self.center + self.half_extents
    }

    /// Whether the two boxes overlap, touching faces included: two boxes
    /// sharing exactly one face plane count as overlapping.
    #[must_use]
    pub fn overlaps(self, other: Self) -> bool {
        let (a_min, a_max) = (self.min(), self.max());
        let (b_min, b_max) = (other.min(), other.max());
        a_min.x <= b_max.x
            && b_min.x <= a_max.x
            && a_min.y <= b_max.y
            && b_min.y <= a_max.y
            && a_min.z <= b_max.z
            && b_min.z <= a_max.z
    }

    /// Assemble a box from already-valid parts. Crate-internal: the
    /// public constructors validate; callers pass finite coordinates and
    /// non-negative half extents (or derived values that inherit both
    /// properties from valid inputs).
    pub(crate) fn from_parts(center: Vec3, half_extents: Vec3) -> Self {
        Self {
            center,
            half_extents,
        }
    }
}

/// The static world's collider set: a small vector of validated AABBs.
///
/// Construction is append-only through [`ColliderSet::insert`]; queries
/// scan every box. At the scene's scale (tens of boxes) the linear scan
/// is the whole broad-phase and no spatial index is warranted.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ColliderSet {
    boxes: Vec<Aabb>,
}

impl ColliderSet {
    /// An empty set.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert one box and return its index. The index identifies the box
    /// in [`ColliderSet::boxes`] and in resolver error reports.
    pub fn insert(&mut self, aabb: Aabb) -> usize {
        self.boxes.push(aabb);
        self.boxes.len() - 1
    }

    /// How many boxes the set holds.
    #[must_use]
    pub fn len(&self) -> usize {
        self.boxes.len()
    }

    /// Whether the set holds no boxes.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.boxes.is_empty()
    }

    /// The inserted boxes, in insertion order.
    #[must_use]
    pub fn boxes(&self) -> &[Aabb] {
        &self.boxes
    }

    /// Broad-phase query: every inserted box whose bounds overlap
    /// `query`, paired with its insertion index.
    pub fn overlapping(&self, query: &Aabb) -> impl Iterator<Item = (usize, &Aabb)> {
        self.boxes
            .iter()
            .enumerate()
            .filter(move |(_, candidate)| candidate.overlaps(*query))
    }
}

/// Coverage of the set: insertion identity, inclusive overlap semantics,
/// and rejection of every invalid construction.
#[cfg(test)]
mod tests {
    use super::{Aabb, ColliderError, ColliderSet};
    use glam::Vec3;

    /// A unit-cube box at `(x, y, z)` spanning one meter per axis.
    fn unit(x: f32, y: f32, z: f32) -> Aabb {
        Aabb::from_min_max(Vec3::new(x, y, z), Vec3::new(x + 1.0, y + 1.0, z + 1.0))
            .expect("unit test box is valid")
    }

    /// Inserts are indexed in order and read back unchanged through
    /// `boxes` and the accessors.
    #[test]
    fn inserts_are_indexed_in_order_and_round_trip() {
        let mut set = ColliderSet::new();
        assert!(set.is_empty());
        let first = unit(0.0, 0.0, 0.0);
        let second = unit(5.0, 0.0, 5.0);
        assert_eq!(set.insert(first), 0);
        assert_eq!(set.insert(second), 1);
        assert_eq!(set.len(), 2);
        assert_eq!(set.boxes(), &[first, second]);
        assert_eq!(first.center(), Vec3::new(0.5, 0.5, 0.5));
        assert_eq!(first.half_extents(), Vec3::splat(0.5));
        assert_eq!(first.min(), Vec3::ZERO);
        assert_eq!(first.max(), Vec3::splat(1.0));
    }

    /// The overlap query is inclusive of exact face contact and skips
    /// strictly separated boxes, reporting insertion indices.
    #[test]
    fn overlap_query_is_inclusive_and_reports_indices() {
        let mut set = ColliderSet::new();
        set.insert(unit(0.0, 0.0, 0.0));
        set.insert(unit(10.0, 10.0, 10.0));
        let touching = unit(1.0, 0.0, 0.0);
        let overlapping: Vec<usize> = set.overlapping(&touching).map(|(index, _)| index).collect();
        assert_eq!(overlapping, vec![0], "face contact counts as overlap");
        let far = unit(50.0, 50.0, 50.0);
        assert!(
            set.overlapping(&far).next().is_none(),
            "separated boxes are skipped"
        );
    }

    /// An empty set answers every query with nothing.
    #[test]
    fn empty_set_overlaps_nothing() {
        let set = ColliderSet::new();
        let query = unit(0.0, 0.0, 0.0);
        assert!(set.overlapping(&query).next().is_none());
    }

    /// Non-finite centers, half extents, and corners are rejected, naming
    /// the offending vector.
    #[test]
    fn non_finite_geometry_is_rejected() {
        let nan = f32::NAN;
        assert_eq!(
            Aabb::try_new(Vec3::new(nan, 0.0, 0.0), Vec3::splat(1.0)),
            Err(ColliderError::NonFinite {
                value: Vec3::new(nan, 0.0, 0.0)
            })
        );
        assert_eq!(
            Aabb::try_new(Vec3::ZERO, Vec3::new(1.0, f32::INFINITY, 1.0)),
            Err(ColliderError::NonFinite {
                value: Vec3::new(1.0, f32::INFINITY, 1.0)
            })
        );
        assert!(matches!(
            Aabb::from_min_max(Vec3::splat(nan), Vec3::splat(1.0)),
            Err(ColliderError::NonFinite { .. })
        ));
    }

    /// Negative half extents are rejected; zero extents stay legal.
    #[test]
    fn negative_half_extents_are_rejected() {
        let half = Vec3::new(-0.1, 1.0, 1.0);
        assert_eq!(
            Aabb::try_new(Vec3::ZERO, half),
            Err(ColliderError::NegativeHalfExtent { half_extents: half })
        );
        assert!(Aabb::try_new(Vec3::ZERO, Vec3::ZERO).is_ok());
    }

    /// `from_min_max` rejects inverted corners and round-trips ordered
    /// ones exactly.
    #[test]
    fn inverted_corners_are_rejected_and_ordered_ones_round_trip() {
        assert_eq!(
            Aabb::from_min_max(Vec3::new(2.0, 0.0, 0.0), Vec3::new(1.0, 1.0, 1.0)),
            Err(ColliderError::MinAboveMax {
                min: Vec3::new(2.0, 0.0, 0.0),
                max: Vec3::new(1.0, 1.0, 1.0),
            })
        );
        let built = unit(1.0, 2.0, 3.0);
        assert_eq!(
            Aabb::from_min_max(built.min(), built.max()),
            Ok(unit(1.0, 2.0, 3.0))
        );
    }
}
