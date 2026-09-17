//! Emergency fixtures and the read-only power bridge (issue #10).
//!
//! One sim fade drives the shared emergency circuit's lenses and point lights.
//! The bridge consumes virtual time after scripted input: the gameplay harness
//! pins that clock to its driven step and zeroes it on capture/loading holds.
//! Normal play uses Bevy's virtual delta. Neither path drains the motion clock.
//! No gameplay system cuts power in milestone 1; tests exercise the sim hook.

use bevy::app::{App, Plugin, Startup, Update};
use bevy::asset::{Assets, Handle};
use bevy::camera::Exposure;
use bevy::color::{Color, LinearRgba};
use bevy::ecs::prelude::{Commands, Component, Local, Query, Res, ResMut, Resource, With};
use bevy::ecs::schedule::IntoScheduleConfigs;
use bevy::light::{AmbientLight, GlobalAmbientLight, PointLight};
use bevy::math::{Quat, Vec3, primitives::Cuboid};
use bevy::mesh::{Mesh, Mesh3d};
use bevy::pbr::{DistanceFog, FogFalloff, MeshMaterial3d, StandardMaterial};
use bevy::time::{Time, Virtual};
use bevy::transform::components::Transform;
use gone_sim::pods::ROOM_WIDTH;
use gone_sim::{FixtureFade, LOGICAL_TICK_SECS, PowerGrid};

use super::SimPodRegistry;
use super::placement::hatch_solids;
use crate::player::{LookApplied, ScriptedInput};

pub(super) const FIXTURE_LUMENS: f32 = 45.0;
pub(super) const FIXTURE_RANGE: f32 = 6.0;
pub(super) const FIXTURE_EMISSIVE: f32 = 2.6;
pub(super) const FIXTURE_SETTLE_TICKS: u16 = 30;
const EMERGENCY_RED: Color = Color::linear_rgb(1.0, 0.0, 0.0);
const LENS_SIZE: Vec3 = Vec3::new(0.42, 0.16, 0.12);
const WALL_MOUNT_HEIGHT: f32 = 2.65;
const WALL_STANDOFF: f32 = 0.10;

/// Bevy storage only; the contained sim machine owns every power transition.
#[derive(Resource, Default)]
pub(crate) struct SimPowerGrid(pub(super) PowerGrid);

#[cfg(test)]
impl SimPowerGrid {
    /// Stage the sim transition without adding a gameplay power-cut trigger.
    pub(crate) fn cut_emergency_power(&mut self) {
        self.0.cut_emergency_power();
    }
}

/// The lens and its colocated point light, with no collision or gameplay role.
#[derive(Component)]
pub(super) struct EmergencyFixture;

#[derive(Resource)]
struct FixtureRender {
    fade: FixtureFade,
    lens: Handle<StandardMaterial>,
}

pub(super) struct EmergencyLightingPlugin;

impl Plugin for EmergencyLightingPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<SimPowerGrid>()
            .init_resource::<Time<Virtual>>()
            .insert_resource(GlobalAmbientLight {
                color: Color::BLACK,
                brightness: 0.0,
                affects_lightmapped_meshes: false,
            })
            .add_systems(Startup, spawn_fixtures)
            .add_systems(
                Update,
                project_power.after(ScriptedInput).before(LookApplied),
            );
    }
}

/// No environment map, skybox, atmosphere or light probes are authored for
/// this room. Ambient and fog are explicitly disabled, including the fog's
/// directional tint; actual fog is #9's effect, not a substitute fill light.
/// EV100 zero is the scene-authored exposure for the dim emergency emitters.
/// Auto-exposure settings are unchanged; visual acceptance remains pending.
pub(crate) fn camera_environment() -> (Exposure, AmbientLight, DistanceFog) {
    (
        Exposure { ev100: 0.0 },
        AmbientLight {
            color: Color::BLACK,
            brightness: 0.0,
            affects_lightmapped_meshes: false,
        },
        DistanceFog {
            color: Color::BLACK,
            directional_light_color: Color::BLACK,
            directional_light_exponent: 1.0,
            falloff: FogFalloff::Exponential { density: 0.0 },
        },
    )
}

