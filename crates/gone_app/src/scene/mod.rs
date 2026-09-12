//! Stasis room greybox scene for the windowed game (issue #7 stage A).
//!
//! Contract: this module builds the opening-beat blockout from primitives in
//! `RunMode::Normal` and in gameplay-content harness runs. The calibration
//! harness lanes never build this plugin, so the calibration scene and every
//! calibration capture stay exactly as they were.
//!
//! The simulation side is authoritative. [`SimWakePhase`] and
//! [`SimPodRegistry`] wrap the `gone_sim` phase machine and the frozen pod
//! registry as resources, and nothing in this module ever writes through
//! them: the wake progression is driven by later briefs (the wake pass is
//! issue #8), and this stage only inserts the contract in its spawn state
//! (`Waking`). A thin sync system ([`sync_pod_scene_state`]) derives the
//! app-side [`PodMirrors`] from the registry and the phase each update and
//! keeps the pod indicator materials honest against that mirror.
//!
//! Geometry is derived from the registry, never hand-placed: pod groups
//! spawn at their registry placements, the jammed hatch sits where the
//! registry says, and the player rig (via `player`) spawns lying in the
//! player pod at the pose [`player_spawn_pose`] returns. Greybox fidelity:
//! flat-shaded greys, one point light at the player pod's open interior,
//! one dim fill light over the torn ceiling, and no asset loading beyond
//! what the post chain already loads.
//!
//! New bevy features were required for this slice and are listed in the
//! app's `Cargo.toml`: `bevy_mesh` (meshes from primitives), `bevy_pbr`
//! (`StandardMaterial` and the PBR pass), and `bevy_light` (light types).

use bevy::app::{App, Plugin, Startup, Update};
use bevy::asset::Assets;
use bevy::color::LinearRgba;
use bevy::ecs::change_detection::DetectChangesMut;
use bevy::ecs::prelude::{Commands, Component, Res, ResMut, Resource};
use bevy::light::GlobalAmbientLight;
use bevy::math::{Quat, Vec3};
use bevy::mesh::Mesh;
use bevy::pbr::StandardMaterial;
use gone_sim::exit::ExitPath;
use gone_sim::{POD_COUNT, PhaseTransition, PodRegistry, WakePhase};

use crate::player::PITCH_LIMIT;
use crate::scene::geometry::{
    AMBIENT_BRIGHTNESS, INDICATOR_LIT_EMISSIVE, spawn_ceiling_damage, spawn_fill_light,
    spawn_hatch, spawn_pod_interior_light, spawn_pods, spawn_room_shell,
};

mod colliders;

mod geometry;

/// Pure world-space placements for every non-pod scene solid.
mod placement;

/// Pure pod construction solids (pod-local). Crate-visible because
/// `placement_truth` builds the shared exit path against the tray floor the
/// cavity build constructs.
pub(crate) mod pod_body;

pub(crate) use colliders::SimColliders;

/// Marks a stasis pod's root entity. A pod's identity, state, and placement
/// live in the sim registry; the marker only tags the scene-side group so
/// tests and the gameplay harness's room observation can find pod groups,
/// and later systems can recognize them.
#[derive(Component)]
pub(crate) struct StasisPod;

/// Marks the jammed hatch group: static dressing this stage; the beat that
/// tries to open it is issue #11's.
#[derive(Component)]
struct JammedHatch;

/// The app's resource over the `gone_sim` wake phase machine. The sim is
/// authoritative: this module reads it and never advances it.
#[derive(Resource)]
pub(crate) struct SimWakePhase(WakePhase);

impl SimWakePhase {
    /// Build the resource at `phase`. Crate-visible so tests and the game
    /// wiring can start the machine at an exact phase.
    pub(crate) const fn new(phase: WakePhase) -> Self {
        Self(phase)
    }

    /// The phase the machine currently sits in.
    pub(crate) fn phase(&self) -> WakePhase {
        self.0
    }

    /// Drive one wake-complete boundary signal through the machine
    /// (`Waking` advances to `AwakeInPod`; re-delivery is a no-op per the
    /// machine's contract). The gameplay harness's readiness override
    /// advances through this signal, and the wake pass's own driver (issue
    /// #8) must advance through it too, behind the readiness barrier.
    #[must_use]
    pub(crate) fn wake_complete(&mut self) -> PhaseTransition {
        self.0.wake_complete()
    }

