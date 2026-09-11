//! Bevy glue layer for the game `gone` (issue #6 slice A).
//!
//! Contract: this crate renders state owned by `gone_sim` and owns no simulation
//! state. This slice is the harness bootstrap: a loading/closed presentation
//! until the renderer has actually presented, a harness input-adapter resource
//! (only under `GONE_HARNESS=1`), frame-coded captures, a JSON report, and a
//! clean self-exit when the scenario completes.
//!
//! Two capture architectures (`bootstrap::RunMode`): harness mode is headless
//! by default — no window and no winit event loop; the schedule runner drives
//! updates and an offscreen render target is the only render target.
//! `GONE_RENDER_CHECK=1` selects the canary: the real window opens (focused:
//! the window must be ordered in for its surface to present, and on macOS a
//! background-launched app only gets its window ordered in by activating;
//! winit exposes no order-in-without-activation or de-focus API) and presents
//! the scene through a second camera, and one onscreen capture is saved beside
//! the first beat's PNG.
//! Without `GONE_HARNESS` the app is the windowed game: the stasis room
//! greybox (`scene`, built from the `gone_sim` pod registry, game mode only),
//! the player rig with first-person mouse look (`player`) and the explicit
//! post chain (`post`, `AgX` tonemapping, center-weighted auto exposure,
//! vignette).
//!
//! Gameplay internals stay crate-private; the only public harness surface is the
//! `harness` protocol module (which `gone_harness` re-exports). Harness-mode
//! captures come from an offscreen render target, not the window swapchain:
//! they are exactly 1920x1080 regardless of window scale or DPI overrides, and
//! their timing is decoupled from the swapchain and present. (`Screenshot::
//! primary_window()` works here with the correct bevy feature set; an earlier
//! probe's all-black captures were our own feature-selection error, not a
//! platform property. See `bootstrap`.)

use std::path::{Path, PathBuf};

use bevy::app::{App, AppExit, PluginGroup, PluginGroupBuilder, ScheduleRunnerPlugin};
use bevy::window::{ExitCondition, PresentMode, Window, WindowPlugin};
use bevy::winit::{WinitPlugin, WinitSettings};

use crate::harness::{Pacing, Scenario, ScenarioMode};
use bootstrap::RunMode;

/// The harness protocol (single home; `gone_harness` re-exports it).
pub mod harness;

mod bootstrap;
mod capture;
mod player;
mod post;
mod scene;

/// Main entry (delegated by `src/main.rs`). The run mode comes from the
/// environment (`GONE_HARNESS`, `GONE_RENDER_CHECK`); harness modes load the
/// runner's scenario, whose pacing decides the window's present mode before
/// `DefaultPlugins` consumes the window config. Under harness mode the bootstrap
/// plugin drives scenario execution and requests the exit when the scenario
/// completes or fails.
///
/// # Panics
/// Panics on unknown harness env values (a stale or misspelled variable must
/// fail the launch loudly instead of silently selecting another mode), in
/// harness mode without `GONE_SCENARIO` (the runner always sets it), and on an
/// unreadable or invalid scenario: a child that cannot load its scenario is a
/// failed run either way.
#[must_use = "the AppExit carries the process exit status; dropping it loses the run's verdict"]
pub fn run() -> AppExit {
    let run_mode = bootstrap::select_run_mode(
        std::env::var("GONE_HARNESS").ok().as_deref(),
        std::env::var("GONE_RENDER_CHECK").ok().as_deref(),
    )
    .unwrap_or_else(|err| panic!("invalid harness environment: {err}"));
    let mut app = App::new();
    match run_mode {
        RunMode::Normal => {
            app.add_plugins(bevy::DefaultPlugins.set(WindowPlugin {
                primary_window: Some(game_window()),
                ..Default::default()
            }));
            // The game's own features (issue #6 slice B, issue #7 stage A):
            // the explicit post chain first (it provides the metering-mask
            // resource the rig camera consumes), then the stasis room scene
            // (it inserts the sim contract resources and the authored player
            // spawn the rig consumes), then first-person look (it spawns the
            // rig).
            app.add_plugins((
                post::GamePostChainPlugin,
                scene::StasisScenePlugin,
                player::PlayerLookPlugin,
            ));
        }
        RunMode::Headless => {
            let scenario = load_harness_scenario();
            app.add_plugins(headless_plugins(&scenario));
            add_harness(&mut app, scenario, run_mode);
        }
        RunMode::Canary => {
            let scenario = load_harness_scenario();
            let mut primary = game_window();
            // The canary window must be ordered in for its surface to present
            // and the primary_window screenshot to read real content. On macOS
            // a background-launched app only gets its window ordered in by
            // activating, so the window is created focused (bevy maps
            // `Window::focused` to winit `with_active` at creation only) and
            // keeps focus for the whole run: winit has no de-focus API
            // (`focus_window` only focuses) and no order-in-without-activation
            // path reachable through bevy.
            if scenario.pacing == Some(Pacing::Uncapped) {
                // Uncapped pacing: lift vsync from the window so wall-clock
                // frame times are not quantized to the refresh rate (the perf
                // lane requires this; `AutoNoVsync` falls back safely where
                // the platform must).
                primary.present_mode = PresentMode::AutoNoVsync;
            }
            app.add_plugins(bevy::DefaultPlugins.set(WindowPlugin {
                primary_window: Some(primary),
                ..Default::default()
            }));
            // The event loop must spin regardless of window focus: focus can
            // move away mid-run (the canary runs on a developer machine), and
            // a throttled loop would stall beat ticks and quantize perf
            // samples to the redraw cadence.
            app.insert_resource(WinitSettings::continuous());
            add_harness(&mut app, scenario, run_mode);
        }
    }
    app.run()
}

