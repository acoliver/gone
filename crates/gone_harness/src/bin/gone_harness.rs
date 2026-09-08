//! The `gone-harness` runner binary (issue #5 / slice A).
//!
//! Drives the real `gone_app` binary as a child process for one scenario, collects
//! artifacts under `tmp/harness/<scenario>/<run-id>/`, verifies beat
//! expectations against the app's `report.json` (a beat that never happens fails
//! naming the missing beat), decodes the frame-code from each captured PNG and asserts
//! it matches the report's tick/frame, and prints the artifact dir on stdout's last
//! line. Two-stage verdict: exit 0 = "machine checks passed, visual verification
//! pending". The binary is OS-portable: `std::process::Command`, forward-slash
//! relative artifact paths, no OS-specific code (on macOS a SIGKILL to the child
//! process id is sufficient for termination; Windows kill-tree is documented as stage-B).

use std::fmt;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use sha2::{Digest as _, Sha256};

use gone_harness::scenario::{Scenario, parse_scenario, scenario_to_json};
use gone_harness::{PROTOCOL_VERSION, report};

const ENV_HARNESS: &str = "GONE_HARNESS";
const ENV_SCENARIO: &str = "GONE_SCENARIO";
const ENV_OUT_DIR: &str = "GONE_OUT_DIR";
/// The environment name for the app-binary content hash the runner computed.
const ENV_APP_HASH: &str = "GONE_APP_HASH";
/// The environment name for the scenario content hash the runner computed.
const ENV_SCENARIO_HASH: &str = "GONE_SCENARIO_HASH";
/// Scenario runtime timeout; the runner owns termination and reaping.
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// The built-in smoke scenario constant: empty scene (Camera3d + clear), a couple
/// of scripted actions, two beat captures, clean exit.
#[must_use]
pub fn smoke_scenario() -> Scenario {
    Scenario {
        name: "smoke".to_owned(),
        seed: 1234,
        ticks_per_second: 60,
        actions: vec![
            gone_harness::ScriptedAction::look(0, 15.0, 0.0),
            gone_harness::ScriptedAction {
                tick: 3,
                action: gone_harness::Action::MoveDelta {
                    forward: 1.0,
                    strafe: 0.0,
                },
            },
            gone_harness::ScriptedAction::press(5, gone_harness::Key::Activate),
            gone_harness::ScriptedAction::release(5, gone_harness::Key::Activate),
        ],
        beats: vec![
            gone_harness::Beat::new("beat-a", 2),
            gone_harness::Beat::new("beat-b", 8),
        ],
        pacing: None,
        max_frames: 600,
    }
}

#[derive(Debug)]
struct RunnerError(String);

impl fmt::Display for RunnerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(f)
    }
}

impl std::error::Error for RunnerError {}

macro_rules! bail {
    ($($arg:tt)*) => {
        return Err(RunnerError(format!($($arg)*)))
    };
}

fn repo_root() -> Result<PathBuf, RunnerError> {
    let dir = std::env::var_os("CARGO_MANIFEST_DIR")
        .ok_or_else(|| RunnerError("CARGO_MANIFEST_DIR is not set".into()))?;
    let mut current = Path::new(&dir).to_path_buf();
    loop {
        let manifest = current.join("Cargo.toml");
        if manifest.is_file()
            && std::fs::read_to_string(&manifest).is_ok_and(|text| text.contains("[workspace]"))
        {
            return Ok(current);
        }
        match current.parent() {
            Some(p) => current = p.to_path_buf(),
            None => bail!("no workspace root above {}", dir.to_string_lossy()),
        }
    }
}

fn run_id(seed: u64) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    format!("{nanos}-s{seed}")
}

/// Real SHA-256 of `bytes`, lowercase hex, the run-identity hash used
/// everywhere the protocol names a build, scenario, or config.
#[must_use]
fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    hex_of(&digest)
}

/// Lowercase hex of a byte slice.
#[must_use]
fn hex_of(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(out, "{b:02x}");
    }
    out
}

