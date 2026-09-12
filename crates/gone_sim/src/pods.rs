//! Stasis pod registry (issue #7 stage A).
//!
//! The single source of truth for the stasis bay layout and pod states:
//! seven pods in two rows flanking the central aisle, the player's pod in
//! one row, and the jammed hatch centered on one short wall. The game scene
//! is built from this data and the scene tests assert against it, so the
//! simulation truth and the rendered geometry cannot drift apart.
//!
//! Units and axes (matching `controller`): meters, up is positive Y, and the
//! floor plane is X/Z with the room's long axis on X. The room is centered
//! on the origin, so the floor spans
//! `[-ROOM_LENGTH / 2, ROOM_LENGTH / 2]` on X and
//! `[-ROOM_WIDTH / 2, ROOM_WIDTH / 2]` on Z. The hatch sits on the +X short
//! wall, centered on it.
//!
//! Pod frame: a pod's long axis is its local Z and its opening faces local
//! +Z. [`PodPlacement::yaw_radians`] rotates local +Z onto the opening's
//! world direction, which is toward the aisle for both rows. Pod backs sit
//! flush against their long wall.
//!
//! Everything here is pure data: no Bevy, no render types, and no public
//! construction path that can produce a registry holding duplicate pod ids
//! or the wrong number of player pods.

use crate::WakePhase;

/// How many stasis pods the bay holds. Fixed: the story's seven-pod room.
pub const POD_COUNT: usize = 7;

/// Room length along X (the long axis), in meters. The hatch wall is at
/// `+ROOM_LENGTH / 2`.
pub const ROOM_LENGTH: f32 = 12.0;

/// Room width along Z, in meters.
pub const ROOM_WIDTH: f32 = 8.0;

/// Floor-to-ceiling height, in meters.
pub const ROOM_CEILING_HEIGHT: f32 = 3.2;

/// Pod length along the pod's local Z (out from its wall), in meters.
pub const POD_LENGTH: f32 = 2.2;

/// Pod width along the pod's local X (along its wall), in meters.
pub const POD_WIDTH: f32 = 0.9;

/// Pod height from floor to the top of the body, in meters.
pub const POD_HEIGHT: f32 = 0.8;

/// Half-width of the central aisle: the frozen 3 m walk corridor between
/// the two pod rows. Pod faces stop short of this band (see the layout test
/// and `controller::POD_EXIT_CLEARANCE`).
pub const AISLE_HALF_WIDTH: f32 = 1.5;

/// One pod's identity: a bay index in `0..POD_COUNT`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PodId(u8);

impl PodId {
    /// The seven bay ids, in index order.
    pub const ALL: [PodId; POD_COUNT] = [
        PodId(0),
        PodId(1),
        PodId(2),
        PodId(3),
        PodId(4),
        PodId(5),
        PodId(6),
    ];

    /// The pod id for `index`, or `None` outside the bay's index range.
    #[must_use]
    pub fn new(index: u8) -> Option<Self> {
        if usize::from(index) < POD_COUNT {
            return Some(Self(index));
        }
        None
    }

    /// The bay index of this pod, always below [`POD_COUNT`].
    #[must_use]
    pub fn index(self) -> usize {
        usize::from(self.0)
    }
}

/// What condition one pod is in during the opening beat.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PodState {
    /// The player's pod: open, restraint popped, occupied until the wake
    /// progression reaches [`WakePhase::Standing`].
    Player,
    /// Open with the occupancy blanket hanging, visibly empty.
    EmptyOpen,
    /// Closed and unpowered: sealed lid, dead status indicators.
    Sealed,
}

impl PodState {
    /// Whether this is the player's pod.
    #[must_use]
    pub fn is_player(self) -> bool {
        matches!(self, Self::Player)
    }

    /// Whether the pod stands open (open lid and a visible cavity).
    #[must_use]
    pub fn is_open(self) -> bool {
        !matches!(self, Self::Sealed)
    }
}

/// Where one pod sits and which way its opening faces, on the floor plane.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PodPlacement {
    /// Floor-plan center of the pod body, in meters: `(x, z)`.
    pub center: (f32, f32),
    /// Yaw about +Y in radians that rotates the pod's local +Z (its opening
    /// direction) onto the opening's world direction.
    pub yaw_radians: f32,
}

/// One stasis pod: identity, condition, and placement. Construction stays
/// crate-private so a registry is the only way pods reach other crates.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Pod {
    id: PodId,
    state: PodState,
    placement: PodPlacement,
}