    /// The machine itself, for systems that drive it through the sim's own
    /// controllers (the get-up controller, the walk state). The app never
    /// writes phases around the controllers; the machine's own typed
    /// contract is the only writer.
    pub(crate) fn machine_mut(&mut self) -> &mut WakePhase {
        &mut self.0
    }
}

/// The app's resource over the `gone_sim` pod registry. The sim is
/// authoritative: this module reads it and never rebuilds it.
#[derive(Resource)]
pub(crate) struct SimPodRegistry(PodRegistry);

impl SimPodRegistry {
    /// The frozen pod registry.
    pub(crate) fn registry(&self) -> &PodRegistry {
        &self.0
    }
}

/// The app-side mirror of one pod's observable sim state.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct PodMirror {
    /// Whether the pod's status indicator plate renders lit.
    indicator_lit: bool,
    /// Whether the pod counts as occupied in the current phase.
    occupied: bool,
}

/// The app-side mirror of the whole registry's observable state, refreshed
/// by [`sync_pod_scene_state`] every update. Rendering reads this; nothing
/// but the sync system writes it.
#[derive(Resource, Clone, Copy, Debug, PartialEq, Eq, Default)]
struct PodMirrors {
    /// Per-pod mirror, indexed by [`PodId::index`].
    pods: [PodMirror; POD_COUNT],
}

/// The indicator material handles for each pod, indexed by
/// [`PodId::index`]. Created by the scene build; consumed by the sync
/// system when a pod's lit state flips.
#[derive(Resource)]
struct PodIndicatorMaterials {
    /// One dedicated material per pod indicator plate.
    handles: [bevy::asset::Handle<StandardMaterial>; POD_COUNT],
}

/// The authored lying spawn: where the player rig starts and how it is
/// aimed. The tests assert against this struct, and `player` builds the rig
/// from exactly one instance of it.
#[derive(Clone, Copy, Debug)]
pub(crate) struct PlayerSpawnPose {
    /// Eye point in world space: inside the player pod, face up.
    pub(crate) eye: Vec3,
    /// Yaw about +Y in radians: the pod's opening direction, so the frame
    /// the wake pass authors continues the pod's orientation.
    pub(crate) yaw_radians: f32,
    /// Pitch about +X in radians: aimed up at the ceiling, one stop short
    /// of the vertical (the same stop look input clamps to).
    pub(crate) pitch_radians: f32,
}

/// Eye height above the pod floor while lying face up: just under the pod
/// wall line of the 0.8 m body. `pod_body`'s ray tests read this, so the
/// authored eye and the geometry guarantees cannot drift apart.
pub(crate) const LYING_EYE_HEIGHT: f32 = 0.62;

/// Distance from the pod center toward the head end (the wall side) where
/// the eye rests: near the head, not centered.
pub(crate) const EYE_FROM_CENTER_TO_HEAD: f32 = 0.55;

/// The authored player rig spawn, computed from the frozen registry at
/// plugin build. `player` consumes this resource to place and aim the rig;
/// its absence there is a wiring error, because game mode always adds both
/// plugins together.
#[derive(Resource, Clone, Copy, Debug)]
pub(crate) struct PlayerSpawn {
    /// The lying-in-the-pod pose the rig starts at.
    pub(crate) pose: PlayerSpawnPose,
}

/// The authored get-up path out of the player pod, built from the frozen
/// registry at plugin build against the tray floor the cavity build
/// actually constructs. `player::motion` consumes it when a get-up intent
/// starts the sim exit controller.
#[derive(Resource, Clone, Copy, Debug)]
pub(crate) struct PlayerExitPath(pub(crate) ExitPath);

/// Adds the stasis room scene to the app: the sim contract resources, the
/// greybox build, and the registry-to-scene sync. Game mode only.
pub struct StasisScenePlugin;

