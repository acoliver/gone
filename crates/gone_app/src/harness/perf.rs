//! Performance-lane protocol (issue #5 stage A).
//!
//! Three pieces live here:
//!
//! * [`PerfPolicy`] is the versioned measurement policy the runner loads from a
//!   checked-in JSON file (`crates/gone_harness/perf-policy.json`) and gates a
//!   run with. The policy is frozen before measurement: the runner parses and
//!   hashes the exact file bytes before spawning the app, and the policy
//!   identity ([`PerfPolicyIdentity`], version + content hash) travels into
//!   the run artifacts.
//! * [`FrameSampleStats`] and [`PerfRun`] are the app's account of one perf
//!   run: the raw wall-clock frame-time samples plus summary statistics
//!   (count, mean, min, max, and the nearest-rank p50/p95/p99 percentiles),
//!   written into the report's optional `perf` section.
//! * [`PerfVerdict`] is the runner's pass/fail artifact, written beside the
//!   report and naming the violated statistic and threshold on a fail.
//!
//! Frame times are wall-clock and inherently non-deterministic: the perf lane
//! carries raw samples rather than reproducible identities and is excluded
//! from the harness's compare/determinism claims. The statistics are judged
//! against policy thresholds, never against a second run.

use std::fmt;

use super::scenario::Pacing;

/// Physical resolution a perf run measured at.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct PerfResolution {
    /// Width in physical pixels.
    pub width: u32,
    /// Height in physical pixels.
    pub height: u32,
}

impl PerfResolution {
    /// A resolution from width and height.
    #[must_use]
    pub const fn new(width: u32, height: u32) -> Self {
        Self { width, height }
    }
}

/// One named frame-time statistic, as listed by the policy's `statistics` set.
#[derive(
    Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, serde::Serialize, serde::Deserialize,
)]
pub enum FrameStatistic {
    /// Number of samples in the window.
    Count,
    /// Mean frame time in ms.
    MeanMs,
    /// Minimum frame time in ms.
    MinMs,
    /// Maximum frame time in ms.
    MaxMs,
    /// 50th-percentile frame time in ms (nearest rank).
    P50Ms,
    /// 95th-percentile frame time in ms (nearest rank).
    P95Ms,
    /// 99th-percentile frame time in ms (nearest rank).
    P99Ms,
}

impl FrameStatistic {
    /// The statistic's name as printed in verdicts and distribution summaries.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Count => "count",
            Self::MeanMs => "mean_ms",
            Self::MinMs => "min_ms",
            Self::MaxMs => "max_ms",
            Self::P50Ms => "p50_ms",
            Self::P95Ms => "p95_ms",
            Self::P99Ms => "p99_ms",
        }
    }

    /// This statistic's value over a recorded sample window.
    ///
    /// # Panics
    /// Panics for a window of more than `u32::MAX` samples: the exact f64
    /// conversion is guaranteed that far past any measurable window, so a
    /// larger count fails loudly instead of rounding.
    #[must_use]
    pub fn value(self, stats: &FrameSampleStats) -> f64 {
        match self {
            Self::Count => sample_count_f64(stats.count),
            Self::MeanMs => stats.mean_ms,
            Self::MinMs => stats.min_ms,
            Self::MaxMs => stats.max_ms,
            Self::P50Ms => stats.p50_ms,
            Self::P95Ms => stats.p95_ms,
            Self::P99Ms => stats.p99_ms,
        }
    }
}

/// Summary statistics over one frame-time sample window (ms, except `count`).
#[derive(Clone, Debug, Default, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct FrameSampleStats {
    /// Samples measured.
    pub count: u64,
    /// Mean frame time in ms.
    pub mean_ms: f64,
    /// Minimum frame time in ms.
    pub min_ms: f64,
    /// Maximum frame time in ms.
    pub max_ms: f64,
    /// 50th-percentile frame time in ms (nearest rank).
    pub p50_ms: f64,
    /// 95th-percentile frame time in ms (nearest rank).
    pub p95_ms: f64,
    /// 99th-percentile frame time in ms (nearest rank).
    pub p99_ms: f64,
}

