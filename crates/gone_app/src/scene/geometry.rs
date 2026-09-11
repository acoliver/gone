//! Greybox geometry for the stasis room (issue #7 stage A).
//!
//! Every shape here is a bevy 3D primitive: cuboids for the room shell,
//! pod bodies, lids, trays, hatch, and plates; toruses for the hanging
//! wire loops. Flat grey `StandardMaterial`s at fixed shades keep the
//! blockout readable without any asset loading. All pod and hatch
//! positions derive from the `gone_sim` registry: this module never
//! hard-codes a pod placement.

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
use gone_sim::pods::{POD_HEIGHT, POD_LENGTH, ROOM_CEILING_HEIGHT, ROOM_LENGTH, ROOM_WIDTH};
use gone_sim::{POD_COUNT, Pod, PodRegistry, PodState};

use super::pod_body::{SolidKind, pod_solids};
use super::{PodMirrors, StasisPod};

/// Shell wall and floor slab thickness, in meters.
const WALL_THICKNESS: f32 = 0.2;

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

/// The status indicator plate, in meters, and its standoff from the pod's
/// foot face plus its mount height.
const PLATE_WIDTH: f32 = 0.2;
const PLATE_HEIGHT: f32 = 0.1;
const PLATE_THICKNESS: f32 = 0.04;
const PLATE_STANDOFF: f32 = 0.02;
const PLATE_MOUNT_HEIGHT: f32 = 0.55;

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

/// Cable tray cross-section, in meters, and the drop of the tray center
/// line below the ceiling.
const TRAY_WIDTH: f32 = 0.3;
const TRAY_HEIGHT: f32 = 0.08;
const TRAY_CEILING_DROP: f32 = 0.15;

/// Hanging wire loop torus size, in meters.
const WIRE_INNER_RADIUS: f32 = 0.035;
const WIRE_OUTER_RADIUS: f32 = 0.11;

/// The hatch opening's size, in meters, and the frame pieces around it.
const HATCH_WIDTH: f32 = 1.2;
const HATCH_HEIGHT: f32 = 2.4;
const FRAME_DEPTH: f32 = 0.18;
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

/// X of the hatch frame's center plane: protruding
/// [`FRAME_DEPTH`] from the wall's inner face.
const HATCH_FRAME_X: f32 = ROOM_LENGTH / 2.0 - FRAME_DEPTH / 2.0;

/// X of the hatch door slab's center plane: recessed behind the frame's
/// front face.
const HATCH_DOOR_X: f32 = ROOM_LENGTH / 2.0 - DOOR_RECESS;

/// One torn cable tray: a long thin box just under the ceiling, tipped off
/// level by `roll_radians` about its run axis (X runs, or Z runs when
/// `yaw_radians` turns the box).
struct TraySpec {
    /// World center of the tray box.
    center: Vec3,
    /// Full box size along world axes before yaw and roll.
    size: Vec3,
    /// Yaw about +Y applied before the roll (a quarter turn makes a Z run).
    yaw_radians: f32,
    /// Roll about the tray's run axis, tipping it off level.
    roll_radians: f32,
}

/// The torn ceiling: trays concentrated over the room center per the
/// story's wounded ceiling, with a junction of runs and one stub toward
/// the player row.
const TORN_TRAYS: [TraySpec; 3] = [
    TraySpec {
        center: Vec3::new(-0.5, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP, 0.35),
        size: Vec3::new(6.0, TRAY_HEIGHT, TRAY_WIDTH),
        yaw_radians: 0.0,
        roll_radians: 0.06,
    },
    TraySpec {
        center: Vec3::new(0.9, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP - 0.04, -0.7),
        size: Vec3::new(4.5, TRAY_HEIGHT, TRAY_WIDTH),
        yaw_radians: core::f32::consts::FRAC_PI_2,
        roll_radians: -0.04,
    },
    TraySpec {
        center: Vec3::new(1.6, ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP + 0.05, 1.1),
        size: Vec3::new(3.0, TRAY_HEIGHT, TRAY_WIDTH),
        yaw_radians: 0.0,
        roll_radians: -0.09,
    },
];