impl Pod {
    /// Build one pod. Crate-private: see [`PodRegistry::try_new`].
    pub(crate) const fn new(id: PodId, state: PodState, placement: PodPlacement) -> Self {
        Self {
            id,
            state,
            placement,
        }
    }

    /// The pod's identity.
    #[must_use]
    pub fn id(self) -> PodId {
        self.id
    }

    /// The pod's condition during the opening beat.
    #[must_use]
    pub fn state(self) -> PodState {
        self.state
    }

    /// Where the pod sits and which way its opening faces.
    #[must_use]
    pub fn placement(self) -> PodPlacement {
        self.placement
    }

    /// Whether the pod counts as occupied in `phase`: the player's pod is
    /// occupied from [`WakePhase::Waking`] through
    /// [`WakePhase::ExitingPod`] and vacates exactly at
    /// [`WakePhase::Standing`]. Every other pod is always empty.
    #[must_use]
    pub fn occupied(self, phase: WakePhase) -> bool {
        match self.state {
            PodState::Player => phase != WakePhase::Standing,
            PodState::EmptyOpen | PodState::Sealed => false,
        }
    }
}

/// The jammed hatch's frozen placement: centered on the +X short wall,
/// facing into the room (toward -X). Static dressing; the door beat that
/// tries to open it is issue #11's.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct HatchPlacement {
    /// Floor-plan center of the hatch opening, in meters: `(x, z)`.
    pub center: (f32, f32),
    /// Yaw about +Y in radians that rotates the hatch's local +Z (its
    /// inward face) onto the face's world direction.
    pub yaw_radians: f32,
}

/// The frozen hatch placement, shared by every registry instance.
const HATCH_PLACEMENT: HatchPlacement = HatchPlacement {
    center: (ROOM_LENGTH / 2.0, 0.0),
    yaw_radians: -core::f32::consts::FRAC_PI_2,
};

/// Distance from a long wall to the center line of its pod row.
const ROW_CENTER_FROM_WALL: f32 = POD_LENGTH / 2.0;

/// Floor-plan Z of the -Z wall row's pod centers (pods backs flush against
/// the wall, openings facing the aisle at +Z).
const ROW_A_Z: f32 = -(ROOM_WIDTH / 2.0 - ROW_CENTER_FROM_WALL);

/// Floor-plan Z of the +Z wall row's pod centers (openings facing the
/// aisle at -Z).
const ROW_B_Z: f32 = ROOM_WIDTH / 2.0 - ROW_CENTER_FROM_WALL;

/// Yaw that points a pod opening toward +Z (the -Z wall row).
const ROW_A_YAW: f32 = 0.0;

/// Yaw that points a pod opening toward -Z (the +Z wall row).
const ROW_B_YAW: f32 = core::f32::consts::PI;

/// Pod centers along X for a row, spaced to leave walking gaps between
/// pods. Shared by both rows.
const ROW_X_CENTERS: [f32; 4] = [-4.8, -3.4, -2.0, -0.6];

/// The frozen opening-beat pods: four in the -Z wall row (ids 0 to 3),
/// three in the +Z wall row (ids 4 to 6), the player's pod id 6 in the
/// three-pod row at the end farthest from the hatch.
const FROZEN_PODS: [Pod; POD_COUNT] = [
    Pod::new(
        PodId(0),
        PodState::Sealed,
        PodPlacement {
            center: (ROW_X_CENTERS[0], ROW_A_Z),
            yaw_radians: ROW_A_YAW,
        },
    ),
    Pod::new(
        PodId(1),
        PodState::EmptyOpen,
        PodPlacement {
            center: (ROW_X_CENTERS[1], ROW_A_Z),
            yaw_radians: ROW_A_YAW,
        },
    ),
    Pod::new(
        PodId(2),
        PodState::Sealed,
        PodPlacement {
            center: (ROW_X_CENTERS[2], ROW_A_Z),
            yaw_radians: ROW_A_YAW,
        },
    ),
    Pod::new(
        PodId(3),
        PodState::EmptyOpen,
        PodPlacement {
            center: (ROW_X_CENTERS[3], ROW_A_Z),
            yaw_radians: ROW_A_YAW,
        },
    ),
    Pod::new(
        PodId(4),
        PodState::Sealed,
        PodPlacement {
            center: (ROW_X_CENTERS[2], ROW_B_Z),
            yaw_radians: ROW_B_YAW,
        },
    ),
    Pod::new(
        PodId(5),
        PodState::EmptyOpen,
        PodPlacement {
            center: (ROW_X_CENTERS[1], ROW_B_Z),
            yaw_radians: ROW_B_YAW,
        },
    ),
    Pod::new(
        PodId(6),
        PodState::Player,
        PodPlacement {
            center: (ROW_X_CENTERS[0], ROW_B_Z),
            yaw_radians: ROW_B_YAW,
        },
    ),
];

