//! The static collider set for the stasis room (issue #7, app wiring of the
//! sim core).
//!
//! One construction path with the rendered scene: the same pure placement
//! data that `geometry` spawns as meshes ([`room_shell`], [`pod_solids`],
//! [`hatch_solids`]) is lifted here into validated `gone_sim`
//! [`Aabb`]s and inserted as the [`SimColliders`] resource at scene setup,
//! so the rendered world and the swept-collision world cannot drift apart.
//! Every box is the conservative world-space hull of its placement's
//! transformed corners: exact for the axis-aligned shell and pod cavity,
//! a few ulps wider for the rotated pieces (the ajar hatch door, the
//! propped open lids), which is the honest bound an axis-aligned collider
//! set can carry for a rotated solid.
//!
//! The status plates, cable trays, and hanging wire loops are dressing
//! outside the walking envelope (above standing head height, or mounted
//! on the aperture face the authored exit path crosses) and are
//! deliberately not colliders, so the exit aperture mouth stays exactly as
//! clear as `gone_sim::exit` authored it.

use bevy::ecs::prelude::Resource;
use bevy::math::{Quat, Vec3};
use gone_sim::{Aabb, ColliderError, ColliderSet, PodRegistry};

use super::placement::{SolidPlacement, hatch_solids, pod_world_transform, room_shell};
use super::pod_body::{PodSolid, pod_solids};

/// The app's resource over the `gone_sim` static collider set. Built once
/// from the same placement data the scene build spawns, then read-only:
/// the swept resolver and the get-up controller query it, nothing rewrites
/// it.
#[derive(Resource, Debug)]
pub(crate) struct SimColliders(ColliderSet);

impl SimColliders {
    /// Build the resource over a finished collider set. The one construction
    /// path is [`scene_collider_set`]; this only wraps its result, so the
    /// swept-collision world can never be rewritten in place.
    pub(crate) fn new(set: ColliderSet) -> Self {
        Self(set)
    }

    /// The collider set the resolver sweeps against.
    pub(crate) fn set(&self) -> &ColliderSet {
        &self.0
    }
}

/// Build the whole static collider set from the same placement data the
/// scene spawns: the room shell, every pod's construction solids through
/// the pod group's world transform, and the hatch group, in that fixed
/// insertion order (the order the resolver's index reports name).
///
/// # Errors
/// Propagates [`ColliderError`] if a placement derived a non-finite or
/// degenerate box, which the frozen placement data cannot produce; the
/// scene build fails at boot rather than running with a partial set.
pub(crate) fn scene_collider_set(registry: &PodRegistry) -> Result<ColliderSet, ColliderError> {
    let mut set = ColliderSet::new();
    for placement in room_shell() {
        insert_placement(&mut set, &placement, Quat::IDENTITY, Vec3::ZERO)?;
    }
    for pod in registry.pods() {
        let (rotation, translation) = pod_world_transform(pod.placement());
        for solid in pod_solids(pod.state()) {
            insert_pod_solid(&mut set, &solid, rotation, translation)?;
        }
    }
    for placement in hatch_solids() {
        insert_placement(&mut set, &placement, Quat::IDENTITY, Vec3::ZERO)?;
    }
    Ok(set)
}

/// Insert one world-frame placement as a collider box, through an optional
/// parent transform (the hatch group sits at the identity).
fn insert_placement(
    set: &mut ColliderSet,
    placement: &SolidPlacement,
    parent_rotation: Quat,
    parent_translation: Vec3,
) -> Result<(), ColliderError> {
    let rotation = parent_rotation * placement.rotation;
    let center = parent_rotation * placement.center + parent_translation;
    insert_box(set, center, placement.size, rotation)
}

/// Insert one pod-local construction solid through the pod group's world
/// transform: the group yaw carries the local frame into the room, and the
/// solid's local roll composes inside it.
fn insert_pod_solid(
    set: &mut ColliderSet,
    solid: &PodSolid,
    group_rotation: Quat,
    group_translation: Vec3,
) -> Result<(), ColliderError> {
    let rotation = group_rotation * Quat::from_rotation_x(solid.roll_radians);
    let center = group_rotation * solid.center + group_translation;
    insert_box(set, center, solid.size, rotation)
}

/// The conservative world AABB of one placed box: the hull of its eight
/// transformed corners, inserted into the set. Exact for axis-aligned
/// rotations; a tight conservative hull otherwise.
fn insert_box(
    set: &mut ColliderSet,
    center: Vec3,
    size: Vec3,
    rotation: Quat,
) -> Result<(), ColliderError> {
    let half = size * 0.5;
    let mut min = Vec3::splat(f32::INFINITY);
    let mut max = Vec3::splat(f32::NEG_INFINITY);
    for x in [-1.0, 1.0] {
        for y in [-1.0, 1.0] {
            for z in [-1.0, 1.0] {
                let corner = center + rotation * (Vec3::new(x, y, z) * half);
                min = min.min(corner);
                max = max.max(corner);
            }
        }
    }
    let aabb = Aabb::from_min_max(min, max)?;
    set.insert(aabb);
    Ok(())
}

/// Coverage of the collider derivation: the pinned box count, the
/// placement-derived geometry of named boxes, and the authored exit
/// aperture staying clear of every collider.
#[cfg(test)]
mod tests {
    use bevy::app::TaskPoolPlugin;
    use bevy::asset::{AssetApp, AssetPlugin};
    use bevy::math::Vec3;
    use bevy::mesh::Mesh;
    use bevy::pbr::StandardMaterial;
    use gone_sim::pods::{POD_LENGTH, POD_WIDTH};
    use gone_sim::{Aabb, PodRegistry};

