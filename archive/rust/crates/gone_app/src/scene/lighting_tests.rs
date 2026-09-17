//! Headless tests of the production scene and its power-to-render bridge.

use std::time::Duration;

use bevy::app::{App, TaskPoolPlugin};
use bevy::asset::{AssetApp, AssetPlugin, Assets};
use bevy::camera::Camera3d;
use bevy::color::LinearRgba;
use bevy::ecs::prelude::{Children, With};
use bevy::light::{
    DirectionalLight, EnvironmentMapLight, GlobalAmbientLight, PointLight, SpotLight,
};
use bevy::mesh::Mesh;
use bevy::pbr::{DistanceFog, FogFalloff, MeshMaterial3d, StandardMaterial};
use bevy::time::{Time, Virtual};
use bevy::transform::components::Transform;
use gone_sim::{FixtureFade, LOGICAL_TICK_SECS, PowerState};

use super::lighting::{
    EmergencyFixture, FIXTURE_LUMENS, FIXTURE_RANGE, FIXTURE_SETTLE_TICKS, SimPowerGrid,
    camera_environment,
};
use super::{JammedHatch, SimColliders, StasisScenePlugin};

fn scene_app() -> App {
    let mut app = App::new();
    app.add_plugins((TaskPoolPlugin::default(), AssetPlugin::default()));
    app.init_asset::<Mesh>().init_asset::<StandardMaterial>();
    app.init_resource::<Time<Virtual>>();
    app.add_plugins(StasisScenePlugin);
    app.world_mut()
        .spawn((Camera3d::default(), camera_environment()));
    app.update();
    app
}

fn step(app: &mut App, seconds: f32) {
    app.world_mut()
        .resource_mut::<Time<Virtual>>()
        .advance_by(Duration::from_secs_f32(seconds));
    app.update();
}

#[test]
fn fixture_mesh_bounds_cannot_cull_the_light_influence_volume() {
    let mut app = scene_app();
    let world = app.world_mut();
    let mut lights = world.query_filtered::<Option<&bevy::mesh::Mesh3d>, With<PointLight>>();
    assert_eq!(lights.iter(world).count(), 8);
    assert!(
        lights.iter(world).all(|mesh| mesh.is_none()),
        "a lens mesh AABB takes precedence over the light range sphere in Bevy visibility"
    );
}

fn assert_output(app: &mut App, level: f32) {
    let materials = app.world().resource::<Assets<StandardMaterial>>();
    let world = app.world();
    for entity in world.iter_entities() {
        if entity.contains::<EmergencyFixture>() {
            let light = entity.get::<PointLight>().expect("fixture light");
            assert!((light.intensity - FIXTURE_LUMENS * level).abs() < 1e-4);
            let children = entity.get::<Children>().expect("fixture lens child");
            assert_eq!(children.len(), 1);
            let handle = world
                .get::<MeshMaterial3d<StandardMaterial>>(children[0])
                .expect("fixture lens");
            let emissive = materials.get(&handle.0).expect("lens material").emissive;
            assert!((emissive.red - super::lighting::FIXTURE_EMISSIVE * level).abs() < 1e-5);
            assert_eq!(emissive.green.to_bits(), 0.0_f32.to_bits());
            assert_eq!(emissive.blue.to_bits(), 0.0_f32.to_bits());
        }
    }
}

#[test]
fn real_bridge_follows_sim_fade_and_repeated_dead_does_not_restart() {
    let mut app = scene_app();
    assert_output(&mut app, 1.0);
    let count = app.world().resource::<Assets<StandardMaterial>>().len();
    app.world_mut()
        .resource_mut::<SimPowerGrid>()
        .0
        .cut_emergency_power();
    step(&mut app, 0.0);
    assert_output(&mut app, 1.0);
    let mut expected = FixtureFade::new(1.0, 0.0, FIXTURE_SETTLE_TICKS).expect("valid fade");
    for _ in 0..FIXTURE_SETTLE_TICKS {
        app.world_mut()
            .resource_mut::<SimPowerGrid>()
            .0
            .cut_emergency_power();
        step(&mut app, LOGICAL_TICK_SECS);
        assert_output(&mut app, expected.tick());
    }
    assert!(expected.is_settled());
    for _ in 0..20 {
        step(&mut app, LOGICAL_TICK_SECS);
        assert_output(&mut app, 0.0);
    }
    assert_eq!(
        app.world().resource::<Assets<StandardMaterial>>().len(),
        count
    );
    assert_eq!(
        app.world().resource::<SimPowerGrid>().0.state(),
        PowerState::Dead
    );
}

#[test]
fn held_frames_and_fractional_steps_obey_the_logical_clock() {
    let mut app = scene_app();
    app.world_mut()
        .resource_mut::<SimPowerGrid>()
        .0
        .cut_emergency_power();
    for _ in 0..20 {
        step(&mut app, 0.0);
        assert_output(&mut app, 1.0);
    }
    step(&mut app, LOGICAL_TICK_SECS / 2.0);
    assert_output(&mut app, 1.0);
    step(&mut app, LOGICAL_TICK_SECS / 2.0);
    let mut fade = FixtureFade::new(1.0, 0.0, FIXTURE_SETTLE_TICKS).expect("valid fade");
    assert_output(&mut app, fade.tick());
    step(&mut app, LOGICAL_TICK_SECS * 3.0);
    for _ in 0..3 {
        fade.tick();
    }
    assert_output(&mut app, fade.intensity());
}