impl Plugin for StasisScenePlugin {
    fn build(&self, app: &mut App) {
        let registry = PodRegistry::frozen();
        let exit_path =
            ExitPath::try_new(registry.player_pod().placement(), pod_body::TRAY_FLOOR_Y)
                .expect("the frozen player pod authors a valid exit path");
        let colliders = colliders::scene_collider_set(&registry)
            .expect("the frozen placement data derives a valid collider set");
        app.insert_resource(SimWakePhase::new(WakePhase::default()))
            .insert_resource(SimPodRegistry(registry))
            .insert_resource(PlayerSpawn {
                pose: player_spawn_pose(&registry),
            })
            .insert_resource(PlayerExitPath(exit_path))
            .insert_resource(SimColliders::new(colliders))
            .init_resource::<PodMirrors>()
            .add_systems(Startup, build_stasis_room)
            .add_systems(Update, sync_pod_scene_state);
    }
}

/// Build the whole greybox once at startup: room shell, the seven pods at
/// their registry placements, the torn ceiling over the room center, the
/// jammed hatch, and the lights. Also seeds the app-side mirror and the
/// indicator material handles the sync system maintains.
fn build_stasis_room(
    mut commands: Commands,
    pods: Res<SimPodRegistry>,
    phase: Res<SimWakePhase>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    commands.insert_resource(GlobalAmbientLight {
        brightness: AMBIENT_BRIGHTNESS,
        ..GlobalAmbientLight::default()
    });
    spawn_room_shell(&mut commands, &mut meshes, &mut materials);
    let registry = pods.into_inner().registry();
    let current_phase = phase.into_inner().phase();
    let mirrors = mirror_pods(registry, current_phase);
    let handles = spawn_pods(
        &mut commands,
        &mut meshes,
        &mut materials,
        registry,
        &mirrors,
    );
    commands.insert_resource(PodIndicatorMaterials { handles });
    commands.insert_resource(mirrors);
    spawn_ceiling_damage(&mut commands, &mut meshes, &mut materials);
    spawn_hatch(&mut commands, &mut meshes, &mut materials);
    spawn_pod_interior_light(&mut commands, registry.player_pod());
    spawn_fill_light(&mut commands);
}

/// Derive the app-side mirror for the whole registry in `phase`: indicators
/// lit only for the player pod, occupancy per the registry's contract.
#[must_use]
fn mirror_pods(registry: &PodRegistry, phase: WakePhase) -> PodMirrors {
    let mut pods = [const {
        PodMirror {
            indicator_lit: false,
            occupied: false,
        }
    }; POD_COUNT];
    for pod in registry.pods() {
        pods[pod.id().index()] = PodMirror {
            indicator_lit: pod.state().is_player(),
            occupied: pod.occupied(phase),
        };
    }
    PodMirrors { pods }
}

/// Keep the app-side mirror and the indicator materials equal to what the
/// sim registry and phase say, right now. The sim resources are read-only
/// here: this system can only converge the scene toward them.
fn sync_pod_scene_state(
    pods: Res<SimPodRegistry>,
    phase: Res<SimWakePhase>,
    mut mirrors: ResMut<PodMirrors>,
    indicators: Res<PodIndicatorMaterials>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let next = mirror_pods(pods.into_inner().registry(), phase.into_inner().phase());
    apply_indicator_materials(
        &mut materials,
        &indicators.into_inner().handles,
        &mirrors,
        &next,
    );
    mirrors.set_if_neq(next);
}

/// Push every indicator whose lit state flipped between `previous` and
/// `next` into its pod's material: emissive when lit, dead black otherwise.
/// Only flipping pods are written, so the assets are not touched on no-op
/// frames.
fn apply_indicator_materials(
    materials: &mut Assets<StandardMaterial>,
    handles: &[bevy::asset::Handle<StandardMaterial>; POD_COUNT],
    previous: &PodMirrors,
    next: &PodMirrors,
) {
    for (index, handle) in handles.iter().enumerate() {
        if previous.pods[index].indicator_lit == next.pods[index].indicator_lit {
            continue;
        }
        let mut material = materials
            .get_mut(handle)
            .expect("indicator materials are created by the scene build before any sync");
        material.emissive = if next.pods[index].indicator_lit {
            INDICATOR_LIT_EMISSIVE
        } else {
            LinearRgba::BLACK
        };
    }
}

