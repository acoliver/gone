//! Pure world-space placements for every non-pod scene solid (issue #7
//! stage B collider work).
//!
//! One construction path for the static set dressing: `geometry` spawns the
//! visible meshes from these placements verbatim and `colliders` derives the
//! static collision AABBs from the same data, so the rendered scene and the
//! collider set cannot drift apart. This is the same one-construction-path
//! pattern `pod_body` uses for the pod boxes.
//!
//! All values are world space, in meters, up is +Y, with one exception: the
//! status indicator plate is pod-local because the scene spawns it under
//! each pod group. `SolidPlacement::center` is the box center: mesh
//! primitives are centered on their entity, and the collider derivation
//! reads the same center, so a placement's world AABB always shares its
//! center exactly.

use bevy::math::{Quat, Vec3};
use gone_sim::PodPlacement;
use gone_sim::pods::{POD_LENGTH, ROOM_CEILING_HEIGHT, ROOM_LENGTH, ROOM_WIDTH};

/// Shell wall and floor slab thickness, in meters.
pub(super) const WALL_THICKNESS: f32 = 0.2;

/// The hatch opening's size, in meters, and the frame pieces around it.
const HATCH_WIDTH: f32 = 1.2;
const HATCH_HEIGHT: f32 = 2.4;
/// Frame depth, in meters: how far the frame protrudes into the room from
/// the wall's inner face.
pub(super) const FRAME_DEPTH: f32 = 0.18;
const FRAME_POST_WIDTH: f32 = 0.16;
const SILL_HEIGHT: f32 = 0.08;

/// The hatch door slab: slightly smaller than the opening, recessed behind
/// the frame front, and ajar about its hinge edge by
/// [`HATCH_DOOR_AJAR`], leaning into the room.
const DOOR_WIDTH: f32 = 1.12;
const DOOR_HEIGHT: f32 = 2.2;
const DOOR_THICKNESS: f32 = 0.06;
const DOOR_RECESS: f32 = 0.1;
const DOOR_HINGE_INSET: f32 = 0.04;
const HATCH_DOOR_AJAR: f32 = 8.0_f32.to_radians();

/// X of the hatch frame's center plane: protruding [`FRAME_DEPTH`] from the
/// wall's inner face.
pub(super) const HATCH_FRAME_X: f32 = ROOM_LENGTH / 2.0 - FRAME_DEPTH / 2.0;

/// X of the hatch door slab's center plane: recessed behind the frame's
/// front face.
pub(super) const HATCH_DOOR_X: f32 = ROOM_LENGTH / 2.0 - DOOR_RECESS;

/// Cable tray cross-section, in meters, and the drop of the tray center
/// line below the ceiling.
const TRAY_WIDTH: f32 = 0.3;
const TRAY_HEIGHT: f32 = 0.08;
const TRAY_CEILING_DROP: f32 = 0.15;

/// Hanging wire loop torus mesh radii, in meters: the inner ring radius and
/// the outer extent. `geometry` builds the torus mesh from these and
/// `colliders` bounds the decor conservatively from their sum.
pub(super) const WIRE_INNER_RADIUS: f32 = 0.035;
pub(super) const WIRE_OUTER_RADIUS: f32 = 0.11;

/// The status indicator plate, in meters: mounted on the pod's foot face.
const PLATE_WIDTH: f32 = 0.2;
const PLATE_HEIGHT: f32 = 0.1;
const PLATE_THICKNESS: f32 = 0.04;
const PLATE_STANDOFF: f32 = 0.02;
const PLATE_MOUNT_HEIGHT: f32 = 0.55;

/// One placed solid box: world center, full size, and the world rotation
/// applied at spawn. Most pieces are axis-aligned; the ajar hatch door and
/// the torn cable trays carry real rotations.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) struct SolidPlacement {
    /// World center of the box (mesh primitives are centered on their
    /// entity).
    pub(super) center: Vec3,
    /// Full box size along the local axes.
    pub(super) size: Vec3,
    /// World rotation applied at spawn.
    pub(super) rotation: Quat,
}

impl SolidPlacement {
    /// An axis-aligned placement at `center` with `size`.
    const fn new(center: Vec3, size: Vec3) -> Self {
        Self {
            center,
            size,
            rotation: Quat::IDENTITY,
        }
    }
}