/// The game window both the normal game and the canary run open: titled,
/// 1920x1080 at an explicit scale factor of 1.0 (so window pixels and capture
/// pixels agree regardless of the desktop's DPI scaling), resizable.
fn game_window() -> Window {
    Window {
        title: "gone".to_owned(),
        resizable: true,
        resolution: bevy::window::WindowResolution::new(1920, 1080).with_scale_factor_override(1.0),
        ..Default::default()
    }
}

/// The headless harness plugin set: no winit event loop and no window at all.
/// `ExitCondition::DontExit` is required — under the default condition a
/// windowless app exits immediately ("No windows are open, exiting") — and
/// the schedule runner paces updates at the scenario clock's rate
/// ([`drive_pace`]).
fn headless_plugins(scenario: &Scenario) -> PluginGroupBuilder {
    bevy::DefaultPlugins
        .build()
        .disable::<WinitPlugin>()
        .set(WindowPlugin {
            primary_window: None,
            exit_condition: ExitCondition::DontExit,
            ..Default::default()
        })
        .add(ScheduleRunnerPlugin::run_loop(drive_pace(scenario)))
}

/// The headless update loop's wait between updates, from the scenario clock:
/// one tick's duration (`1 / ticks_per_second`, in whole nanoseconds) on the
/// capture lane, so the simulation's wall-clock rate is the scenario's
/// declared rate modulo render cost and sleep granularity; zero on the perf
/// lane, which samples real frame times and must not be paced. The canary
/// lane has no runner wait to configure: winit owns its loop and the display
/// paces its presents, so the clock rule there is unchanged and the wall rate
/// is the display's present rate.
#[must_use]
fn drive_pace(scenario: &Scenario) -> std::time::Duration {
    match scenario.mode {
        ScenarioMode::Capture => {
            std::time::Duration::from_nanos(1_000_000_000 / scenario.ticks_per_second)
        }
        ScenarioMode::Perf => std::time::Duration::ZERO,
    }
}

/// Add the harness bootstrap plugin for either capture mode.
fn add_harness(app: &mut App, scenario: Scenario, mode: RunMode) {
    let out_dir = std::env::var("GONE_OUT_DIR").ok().map(PathBuf::from);
    let config_hash = std::env::var("GONE_CONFIG_HASH").unwrap_or_default();
    app.add_plugins(bootstrap::BootstrapPlugin::new(
        scenario,
        out_dir,
        config_hash,
        mode,
    ));
}

/// Load the scenario file the runner pointed at (`GONE_SCENARIO`). Only the
/// harness lanes call this.
///
/// # Panics
/// Panics without `GONE_SCENARIO` (the runner always sets it).
fn load_harness_scenario() -> Scenario {
    let path = std::env::var("GONE_SCENARIO").ok().map(PathBuf::from);
    path.as_deref()
        .map(load_scenario)
        .expect("GONE_HARNESS requires GONE_SCENARIO (the runner always sets it)")
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

#[cfg(test)]
mod tests {
    use crate::harness::{Scenario, ScenarioMode};

    use super::drive_pace;

    #[test]
    fn app_crate_builds() {}

    #[test]
    fn the_capture_lane_paces_at_the_scenario_tick_rate() {
        // One tick's duration per update, in whole nanoseconds: the 60 Hz
        // default paces at 16_666_666 ns and a 125 Hz scenario at 8 ms.
        let scenario = Scenario {
            mode: ScenarioMode::Capture,
            ticks_per_second: 60,
            ..Scenario::default()
        };
        assert_eq!(drive_pace(&scenario).as_nanos(), 16_666_666);
        let scenario = Scenario {
            mode: ScenarioMode::Capture,
            ticks_per_second: 125,
            ..Scenario::default()
        };
        assert_eq!(drive_pace(&scenario).as_millis(), 8);
    }

    #[test]
    fn the_perf_lane_is_never_paced() {
        // Perf samples real frame times; a paced loop would measure the
        // pacing instead of the render cost.
        let scenario = Scenario {
            mode: ScenarioMode::Perf,
            ticks_per_second: 60,
            ..Scenario::default()
        };
        assert_eq!(drive_pace(&scenario), std::time::Duration::ZERO);
    }
}