/// The player's spawn pose: lying in the player pod at the registry's
/// placement, face up, aimed at the ceiling. The eye sits toward the head
/// end at [`LYING_EYE_HEIGHT`], and the yaw continues the pod's opening
/// direction.
#[must_use]
pub(crate) fn player_spawn_pose(registry: &PodRegistry) -> PlayerSpawnPose {
    let pod = registry.player_pod();
    let placement = pod.placement();
    let rotation = Quat::from_rotation_y(placement.yaw_radians);
    let local_eye = Vec3::new(0.0, LYING_EYE_HEIGHT, -EYE_FROM_CENTER_TO_HEAD);
    let eye = rotation * local_eye + Vec3::new(placement.center.0, 0.0, placement.center.1);
    PlayerSpawnPose {
        eye,
        yaw_radians: placement.yaw_radians,
        pitch_radians: PITCH_LIMIT,
    }
}

#[cfg(test)]
mod tests {
    use bevy::app::TaskPoolPlugin;
    use bevy::asset::{AssetApp, AssetPlugin, Handle};
    use bevy::color::LinearRgba;
    use bevy::ecs::prelude::With;
    use bevy::math::Quat;
    use bevy::mesh::Mesh;
    use bevy::pbr::StandardMaterial;
    use bevy::transform::components::Transform;
    use gone_sim::pods::{POD_HEIGHT, POD_LENGTH, POD_WIDTH};
    use gone_sim::{POD_COUNT, PodId, PodRegistry, PodState, WakePhase};

    use super::placement::{hatch_solids, room_shell};
    use super::pod_body::pod_solids;
    use super::{
        JammedHatch, PodIndicatorMaterials, PodMirrors, SimColliders, SimPodRegistry, SimWakePhase,
        StasisPod, StasisScenePlugin, apply_indicator_materials, mirror_pods, player_spawn_pose,
    };
    use crate::player::PITCH_LIMIT;

    /// A test app with the asset stores the scene build needs and the scene
    /// plugin itself. No renderer: startup only creates meshes, materials,
    /// and entities.
    fn scene_app() -> bevy::app::App {
        let mut app = bevy::app::App::new();
        app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
        app.init_asset::<Mesh>().init_asset::<StandardMaterial>();
        app.add_plugins(StasisScenePlugin);
        app
    }

    /// The registry is the single source of truth: the spawned pod groups
    /// are exactly the registry's placements and yaws, and there are seven.
    /// The two sets are compared as sorted multisets keyed on (x, z): the
    /// marker carries no id, because the registry is the identity truth.
    #[test]
    fn scene_spawns_seven_pods_at_their_registry_placements() {
        let mut app = scene_app();
        app.update();
        let registry = PodRegistry::frozen();
        let mut spawned: Vec<(f32, f32, f32, Quat)> = app
            .world_mut()
            .query_filtered::<&Transform, With<StasisPod>>()
            .iter(app.world())
            .map(|transform| {
                (
                    transform.translation.x,
                    transform.translation.y,
                    transform.translation.z,
                    transform.rotation,
                )
            })
            .collect();
        assert_eq!(spawned.len(), POD_COUNT);
        let mut expected: Vec<(f32, f32, f32, Quat)> = registry
            .pods()
            .iter()
            .map(|pod| {
                let placement = pod.placement();
                (
                    placement.center.0,
                    0.0,
                    placement.center.1,
                    Quat::from_rotation_y(placement.yaw_radians),
                )
            })
            .collect();
        let order = |pod: &(f32, f32, f32, Quat), other: &(f32, f32, f32, Quat)| {
            pod.0.total_cmp(&other.0).then(pod.2.total_cmp(&other.2))
        };
        spawned.sort_by(|a, b| order(a, b));
        expected.sort_by(|a, b| order(a, b));
        for (position, (actual, expected)) in spawned.iter().zip(expected.iter()).enumerate() {
            assert!(
                (actual.0 - expected.0).abs() < 1e-5,
                "pod {position} x offset"
            );
            assert!(actual.1.abs() < 1e-5, "pods sit on the floor");
            assert!(
                (actual.2 - expected.2).abs() < 1e-5,
                "pod {position} z offset"
            );
            assert_eq!(actual.3, expected.3, "pod {position} yaw");
        }
    }