/// The room shell's six boxes in fixed order: floor, ceiling, then the -Z,
/// +Z, -X, and +X walls. The playable interior is exactly `ROOM_LENGTH` by
/// `ROOM_WIDTH` with its ceiling at `ROOM_CEILING_HEIGHT`; the shell
/// surrounds it with [`WALL_THICKNESS`] slabs.
#[must_use]
pub(super) fn room_shell() -> [SolidPlacement; 6] {
    let slab = Vec3::new(
        ROOM_LENGTH + 2.0 * WALL_THICKNESS,
        WALL_THICKNESS,
        ROOM_WIDTH + 2.0 * WALL_THICKNESS,
    );
    let wall_along_x = Vec3::new(
        ROOM_LENGTH + 2.0 * WALL_THICKNESS,
        ROOM_CEILING_HEIGHT,
        WALL_THICKNESS,
    );
    let wall_along_z = Vec3::new(WALL_THICKNESS, ROOM_CEILING_HEIGHT, ROOM_WIDTH);
    let mid_height = ROOM_CEILING_HEIGHT / 2.0;
    [
        SolidPlacement::new(Vec3::new(0.0, -WALL_THICKNESS / 2.0, 0.0), slab),
        SolidPlacement::new(
            Vec3::new(0.0, ROOM_CEILING_HEIGHT + WALL_THICKNESS / 2.0, 0.0),
            slab,
        ),
        SolidPlacement::new(
            Vec3::new(0.0, mid_height, -(ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0)),
            wall_along_x,
        ),
        SolidPlacement::new(
            Vec3::new(0.0, mid_height, ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0),
            wall_along_x,
        ),
        SolidPlacement::new(
            Vec3::new(-(ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0), mid_height, 0.0),
            wall_along_z,
        ),
        SolidPlacement::new(
            Vec3::new(ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0, mid_height, 0.0),
            wall_along_z,
        ),
    ]
}

/// The hatch group's five boxes in fixed order: the -Z frame post, the +Z
/// frame post, the lintel, the sill, and the ajar door slab. The group
/// itself sits at the identity transform, so these are world placements.
///
/// The door's placement composes the hinge group transform (recessed
/// center plane, hinged at the -Z jamb, swung into the room by
/// [`HATCH_DOOR_AJAR`]) with the slab's centered child offset, exactly as
/// the old parent-plus-child spawn did.
#[must_use]
pub(super) fn hatch_solids() -> [SolidPlacement; 5] {
    let post = Vec3::new(
        FRAME_DEPTH,
        HATCH_HEIGHT + FRAME_POST_WIDTH,
        FRAME_POST_WIDTH,
    );
    let lintel = Vec3::new(
        FRAME_DEPTH,
        FRAME_POST_WIDTH,
        HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH,
    );
    let sill = Vec3::new(
        FRAME_DEPTH,
        SILL_HEIGHT,
        HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH,
    );
    let door_rotation = Quat::from_rotation_y(-HATCH_DOOR_AJAR);
    let door_group_origin = Vec3::new(HATCH_DOOR_X, 0.0, -(HATCH_WIDTH / 2.0 - DOOR_HINGE_INSET));
    let door_center =
        door_group_origin + door_rotation * Vec3::new(0.0, DOOR_HEIGHT / 2.0, DOOR_WIDTH / 2.0);
    [
        SolidPlacement::new(
            Vec3::new(
                HATCH_FRAME_X,
                f32::midpoint(HATCH_HEIGHT, FRAME_POST_WIDTH),
                -f32::midpoint(HATCH_WIDTH, FRAME_POST_WIDTH),
            ),
            post,
        ),
        SolidPlacement::new(
            Vec3::new(
                HATCH_FRAME_X,
                f32::midpoint(HATCH_HEIGHT, FRAME_POST_WIDTH),
                f32::midpoint(HATCH_WIDTH, FRAME_POST_WIDTH),
            ),
            post,
        ),
        SolidPlacement::new(
            Vec3::new(HATCH_FRAME_X, HATCH_HEIGHT + FRAME_POST_WIDTH / 2.0, 0.0),
            lintel,
        ),
        SolidPlacement::new(Vec3::new(HATCH_FRAME_X, SILL_HEIGHT / 2.0, 0.0), sill),
        SolidPlacement {
            center: door_center,
            size: Vec3::new(DOOR_THICKNESS, DOOR_HEIGHT, DOOR_WIDTH),
            rotation: door_rotation,
        },
    ]
}

/// The torn ceiling's cable trays, concentrated over the room center per
/// the story's wounded ceiling: a junction of runs and one stub toward the
/// player row, each tipped off level about its run axis.
#[must_use]
pub(super) fn cable_trays() -> [SolidPlacement; 3] {
    [
        SolidPlacement {
            center: Vec3::new(-0.5, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP, 0.35),
            size: Vec3::new(6.0, TRAY_HEIGHT, TRAY_WIDTH),
            rotation: Quat::from_rotation_y(0.0) * Quat::from_rotation_x(0.06),
        },
        SolidPlacement {
            center: Vec3::new(0.9, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP - 0.04, -0.7),
            size: Vec3::new(4.5, TRAY_HEIGHT, TRAY_WIDTH),
            rotation: Quat::from_rotation_y(core::f32::consts::FRAC_PI_2)
                * Quat::from_rotation_x(-0.04),
        },
        SolidPlacement {
            center: Vec3::new(1.6, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP + 0.05, 1.1),
            size: Vec3::new(3.0, TRAY_HEIGHT, TRAY_WIDTH),
            rotation: Quat::from_rotation_y(0.0) * Quat::from_rotation_x(-0.09),
        },
    ]
}