/// Hanging wire loops: positions over the room center with a per-loop yaw
/// so the toruses do not read as one stamped ring.
const WIRE_LOOPS: [(Vec3, f32); 5] = [
    (Vec3::new(-1.3, 2.7, 0.5), 0.4),
    (Vec3::new(-0.4, 2.55, 0.2), 1.3),
    (Vec3::new(0.3, 2.78, -0.5), 2.2),
    (Vec3::new(1.1, 2.62, 0.8), 0.9),
    (Vec3::new(2.0, 2.5, -0.2), 2.9),
];

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

/// Spawn one cuboid child under `parent` at `transform` with the given
/// handles. Mesh primitives are centered on their entity, so `transform`
/// is the box center.
fn box_child(
    parent: &mut ChildSpawnerCommands<'_>,
    mesh: Handle<Mesh>,
    material: Handle<StandardMaterial>,
    transform: Transform,
) {
    parent.spawn((Mesh3d(mesh), MeshMaterial3d(material), transform));
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
    let slab = Vec3::new(
        ROOM_LENGTH + 2.0 * WALL_THICKNESS,
        WALL_THICKNESS,
        ROOM_WIDTH + 2.0 * WALL_THICKNESS,
    );
    commands.spawn((
        Mesh3d(meshes.add(Cuboid::new(slab.x, slab.y, slab.z))),
        MeshMaterial3d(floor),
        Transform::from_translation(Vec3::new(0.0, -WALL_THICKNESS / 2.0, 0.0)),
    ));
    commands.spawn((
        Mesh3d(meshes.add(Cuboid::new(slab.x, slab.y, slab.z))),
        MeshMaterial3d(ceiling),
        Transform::from_translation(Vec3::new(
            0.0,
            ROOM_CEILING_HEIGHT + WALL_THICKNESS / 2.0,
            0.0,
        )),
    ));
    for sign_z in [-1.0, 1.0] {
        commands.spawn((
            Mesh3d(meshes.add(Cuboid::new(
                ROOM_LENGTH + 2.0 * WALL_THICKNESS,
                ROOM_CEILING_HEIGHT,
                WALL_THICKNESS,
            ))),
            MeshMaterial3d(wall.clone()),
            Transform::from_translation(Vec3::new(
                0.0,
                ROOM_CEILING_HEIGHT / 2.0,
                sign_z * (ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0),
            )),
        ));
    }
    for sign_x in [-1.0, 1.0] {
        commands.spawn((
            Mesh3d(meshes.add(Cuboid::new(WALL_THICKNESS, ROOM_CEILING_HEIGHT, ROOM_WIDTH))),
            MeshMaterial3d(wall.clone()),
            Transform::from_translation(Vec3::new(
                sign_x * (ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0),
                ROOM_CEILING_HEIGHT / 2.0,
                0.0,
            )),
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
        commands
            .spawn((
                StasisPod,
                Transform::from_translation(Vec3::new(placement.center.0, 0.0, placement.center.1))
                    .with_rotation(Quat::from_rotation_y(placement.yaw_radians)),
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
        let transform = Transform::from_translation(solid.center)
            .with_rotation(Quat::from_rotation_x(solid.roll_radians));
        box_child(
            parent,
            meshes.add(Cuboid::new(solid.size.x, solid.size.y, solid.size.z)),
            materials.add(flat_grey(solid_shade(solid.kind))),
            transform,
        );
    }
    box_child(
        parent,
        meshes.add(Cuboid::new(PLATE_WIDTH, PLATE_HEIGHT, PLATE_THICKNESS)),
        indicator,
        Transform::from_translation(Vec3::new(
            0.0,
            PLATE_MOUNT_HEIGHT,
            POD_LENGTH / 2.0 + PLATE_STANDOFF,
        )),
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
    for spec in TORN_TRAYS {
        let rotation =
            Quat::from_rotation_y(spec.yaw_radians) * Quat::from_rotation_x(spec.roll_radians);
        commands.spawn((
            Mesh3d(meshes.add(Cuboid::new(spec.size.x, spec.size.y, spec.size.z))),
            MeshMaterial3d(tray.clone()),
            Transform::from_translation(spec.center).with_rotation(rotation),
        ));
    }
    for (center, swing_radians) in WIRE_LOOPS {
        // A quarter turn tips the torus from face-up to hanging vertical;
        // the yaw varies the loop planes so they read as separate strands.
        let rotation = Quat::from_rotation_x(core::f32::consts::FRAC_PI_2)
            * Quat::from_rotation_y(swing_radians);
        commands.spawn((
            Mesh3d(meshes.add(Torus::new(WIRE_INNER_RADIUS, WIRE_OUTER_RADIUS))),
            MeshMaterial3d(wire.clone()),
            Transform::from_translation(center).with_rotation(rotation),
        ));
    }
}

/// Spawn the jammed hatch on the +X short wall: a frame protruding from
/// the wall around a recessed door slab that leans ajar into the room.
/// Static dressing; the door beat is issue #11's.
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
            hatch_frame_posts(parent, meshes, &frame);
            hatch_frame_lintel_and_sill(parent, meshes, frame);
            hatch_ajar_door(parent, meshes, door);
        });
}

/// The frame's two posts flanking the opening, each spanning the opening's
/// full height plus its own width so the lintel caps it flush.
fn hatch_frame_posts(
    parent: &mut ChildSpawnerCommands<'_>,
    meshes: &mut Assets<Mesh>,
    frame: &Handle<StandardMaterial>,
) {
    for sign_z in [-1.0, 1.0] {
        box_child(
            parent,
            meshes.add(Cuboid::new(
                FRAME_DEPTH,
                HATCH_HEIGHT + FRAME_POST_WIDTH,
                FRAME_POST_WIDTH,
            )),
            frame.clone(),
            Transform::from_translation(Vec3::new(
                HATCH_FRAME_X,
                f32::midpoint(HATCH_HEIGHT, FRAME_POST_WIDTH),
                sign_z * f32::midpoint(HATCH_WIDTH, FRAME_POST_WIDTH),
            )),
        );
    }
}

/// The frame's lintel over the opening and its sill under it, spanning the
/// posts' outer width so the frame reads as one piece.
fn hatch_frame_lintel_and_sill(
    parent: &mut ChildSpawnerCommands<'_>,
    meshes: &mut Assets<Mesh>,
    frame: Handle<StandardMaterial>,
) {
    box_child(
        parent,
        meshes.add(Cuboid::new(
            FRAME_DEPTH,
            FRAME_POST_WIDTH,
            HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH,
        )),
        frame.clone(),
        Transform::from_translation(Vec3::new(
            HATCH_FRAME_X,
            HATCH_HEIGHT + FRAME_POST_WIDTH / 2.0,
            0.0,
        )),
    );
    box_child(
        parent,
        meshes.add(Cuboid::new(
            FRAME_DEPTH,
            SILL_HEIGHT,
            HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH,
        )),
        frame,
        Transform::from_translation(Vec3::new(HATCH_FRAME_X, SILL_HEIGHT / 2.0, 0.0)),
    );
}

/// The door slab, hung from its hinge edge at the frame's -Z jamb and
/// leaning ajar into the room: negative yaw swings the free edge toward
/// -X. The slab mesh is centered on its entity, hence the child offset.
fn hatch_ajar_door(
    parent: &mut ChildSpawnerCommands<'_>,
    meshes: &mut Assets<Mesh>,
    door: Handle<StandardMaterial>,
) {
    parent
        .spawn((
            Transform::from_translation(Vec3::new(
                HATCH_DOOR_X,
                0.0,
                -(HATCH_WIDTH / 2.0 - DOOR_HINGE_INSET),
            ))
            .with_rotation(Quat::from_rotation_y(-HATCH_DOOR_AJAR)),
            // The slab child inherits visibility (bevy warning B0004).
            Visibility::default(),
        ))
        .with_children(|slab| {
            box_child(
                slab,
                meshes.add(Cuboid::new(DOOR_THICKNESS, DOOR_HEIGHT, DOOR_WIDTH)),
                door,
                Transform::from_translation(Vec3::new(0.0, DOOR_HEIGHT / 2.0, DOOR_WIDTH / 2.0)),
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

    use super::{FRAME_DEPTH, HATCH_DOOR_X, HATCH_FRAME_X};

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