/// A rejected registry construction.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PodRegistryError {
    /// Two pods carried the same id. A registry holds each of the seven
    /// bay ids exactly once.
    DuplicatePodId {
        /// The id that appeared more than once.
        id: PodId,
    },
    /// The pod set did not carry exactly one player pod. The registry's
    /// occupancy contract needs exactly one.
    PlayerPodCount {
        /// How many player pods the pod set carried.
        found: usize,
    },
}

impl std::fmt::Display for PodRegistryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::DuplicatePodId { id } => write!(
                f,
                "duplicate stasis pod id {}: each bay id must appear exactly once",
                id.index()
            ),
            Self::PlayerPodCount { found } => write!(
                f,
                "a stasis registry needs exactly one player pod, found {found}"
            ),
        }
    }
}

impl std::error::Error for PodRegistryError {}

/// The stasis bay's pod set: the truth the scene and the scene tests read.
///
/// Construction is validated: ids are distinct, indices are in range, and
/// exactly one pod is the player's. [`PodRegistry::frozen`] is the
/// canonical opening-beat instance; [`PodRegistry::try_new`] is the
/// validated general constructor. No other path builds a registry, so no
/// registry can hold duplicate pod ids.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PodRegistry {
    pods: [Pod; POD_COUNT],
    player_index: usize,
}

impl PodRegistry {
    /// The canonical opening-beat registry: the frozen two-row layout with
    /// the player in pod id 6.
    #[must_use]
    pub fn frozen() -> Self {
        Self::build(FROZEN_PODS)
    }

    /// Build a registry over an explicit pod set, rejecting duplicate ids
    /// and player-pod counts other than one. The stored pod set is sorted
    /// by id, so `pod(id)` returns the pod carrying that id whatever order
    /// the input arrived in; placements are carried through and the frozen
    /// layout lives in [`PodRegistry::frozen`].
    ///
    /// # Errors
    /// [`PodRegistryError::DuplicatePodId`] when two pods share an id, and
    /// [`PodRegistryError::PlayerPodCount`] when the set does not carry
    /// exactly one player pod.
    pub fn try_new(pods: [Pod; POD_COUNT]) -> Result<Self, PodRegistryError> {
        // Store the pods sorted by id regardless of input order: `pod(id)`
        // indexes by id, so a valid-but-permuted input must not preserve its
        // arrival order. Sorting first also makes duplicate ids adjacent.
        let mut pods = pods;
        pods.sort_by_key(|pod| pod.id);
        for window in pods.windows(2) {
            if window[0].id == window[1].id {
                return Err(PodRegistryError::DuplicatePodId { id: window[1].id });
            }
        }
        let player_index = match pods.iter().position(|pod| pod.state.is_player()) {
            // The position scan found the first player pod; a second one
            // could only sit after it.
            Some(index) if !pods[index + 1..].iter().any(|pod| pod.state.is_player()) => index,
            Some(first) => {
                let found = 1 + pods[first + 1..]
                    .iter()
                    .filter(|pod| pod.state.is_player())
                    .count();
                return Err(PodRegistryError::PlayerPodCount { found });
            }
            None => return Err(PodRegistryError::PlayerPodCount { found: 0 }),
        };
        Ok(Self::build_with_player(pods, player_index))
    }

    /// The pod set, ordered by id.
    #[must_use]
    pub fn pods(&self) -> &[Pod] {
        &self.pods
    }

    /// The pod with id `id`.
    ///
    /// # Panics
    /// Never: a validated registry holds every id in [`PodId::ALL`], and
    /// `PodId` cannot name an index outside that set.
    #[must_use]
    pub fn pod(&self, id: PodId) -> &Pod {
        &self.pods[id.index()]
    }

    /// The player's pod.
    ///
    /// # Panics
    /// Never: a validated registry carries exactly one player pod, and
    /// `player_index` names it.
    #[must_use]
    pub fn player_pod(&self) -> &Pod {
        &self.pods[self.player_index]
    }