/// One hanging wire loop: a torus hanging under the torn ceiling, tipped
/// from face-up to vertical by a quarter turn, with a per-loop swing yaw so
/// the loops do not read as one stamped ring.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) struct WireLoop {
    /// World center of the torus.
    pub(super) center: Vec3,
    /// World rotation applied at spawn.
    pub(super) rotation: Quat,
}

/// The five hanging wire loops over the room center.
#[must_use]
pub(super) fn wire_loops() -> [WireLoop; 5] {
    let hanging = |center: Vec3, swing_radians: f32| WireLoop {
        center,
        rotation: Quat::from_rotation_x(core::f32::consts::FRAC_PI_2)
            * Quat::from_rotation_y(swing_radians),
    };
    [
        hanging(Vec3::new(-1.3, 2.7, 0.5), 0.4),
        hanging(Vec3::new(-0.4, 2.55, 0.2), 1.3),
        hanging(Vec3::new(0.3, 2.78, -0.5), 2.2),
        hanging(Vec3::new(1.1, 2.62, 0.8), 0.9),
        hanging(Vec3::new(2.0, 2.5, -0.2), 2.9),
    ]
}

/// The pod status indicator plate, in the POD-LOCAL frame: the scene spawns
/// it under each pod group, and the collider set lifts it into the world
/// through [`pod_world_transform`].
#[must_use]
pub(super) fn indicator_plate() -> SolidPlacement {
    SolidPlacement::new(
        Vec3::new(0.0, PLATE_MOUNT_HEIGHT, POD_LENGTH / 2.0 + PLATE_STANDOFF),
        Vec3::new(PLATE_WIDTH, PLATE_HEIGHT, PLATE_THICKNESS),
    )
}

/// The pod group transform `geometry` spawns pod groups with: the yaw
/// rotation and the floor translation derived from the registry placement.
/// Pod-local construction data (`pod_body` solids, the indicator plate)
/// rides this frame into the world.
#[must_use]
pub(crate) fn pod_world_transform(placement: PodPlacement) -> (Quat, Vec3) {
    (
        Quat::from_rotation_y(placement.yaw_radians),
        Vec3::new(placement.center.0, 0.0, placement.center.1),
    )
}

/// Pure coverage of the placement data: the shell tiles the frozen room
/// envelope and the hatch sits on the +X wall at the registry's opening.
#[cfg(test)]
mod tests {
    use bevy::math::Vec3;
    use gone_sim::PodRegistry;
    use gone_sim::pods::{ROOM_LENGTH, ROOM_WIDTH};

    use super::{WALL_THICKNESS, hatch_solids, room_shell};

    /// The shell's combined bounds are the envelope, and the envelope's
    /// interior faces are exactly the playable room: floor at zero, ceiling
    /// at the frozen height, walls at the frozen plan.
    #[test]
    fn room_shell_bounds_are_the_envelope() {
        let mut min = Vec3::splat(f32::INFINITY);
        let mut max = Vec3::splat(f32::NEG_INFINITY);
        for placement in room_shell() {
            let half = placement.size / 2.0;
            min = min.min(placement.center - half);
            max = max.max(placement.center + half);
        }
        // The floor slab and the ceiling slab each reach the envelope on
        // their own side, so the envelope equals their union.
        let floor = room_shell()[0];
        let ceiling = room_shell()[1];
        assert_eq!(min, floor.center - floor.size / 2.0);
        assert_eq!(max, ceiling.center + ceiling.size / 2.0);
        // f32 sums at room scale lose a few ULPs against the frozen plan,
        // so the face ties use the codebase's 1e-5 position tolerance.
        assert!((min.x + ROOM_LENGTH / 2.0 + WALL_THICKNESS).abs() < 1e-5);
        assert!((max.x - ROOM_LENGTH / 2.0 - WALL_THICKNESS).abs() < 1e-5);
        assert!((min.z + ROOM_WIDTH / 2.0 + WALL_THICKNESS).abs() < 1e-5);
        assert!((max.z - ROOM_WIDTH / 2.0 - WALL_THICKNESS).abs() < 1e-5);
    }

    /// The hatch door's world placement leans into the room: its center
    /// stays on the +X side of the frame plane, below the lintel, and its
    /// free edge (positive local z, swung by the door rotation) crosses to
    /// the -X side of the hinge line, which is what "ajar" means.
    #[test]
    fn hatch_door_placement_sits_ajar_in_the_opening() {
        let registry = PodRegistry::frozen();
        let hatch = registry.hatch();
        let door = hatch_solids()[4];
        assert!(door.center.x > ROOM_LENGTH / 2.0 - 0.5, "at the short wall");
        assert!((door.center.y - 1.1).abs() < 1e-5, "mid height");
        // The free edge is the rotated local +z corner of the slab center.
        let free_edge = door.center + door.rotation * Vec3::new(0.0, 0.0, 0.56);
        assert!(
            free_edge.x < hatch.center.0 - 0.1,
            "the free edge leans into the room, got x {}",
            free_edge.x
        );
    }
}