/// One wall fixture above each registry pod and one above the existing hatch
/// lintel. All are outside the standing envelope; route solids stay untouched.
fn fixture_transforms(pods: &SimPodRegistry) -> Vec<Transform> {
    let mut transforms: Vec<_> = pods
        .registry()
        .pods()
        .iter()
        .map(|pod| {
            let placement = pod.placement();
            let side = placement.center.1.signum();
            Transform::from_xyz(
                placement.center.0,
                WALL_MOUNT_HEIGHT,
                side * (ROOM_WIDTH / 2.0 - WALL_STANDOFF),
            )
        })
        .collect();
    let lintel = hatch_solids()[2];
    transforms.push(
        Transform::from_translation(lintel.center + Vec3::new(-WALL_STANDOFF, 0.22, 0.0))
            .with_rotation(Quat::from_rotation_y(core::f32::consts::FRAC_PI_2)),
    );
    transforms
}

fn spawn_fixtures(
    mut commands: Commands,
    pods: Res<SimPodRegistry>,
    grid: Res<SimPowerGrid>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let level = f32::from(grid.into_inner().0.state().emergency_fixtures_lit());
    let lens = materials.add(StandardMaterial {
        base_color: Color::srgb(0.18, 0.01, 0.01),
        emissive: LinearRgba::rgb(FIXTURE_EMISSIVE * level, 0.0, 0.0),
        perceptual_roughness: 0.8,
        ..StandardMaterial::default()
    });
    let mesh = meshes.add(Cuboid::from_size(LENS_SIZE));
    for transform in fixture_transforms(pods.into_inner()) {
        commands
            .spawn((
                EmergencyFixture,
                PointLight {
                    color: EMERGENCY_RED,
                    intensity: FIXTURE_LUMENS * level,
                    range: FIXTURE_RANGE,
                    radius: 0.08,
                    shadow_maps_enabled: false,
                    contact_shadows_enabled: false,
                    ..PointLight::default()
                },
                transform,
            ))
            .with_children(|parent| {
                // A mesh AABB overrides range-sphere culling if put on the light.
                parent.spawn((
                    Mesh3d(mesh.clone()),
                    MeshMaterial3d(lens.clone()),
                    Transform::IDENTITY,
                ));
            });
    }
    commands.insert_resource(FixtureRender {
        fade: FixtureFade::holding(level).expect("power maps to a finite nonnegative level"),
        lens,
    });
}

fn project_power(
    grid: Res<SimPowerGrid>,
    time: Res<Time<Virtual>>,
    mut render: ResMut<FixtureRender>,
    mut lights: Query<&mut PointLight, With<EmergencyFixture>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    mut remainder: Local<f32>,
) {
    let target = f32::from(grid.into_inner().0.state().emergency_fixtures_lit());
    if render.fade.target().to_bits() != target.to_bits() {
        render
            .fade
            .retarget(target, FIXTURE_SETTLE_TICKS)
            .expect("power maps to a finite nonnegative level");
    }
    *remainder += time.into_inner().delta_secs();
    while *remainder >= LOGICAL_TICK_SECS {
        *remainder -= LOGICAL_TICK_SECS;
        render.fade.tick();
    }
    let level = render.fade.intensity();
    for mut light in &mut lights {
        let intensity = FIXTURE_LUMENS * level;
        if light.intensity.to_bits() != intensity.to_bits() {
            light.intensity = intensity;
        }
    }
    let emissive = LinearRgba::rgb(FIXTURE_EMISSIVE * level, 0.0, 0.0);
    if materials
        .get(&render.lens)
        .expect("fixture lens exists")
        .emissive
        != emissive
    {
        materials
            .get_mut(&render.lens)
            .expect("fixture lens exists")
            .emissive = emissive;
    }
}
