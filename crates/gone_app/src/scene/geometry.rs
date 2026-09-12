//! Greybox geometry for the stasis room (issue #7 stage A).
//!
//! Every shape here is a bevy 3D primitive: cuboids for the room shell,
//! pod bodies, lids, trays, hatch, and plates; toruses for the hanging
//! wire loops. Flat grey `StandardMaterial`s at fixed shades keep the
//! blockout readable without any asset loading. All pod and hatch
//! positions derive from the `gone_sim` registry: this module never
//! hard-codes a pod placement. The static pieces (room shell, hatch,
//! trays, wires, indicator plate) spawn verbatim from the pure placements
//! in `placement`, the same data the collider set is derived from.

use bevy::asset::{Assets, Handle};
use bevy::camera::visibility::Visibility;
use bevy::color::{Color, LinearRgba};
use bevy::ecs::hierarchy::ChildSpawnerCommands;
use bevy::ecs::prelude::Commands;
use bevy::light::PointLight;
use bevy::math::primitives::{Cuboid, Torus};
use bevy::math::{Quat, Vec3};
use bevy::mesh::{Mesh, Mesh3d};
use bevy::pbr::{MeshMaterial3d, StandardMaterial};
use bevy::transform::components::Transform;
use gone_sim::pods::{POD_HEIGHT, POD_LENGTH};
use gone_sim::{POD_COUNT, Pod, PodRegistry, PodState};

use super::pod_body::{SolidKind, pod_solids};
use super::{PodMirrors, StasisPod};
use crate::scene::placement::{
    SolidPlacement, WIRE_INNER_RADIUS, WIRE_OUTER_RADIUS, WireLoop, cable_trays, hatch_solids,
    indicator_plate, pod_world_transform, room_shell, wire_loops,
};

/// Grey shades for the flat greybox materials, in linear-ish srgb terms.
const FLOOR_SHADE: f32 = 0.32;
const WALL_SHADE: f32 = 0.4;
const CEILING_SHADE: f32 = 0.26;
const POD_BODY_SHADE: f32 = 0.45;
const POD_LID_SHADE: f32 = 0.42;
const POD_CAVITY_SHADE: f32 = 0.05;
const BLANKET_SHADE: f32 = 0.55;
const TRAY_SHADE: f32 = 0.24;
const WIRE_SHADE: f32 = 0.18;
const HATCH_FRAME_SHADE: f32 = 0.33;
const HATCH_DOOR_SHADE: f32 = 0.38;

/// Emissive color of a lit status indicator: a warm white that reads as
/// powered at greybox fidelity.
pub(super) const INDICATOR_LIT_EMISSIVE: LinearRgba = LinearRgba::rgb(2.6, 2.3, 1.9);

/// Ambient light level for the greybox: dim, so the pod interior light and
/// the fill light read against it.
pub(super) const AMBIENT_BRIGHTNESS: f32 = 20.0;

/// The player pod's interior light: a small, low, close-range source just
/// outside the open face, so the open interior reads as slightly lit.
const POD_LIGHT_LUMENS: f32 = 12.0;
const POD_LIGHT_RANGE: f32 = 2.6;
const POD_LIGHT_STANDOFF: f32 = 0.35;
const POD_LIGHT_RISE: f32 = 0.2;

/// The room-center fill light: enough for the greybox to read while the
/// wrecked ceiling stays dim overhead.
const FILL_LIGHT_LUMENS: f32 = 40.0;
const FILL_LIGHT_RANGE: f32 = 9.0;
const FILL_LIGHT_HEIGHT: f32 = 2.8;

/// A flat grey `StandardMaterial` at `shade`, fully rough so the greybox
/// reads as untextured mass under any light.
fn flat_grey(shade: f32) -> StandardMaterial {
    StandardMaterial {
        base_color: Color::srgb(shade, shade, shade),
        perceptual_roughness: 0.95,
        ..StandardMaterial::default()
    }
}

/// The status indicator material: lit pods glow warm white, dead pods are
/// dark grey with no emissive at all.
fn indicator_material(lit: bool) -> StandardMaterial {
    let shade = if lit { 0.36 } else { 0.08 };
    StandardMaterial {
        base_color: Color::srgb(shade, shade, shade),
        emissive: if lit {
            INDICATOR_LIT_EMISSIVE
        } else {
            LinearRgba::BLACK
        },
        perceptual_roughness: 0.6,
        ..StandardMaterial::default()
    }
}

/// The spawn transform for one placed solid: meshes are centered on their
/// entity, so the placement center is the translation.
fn placement_transform(placement: &SolidPlacement) -> Transform {
    Transform::from_translation(placement.center).with_rotation(placement.rotation)
}

/// Spawn one cuboid child under `parent` for `placement` with the given
/// handles.
fn box_child(
    parent: &mut ChildSpawnerCommands<'_>,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    placement: &SolidPlacement,
) {
    parent.spawn((
        Mesh3d(mesh),
        MeshMaterial3d(material),
        placement_transform(placement),
    ));
}