impl FrameSampleStats {
    /// Summarize a sample window. `None` when the window is empty: an empty
    /// window has no mean and no percentiles, and the lane never invents one.
    #[must_use]
    pub fn from_samples(samples_ms: &[f64]) -> Option<Self> {
        let count = samples_ms.len();
        if count == 0 {
            return None;
        }
        let mut sorted = samples_ms.to_vec();
        sorted.sort_by(f64::total_cmp);
        let mean = samples_ms.iter().sum::<f64>() / sample_count_f64(count as u64);
        Some(Self {
            count: count as u64,
            mean_ms: mean,
            min_ms: sorted[0],
            max_ms: sorted[count - 1],
            p50_ms: percentile(&sorted, 50),
            p95_ms: percentile(&sorted, 95),
            p99_ms: percentile(&sorted, 99),
        })
    }
}

/// Exact `f64` for a sample count. `f64` represents integers exactly through
/// `2^53`, so the `u32` bound sits nowhere near the rounding cliff, and a
/// window that large cannot be measured in this lane's lifetime: fail fast
/// instead of quietly dividing by a rounded count.
fn sample_count_f64(count: u64) -> f64 {
    f64::from(u32::try_from(count).expect("sample window holds more than u32::MAX frames"))
}

/// Nearest-rank `p`th percentile (`p` in 1..=100) of an ascending-sorted
/// window. The rank is `ceil(p * n / 100)` in exact integer math, 1-based, so
/// the small-window edge cases are the documented ones: p95 of ten samples is
/// the maximum, and p50 of one hundred is the 50th order statistic.
#[must_use]
fn percentile(sorted: &[f64], p: u64) -> f64 {
    let n = sorted.len() as u64;
    let rank = usize::try_from((p * n).div_ceil(100))
        .expect("percentile rank is within the window length");
    sorted[rank - 1]
}

/// One threshold breach: the statistic, its measured value, and the policy
/// ceiling it exceeded.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ThresholdViolation {
    /// The statistic that breached.
    pub statistic: FrameStatistic,
    /// The measured value in ms (or samples, for `Count`).
    pub observed_ms: f64,
    /// The policy ceiling in ms.
    pub limit_ms: f64,
}

impl fmt::Display for ThresholdViolation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{} {:.3} exceeds limit {:.3}",
            self.statistic.name(),
            self.observed_ms,
            self.limit_ms
        )
    }
}

/// The thresholds a policy enforces on the recorded statistics: ceilings in ms
/// over the sample window. A measured statistic above its ceiling violates
/// the policy and fails the run.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PerfThresholds {
    /// Mean frame-time ceiling in ms.
    pub mean_ms_max: f64,
    /// 95th-percentile frame-time ceiling in ms.
    pub p95_ms_max: f64,
}

impl PerfThresholds {
    /// The statistics these thresholds are expressed on. A policy must list
    /// each of them under `statistics`, so a threshold can never reference a
    /// number the lane does not report.
    pub const ENFORCED_STATISTICS: [FrameStatistic; 2] =
        [FrameStatistic::MeanMs, FrameStatistic::P95Ms];

    /// The run's threshold breaches, in policy order (mean first, then p95);
    /// empty when every threshold held.
    #[must_use]
    pub fn violations(&self, stats: &FrameSampleStats) -> Vec<ThresholdViolation> {
        let checked = [
            (FrameStatistic::MeanMs, self.mean_ms_max),
            (FrameStatistic::P95Ms, self.p95_ms_max),
        ];
        checked
            .into_iter()
            .filter_map(|(statistic, limit_ms)| {
                let observed_ms = statistic.value(stats);
                (observed_ms > limit_ms).then_some(ThresholdViolation {
                    statistic,
                    observed_ms,
                    limit_ms,
                })
            })
            .collect()
    }
}

/// The versioned performance policy. Frozen before measurement: the runner
/// parses and hashes the file, then spawns the app, then judges the run's
/// recorded statistics against these thresholds. Any policy change is a new
/// `policy_version`.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PerfPolicy {
    /// Policy version string, bumped on every policy change.
    pub policy_version: String,
    /// Frames run after readiness before sampling starts (unrecorded warmup).
    pub warmup_frames: u64,
    /// Rendered frames sampled into the recorded window.
    pub sample_frames: u64,
    /// Presentation pacing the run uses. `Uncapped` keeps wall-clock frame
    /// times from being quantized by vsync.
    pub presentation: Pacing,
    /// Camera route description for the calibration scene. Recorded, never
    /// simulated: the lane does not fake motion the scene does not run.
    pub camera_route: String,
    /// Concurrent effects running during the sample window (none in the
    /// calibration scene; recorded so the measured scene is unambiguous).
    pub concurrent_effects: String,
    /// Physical resolution the run measures at.
    pub resolution: PerfResolution,
    /// Statistics the lane reports for the sample window.
    pub statistics: Vec<FrameStatistic>,
    /// Thresholds the runner enforces on the recorded statistics.
    pub thresholds: PerfThresholds,
}