#[test]
fn render_observations_cannot_change_power_and_are_projected_from_sim() {
    let mut app = scene_app();
    for mut light in app
        .world_mut()
        .query::<&mut PointLight>()
        .iter_mut(app.world_mut())
    {
        light.intensity = 0.0;
    }
    step(&mut app, 0.0);
    assert_eq!(
        app.world().resource::<SimPowerGrid>().0.state(),
        PowerState::Emergency
    );
    assert_output(&mut app, 1.0);
}

#[test]
fn authored_sources_are_only_red_fixtures_with_dead_indicators() {
    let mut app = scene_app();
    let world = app.world_mut();
    let mut lights = world.query::<(&PointLight, &Transform)>();
    assert_eq!(
        lights.iter(world).count(),
        8,
        "seven wall fixtures and one over hatch"
    );
    for (light, position) in lights.iter(world) {
        assert_eq!(light.color.to_linear(), LinearRgba::rgb(1.0, 0.0, 0.0));
        assert_eq!(light.range.to_bits(), FIXTURE_RANGE.to_bits());
        assert!(!light.shadow_maps_enabled);
        assert!(!light.contact_shadows_enabled);
        assert!(position.translation.y > 2.4, "outside the walking envelope");
    }
    assert_eq!(world.query::<&SpotLight>().iter(world).count(), 0);
    assert_eq!(world.query::<&DirectionalLight>().iter(world).count(), 0);
}

#[test]
fn authored_environment_and_fog_contribute_no_light() {
    let mut app = scene_app();
    let world = app.world_mut();
    assert_eq!(world.query::<&EnvironmentMapLight>().iter(world).count(), 0);
    assert_eq!(
        world
            .query::<&bevy::core_pipeline::Skybox>()
            .iter(world)
            .count(),
        0
    );
    let ambient = world.resource::<GlobalAmbientLight>();
    assert_eq!(ambient.color, bevy::color::Color::BLACK);
    assert_eq!(ambient.brightness.to_bits(), 0.0_f32.to_bits());
    for fog in world.query::<&DistanceFog>().iter(world) {
        assert_eq!(fog.color, bevy::color::Color::BLACK);
        assert_eq!(fog.directional_light_color, bevy::color::Color::BLACK);
        assert!(matches!(fog.falloff, FogFalloff::Exponential { density } if density == 0.0));
    }
}

#[test]
fn authored_materials_have_no_nonred_emission_or_unlit_bypass() {
    let app = scene_app();
    let materials = app.world().resource::<Assets<StandardMaterial>>();
    for (_, material) in materials.iter() {
        assert_eq!(material.emissive.green.to_bits(), 0.0_f32.to_bits());
        assert_eq!(material.emissive.blue.to_bits(), 0.0_f32.to_bits());
        assert!(
            !material.unlit,
            "no unlit white surface bypasses scene lighting"
        );
        assert!(material.emissive_texture.is_none());
    }
}

#[test]
fn all_seven_pod_plates_stay_unpowered_across_wake_and_power_changes() {
    let mut app = scene_app();
    let mut groups = app
        .world_mut()
        .query_filtered::<&Children, With<super::StasisPod>>();
    let plate_position = super::placement::indicator_plate().center;
    let plates: Vec<_> = groups
        .iter(app.world())
        .flat_map(|children| children.iter())
        .filter(|child| {
            app.world()
                .get::<Transform>(**child)
                .expect("pod solid")
                .translation
                == plate_position
        })
        .map(|child| {
            app.world()
                .get::<MeshMaterial3d<StandardMaterial>>(*child)
                .expect("plate material")
                .0
                .clone()
        })
        .collect();
    assert_eq!(plates.len(), gone_sim::POD_COUNT);
    let _ = app
        .world_mut()
        .resource_mut::<super::SimWakePhase>()
        .wake_complete();
    app.world_mut()
        .resource_mut::<SimPowerGrid>()
        .0
        .cut_emergency_power();
    for _ in 0..=FIXTURE_SETTLE_TICKS {
        let materials = app.world().resource::<Assets<StandardMaterial>>();
        for handle in &plates {
            assert_eq!(
                materials.get(handle).expect("plate").emissive,
                LinearRgba::BLACK
            );
        }
        step(&mut app, LOGICAL_TICK_SECS);
    }
}

fn hatch_transforms(app: &mut App) -> Vec<Transform> {
    let mut query = app
        .world_mut()
        .query_filtered::<&Children, With<JammedHatch>>();
    query
        .single(app.world())
        .expect("hatch")
        .iter()
        .map(|child| *app.world().get::<Transform>(*child).expect("hatch solid"))
        .collect()
}

#[test]
fn power_cut_preserves_hatch_solids_and_blocking_colliders() {
    let mut app = scene_app();
    let hatch = hatch_transforms(&mut app);
    let boxes = app
        .world()
        .resource::<SimColliders>()
        .set()
        .boxes()
        .to_vec();
    let door = super::placement::hatch_solids()[4];
    let probe = gone_sim::Aabb::from_min_max(
        door.center - bevy::math::Vec3::splat(0.01),
        door.center + bevy::math::Vec3::splat(0.01),
    )
    .expect("probe inside refused hatch");
    assert!(
        app.world()
            .resource::<SimColliders>()
            .set()
            .overlapping(&probe)
            .next()
            .is_some()
    );
    app.world_mut()
        .resource_mut::<SimPowerGrid>()
        .0
        .cut_emergency_power();
    for _ in 0..FIXTURE_SETTLE_TICKS {
        step(&mut app, LOGICAL_TICK_SECS);
    }
    assert_eq!(hatch_transforms(&mut app), hatch);
    let colliders = app.world().resource::<SimColliders>().set();
    assert_eq!(colliders.boxes(), boxes);
    assert!(colliders.overlapping(&probe).next().is_some());
}
