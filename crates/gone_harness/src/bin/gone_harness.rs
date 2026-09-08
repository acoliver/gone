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
use gone_harness::{
    FrameSampleStats, PROTOCOL_VERSION, PerfPolicy, PerfPolicyIdentity, PerfVerdict, ScenarioMode,
    parse_perf_policy, perf_verdict_to_json, report,
};

const ENV_HARNESS: &str = "GONE_HARNESS";
const ENV_SCENARIO: &str = "GONE_SCENARIO";
const ENV_OUT_DIR: &str = "GONE_OUT_DIR";
/// The environment name for the app-binary content hash the runner computed.
const ENV_APP_HASH: &str = "GONE_APP_HASH";
/// The environment name for the scenario content hash the runner computed.
const ENV_SCENARIO_HASH: &str = "GONE_SCENARIO_HASH";
/// Scenario runtime timeout; the runner owns termination and reaping.
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);

/// Workspace-relative home of the checked-in perf policy the perf lane gates
/// with. The file ships with the repo; the runner hashes the exact bytes it
/// measured against into the run artifacts.
const PERF_POLICY_PATH: &str = "crates/gone_harness/perf-policy.json";

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
        mode: ScenarioMode::Capture,
        warmup_frames: 0,
        sample_frames: 0,
    }
}

