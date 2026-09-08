//! Bevy glue layer for the game `gone` (issue #6 slice A).
//!
//! Contract: this crate renders state owned by `gone_sim` and owns no simulation
//! state. This slice is the harness bootstrap: a real OS window, a camera
//! rendering an intentional scene, a loading/closed presentation until the
//! renderer has actually presented, a harness input-adapter resource (only under
//! `GONE_HARNESS=1`), frame-coded captures taken from an offscreen render
//! target, a JSON report, and a clean self-exit when the scenario completes.
//!
//! Gameplay internals stay crate-private; the only public harness surface is the
//! `harness` protocol module (which `gone_harness` re-exports). In both modes the
//! app is the normal winit app: the `WinitPlugin` runner owns the OS event loop,
//! which is what opens the window and presents frames (issue #15). Harness-mode
//! captures come from an offscreen render target, not the window swapchain:
//! they are exactly 1920x1080 regardless of window scale or DPI overrides, and
//! their timing is decoupled from the swapchain and present. (`Screenshot::
//! primary_window()` works here with the correct bevy feature set; an earlier
//! probe's all-black captures were our own feature-selection error, not a
//! platform property. The window presents nothing during harness runs, so
//! switching captures to it is a possible future simplification. See
//! `bootstrap`.)

use std::path::{Path, PathBuf};

use bevy::app::{App, AppExit, PluginGroup};
use bevy::camera::ClearColor;
use bevy::color::Color;
use bevy::prelude::{Camera3d, Commands, Transform};
use bevy::window::{PresentMode, Window, WindowPlugin};
use bevy::winit::WinitSettings;

use crate::harness::{Pacing, Scenario};

/// The harness protocol (single home; `gone_harness` re-exports it).
pub mod harness;

mod bootstrap;
mod capture;

/// Main entry (delegated by `src/main.rs`). In both modes the app runs under the
/// default winit runner; under harness mode the bootstrap plugin drives scenario
/// execution and requests the exit when the scenario completes or fails.
///
/// # Panics
/// Panics in harness mode without `GONE_SCENARIO` (the runner always sets it),
/// and on an unreadable or invalid scenario: a child that cannot load its
/// scenario is a failed run either way.
pub fn run() -> AppExit {
    let mut app = App::new();
    let mut primary = Window {
        title: "gone".to_owned(),
        resizable: true,
        resolution: bevy::window::WindowResolution::new(1920, 1080).with_scale_factor_override(1.0),
        ..Default::default()
    };

    // The harness scenario is parsed once here: its pacing decides the
    // window's present mode before DefaultPlugins consumes the window config,
    // and the parsed scenario then drives the bootstrap plugin.
    let harness_scenario = if std::env::var("GONE_HARNESS").is_ok_and(|v| v == "1") {
        let path = std::env::var("GONE_SCENARIO").ok().map(PathBuf::from);
        Some(
            path.as_deref()
                .map(load_scenario)
                .expect("GONE_HARNESS requires GONE_SCENARIO (the runner always sets it)"),
        )
    } else {
        None
    };
    if let Some(scenario) = &harness_scenario
        && scenario.pacing == Some(Pacing::Uncapped)
    {
        // Uncapped pacing: lift vsync from the window so wall-clock frame
        // times are not quantized to the refresh rate (the perf lane requires
        // this; `AutoNoVsync` falls back safely where the platform must).
        primary.present_mode = PresentMode::AutoNoVsync;
    }

    app.add_plugins(bevy::DefaultPlugins.set(WindowPlugin {
        primary_window: Some(primary),
        ..Default::default()
    }));

    if let Some(scenario) = harness_scenario {
        // Harness lane: the event loop must spin regardless of window focus. A
        // spawned harness window may never take focus, and a throttled loop
        // would stall beat ticks and quantize perf samples to the redraw
        // cadence.
        app.insert_resource(WinitSettings::continuous());
        let out_dir = std::env::var("GONE_OUT_DIR").ok().map(PathBuf::from);
        let config_hash = std::env::var("GONE_CONFIG_HASH").unwrap_or_default();
        app.add_plugins(bootstrap::BootstrapPlugin::new(
            scenario,
            out_dir,
            config_hash,
        ));
    } else {
        app.add_systems(bevy::app::Startup, setup_camera_scene);
    }
    app.run()
}

/// Read and parse the scenario file the runner pointed at.
///
/// # Panics
/// Panics on an unreadable or invalid scenario: the runner treats a child that
/// never runs its scenario as a failed run either way.
fn load_scenario(path: &Path) -> Scenario {
    let text = std::fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("cannot read scenario {}: {e}", path.display()));
    crate::harness::scenario::parse_scenario(&text).unwrap_or_else(|e| panic!("bad scenario: {e}"))
}

/// The non-harness app is a plain window with the intentional empty scene: one
/// camera and a dark clear color (the loading/closed presentation).
fn setup_camera_scene(mut commands: Commands) {
    commands.spawn((Camera3d::default(), Transform::from_xyz(0.0, 0.5, 5.0)));
    commands.insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.02)));
}

#[cfg(test)]
mod tests {
    #[test]
    fn app_crate_builds() {}
}