    /// Every pod group carries exactly one mesh child per pure
    /// construction solid plus the indicator plate, matched by placement
    /// to the registry's pod state: the scene spawns `pod_body`'s data
    /// verbatim instead of drawing its own shapes. Regression: pod
    /// construction used to drift between the pure description and the
    /// spawned boxes, which let a cavity rebuild silently change nothing
    /// on screen.
    #[test]
    fn pod_groups_spawn_one_child_per_construction_solid() {
        let mut app = scene_app();
        app.update();
        let registry = PodRegistry::frozen();
        let mut groups = app
            .world_mut()
            .query_filtered::<(&Transform, &bevy::ecs::hierarchy::Children), With<StasisPod>>();
        for (transform, children) in groups.iter(app.world()) {
            let pod = registry
                .pods()
                .iter()
                .find(|pod| {
                    let placement = pod.placement();
                    (placement.center.0 - transform.translation.x).abs() < 1e-5
                        && (placement.center.1 - transform.translation.z).abs() < 1e-5
                })
                .expect("every spawned pod group sits at a registry placement");
            let expected = pod_solids(pod.state()).len() + 1;
            assert_eq!(
                children.len(),
                expected,
                "pod {} spawns its construction solids plus the plate",
                pod.id().index()
            );
        }
        // One construction path pinned both ways: the collider set holds
        // exactly one box per spawned construction solid (the shell, every
        // pod's solids, and the hatch group), so the rendered scene and
        // the swept-collision world are the same numbers.
        let colliders = app.world().resource::<SimColliders>();
        let expected_boxes = room_shell().len()
            + registry
                .pods()
                .iter()
                .map(|pod| pod_solids(pod.state()).len())
                .sum::<usize>()
            + hatch_solids().len();
        assert_eq!(
            colliders.set().len(),
            expected_boxes,
            "one collider box per spawned construction solid"
        );
    }

    /// The spawned hatch group sits where the registry says: on the +X
    /// short wall, spanning the wall's centered opening, with its door
    /// group hinged at the -Z jamb and swung into the room. Regression for
    /// a test that only counted group children and re-asserted registry
    /// constants without ever reading the spawned transforms.
    #[test]
    fn hatch_group_spawns_on_the_registry_short_wall_with_an_ajar_door() {
        let mut app = scene_app();
        app.update();
        let mut hatches = app
            .world_mut()
            .query_filtered::<(bevy::ecs::prelude::Entity, &bevy::ecs::hierarchy::Children), With<JammedHatch>>();
        let (group, children) = hatches
            .single(app.world())
            .expect("exactly one jammed hatch group");
        assert!(
            app.world().get_entity(group).is_ok(),
            "the hatch group entity is alive"
        );
        assert!(
            children.len() >= 4,
            "the frame posts, lintel, sill, and door group are spawned"
        );
        let hatch = PodRegistry::frozen().hatch();
        let mut min_z = f32::INFINITY;
        let mut max_z = f32::NEG_INFINITY;
        let mut ajar_doors = 0usize;
        for child in children {
            let transform = app
                .world()
                .get_entity(*child)
                .expect("hatch child exists")
                .get::<Transform>()
                .expect("hatch children carry transforms");
            // Every piece is at the +X short wall and inside the room
            // (the frame protrudes inward, the door recesses inward).
            assert!(
                transform.translation.x <= hatch.center.0 + f32::EPSILON,
                "no hatch piece pokes outside the wall"
            );
            assert!(
                transform.translation.x > hatch.center.0 - 0.5,
                "every hatch piece sits at the short wall, got x {}",
                transform.translation.x
            );
            assert!(
                transform.translation.y >= 0.0,
                "hatch pieces sit on or above the floor"
            );
            min_z = min_z.min(transform.translation.z);
            max_z = max_z.max(transform.translation.z);
            if transform.rotation != Quat::IDENTITY {
                ajar_doors += 1;
                // The door group hinges at the -Z jamb and leans into the
                // room: negative yaw about Y.
                assert!(
                    transform.translation.z < 0.0,
                    "the door hinges on the -Z jamb, got z {}",
                    transform.translation.z
                );
                assert!(
                    transform.rotation.y < 0.0,
                    "negative yaw swings the free edge into the room"
                );
            }
        }
        assert_eq!(ajar_doors, 1, "exactly one ajar door group");
        // The pieces straddle the hatch's centered z: the opening spans
        // across the wall's center line rather than clumping on one side.
        assert!(
            min_z < hatch.center.1 && max_z > hatch.center.1,
            "the frame straddles the registry's centered opening (z {min_z}..{max_z})"
        );
    }

