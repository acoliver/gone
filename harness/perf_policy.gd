class_name HarnessPerfPolicy
extends RefCounted
## The perf lane's versioned measurement policy and its math, ported from
## Rust harness/perf.rs. One checked-in policy file (harness/perf-policy
## .json) is the single copy: the runner parses + hashes its exact bytes
## before spawning the app, the app reads the same file through
## GONE_PERF_POLICY, and the runner judges the report's recorded stats
## against these thresholds. Wall-clock samples are non-deterministic by
## nature; only the thresholds judge them, never a second run.

const ENFORCED_STATISTICS: Array[String] = ["MeanMs", "P95Ms"]
const STATISTIC_NAMES: Dictionary = {
	"Count": "count", "MeanMs": "mean_ms", "MinMs": "min_ms", "MaxMs": "max_ms",
	"P50Ms": "p50_ms", "P95Ms": "p95_ms", "P99Ms": "p99_ms",
}

static func parse_policy(text: String) -> Dictionary:
	var parsed = JSON.parse_string(text)
	if parsed == null or not (parsed is Dictionary):
		return {"policy": null, "error": "perf policy parse error: not a JSON object"}
	var data: Dictionary = parsed
	var policy := {}
	for key: String in ["policy_version", "presentation", "camera_route", "concurrent_effects"]:
		if not data.has(key) or not (data[key] is String) or String(data[key]).is_empty():
			return {"policy": null, "error": "perf policy parse error: missing `%s`" % key}
		policy[key] = data[key]
	policy.warmup_frames = int(data.get("warmup_frames", 0))
	policy.sample_frames = int(data.get("sample_frames", 0))
	if policy.sample_frames < 1:
		return {"policy": null,
			"error": "perf policy: sample_frames must be at least 1"}
	var resolution: Dictionary = data.get("resolution", {})
	if not (resolution is Dictionary) or not resolution.has("width") or not resolution.has("height"):
		return {"policy": null, "error": "perf policy parse error: missing resolution"}
	policy.resolution = {"width": int(resolution.width), "height": int(resolution.height)}
	var statistics: Array = data.get("statistics", [])
	var names: Array[String] = []
	for entry in statistics:
		var name := String(entry)
		if not STATISTIC_NAMES.has(name):
			return {"policy": null,
				"error": "perf policy: unknown statistic `%s`" % name}
		names.append(name)
	for enforced: String in ENFORCED_STATISTICS:
		if not names.has(enforced):
			return {"policy": null,
				"error": "perf policy: threshold statistic `%s` is not in the reported `statistics` list" % STATISTIC_NAMES[enforced]}
	policy.statistics = names
	var thresholds: Dictionary = data.get("thresholds", {})
	if not thresholds.has("mean_ms_max") or not thresholds.has("p95_ms_max"):
		return {"policy": null, "error": "perf policy parse error: missing thresholds"}
	policy.thresholds = {"mean_ms_max": float(thresholds.mean_ms_max),
		"p95_ms_max": float(thresholds.p95_ms_max)}
	return {"policy": policy, "error": ""}

## Nearest-rank p-th percentile (1..=100) of an ascending-sorted window:
## rank ceil(p*n/100), 1-based, so p95 of ten samples is the maximum.
static func percentile(sorted: Array, p: int) -> float:
	var n: int = sorted.size()
	var rank: int = ceili(p * n / 100.0)
	return float(sorted[clampi(rank - 1, 0, n - 1)])

## Summary statistics over one sample window; {} when the window is empty
## (an empty window has no mean and no percentiles, never an invented one).
static func stats_from_samples(samples_ms: Array) -> Dictionary:
	var count: int = samples_ms.size()
	if count == 0:
		return {}
	var sorted: Array = samples_ms.duplicate()
	sorted.sort()
	var total: float = 0.0
	for sample: float in samples_ms:
		total += sample
	var mean: float = total / float(count)
	return {
		"count": count,
		"mean_ms": mean,
		"min_ms": float(sorted[0]),
		"max_ms": float(sorted[count - 1]),
		"p50_ms": percentile(sorted, 50),
		"p95_ms": percentile(sorted, 95),
		"p99_ms": percentile(sorted, 99),
		"fps": 1000.0 / mean if mean > 0.0 else 0.0,
	}

## The run's threshold breaches in policy order (mean first, then p95).
static func violations(thresholds: Dictionary, stats: Dictionary) -> Array:
	var out: Array = []
	for pair: Array in [["MeanMs", "mean_ms", "mean_ms_max"], ["P95Ms", "p95_ms", "p95_ms_max"]]:
		var observed: float = float(stats.get(pair[1], 0.0))
		var limit: float = float(thresholds[pair[2]])
		if observed > limit:
			out.append({"statistic": STATISTIC_NAMES[pair[0]],
				"name": pair[0], "observed_ms": observed, "limit_ms": limit})
	return out

## The policy identity recorded into run artifacts: version string plus
## the sha256 of the exact policy file bytes the run was gated with.
static func policy_identity(policy: Dictionary, policy_sha256: String) -> Dictionary:
	return {"policy_version": policy.policy_version, "sha256": policy_sha256}

## Parse the report's perf section and verify its shape against the
## policy: declared window echoed, resolution echoed, sample count met.
## Returns "" or the first failure.
static func verify_run_shape(policy: Dictionary, perf: Dictionary) -> String:
	if perf.is_empty():
		return "report has no perf section; the app did not run the perf lane"
	if int(perf.get("warmup_frames", -1)) != int(policy.warmup_frames):
		return "perf warmup_frames %d != policy %d" % [int(perf.get("warmup_frames", -1)), int(policy.warmup_frames)]
	if int(perf.get("sample_frames", -1)) != int(policy.sample_frames):
		return "perf sample_frames %d != policy %d" % [int(perf.get("sample_frames", -1)), int(policy.sample_frames)]
	var resolution: Dictionary = perf.get("resolution", {})
	if not (resolution is Dictionary) or int(resolution.get("width", 0)) != int(policy.resolution.width) \
			or int(resolution.get("height", 0)) != int(policy.resolution.height):
		return "perf resolution %s != policy %s" % [str(resolution), str(policy.resolution)]
	var stats: Dictionary = perf.get("stats", {})
	if not (stats is Dictionary) or stats.is_empty():
		return "perf section has no stats"
	if int(stats.get("count", 0)) != int(policy.sample_frames):
		return "perf sample count %d != policy sample_frames %d" % [int(stats.get("count", 0)), int(policy.sample_frames)]
	var samples: Array = perf.get("samples_ms", [])
	if samples.size() != int(policy.sample_frames):
		return "perf samples_ms length %d != policy sample_frames %d" % [samples.size(), int(policy.sample_frames)]
	return ""

## Fold a stats dictionary into the one-line distribution summary the
## verdict prints.
static func distribution_line(stats: Dictionary) -> String:
	return "perf: count %d  mean %.3fms  min %.3fms  p95 %.3fms  max %.3fms  fps %.1f" % [
		int(stats.get("count", 0)), float(stats.get("mean_ms", 0.0)),
		float(stats.get("min_ms", 0.0)), float(stats.get("p95_ms", 0.0)),
		float(stats.get("max_ms", 0.0)), float(stats.get("fps", 0.0))]