impl PerfPolicy {
    fn validate(&self) -> Result<(), String> {
        if self.sample_frames == 0 {
            return Err("perf policy: sample_frames must be at least 1".to_owned());
        }
        for stat in PerfThresholds::ENFORCED_STATISTICS {
            if !self.statistics.contains(&stat) {
                return Err(format!(
                    "perf policy: threshold statistic `{}` is not in the reported `statistics` list",
                    stat.name()
                ));
            }
        }
        Ok(())
    }
}

/// Parse a perf policy from JSON text, validating internal consistency: the
/// sample window must be nonempty and every threshold statistic must be one
/// the policy reports.
///
/// # Errors
/// A message when the JSON is invalid, the sample window is empty, or a
/// threshold references an unreported statistic.
pub fn parse_perf_policy(text: &str) -> Result<PerfPolicy, String> {
    let policy: PerfPolicy =
        serde_json::from_str(text).map_err(|e| format!("perf policy parse error: {e}"))?;
    policy.validate()?;
    Ok(policy)
}

/// The perf lane's report section: what the app ran and measured. The raw
/// samples are wall-clock ms in sample order and are not reproducible
/// run-to-run; only the thresholds judge them.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PerfRun {
    /// Warmup frames the app ran before sampling (as the scenario declared).
    pub warmup_frames: u64,
    /// Sampled frames in the window (as the scenario declared).
    pub sample_frames: u64,
    /// Presentation pacing the run used (what the window was configured with).
    pub presentation: Pacing,
    /// Physical resolution the run measured at.
    pub resolution: PerfResolution,
    /// Raw wall-clock frame times in ms, in sample order.
    pub samples_ms: Vec<f64>,
    /// Summary statistics over `samples_ms`.
    pub stats: FrameSampleStats,
}

/// The policy identity recorded into run artifacts: the version string plus
/// the sha2-256 of the exact policy file bytes the run was gated with.
#[derive(Clone, Debug, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct PerfPolicyIdentity {
    /// The policy's version string.
    pub policy_version: String,
    /// sha2-256 (lowercase hex) of the policy file bytes.
    pub sha256: String,
}

/// The runner's perf verdict, written as `perf-verdict.json` beside the run's
/// report: the decision, the policy identity that decided it, the threshold
/// breaches (empty on a pass), and the recorded distribution summary.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct PerfVerdict {
    /// True when every policy threshold held.
    pub passed: bool,
    /// Which policy judged the run.
    pub policy: PerfPolicyIdentity,
    /// Threshold breaches, in policy order; empty on a pass.
    pub violations: Vec<ThresholdViolation>,
    /// The recorded distribution summary.
    pub stats: FrameSampleStats,
}

/// Write a perf verdict as JSON text.
///
/// # Errors
/// Returns a message when the verdict cannot be serialized.
pub fn perf_verdict_to_json(verdict: &PerfVerdict) -> Result<String, String> {
    serde_json::to_string_pretty(verdict).map_err(|e| format!("perf verdict serialize: {e}"))
}

#[cfg(test)]
mod tests {
    use super::{
        FrameSampleStats, FrameStatistic, PerfPolicyIdentity, PerfResolution, PerfRun, PerfVerdict,
        ThresholdViolation, parse_perf_policy, perf_verdict_to_json,
    };
    use crate::harness::scenario::Pacing;

