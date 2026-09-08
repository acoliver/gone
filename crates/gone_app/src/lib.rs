//! Bevy glue layer for the game `gone` (issue #6 slice A).
//!
//! Contract: this crate renders state owned by `gone_sim` and owns no simulation
//! state. This slice is the harness bootstrap: a real window, a camera rendering an
//! intentional empty scene, a loading/closed presentation until the renderer is ready,
//! a harness input-adapter resource (only under `GONE_HARNESS=1`), frame-coded
//! captures, a JSON report, and a clean self-exit when the scenario completes.
//!
//! Gameplay internals stay crate-private; the only public harness surface is the
//! `harness` protocol module (which `gone_harness` re-exports). Under harness mode
//! the app uses its own runner so it never needs an OS window; the runner survives even
//! where a window cannot open.

use std::path::PathBuf;

use bevy::app::{App, AppExit, PluginGroup};
use bevy::camera::ClearColor;
use bevy::color::Color;
use bevy::prelude::{Camera3d, Commands, Transform};
use bevy::window::{Window, WindowPlugin};

/// The harness protocol (single home; `gone_harness` re-exports it).
pub mod harness;

mod bootstrap;

/// Main entry (delegated by `src/main.rs`). The window is created by the plugin
/// build; under harness mode the bootstrap plugin drives scenario execution and swaps
/// in its own runner so no visible window is required.
pub fn run() -> AppExit {
    let mut app = App::new();
    let primary = Window {
        title: "gone".to_owned(),
        resizable: true,
        resolution: bevy::window::WindowResolution::new(1920, 1080).with_scale_factor_override(1.0),
        ..Default::default()
    };
    app.add_plugins(bevy::DefaultPlugins.set(WindowPlugin {
        primary_window: Some(primary),
        ..Default::default()
    }));

    if std::env::var("GONE_HARNESS").is_ok_and(|v| v == "1") {
        let scenario_path = std::env::var("GONE_SCENARIO").ok().map(PathBuf::from);
        let out_dir = std::env::var("GONE_OUT_DIR").ok().map(PathBuf::from);
        let config_hash = std::env::var("GONE_CONFIG_HASH").unwrap_or_default();
        app.add_plugins(bootstrap::BootstrapPlugin::new(
            scenario_path,
            out_dir,
            config_hash,
        ));
        app.set_runner(harness_runner);
    } else {
        app.add_systems(bevy::app::Startup, setup_camera_scene);
    }
    app.run()
}

/// The non-harness app is a plain window with the intentional empty scene: one
/// camera and a dark clear color (the loading/closed presentation).
fn setup_camera_scene(mut commands: Commands) {
    commands.spawn((Camera3d::default(), Transform::from_xyz(0.0, 0.5, 5.0)));
    commands.insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.02)));
}

/// The harness runner: initialize the app then update until the bootstrap requests an
/// exit. No OS window is opened; the render sub-app runs from extraction each update,
/// which is all the harness capture lane needs.
fn harness_runner(mut app: App) -> AppExit {
    app.finish();
    app.cleanup();
    loop {
        app.update();
        if let Some(exit) = app.should_exit() {
            return exit;
        }
        std::thread::sleep(std::time::Duration::from_millis(1));
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn app_crate_builds() {}
}