/// Spawn the room shell: floor slab, ceiling slab, and four walls at the
/// registry's room scale, so the playable interior is exactly
/// `ROOM_LENGTH` by `ROOM_WIDTH` with its ceiling at
/// [`gone_sim::pods::ROOM_CEILING_HEIGHT`].
pub(super) fn spawn_room_shell(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    let floor = materials.add(flat_grey(FLOOR_SHADE));
    let wall = materials.add(flat_grey(WALL_SHADE));
    let ceiling = materials.add(flat_grey(CEILING_SHADE));
    for (index, placement) in room_shell().into_iter().enumerate() {
        let material = match index {
            0 => floor.clone(),
            1 => ceiling.clone(),
            _ => wall.clone(),
        };
        commands.spawn((
            Mesh3d(meshes.add(Cuboid::new(
                placement.size.x,
                placement.size.y,
                placement.size.z,
            ))),
            MeshMaterial3d(material),
            placement_transform(&placement),
        ));
    }
}

/// Spawn one pod group per registry pod at its registry placement. Returns
/// each pod's dedicated indicator material handle, indexed by pod id, so
/// the sync system can keep the lit states honest.
pub(super) fn spawn_pods(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    registry: &PodRegistry,
    mirrors: &PodMirrors,
) -> [Handle<StandardMaterial>; POD_COUNT] {
    let handles: [Handle<StandardMaterial>; POD_COUNT] = std::array::from_fn(|index| {
        materials.add(indicator_material(mirrors.pods[index].indicator_lit))
    });
    for pod in registry.pods() {
        let placement = pod.placement();
        let (rotation, translation) = pod_world_transform(placement);
        commands
            .spawn((
                StasisPod,
                Transform::from_translation(translation).with_rotation(rotation),
                Visibility::default(),
            ))
            .with_children(|parent| {
                fill_pod(
                    parent,
                    meshes,
                    materials,
                    pod.state(),
                    handles[pod.id().index()].clone(),
                );
            });
    }
    handles
}

/// Fill one pod group's children in the pod's local frame: the pure
/// construction solids for its state (`pod_body::pod_solids`, spawned
/// verbatim) and the foot-mounted indicator plate.
fn fill_pod(
    parent: &mut ChildSpawnerCommands<'_>,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
    state: PodState,
    indicator: Handle<StandardMaterial>,
) {
    for solid in pod_solids(state) {
        parent.spawn((
            Mesh3d(meshes.add(Cuboid::new(solid.size.x, solid.size.y, solid.size.z))),
            MeshMaterial3d(materials.add(flat_grey(solid_shade(solid.kind)))),
            Transform::from_translation(solid.center)
                .with_rotation(Quat::from_rotation_x(solid.roll_radians)),
        ));
    }
    let plate = indicator_plate();
    box_child(
        parent,
        meshes.add(Cuboid::new(plate.size.x, plate.size.y, plate.size.z)),
        indicator,
        &plate,
    );
}

/// The grey shade for one construction solid kind.
fn solid_shade(kind: SolidKind) -> f32 {
    match kind {
        SolidKind::Body => POD_BODY_SHADE,
        SolidKind::Cavity => POD_CAVITY_SHADE,
        SolidKind::Lid => POD_LID_SHADE,
        SolidKind::Blanket => BLANKET_SHADE,
    }
}

/// Spawn the torn ceiling: cable tray runs concentrated over the room
/// center, each tipped off level, with hanging wire loops beneath them.
pub(super) fn spawn_ceiling_damage(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    let tray = materials.add(flat_grey(TRAY_SHADE));
    let wire = materials.add(flat_grey(WIRE_SHADE));
    for placement in cable_trays() {
        commands.spawn((
            Mesh3d(meshes.add(Cuboid::new(
                placement.size.x,
                placement.size.y,
                placement.size.z,
            ))),
            MeshMaterial3d(tray.clone()),
            placement_transform(&placement),
        ));
    }
    for WireLoop { center, rotation } in wire_loops() {
        commands.spawn((
            Mesh3d(meshes.add(Torus::new(WIRE_INNER_RADIUS, WIRE_OUTER_RADIUS))),
            MeshMaterial3d(wire.clone()),
            Transform::from_translation(center).with_rotation(rotation),
        ));
    }
}

/// How many of the hatch group's pieces are frame (posts, lintel, sill);
/// the last piece is the ajar door slab.
const HATCH_FRAME_PIECES: usize = 4;

/// Spawn the jammed hatch on the +X short wall: a frame protruding from
/// the wall around a recessed door slab that leans ajar into the room.
/// Static dressing; the door beat is issue #11's. All five pieces spawn
/// verbatim from `placement::hatch_solids`, the same data the collider set
/// is derived from.
pub(super) fn spawn_hatch(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    let frame = materials.add(flat_grey(HATCH_FRAME_SHADE));
    let door = materials.add(flat_grey(HATCH_DOOR_SHADE));
    commands
        .spawn((
            super::JammedHatch,
            Transform::IDENTITY,
            Visibility::default(),
        ))
        .with_children(|parent| {
            let solids = hatch_solids();
            let (frame_pieces, door_piece) = solids.split_at(HATCH_FRAME_PIECES);
            for placement in frame_pieces {
                box_child(
                    parent,
                    meshes.add(Cuboid::new(
                        placement.size.x,
                        placement.size.y,
                        placement.size.z,
                    )),
                    frame.clone(),
                    placement,
                );
            }
            let door_placement = &door_piece[0];
            box_child(
                parent,
                meshes.add(Cuboid::new(
                    door_placement.size.x,
                    door_placement.size.y,
                    door_placement.size.z,
                )),
                door,
                door_placement,
            );
        });
}