    /// A policy-shaped JSON with the given threshold and statistics list.
    fn policy_json(thresholds: &str, statistics: &str) -> String {
        format!(
            r#"{{
                "policy_version": "calibration-v1",
                "warmup_frames": 12,
                "sample_frames": 100,
                "presentation": "Uncapped",
                "camera_route": "static",
                "concurrent_effects": "none",
                "resolution": {{"width": 1920, "height": 1080}},
                "statistics": {statistics},
                "thresholds": {thresholds}
            }}"#
        )
    }

    const FULL_STATISTICS: &str =
        r#"["Count", "MeanMs", "MinMs", "MaxMs", "P50Ms", "P95Ms", "P99Ms"]"#;

    /// Exact-equality assertion for the f64 statistics these tests check.
    /// Every expected value (integer sums, exact divisions, and sorted-element
    /// picks) is exactly representable, so correctly rounded arithmetic must
    /// land on it bit for bit: even a one-ulp mismatch is a real bug, not
    /// rounding noise.
    fn assert_stat_eq(actual: f64, expected: f64) {
        assert!(
            (actual - expected).abs() < f64::EPSILON,
            "expected {expected}, got {actual}"
        );
    }

    #[test]
    fn policy_parses() {
        let policy = parse_perf_policy(&policy_json(
            r#"{"mean_ms_max": 25.0, "p95_ms_max": 50.0}"#,
            FULL_STATISTICS,
        ))
        .expect("valid policy");
        assert_eq!(policy.policy_version, "calibration-v1");
        assert_eq!(policy.warmup_frames, 12);
        assert_eq!(policy.sample_frames, 100);
        assert_eq!(policy.presentation, Pacing::Uncapped);
        assert_eq!(policy.resolution, PerfResolution::new(1920, 1080));
        assert_eq!(policy.statistics.len(), 7);
        assert_stat_eq(policy.thresholds.mean_ms_max, 25.0);
        assert_stat_eq(policy.thresholds.p95_ms_max, 50.0);
    }

    #[test]
    fn policy_parse_rejects_malformed_json_and_missing_fields() {
        assert!(parse_perf_policy("{ nope").is_err());
        let missing_version = policy_json(
            r#"{"mean_ms_max": 25.0, "p95_ms_max": 50.0}"#,
            FULL_STATISTICS,
        )
        .replace("policy_version", "version");
        assert!(
            parse_perf_policy(&missing_version).is_err(),
            "a policy without a version string must not parse"
        );
    }

    #[test]
    fn policy_parse_rejects_an_empty_sample_window() {
        let json = policy_json(
            r#"{"mean_ms_max": 25.0, "p95_ms_max": 50.0}"#,
            FULL_STATISTICS,
        )
        .replace("\"sample_frames\": 100", "\"sample_frames\": 0");
        let err = parse_perf_policy(&json).expect_err("zero-sample window must fail");
        assert!(
            err.contains("sample_frames"),
            "error names the field: {err}"
        );
    }

    #[test]
    fn policy_parse_rejects_thresholds_on_unreported_statistics() {
        let listed = r#"["Count", "MeanMs"]"#;
        let err = parse_perf_policy(&policy_json(
            r#"{"mean_ms_max": 25.0, "p95_ms_max": 50.0}"#,
            listed,
        ))
        .expect_err("p95 threshold without a p95 report must fail");
        assert!(
            err.contains("p95_ms"),
            "error names the unreported statistic: {err}"
        );
    }

    #[test]
    fn statistics_math_is_exact_on_a_known_vector() {
        // 1..=100: mean 50.5, and the nearest-rank percentiles are the order
        // statistics ceil(p * n / 100): p50 -> 50th, p95 -> 95th, p99 -> 99th.
        let samples: Vec<f64> = (1..=100).map(f64::from).collect();
        let stats = FrameSampleStats::from_samples(&samples).expect("nonempty");
        assert_eq!(stats.count, 100);
        assert_stat_eq(stats.mean_ms, 50.5);
        assert_stat_eq(stats.min_ms, 1.0);
        assert_stat_eq(stats.max_ms, 100.0);
        assert_stat_eq(stats.p50_ms, 50.0);
        assert_stat_eq(stats.p95_ms, 95.0);
        assert_stat_eq(stats.p99_ms, 99.0);
    }

    #[test]
    fn small_windows_use_the_nearest_rank_rules() {
        // Ten samples 1..=10: p50 rank is ceil(5) = 5 -> 5.0; the p95 and p99
        // ranks both ceil past the 9.5 and 9.9 marks to the maximum.
        let samples: Vec<f64> = (1..=10).map(f64::from).collect();
        let stats = FrameSampleStats::from_samples(&samples).expect("nonempty");
        assert_stat_eq(stats.p50_ms, 5.0);
        assert_stat_eq(stats.p95_ms, 10.0);
        assert_stat_eq(stats.p99_ms, 10.0);
        // Input order must not matter: the same window shuffled agrees.
        let mut shuffled = samples.clone();
        shuffled.reverse();
        assert_eq!(FrameSampleStats::from_samples(&shuffled), Some(stats));
    }

    #[test]
    fn empty_samples_have_no_statistics() {
        assert_eq!(FrameSampleStats::from_samples(&[]), None);
    }

    /// A constant window of 600 samples at `value_ms`: its mean and every
    /// percentile equal `value_ms` exactly.
    fn constant_stats(value_ms: f64) -> FrameSampleStats {
        FrameSampleStats::from_samples(&vec![value_ms; 600]).expect("nonempty")
    }

    #[test]
    fn clean_statistics_pass_the_thresholds() {
        let thresholds = super::PerfThresholds {
            mean_ms_max: 25.0,
            p95_ms_max: 50.0,
        };
        assert_eq!(
            thresholds.violations(&constant_stats(2.0)),
            Vec::new(),
            "a 2 ms window is inside both ceilings"
        );
    }

    #[test]
    fn mean_violation_is_named_with_observed_and_limit() {
        let thresholds = super::PerfThresholds {
            mean_ms_max: 25.0,
            p95_ms_max: 50.0,
        };
        let violations = thresholds.violations(&constant_stats(31.0));
        assert_eq!(
            violations.len(),
            1,
            "only the mean breaches: {violations:?}"
        );
        let v = violations[0];
        assert_eq!(v.statistic, FrameStatistic::MeanMs);
        assert_eq!(v.statistic.name(), "mean_ms");
        assert!((v.observed_ms - 31.0).abs() < f64::EPSILON);
        assert!((v.limit_ms - 25.0).abs() < f64::EPSILON);
        let text = v.to_string();
        assert!(
            text.contains("mean_ms") && text.contains("31") && text.contains("25"),
            "violation renders the statistic, observed, and limit: {text}"
        );
    }

    #[test]
    fn both_violations_report_in_policy_order() {
        let thresholds = super::PerfThresholds {
            mean_ms_max: 25.0,
            p95_ms_max: 50.0,
        };
        let violations = thresholds.violations(&constant_stats(60.0));
        assert_eq!(violations.len(), 2);
        assert_eq!(violations[0].statistic, FrameStatistic::MeanMs);
        assert_eq!(violations[1].statistic, FrameStatistic::P95Ms);
    }

    #[test]
    fn perf_run_report_roundtrip_with_samples() {
        let samples: Vec<f64> = (1..=100).map(f64::from).collect();
        let run = PerfRun {
            warmup_frames: 12,
            sample_frames: 100,
            presentation: Pacing::Uncapped,
            resolution: PerfResolution::new(1920, 1080),
            samples_ms: samples.clone(),
            stats: FrameSampleStats::from_samples(&samples).expect("nonempty"),
        };
        let text = serde_json::to_string(&run).expect("serializes");
        let parsed: PerfRun = serde_json::from_str(&text).expect("parses");
        assert_eq!(parsed, run);
        assert_eq!(parsed.samples_ms.len(), 100);
    }

    #[test]
    fn verdict_artifact_roundtrips() {
        let verdict = PerfVerdict {
            passed: false,
            policy: PerfPolicyIdentity {
                policy_version: "calibration-v1".to_owned(),
                sha256: "ab12".to_owned(),
            },
            violations: vec![ThresholdViolation {
                statistic: FrameStatistic::MeanMs,
                observed_ms: 31.5,
                limit_ms: 25.0,
            }],
            stats: FrameSampleStats {
                count: 600,
                mean_ms: 31.5,
                min_ms: 1.0,
                max_ms: 90.0,
                p50_ms: 30.0,
                p95_ms: 45.0,
                p99_ms: 60.0,
            },
        };
        let json = perf_verdict_to_json(&verdict).expect("serializes");
        let parsed: PerfVerdict = serde_json::from_str(&json).expect("parses");
        assert_eq!(parsed, verdict);
        assert!(json.contains("mean_ms"), "the artifact names the statistic");
    }
}
