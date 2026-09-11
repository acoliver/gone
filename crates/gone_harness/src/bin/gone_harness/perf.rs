//! The perf lane: run the calibration scenario capture-free, then judge the
//! report's recorded frame-time statistics against the checked-in policy.

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gone_harness::scenario::{Scenario, scenario_to_json};
use gone_harness::{
    Content, FrameSampleStats, PerfPolicy, PerfPolicyIdentity, PerfVerdict, ScenarioMode,
    parse_perf_policy, perf_verdict_to_json, report,
};

use crate::error::{RunnerError, bail};
use crate::hash::sha256_hex;
use crate::paths::{load_scenario, read_or, repo_root, root_scenario, write_or};
use crate::run::run_scenario;

/// Workspace-relative home of the checked-in perf policy the perf lane gates
/// with. The file ships with the repo; the runner hashes the exact bytes it
/// measured against into the run artifacts.
const PERF_POLICY_PATH: &str = "crates/gone_harness/perf-policy.json";

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
        content: Content::Calibration,
        calibration: None,
    }
}

/// The perf lane: run the calibration scenario capture-free, then judge the
/// report's recorded frame-time statistics against the checked-in policy.
/// Exit 0 on pass, 1 on any failure or threshold breach. `render_check` is
/// accepted for signature symmetry; a beatless perf scenario fails fast in
/// [`run_scenario`] because the canary captures at the first beat.
pub(crate) fn run_perf(args: &[String], render_check: bool) -> i32 {
    match perf_impl(args, render_check) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("{e}");
            1
        }
    }
}

fn perf_impl(args: &[String], render_check: bool) -> Result<i32, RunnerError> {
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
    let run_dir = run_scenario(&root, &scenario_path, &scenario, &out_root, render_check)?;

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