/// The calibration perf scenario derived from the policy: the bootstrap scene
/// (clear + frame-code chip sprite) with no actions and no beats, the policy's
/// presentation pacing and warmup/sample window, and a frame deadline above
/// the window (inert on this lane — a perf scenario has no beats to miss, but
/// the scenario stays self-describing).
#[must_use]
fn perf_calibration_scenario(policy: &PerfPolicy) -> Scenario {
    Scenario {
        name: "perf-calibration".to_owned(),
        seed: 1234,
        ticks_per_second: gone_harness::TICKS_PER_SECOND,
        actions: Vec::new(),
        beats: Vec::new(),
        pacing: Some(policy.presentation),
        max_frames: policy.warmup_frames + policy.sample_frames + 120,
        mode: ScenarioMode::Perf,
        warmup_frames: policy.warmup_frames,
        sample_frames: policy.sample_frames,
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

/// Route one command line to the smoke, perf, compare, or scenario run.
fn dispatch(args: &[String]) -> i32 {
    match args.get(1).map(String::as_str) {
        None => {
            eprintln!(
                "usage: gone-harness <smoke | perf [scenario] | compare <scenario> | <scenario.json>>"
            );
            2
        }
        Some("smoke") => run_smoke(),
        Some("perf") => run_perf(args),
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

/// The perf lane: run the calibration scenario capture-free, then judge the
/// report's recorded frame-time statistics against the checked-in policy.
/// Exit 0 on pass, 1 on any failure or threshold breach.
fn run_perf(args: &[String]) -> i32 {
    match perf_impl(args) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}

fn perf_impl(args: &[String]) -> Result<i32, RunnerError> {
    let root = repo_root()?;
    let policy_path = root.join(PERF_POLICY_PATH);
    let policy_bytes = read_or("perf policy", &policy_path)?;
    let policy = parse_perf_policy(&String::from_utf8_lossy(&policy_bytes)).map_err(RunnerError)?;
    // The policy is frozen before measurement: identity is the version string
    // plus the hash of the exact bytes this run is judged against.
    let identity = PerfPolicyIdentity {
        policy_version: policy.policy_version.clone(),
        sha256: sha256_hex(&policy_bytes),
    };

    let (scenario_path, scenario) = resolve_perf_scenario(args, &root, &policy)?;
    let out_root = root.join("tmp").join("harness");
    let run_dir = run_scenario(&root, &scenario_path, &scenario, &out_root)?;

    let report_bytes = read_or("report", &run_dir.join("report.json"))?;
    let parsed = report::parse_report(&String::from_utf8_lossy(&report_bytes))
        .map_err(|e| RunnerError(format!("report parse: {e}")))?;
    let perf = parsed.perf.as_ref().ok_or_else(|| {
        RunnerError("report has no perf section; the app did not run the perf lane".into())
    })?;

    verify_run_shape(&policy, perf)?;
    let violations = policy.thresholds.violations(&perf.stats);
    let verdict = PerfVerdict {
        passed: violations.is_empty(),
        policy: identity,
        violations: violations.clone(),
        stats: perf.stats.clone(),
    };
    let verdict_text = perf_verdict_to_json(&verdict)
        .map_err(|e| RunnerError(format!("verdict artifact: {e}")))?;
    write_or(
        "perf verdict",
        &run_dir.join("perf-verdict.json"),
        verdict_text.as_bytes(),
    )?;

    println!("{}", verdict_line(&verdict));
    println!("{}", distribution_line(&policy, &verdict.stats));
    println!("ARTIFACTS: {}", run_dir.display());
    Ok(i32::from(!verdict.passed))
}

/// The perf scenario to run: the policy-derived calibration scenario by
/// default, or the scenario file named on the command line (which must be a
/// perf-mode scenario — a capture scenario in the perf lane is a caller error).
fn resolve_perf_scenario(
    args: &[String],
    root: &Path,
    policy: &PerfPolicy,
) -> Result<(PathBuf, Scenario), RunnerError> {
    match args.get(2) {
        None => {
            let scenario = perf_calibration_scenario(policy);
            let path = root.join("tmp").join("perf-scenario.json");
            let json = scenario_to_json(&scenario)
                .map_err(|e| RunnerError(format!("perf scenario serialize: {e}")))?;
            write_or("perf scenario", &path, json.as_bytes())?;
            Ok((path, scenario))
        }
        Some(arg) => {
            let path = root_scenario(arg)?;
            let scenario = load_scenario(&path)?;
            if scenario.mode != ScenarioMode::Perf {
                bail!(
                    "scenario `{}` is not a perf-mode scenario (its `mode` must be `perf`)",
                    scenario.name
                );
            }
            Ok((path, scenario))
        }
    }
}

/// The measured window must be the policy's window: a verdict names a policy,
/// so the run judged by it must have the policy's shape (window, presentation,
/// resolution). These are identity checks, not thresholds.
fn verify_run_shape(policy: &PerfPolicy, perf: &gone_harness::PerfRun) -> Result<(), RunnerError> {
    if perf.warmup_frames != policy.warmup_frames || perf.sample_frames != policy.sample_frames {
        bail!(
            "run shape mismatch: policy warmup+sample {}+{}, report {}+{}",
            policy.warmup_frames,
            policy.sample_frames,
            perf.warmup_frames,
            perf.sample_frames
        );
    }
    if perf.presentation != policy.presentation {
        bail!(
            "presentation mismatch: policy {:?}, run {:?}",
            policy.presentation,
            perf.presentation
        );
    }
    if perf.resolution != policy.resolution {
        bail!(
            "resolution mismatch: policy {}x{}, run {}x{}",
            policy.resolution.width,
            policy.resolution.height,
            perf.resolution.width,
            perf.resolution.height
        );
    }
    Ok(())
}

/// The single-line verdict: PASS or FAIL, the policy identity, and on a fail
/// each violated statistic with its observed value and threshold.
#[must_use]
fn verdict_line(verdict: &PerfVerdict) -> String {
    let head = if verdict.passed {
        "PERF PASS"
    } else {
        "PERF FAIL"
    };
    let mut line = format!(
        "{head}: policy `{}` sha256 {}",
        verdict.policy.policy_version, verdict.policy.sha256
    );
    for violation in &verdict.violations {
        let _ = write!(line, "; {violation}");
    }
    line
}

/// The distribution summary over exactly the policy's reported statistics.
#[must_use]
fn distribution_line(policy: &PerfPolicy, stats: &FrameSampleStats) -> String {
    let mut line = String::from("DISTRIBUTIONS:");
    for stat in &policy.statistics {
        let _ = write!(line, " {} {:.3}", stat.name(), stat.value(stats));
    }
    line
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

#[cfg(test)]
mod tests {
    use gone_harness::{
        FrameSampleStats, FrameStatistic, Pacing, PerfResolution, PerfThresholds, PerfVerdict,
        ScenarioMode, ThresholdViolation,
    };

    use super::{PERF_POLICY_PATH, distribution_line, perf_calibration_scenario, verdict_line};

    /// The checked-in policy is the lane's frozen contract: it must always
    /// parse, and its thresholds must sit on statistics it reports.
    #[test]
    fn checked_in_policy_parses() {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/perf-policy.json");
        assert!(
            path.ends_with(PERF_POLICY_PATH),
            "the include_str'd policy is the file the runtime path names"
        );
        let policy = gone_harness::parse_perf_policy(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/perf-policy.json"
        )))
        .expect("checked-in policy is valid");
        assert!(!policy.policy_version.is_empty(), "the policy is versioned");
        assert_eq!(policy.presentation, Pacing::Uncapped);
        assert_eq!(policy.resolution, PerfResolution::new(1920, 1080));
        assert!(policy.sample_frames >= 1);
        assert!(policy.camera_route.contains("static"));
    }

    #[test]
    fn calibration_scenario_matches_the_policy() {
        let policy = gone_harness::parse_perf_policy(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/perf-policy.json"
        )))
        .expect("checked-in policy is valid");
        let scenario = perf_calibration_scenario(&policy);
        assert_eq!(scenario.mode, ScenarioMode::Perf);
        assert!(scenario.actions.is_empty(), "calibration has no actions");
        assert!(scenario.beats.is_empty(), "calibration has no beats");
        assert_eq!(scenario.pacing, Some(policy.presentation));
        assert_eq!(scenario.warmup_frames, policy.warmup_frames);
        assert_eq!(scenario.sample_frames, policy.sample_frames);
        assert!(
            scenario.max_frames >= policy.warmup_frames + policy.sample_frames,
            "the deadline never lands inside the measured window"
        );
    }

    fn verdict(mean_ms: f64, p95_ms: f64) -> PerfVerdict {
        let stats = FrameSampleStats {
            count: 600,
            mean_ms,
            min_ms: 1.0,
            max_ms: 90.0,
            p50_ms: 2.0,
            p95_ms,
            p99_ms: 60.0,
        };
        let thresholds = PerfThresholds {
            mean_ms_max: 25.0,
            p95_ms_max: 50.0,
        };
        let violations = thresholds.violations(&stats);
        PerfVerdict {
            passed: violations.is_empty(),
            policy: gone_harness::PerfPolicyIdentity {
                policy_version: "calibration-v1".to_owned(),
                sha256: "3f2a".to_owned(),
            },
            violations,
            stats,
        }
    }

    #[test]
    fn pass_verdict_is_one_line_naming_the_policy() {
        let line = verdict_line(&verdict(2.0, 3.0));
        assert!(line.starts_with("PERF PASS"), "{line}");
        assert!(line.contains("calibration-v1"), "{line}");
        assert!(line.contains("3f2a"), "the policy hash travels: {line}");
    }

    #[test]
    fn fail_verdict_names_the_violated_statistic_and_threshold() {
        let line = verdict_line(&verdict(31.0, 30.0));
        assert!(line.starts_with("PERF FAIL"), "{line}");
        assert!(
            line.contains("mean_ms 31.000 exceeds limit 25.000"),
            "the violated statistic, observed value, and limit are named: {line}"
        );
        assert!(
            !line.contains("p95_ms"),
            "only the violated statistic is named: {line}"
        );
    }

    #[test]
    fn distribution_line_lists_the_policy_statistics_in_order() {
        let policy = gone_harness::parse_perf_policy(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/perf-policy.json"
        )))
        .expect("checked-in policy is valid");
        let line = distribution_line(&policy, &verdict(2.0, 3.0).stats);
        let expected: Vec<&str> = policy
            .statistics
            .iter()
            .map(|stat: &FrameStatistic| stat.name())
            .collect();
        let mut names = line
            .split(' ')
            .filter(|word| word.contains("_ms") || *word == "count");
        for expected_name in &expected {
            assert_eq!(
                names.next(),
                Some(*expected_name),
                "statistics appear in policy order: {line}"
            );
        }
        assert_eq!(
            names.next(),
            None,
            "no statistics beyond the policy's list: {line}"
        );
    }

    #[test]
    fn threshold_violation_display_is_verdict_ready() {
        let v = ThresholdViolation {
            statistic: FrameStatistic::P95Ms,
            observed_ms: 55.25,
            limit_ms: 50.0,
        };
        assert_eq!(v.to_string(), "p95_ms 55.250 exceeds limit 50.000");
    }
}