    use super::super::StasisScenePlugin;
    use super::{SimColliders, pod_solids, scene_collider_set};
    use crate::scene::placement::{FRAME_DEPTH, HATCH_FRAME_X, hatch_solids, room_shell};
    use crate::scene::pod_body::{CAVITY_WALL, TRAY_FLOOR_Y};

    /// The pinned static box count: six shell slabs, one box per pod
    /// construction solid (6+7+6+7+6+7+6 across the two rows' states),
    /// and five hatch pieces.
    const PINNED_BOX_COUNT: usize = 56;

    /// A test app with the asset stores the scene build needs and the
    /// scene plugin itself. No renderer: the colliders are pure data.
    fn scene_app() -> bevy::app::App {
        let mut app = bevy::app::App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app.init_asset::<Mesh>().init_asset::<StandardMaterial>();
        app.add_plugins(StasisScenePlugin);
        app
    }

    /// Per-component closeness at the codebase's position tolerance.
    fn assert_close(actual: Vec3, expected: Vec3, label: &str) {
        let drift = (actual - expected).abs();
        assert!(
            drift.x < 1e-5 && drift.y < 1e-5 && drift.z < 1e-5,
            "{label}: expected {expected:?}, got {actual:?}"
        );
    }

    /// The set holds exactly the pinned box count, and the resource the
    /// plugin inserts is the same derivation the builder produces: one
    /// construction path, pinned.
    #[test]
    fn the_collider_resource_carries_the_pinned_box_count() {
        let mut app = scene_app();
        app.update();
        let resource = app.world().resource::<SimColliders>();
        assert_eq!(resource.set().len(), PINNED_BOX_COUNT);
        let rebuilt = scene_collider_set(&PodRegistry::frozen()).expect("the frozen set derives");
        assert_eq!(
            resource.set(),
            &rebuilt,
            "the resource is the builder's set"
        );
    }

    /// Named boxes carry their placements' geometry: the floor slab tops
    /// out exactly at the room floor, the player pod's base slab sits at
    /// its registry placement, and the hatch frame stands on the +X wall.
    #[test]
    fn named_boxes_derive_from_their_placements() {
        let registry = PodRegistry::frozen();
        let set = scene_collider_set(&registry).expect("the frozen set derives");
        let boxes = set.boxes();

        let floor = boxes[0];
        assert_close(floor.min(), Vec3::new(-6.2, -0.2, -4.2), "floor min");
        assert_close(floor.max(), Vec3::new(6.2, 0.0, 4.2), "floor max");

        // The player pod (id 6) closes the pod run: its base slab is the
        // first box after the other six pods' solids, before the hatch.
        let before_player: usize = registry
            .pods()
            .iter()
            .take_while(|pod| !pod.state().is_player())
            .map(|pod| pod_solids(pod.state()).len())
            .sum();
        let base = boxes[room_shell().len() + before_player];
        assert_close(
            base.center(),
            Vec3::new(-4.8, 0.05, 2.9),
            "player base center",
        );
        assert_close(
            base.half_extents(),
            Vec3::new(POD_WIDTH / 2.0, 0.05, POD_LENGTH / 2.0),
            "player base half extents",
        );

        let first_post = boxes[PINNED_BOX_COUNT - hatch_solids().len()];
        assert_close(
            first_post.center(),
            Vec3::new(
                HATCH_FRAME_X,
                f32::midpoint(2.4, 0.16),
                -f32::midpoint(1.2, 0.16),
            ),
            "hatch -Z post center",
        );
        assert_close(
            first_post.half_extents(),
            Vec3::new(FRAME_DEPTH / 2.0, 1.28, 0.08),
            "hatch -Z post half extents",
        );
    }

    /// The authored exit aperture stays clear: no collider reaches into
    /// the mouth strip the walk-through crosses (between the side walls'
    /// foot-end line and the pod's foot face, from the tray floor up past
    /// standing head height), so the get-up beat the sim authored is
    /// walkable against the real set. Regression: the foot-mounted status
    /// plate would block the mouth. The strip's near line sits a hundredth
    /// inside the walls' exact foot-end face, because overlap is inclusive
    /// of touching faces and the walls end exactly on it.
    #[test]
    fn the_exit_aperture_mouth_stays_clear_of_every_collider() {
        let registry = PodRegistry::frozen();
        let set = scene_collider_set(&registry).expect("the frozen set derives");
        let player = registry.player_pod().placement();
        let (sin, cos) = player.yaw_radians.sin_cos();
        let to_world = |local: Vec3| {
            Vec3::new(
                player.center.0 + local.x * cos + local.z * sin,
                local.y,
                player.center.1 - local.x * sin + local.z * cos,
            )
        };
        let mouth_start = POD_LENGTH / 2.0 - CAVITY_WALL + 0.01;
        let near = to_world(Vec3::new(-POD_WIDTH / 2.0, TRAY_FLOOR_Y, mouth_start));
        let far = to_world(Vec3::new(POD_WIDTH / 2.0, 1.9, POD_LENGTH / 2.0));
        let strip = Aabb::from_min_max(near.min(far), near.max(far))
            .expect("the mouth strip is a valid box");
        let overlappers: Vec<usize> = set.overlapping(&strip).map(|(index, _)| index).collect();
        assert!(
            overlappers.is_empty(),
            "nothing may stand in the exit mouth: boxes {overlappers:?}"
        );
    }
}