fn read_or(context: &str, path: &Path) -> Result<Vec<u8>, RunnerError> {
    std::fs::read(path)
        .map_err(|e| RunnerError(format!("failed to read {context} {}: {e}", path.display())))
}

fn write_or(context: &str, path: &Path, bytes: &[u8]) -> Result<(), RunnerError> {
    std::fs::write(path, bytes)
        .map_err(|e| RunnerError(format!("failed to write {context} {}: {e}", path.display())))
}

/// Spawn the app with harness env. The child is kept alive and reaped by this runner.
struct AppChild {
    child: Child,
}

impl Drop for AppChild {
    fn drop(&mut self) {
        // Never orphan: on drop (including panic paths) kill the child if it is
        // still running and reap it.
        if let Ok(None) = self.child.try_wait() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}

/// Spawn the app with harness env and the run-identity hashes.
fn spawn_app(
    root: &Path,
    scenario_path: &Path,
    out_dir: &Path,
    app_hash: &str,
    scenario_hash: &str,
    config_hash: &str,
) -> Result<AppChild, RunnerError> {
    let app = root.join("target").join("debug").join("gone_app");
    if !app.is_file() {
        bail!(
            "app binary not found: {} (build with cargo build first)",
            app.display()
        );
    }
    let child = Command::new(&app)
        .env(ENV_HARNESS, "1")
        .env(ENV_SCENARIO, scenario_path)
        .env(ENV_OUT_DIR, out_dir)
        .env(ENV_APP_HASH, app_hash)
        .env(ENV_SCENARIO_HASH, scenario_hash)
        .env("GONE_CONFIG_HASH", config_hash)
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .current_dir(root)
        .spawn()
        .map_err(|e| RunnerError(format!("failed to spawn {}: {e}", app.display())))?;
    Ok(AppChild { child })
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

fn run_scenario(
    root: &Path,
    scenario_path: &Path,
    scenario: &Scenario,
    out_root: &Path,
) -> Result<PathBuf, RunnerError> {
    let id = run_id(scenario.seed);
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

    let scenario_copy = run_dir.join("scenario.json");
    write_or("scenario copy", &scenario_copy, &scenario_bytes)?;

    let mut child = spawn_app(
        root,
        scenario_path,
        &run_dir,
        &app_hash,
        &scenario_hash,
        &config_hash,
    )?;
    let status = wait_for_app(&mut child, DEFAULT_TIMEOUT, &scenario.name)?;
    disband_scenario(&run_dir, &scenario_bytes);

    // The report is the app's own account of the run, including why it exited
    // nonzero (a deadline with uncaptured beats, a failed capture save), so
    // verify it first: a machine-check failure names the artifact. Only a run
    // whose report fully verifies falls back to the bare exit-status error.
    let report_path = run_dir.join("report.json");
    let report_bytes = read_or("report", &report_path)?;
    let report_text = String::from_utf8_lossy(&report_bytes);
    let parsed = report::parse_report(&report_text)
        .map_err(|e| RunnerError(format!("report parse: {e}")))?;

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

    verify_captures(scenario, &parsed, &run_dir)?;

    if !status.success() {
        bail!(
            "app exited nonzero ({status}) for scenario `{}`",
            scenario.name
        );
    }

    Ok(run_dir)
}

/// Wait for the app child to finish, killing it after `timeout` seconds.
fn wait_for_app(
    child: &mut AppChild,
    timeout: Duration,
    scenario: &str,
) -> Result<std::process::ExitStatus, RunnerError> {
    let start = Instant::now();
    loop {
        if start.elapsed() > timeout {
            child
                .child
                .kill()
                .map_err(|e| RunnerError(format!("kill failed: {e}")))?;
            let _ = child.child.wait();
            bail!(
                "scenario `{scenario}` timed out after {}s",
                timeout.as_secs()
            );
        }
        match child.child.try_wait() {
            Ok(Some(status)) => return Ok(status),
            Ok(None) => std::thread::sleep(Duration::from_millis(10)),
            Err(e) => bail!("waitpid error: {e}"),
        }
    }
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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    std::process::exit(dispatch(&args));
}

/// Route one command line to the smoke, compare, or scenario run.
fn dispatch(args: &[String]) -> i32 {
    match args.get(1).map(String::as_str) {
        None => {
            eprintln!("usage: gone-harness <smoke | compare <scenario> | <scenario.json>>");
            2
        }
        Some("smoke") => run_smoke(),
        Some("compare") => run_compare(args),
        Some(path) => run_one(path),
    }
}

fn run_smoke() -> i32 {
    let scenario = smoke_scenario();
    let root = repo_root().expect("root");
    let out_root = root.join("tmp").join("harness");
    let scenario_path = root.join("tmp").join("smoke-scenario.json");
    let json = scenario_to_json(&scenario).expect("scenario json");
    write_or("smoke scenario", &scenario_path, json.as_bytes()).expect("write");
    match run_scenario(&root, &scenario_path, &scenario, &out_root) {
        Ok(run_dir) => {
            println!(
                "MACHINE PASS: scenario `{}`; machine checks passed, visual verification pending",
                scenario.name
            );
            println!("ARTIFACTS: {}", run_dir.display());
            0
        }
        Err(e) => {
            eprintln!("{e}");
            println!("ARTIFACTS: {}", out_root.join(&scenario.name).display());
            1
        }
    }
}

fn run_compare(args: &[String]) -> i32 {
    let path_arg = args.get(2).map_or("smoke", String::as_str);
    let scenario_path = root_scenario(path_arg).expect("scenario path");
    let scenario = load_scenario(&scenario_path).expect("scenario");
    let root = repo_root().expect("root");
    let out_root = root.join("tmp").join("harness");
    let run_a = run_scenario(&root, &scenario_path, &scenario, &out_root).expect("run A");
    let run_b = run_scenario(&root, &scenario_path, &scenario, &out_root).expect("run B");
    let seq = |run: &Path| -> Vec<String> {
        let text = std::fs::read_to_string(run.join("report.json")).unwrap_or_default();
        report::parse_report(&text)
            .map(|r| r.events.iter().map(|e| format!("{e:?}")).collect())
            .unwrap_or_default()
    };
    let (a, b) = (seq(&run_a), seq(&run_b));
    if a == b {
        println!("COMPARE PASS: two runs identical ({} events)", a.len());
        0
    } else {
        let first = a.iter().zip(&b).position(|(x, y)| x != y).unwrap_or(0);
        println!("COMPARE DIVERGENCE at event {first}: {a:?} vs {b:?}");
        1
    }
}

fn run_one(path: &str) -> i32 {
    let scenario_path = root_scenario(path).expect("scenario path");
    let scenario = load_scenario(&scenario_path).expect("scenario");
    let root = repo_root().expect("root");
    let out_root = root.join("tmp").join("harness");
    match run_scenario(&root, &scenario_path, &scenario, &out_root) {
        Ok(run_dir) => {
            println!(
                "MACHINE PASS: scenario `{}`; machine checks passed, visual verification pending",
                scenario.name
            );
            println!("ARTIFACTS: {}", run_dir.display());
            0
        }
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}

fn root_scenario(arg: &str) -> Result<PathBuf, RunnerError> {
    if arg == "smoke" {
        let root = repo_root()?;
        return Ok(root.join("tmp").join("smoke-scenario.json"));
    }
    let p = PathBuf::from(arg);
    if p.is_absolute() {
        Ok(p)
    } else {
        Ok(repo_root()?.join(p))
    }
}

fn load_scenario(path: &Path) -> Result<Scenario, RunnerError> {
    let bytes = read_or("scenario file", path)?;
    let text = String::from_utf8_lossy(&bytes);
    parse_scenario(&text).map_err(RunnerError)
}