/// Spawn the player pod's interior light just outside the pod's open face:
/// the open interior reads as slightly lit, the rest of the bay stays dim.
pub(super) fn spawn_pod_interior_light(commands: &mut Commands, pod: &Pod) {
    let placement = pod.placement();
    let facing = Vec3::new(
        placement.yaw_radians.sin(),
        0.0,
        placement.yaw_radians.cos(),
    );
    let position = Vec3::new(placement.center.0, 0.0, placement.center.1)
        + facing * (POD_LENGTH / 2.0 + POD_LIGHT_STANDOFF)
        + Vec3::Y * (POD_HEIGHT + POD_LIGHT_RISE);
    commands.spawn((
        PointLight {
            intensity: POD_LIGHT_LUMENS,
            range: POD_LIGHT_RANGE,
            ..PointLight::default()
        },
        Transform::from_translation(position),
    ));
}

/// Spawn the room-center fill light under the torn ceiling: dim, wide, and
/// only there so the greybox reads at all.
pub(super) fn spawn_fill_light(commands: &mut Commands) {
    commands.spawn((
        PointLight {
            intensity: FILL_LIGHT_LUMENS,
            range: FILL_LIGHT_RANGE,
            ..PointLight::default()
        },
        Transform::from_translation(Vec3::new(0.0, FILL_LIGHT_HEIGHT, 0.0)),
    ));
}

/// App-side coverage of the geometry derivation: pod body boxes stay
/// inside the room and clear the frozen aisle band, and the hatch
/// placement is on the correct wall.
#[cfg(test)]
mod tests {
    use gone_sim::controller::POD_EXIT_CLEARANCE;
    use gone_sim::pods::{AISLE_HALF_WIDTH, POD_LENGTH, POD_WIDTH, ROOM_LENGTH, ROOM_WIDTH};
    use gone_sim::{PodId, PodRegistry};

    use crate::scene::placement::{FRAME_DEPTH, HATCH_DOOR_X, HATCH_FRAME_X};

    /// The pod body boxes derived from registry placements are axis-aligned
    /// (the frozen yaws are 0 and pi), inside the room, and stop short of
    /// the frozen aisle band by at least the frozen exit clearance.
    #[test]
    fn pod_boxes_stay_in_the_room_and_clear_the_aisle() {
        let registry = PodRegistry::frozen();
        for pod in registry.pods() {
            let placement = pod.placement();
            let (x, z) = placement.center;
            assert!(
                x.abs() + POD_WIDTH / 2.0 <= ROOM_LENGTH / 2.0,
                "pod {} inside the long axis",
                pod.id().index()
            );
            assert!(
                z.abs() + POD_LENGTH / 2.0 <= ROOM_WIDTH / 2.0,
                "pod {} inside the short axis",
                pod.id().index()
            );
            let aisle_face = z.abs() - POD_LENGTH / 2.0;
            assert!(
                aisle_face >= AISLE_HALF_WIDTH + POD_EXIT_CLEARANCE,
                "pod {} clears the aisle band",
                pod.id().index()
            );
        }
    }

    /// The app's frozen hatch constants sit on the +X wall, recessed
    /// behind the frame front, and the frame protrudes into the room from
    /// the wall face.
    #[test]
    fn hatch_constants_sit_on_the_plus_x_wall() {
        // Pure-constant relations are pinned at compile time; the runtime
        // asserts below tie the same constants to the registry's values.
        const { assert!(HATCH_DOOR_X < ROOM_LENGTH / 2.0) };
        let registry = PodRegistry::frozen();
        let hatch = registry.hatch();
        assert!(
            (hatch.center.0 - ROOM_LENGTH / 2.0).abs() < 1e-6,
            "the registry puts the hatch on the +X wall"
        );
        let frame_front = HATCH_FRAME_X - FRAME_DEPTH / 2.0;
        assert!(
            frame_front < ROOM_LENGTH / 2.0,
            "the frame protrudes from the wall face into the room"
        );
        assert!(
            HATCH_DOOR_X > frame_front,
            "the door sits recessed behind the frame front"
        );
        // The frame's center plane matches the registry's hatch center.
        assert!((HATCH_FRAME_X + FRAME_DEPTH / 2.0 - hatch.center.0).abs() < 1e-6);
        // The player pod lookup used by the scene build is stable.
        assert_eq!(
            registry.player_pod().id(),
            PodId::ALL[6],
            "the player pod is id 6"
        );
    }
}