    /// The spawn pose lies in the player pod, under the lid line, aimed up
    /// at the ceiling, continuing the pod's opening yaw.
    #[test]
    fn spawn_pose_lies_in_the_player_pod_aimed_at_the_ceiling() {
        let registry = PodRegistry::frozen();
        let pose = player_spawn_pose(&registry);
        let placement = registry.player_pod().placement();
        // Eye height: above the pod floor, below the pod silhouette top.
        assert!(pose.eye.y > 0.0, "eye above the pod floor");
        assert!(pose.eye.y < POD_HEIGHT, "eye under the pod lid line");
        // Lying inside the pod's body footprint, toward the head end.
        assert!((pose.eye.x - placement.center.0).abs() < POD_WIDTH / 2.0);
        assert!((pose.eye.z - placement.center.1).abs() < POD_LENGTH / 2.0);
        assert!(
            pose.eye.z.abs() > placement.center.1.abs(),
            "head toward the wall"
        );
        // Aimed at the ceiling, within the look clamp.
        assert!(pose.pitch_radians > core::f32::consts::FRAC_PI_2 * 0.75);
        assert!(pose.pitch_radians <= PITCH_LIMIT + f32::EPSILON);
        // The pose's yaw continues the pod's opening direction.
        assert!((pose.yaw_radians - placement.yaw_radians).abs() < 1e-6);
    }

    /// The mirror follows the registry and the phase: the player pod is
    /// the only lit and only occupied pod from Waking through `ExitingPod`,
    /// and everything vacates at Standing. Non-player occupancy is zero at
    /// the startup phase.
    #[test]
    fn mirror_tracks_the_registry_and_the_phase() {
        let registry = PodRegistry::frozen();
        let waking = mirror_pods(&registry, WakePhase::Waking);
        for (index, mirror) in waking.pods.iter().enumerate() {
            let is_player = registry.pod(PodId::ALL[index]).state().is_player();
            assert_eq!(mirror.indicator_lit, is_player, "indicator for pod {index}");
            assert_eq!(mirror.occupied, is_player, "occupancy for pod {index}");
        }
        assert_eq!(
            waking.pods.iter().filter(|mirror| mirror.occupied).count(),
            registry.occupancy_count(WakePhase::Waking)
        );
        assert!(registry.zero_non_player_occupancy(WakePhase::Waking));
        for phase in [WakePhase::AwakeInPod, WakePhase::ExitingPod] {
            let mirrored = mirror_pods(&registry, phase);
            assert_eq!(
                mirrored
                    .pods
                    .iter()
                    .filter(|mirror| mirror.occupied)
                    .count(),
                1,
                "only the player pod is occupied in {phase:?}"
            );
            assert!(registry.zero_non_player_occupancy(phase));
        }
        let standing = mirror_pods(&registry, WakePhase::Standing);
        assert!(
            !standing.pods[6].occupied,
            "the player pod vacates at Standing"
        );
        assert!(
            standing.pods[6].indicator_lit,
            "the player indicator stays lit"
        );
        assert_eq!(
            standing
                .pods
                .iter()
                .filter(|mirror| mirror.occupied)
                .count(),
            registry.occupancy_count(WakePhase::Standing)
        );
    }