    /// The hatch's frozen placement.
    #[must_use]
    pub fn hatch(&self) -> HatchPlacement {
        HATCH_PLACEMENT
    }

    /// How many pods count as occupied in `phase`: one (the player's) from
    /// `Waking` through `ExitingPod`, zero at `Standing`.
    #[must_use]
    pub fn occupancy_count(&self, phase: WakePhase) -> usize {
        self.pods.iter().filter(|pod| pod.occupied(phase)).count()
    }

    /// Whether every non-player pod is empty in `phase`. Holds in every
    /// phase by construction; the predicate exists so scenario and scene
    /// tests can assert the contract directly.
    #[must_use]
    pub fn zero_non_player_occupancy(&self, phase: WakePhase) -> bool {
        self.pods
            .iter()
            .filter(|pod| !pod.state.is_player())
            .all(|pod| !pod.occupied(phase))
    }

    /// Assemble a registry over an already-validated pod set.
    fn build(pods: [Pod; POD_COUNT]) -> Self {
        let player_index = pods
            .iter()
            .position(|pod| pod.state.is_player())
            .expect("frozen pod set carries exactly one player pod");
        Self::build_with_player(pods, player_index)
    }

    /// Assemble a registry with a known player index.
    fn build_with_player(pods: [Pod; POD_COUNT], player_index: usize) -> Self {
        Self { pods, player_index }
    }
}

/// Exhaustive, pure coverage of the registry: the frozen layout, the
/// occupancy contract over every phase, and the rejection of invalid pod
/// sets.
#[cfg(test)]
mod tests {
    use super::{
        AISLE_HALF_WIDTH, HatchPlacement, POD_COUNT, POD_HEIGHT, POD_LENGTH, POD_WIDTH, PodId,
        PodPlacement, PodRegistry, PodRegistryError, PodState, ROOM_CEILING_HEIGHT, ROOM_LENGTH,
        ROOM_WIDTH, ROW_A_Z, ROW_B_YAW, ROW_B_Z,
    };
    use crate::controller::POD_EXIT_CLEARANCE;
    use crate::phase::WakePhase;

    /// Every phase in progression order.
    const ALL_PHASES: [WakePhase; 4] = [
        WakePhase::Waking,
        WakePhase::AwakeInPod,
        WakePhase::ExitingPod,
        WakePhase::Standing,
    ];

    /// A pod with the given id and state, placed off-room so tests can see
    /// that placement is carried through `try_new` untouched.
    fn pod_at(index: u8, state: PodState) -> super::Pod {
        super::Pod::new(
            PodId::new(index).expect("test indices are in range"),
            state,
            PodPlacement {
                center: (0.0, 0.0),
                yaw_radians: 0.0,
            },
        )
    }

    /// The frozen registry holds the seven distinct bay ids in two rows
    /// with exactly one player pod, id 6, in the three-pod row.
    #[test]
    fn frozen_registry_holds_seven_distinct_pods_in_two_rows() {
        let registry = PodRegistry::frozen();
        assert_eq!(registry.pods().len(), POD_COUNT);
        let mut seen: Vec<usize> = registry.pods().iter().map(|pod| pod.id().index()).collect();
        seen.sort_unstable();
        seen.dedup();
        assert_eq!(seen.len(), POD_COUNT, "ids must be distinct");
        for pod in registry.pods() {
            assert!(PodId::ALL.contains(&pod.id()), "every id is a bay id");
        }
        assert_frozen_row(&registry, ROW_A_Z, 0.0, 4, "row A faces +Z");
        assert_frozen_row(&registry, ROW_B_Z, ROW_B_YAW, 3, "row B faces -Z");
        // Exactly one player pod, id 6, in row B.
        let players: Vec<_> = registry
            .pods()
            .iter()
            .filter(|pod| pod.state().is_player())
            .collect();
        assert_eq!(players.len(), 1);
        assert_eq!(players[0].id().index(), 6);
        assert_eq!(registry.player_pod().id().index(), 6);
        assert!((players[0].placement().center.1 - ROW_B_Z).abs() < 1e-6);
    }

