//! One scenario run end to end: hash the spawned bytes, write the run dir,
//! spawn the app, wait, then the report loading/verification semantics
//! (protocol version and run identity), the beat/capture verification, and
//! the lane-specific checks (gameplay, render-check onscreen).

use std::path::{Path, PathBuf};
use std::time::Duration;

use gone_harness::gameplay;
use gone_harness::scenario::Scenario;
use gone_harness::{Content, PROTOCOL_VERSION, onscreen, report};

use crate::app::{RunIdentity, spawn_app, wait_for_app};
use crate::error::{RunnerError, bail};
use crate::hash::sha256_hex;
use crate::paths::{read_or, run_id, write_or};

/// Scenario runtime timeout; the runner owns termination and reaping.
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// Run one scenario end to end: spawn the app, wait, verify the report and
/// captures, and return the run dir. Under `render_check` the app runs the
/// canary lane and the run's single onscreen capture is machine-verified too;
/// a beatless scenario fails fast before spawning, since the canary captures
/// at the first beat.
pub(crate) fn run_scenario(
    root: &Path,
    scenario_path: &Path,
    scenario: &Scenario,
    out_root: &Path,
    render_check: bool,
) -> Result<PathBuf, RunnerError> {
    if render_check && scenario.beats.is_empty() {
        bail!(
            "render-check requires a scenario with at least one beat: the canary \
             captures the onscreen frame at the first beat (scenario `{}` has none)",
            scenario.name
        );
    }
    let id = run_id(scenario.seed, render_check);
    let run_dir = out_root.join(&scenario.name).join(&id);
    std::fs::create_dir_all(&run_dir).map_err(|e| {
        RunnerError(format!(
            "failed to create run dir {}: {e}",
            run_dir.display()
        ))
    })?;

    let app_bytes = read_or("app binary", &root.join("target/debug/gone_app"))?;
    let scenario_bytes = read_or("scenario", scenario_path)?;
    // The config string sent to the app: the environment carries the scenario bytes'
    // content hash, and the app echoes it back so the runner can prove the app saw
    // and wrote the same identity values.
    let app_hash = sha256_hex(&app_bytes);
    let scenario_hash = sha256_hex(&scenario_bytes);
    let config_hash = sha256_hex(&scenario_bytes);
    let identity = RunIdentity {
        app: &app_hash,
        scenario: &scenario_hash,
        config: &config_hash,
    };

    let scenario_copy = run_dir.join("scenario.json");
    write_or("scenario copy", &scenario_copy, &scenario_bytes)?;

    let mut child = spawn_app(root, scenario_path, &run_dir, &identity, render_check)?;
    let status = wait_for_app(&mut child, DEFAULT_TIMEOUT, &scenario.name)?;
    disband_scenario(&run_dir, &scenario_bytes);

    // The report is the app's own account of the run, including why it exited
    // nonzero (a deadline with uncaptured beats, a failed capture save), so
    // verify it first: a machine-check failure names the artifact. Only a run
    // whose report fully verifies falls back to the bare exit-status error.
    let report_path = run_dir.join("report.json");
    let report_bytes = read_or("report", &report_path)?;
    let report_text = String::from_utf8_lossy(&report_bytes);
    let parsed = verify_report(&report_text, identity.app, identity.config)?;

    verify_captures(scenario, &parsed, &run_dir)?;
    if scenario.content == Content::Gameplay {
        // The gameplay lane's own machine checks (see `gone_harness::gameplay`):
        // room presence and the scripted-look yaw replay, and on the full lane
        // the wake progression, the exit waypoint, and the door walk.
        if scenario.name == gameplay::GAMEPLAY_FULL_SCENARIO_NAME {
            gameplay::verify_gameplay_full(scenario, &parsed).map_err(RunnerError)?;
        } else {
            gameplay::verify_gameplay(scenario, &parsed).map_err(RunnerError)?;
        }
    }
    if render_check {
        onscreen::verify_run(scenario, &parsed, &run_dir).map_err(RunnerError)?;
    }

    if !status.success() {
        bail!(
            "app exited nonzero ({status}) for scenario `{}`",
            scenario.name
        );
    }

    Ok(run_dir)
}

/// Parse the run's report and verify its protocol version and run identity
/// against the hashes this runner computed and sent.
fn verify_report(
    report_text: &str,
    app_hash: &str,
    config_hash: &str,
) -> Result<report::Report, RunnerError> {
    let parsed =
        report::parse_report(report_text).map_err(|e| RunnerError(format!("report parse: {e}")))?;
    if parsed.protocol_version != PROTOCOL_VERSION {
        bail!(
            "protocol version mismatch: report {}, runner {}",
            parsed.protocol_version,
            PROTOCOL_VERSION
        );
    }
    if parsed.identity.app_hash != app_hash {
        bail!("run identity mismatch: app content hash differs from the binary we spawned");
    }
    if parsed.identity.config_hash != config_hash {
        bail!("run identity mismatch: config content hash differs from the scenario we spawned");
    }
    Ok(parsed)
}

/// Verify the captured PNGs decode to the report's tick/frame for every beat, and
/// every expected beat from the scenario happened (naming any missing one).
fn verify_captures(
    scenario: &Scenario,
    report: &report::Report,
    run_dir: &Path,
) -> Result<(), RunnerError> {
    // 1. every expected beat must be in the report's beat manifest.
    for beat in &scenario.beats {
        if !report.beats.contains_key(&beat.name) {
            bail!(
                "missing beat `{}` (expected tick {}): report has no beat named {}",
                beat.name,
                beat.tick,
                beat.name
            );
        }
    }

    // 2. decode each captured PNG and assert it carries the report's tick/frame.
    for (name, entry) in &report.beats {
        let path = run_dir.join(&entry.file);
        if !path.is_file() {
            bail!("beat `{name}` capture file is missing: {}", path.display());
        }
        let bytes = read_or("capture", &path)?;
        let img = image::load_from_memory(&bytes)
            .map_err(|e| RunnerError(format!("beat `{name}` PNG invalid: {e}")))?;
        let (tick, frame) = decode_frame_chip(&img, name)?;
        if tick == entry.tick && frame == entry.frame {
            continue;
        }
        bail!(
            "beat `{name}` frame-code mismatch: capture shows (tick {tick}, frame {frame}), report says (tick {}, frame {})",
            entry.tick,
            entry.frame
        );
    }
    Ok(())
}

/// Decode the top-left frame-code chip from a captured PNG. The crop and the
/// lattice decode live in the shared protocol (`frame::decode_chip_from_rgb`);
/// the runner only wraps the error with the beat name.
fn decode_frame_chip(img: &image::DynamicImage, name: &str) -> Result<(u64, u64), RunnerError> {
    let rgb = img.to_rgb8();
    gone_harness::frame::decode_chip_from_rgb(rgb.as_raw(), 3, rgb.width(), rgb.height())
        .map_err(|e| RunnerError(format!("beat `{name}` frame-code decode: {e}")))
}

/// Persist the scenario bytes beside the report so each run dir is self-describing.
fn disband_scenario(run_dir: &Path, scenario_bytes: &[u8]) {
    write_or(
        "scenario copy",
        &run_dir.join("scenario.json"),
        scenario_bytes,
    )
    .unwrap_or_else(|e| eprintln!("{e}"));
}
