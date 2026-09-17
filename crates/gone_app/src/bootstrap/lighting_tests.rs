//! The real gameplay drive and readback holds pace emergency fades.

use bevy::app::App;
use bevy::light::PointLight;
use gone_sim::FixtureFade;

use super::state::{HarnessState, Readiness};
use super::wake_harness_tests::{play_render_world, wake_harness_app};
use crate::harness::{Beat, Content, Scenario};
use crate::scene::SimPowerGrid;
use crate::wake_pass::WakeEyelidPipelineReadiness;

fn intensities(app: &mut App) -> Vec<f32> {
    app.world_mut()
        .query::<&PointLight>()
        .iter(app.world())
        .map(|light| light.intensity)
        .collect()
}

fn assert_level(app: &mut App, expected: f32) {
    let values = intensities(app);
    assert_eq!(values.len(), 8);
    assert!(
        values.iter().all(|value| (value - expected).abs() < 1e-4),
        "{values:?} != {expected}"
    );
}

fn held_capture(rate: u64, multiplier: u64, divisor: u64) {
    let scenario = Scenario {
        name: format!("emergency-fade-{rate}"),
        content: Content::Gameplay,
        ticks_per_second: rate,
        beats: vec![Beat::new("mid-fade", 3), Beat::new("settled", 120)],
        ..Scenario::default()
    };
    let mut app = wake_harness_app(
        WakeEyelidPipelineReadiness::Compiling,
        scenario,
        "emergency-fade",
    );
    app.world_mut().resource_mut::<HarnessState>().out_dir =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../tmp/issue10-emergency-render")
            .join(format!("ecs-{rate}-{}", std::process::id()));
    app.update();
    let initial = intensities(&mut app)[0];
    app.world_mut()
        .resource_mut::<SimPowerGrid>()
        .cut_emergency_power();
    for _ in 0..10 {
        app.update();
        assert_level(&mut app, initial);
        assert_eq!(*app.world().resource::<Readiness>(), Readiness::Loading);
    }
    app.insert_resource(WakeEyelidPipelineReadiness::Ready);
    for _ in 0..20 {
        app.update();
        if app
            .world()
            .resource::<HarnessState>()
            .capture_in_flight
            .is_some()
        {
            break;
        }
        play_render_world(&mut app);
    }
    let state = app.world().resource::<HarnessState>();
    assert!(state.capture_in_flight.is_some());
    assert_eq!(state.tick, 4);
    let mut expected = FixtureFade::new(initial, 0.0, 30).expect("authored settle");
    for _ in 0..state.tick * multiplier / divisor {
        expected.tick();
    }
    assert_level(&mut app, expected.intensity());
    for _ in 0..20 {
        app.update();
        assert_eq!(app.world().resource::<HarnessState>().tick, 4);
        assert_level(&mut app, expected.intensity());
    }
    play_render_world(&mut app);
    for _ in 0..70 {
        app.update();
        play_render_world(&mut app);
    }
    assert_level(&mut app, 0.0);
}

#[test]
fn emergency_fades_follow_real_harness_clock_across_rates_and_readback_holds() {
    for (rate, multiplier, divisor) in [(30, 2, 1), (60, 1, 1), (120, 1, 2)] {
        held_capture(rate, multiplier, divisor);
    }
}