    /// One frozen row's contract: `expected_count` pods sit at the row's
    /// wall line `row_z`, every opening facing the aisle at `expected_yaw`.
    fn assert_frozen_row(
        registry: &PodRegistry,
        row_z: f32,
        expected_yaw: f32,
        expected_count: usize,
        label: &'static str,
    ) {
        let row: Vec<_> = registry
            .pods()
            .iter()
            .filter(|pod| (pod.placement().center.1 - row_z).abs() < 1e-6)
            .collect();
        assert_eq!(row.len(), expected_count, "{label}");
        for pod in &row {
            assert!(
                (pod.placement().yaw_radians - expected_yaw).abs() < 1e-6,
                "{label}"
            );
        }
    }

    /// The frozen state split: three sealed pods, three empty-open pods,
    /// and one open player pod.
    #[test]
    fn frozen_state_split_is_three_sealed_three_open_one_player() {
        let registry = PodRegistry::frozen();
        let sealed = registry
            .pods()
            .iter()
            .filter(|pod| pod.state() == PodState::Sealed)
            .count();
        let empty_open = registry
            .pods()
            .iter()
            .filter(|pod| pod.state() == PodState::EmptyOpen)
            .count();
        assert_eq!(sealed, 3, "three sealed pods");
        assert_eq!(empty_open, 3, "three empty-open pods");
        assert_eq!(
            registry
                .pods()
                .iter()
                .filter(|pod| pod.state().is_player())
                .count(),
            1,
            "exactly one player pod"
        );
    }

    /// Every frozen pod's body box sits inside the room, stops short of the
    /// central aisle by the frozen exit clearance, and the hatch is
    /// centered on the +X short wall facing -X.
    #[test]
    fn frozen_layout_respects_room_aisle_and_hatch() {
        const { assert!(POD_HEIGHT <= ROOM_CEILING_HEIGHT) };
        let registry = PodRegistry::frozen();
        let room_half_length = ROOM_LENGTH / 2.0;
        let room_half_width = ROOM_WIDTH / 2.0;
        for pod in registry.pods() {
            let placement = pod.placement();
            let (x, z) = placement.center;
            // Axis-aligned yaws (0 or pi) keep the body box's extents on X
            // and Z: width along the wall, length into the room.
            assert!(
                x.abs() + POD_WIDTH / 2.0 <= room_half_length,
                "pod inside X"
            );
            assert!(
                z.abs() + POD_LENGTH / 2.0 <= room_half_width,
                "pod inside Z"
            );
            // The aisle-side face of the body box must clear the frozen
            // aisle band by at least the frozen exit clearance.
            let aisle_face = z.abs() - POD_LENGTH / 2.0;
            assert!(
                aisle_face >= AISLE_HALF_WIDTH + POD_EXIT_CLEARANCE,
                "pod clears the aisle: face {aisle_face}"
            );
        }
        let hatch: HatchPlacement = registry.hatch();
        assert!(
            (hatch.center.0 - ROOM_LENGTH / 2.0).abs() < 1e-6,
            "hatch on the +X wall"
        );
        assert!(hatch.center.1.abs() < 1e-6, "hatch centered on the wall");
        // Facing -X (into the room): direction (sin yaw, cos yaw).
        assert!(hatch.yaw_radians.sin() < 0.0);
        assert!(hatch.yaw_radians.cos().abs() < 1e-6);
    }

    /// Occupancy is the player pod alone, until Standing.
    #[test]
    fn occupancy_counts_follow_the_phase() {
        let registry = PodRegistry::frozen();
        for phase in ALL_PHASES {
            assert!(
                registry.zero_non_player_occupancy(phase),
                "non-player pods are empty in {phase:?}"
            );
        }
        assert_eq!(registry.occupancy_count(WakePhase::Waking), 1);
        assert_eq!(registry.occupancy_count(WakePhase::AwakeInPod), 1);
        assert_eq!(registry.occupancy_count(WakePhase::ExitingPod), 1);
        assert_eq!(registry.occupancy_count(WakePhase::Standing), 0);
        assert!(registry.player_pod().occupied(WakePhase::ExitingPod));
        assert!(!registry.player_pod().occupied(WakePhase::Standing));
    }

    /// A pod set with a repeated id is rejected, naming the id.
    #[test]
    fn duplicate_pod_ids_are_rejected() {
        let mut pods = [
            pod_at(0, PodState::Player),
            pod_at(1, PodState::Sealed),
            pod_at(2, PodState::EmptyOpen),
            pod_at(3, PodState::Sealed),
            pod_at(4, PodState::EmptyOpen),
            pod_at(5, PodState::Sealed),
            pod_at(6, PodState::EmptyOpen),
        ];
        pods[6] = pods[0];
        let err = PodRegistry::try_new(pods).expect_err("duplicate ids must be rejected");
        assert_eq!(err, PodRegistryError::DuplicatePodId { id: pods[0].id() });
        let text = err.to_string();
        assert!(text.contains("duplicate"), "display: {text}");
    }