    /// The sync system converges the mirror to the phase without touching
    /// the authoritative sim resources, and the indicator materials carry
    /// the lit state at startup.
    #[test]
    fn sync_converges_the_mirror_and_leaves_the_sim_authoritative() {
        let mut app = scene_app();
        app.update();
        {
            let registry = app.world().resource::<SimPodRegistry>();
            let phase = app.world().resource::<SimWakePhase>();
            assert_eq!(phase.phase(), WakePhase::Waking, "spawn phase is Waking");
            assert!(registry.registry().zero_non_player_occupancy(phase.phase()));
            let mirrors = app.world().resource::<PodMirrors>();
            assert!(
                mirrors.pods[6].occupied,
                "the player pod is occupied at spawn"
            );
            let handles = &app.world().resource::<PodIndicatorMaterials>().handles;
            let materials = app
                .world()
                .resource::<bevy::asset::Assets<StandardMaterial>>();
            let player = materials
                .get(&handles[6])
                .expect("the scene build created the player indicator material");
            assert_eq!(player.emissive, super::geometry::INDICATOR_LIT_EMISSIVE);
            let dead = materials
                .get(&handles[0])
                .expect("the scene build created the pod 0 indicator material");
            assert_eq!(dead.emissive, LinearRgba::BLACK);
        }
        // Advance the sim phase the way the wake pass will, then let the
        // sync system observe it.
        app.world_mut().resource_mut::<SimWakePhase>().0 = WakePhase::Standing;
        app.update();
        let frozen = PodRegistry::frozen();
        {
            let registry = app.world().resource::<SimPodRegistry>();
            assert_eq!(
                registry.registry(),
                &frozen,
                "the app never mutates the sim registry"
            );
            let mirrors = app.world().resource::<PodMirrors>();
            assert!(!mirrors.pods[6].occupied, "the mirror follows the phase");
            assert!(
                mirrors.pods[6].indicator_lit,
                "indicators follow the registry"
            );
        }
    }

    /// The indicator material writer flips emissive exactly for pods whose
    /// lit state changed between the two mirrors, in both directions.
    #[test]
    fn indicator_materials_flip_exactly_for_changed_pods() {
        let mut materials = bevy::asset::Assets::<StandardMaterial>::default();
        let mut handles: [Handle<StandardMaterial>; POD_COUNT] =
            std::array::from_fn(|_| materials.add(StandardMaterial::default()));
        let previous = PodMirrors::default();
        let mut next = previous;
        next.pods[2].indicator_lit = true;
        next.pods[6].indicator_lit = true;
        apply_indicator_materials(&mut materials, &handles, &previous, &next);
        for index in [0usize, 1, 3, 4, 5] {
            let material = materials.get(&handles[index]).expect("material exists");
            assert_eq!(
                material.emissive,
                LinearRgba::BLACK,
                "pod {index} stays dead"
            );
        }
        for index in [2usize, 6] {
            let material = materials.get(&handles[index]).expect("material exists");
            assert_eq!(
                material.emissive,
                super::geometry::INDICATOR_LIT_EMISSIVE,
                "pod {index} lights up"
            );
        }
        // Flipping only pod 2 back rewrites its material dead again; a pod
        // whose lit state did not change is never written.
        handles[2] = materials.add(StandardMaterial {
            emissive: super::geometry::INDICATOR_LIT_EMISSIVE,
            ..StandardMaterial::default()
        });
        let mut revert = next;
        revert.pods[2].indicator_lit = false;
        apply_indicator_materials(&mut materials, &handles, &next, &revert);
        let material = materials.get(&handles[2]).expect("material exists");
        assert_eq!(material.emissive, LinearRgba::BLACK);
        let material = materials.get(&handles[6]).expect("material exists");
        assert_eq!(
            material.emissive,
            super::geometry::INDICATOR_LIT_EMISSIVE,
            "pod 6 unchanged between these mirrors"
        );
    }

    /// Every pod state's registry shape is exercised somewhere in the
    /// scene: the frozen split is three sealed, three empty-open, one
    /// player pod.
    #[test]
    fn frozen_scene_split_covers_every_pod_state() {
        let registry = PodRegistry::frozen();
        let states: Vec<PodState> = registry.pods().iter().map(|pod| pod.state()).collect();
        assert_eq!(states.iter().filter(|s| **s == PodState::Sealed).count(), 3);
        assert_eq!(
            states.iter().filter(|s| **s == PodState::EmptyOpen).count(),
            3
        );
        assert_eq!(states.iter().filter(|s| s.is_player()).count(), 1);
    }
}