    /// A pod set without exactly one player pod is rejected, naming the
    /// count.
    #[test]
    fn player_pod_count_is_enforced() {
        let none = [
            pod_at(0, PodState::Sealed),
            pod_at(1, PodState::EmptyOpen),
            pod_at(2, PodState::Sealed),
            pod_at(3, PodState::EmptyOpen),
            pod_at(4, PodState::Sealed),
            pod_at(5, PodState::EmptyOpen),
            pod_at(6, PodState::Sealed),
        ];
        assert_eq!(
            PodRegistry::try_new(none),
            Err(PodRegistryError::PlayerPodCount { found: 0 })
        );
        let mut two = [
            pod_at(0, PodState::Player),
            pod_at(1, PodState::Sealed),
            pod_at(2, PodState::EmptyOpen),
            pod_at(3, PodState::Sealed),
            pod_at(4, PodState::EmptyOpen),
            pod_at(5, PodState::Sealed),
            pod_at(6, PodState::EmptyOpen),
        ];
        two[6] = pod_at(6, PodState::Player);
        assert_eq!(
            PodRegistry::try_new(two),
            Err(PodRegistryError::PlayerPodCount { found: 2 })
        );
    }

    /// A valid pod set round-trips through `try_new`, and pod lookup by id
    /// reads back the pod that was stored.
    #[test]
    fn valid_pod_sets_round_trip_through_try_new() {
        let frozen = PodRegistry::frozen();
        let mut pods = [frozen.pods()[0]; POD_COUNT];
        pods.copy_from_slice(frozen.pods());
        let rebuilt = PodRegistry::try_new(pods).expect("frozen set is valid");
        assert_eq!(rebuilt, frozen);
        for pod in frozen.pods() {
            assert_eq!(frozen.pod(pod.id()), pod);
        }
    }

    /// Regression: `try_new` used to preserve input order while `pod(id)`
    /// indexes by id, so a valid-but-permuted pod set silently returned the
    /// wrong pod for every id it did not keep in place. The stored set must
    /// be ordered by id, whatever order the input arrived in.
    #[test]
    fn permuted_pod_sets_still_look_up_every_id_correctly() {
        let frozen = PodRegistry::frozen();
        // Reversed input order.
        let mut pods = [frozen.pods()[0]; POD_COUNT];
        pods.copy_from_slice(frozen.pods());
        pods.reverse();
        let reversed = PodRegistry::try_new(pods).expect("permuted set is valid");
        assert_eq!(reversed, frozen, "order-independent registry contents");
        for id in PodId::ALL {
            assert_eq!(reversed.pod(id).id(), id, "reversed input, id {id:?}");
        }
        assert_eq!(reversed.player_pod().id(), frozen.player_pod().id());

        // Two ids swapped in an otherwise ordered input.
        let mut pods = [frozen.pods()[0]; POD_COUNT];
        pods.copy_from_slice(frozen.pods());
        pods.swap(1, 5);
        let swapped = PodRegistry::try_new(pods).expect("permuted set is valid");
        assert_eq!(swapped, frozen);
        for id in PodId::ALL {
            assert_eq!(swapped.pod(id).id(), id, "swapped input, id {id:?}");
        }

        // The player pod moves with its pod, not with its input position.
        assert_eq!(
            swapped.player_pod().placement(),
            frozen.player_pod().placement(),
            "the player pod is found by identity, not input position"
        );
    }

    /// `PodId::new` admits exactly the bay indices, and `ALL` lists them
    /// in order.
    #[test]
    fn pod_ids_cover_the_bay_range_only() {
        for index in 0..POD_COUNT {
            let id = PodId::new(u8::try_from(index).expect("bay indices fit u8"))
                .expect("index below the pod count");
            assert_eq!(id.index(), index);
        }
        assert_eq!(
            PodId::new(u8::try_from(POD_COUNT).expect("seven fits u8")),
            None
        );
        assert_eq!(PodId::new(255), None);
        for (position, id) in PodId::ALL.iter().enumerate() {
            assert_eq!(id.index(), position);
        }
    }
}
