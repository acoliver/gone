extends SimTestCase
## Engine-independent assertions for the perf lane's policy math, ported
## from Rust harness/perf.rs tests: policy parse + validation, the
## nearest-rank percentile rules, summary statistics on known vectors,
## threshold breach naming/order, and the report-shape verification.

const PerfPolicy := preload("res://harness/perf_policy.gd")

func test_policy_parses() -> void:
	var policy: Dictionary = PerfPolicy.parse_policy(policy_json("25.0", "50.0", full_statistics())).policy
	assert_str(policy.policy_version, "calibration-v1", "policy version")

func assert_str(actual: String, expected: String, message: String) -> void:
	if actual != expected:
		_fail("%s: expected `%s`, got `%s`" % [message, expected, actual])

func test_policy_parse_rejects_malformed_json() -> void:
	assert_true(PerfPolicy.parse_policy("{ nope").error != "", "malformed JSON must fail")
	assert_true(PerfPolicy.parse_policy("{}").error != "", "empty policy must fail")

func test_policy_parse_rejects_empty_sample_window() -> void:
	var json: String = policy_json("25.0", "50.0", full_statistics()).replace("\"sample_frames\": 100", "\"sample_frames\": 0")
	var error: String = PerfPolicy.parse_policy(json).error
	assert_true(error.contains("sample_frames"), "error names the field: %s" % error)

func test_policy_parse_rejects_thresholds_on_unreported_statistics() -> void:
	var error: String = PerfPolicy.parse_policy(policy_json("25.0", "50.0",
		"[\"Count\", \"MeanMs\"]")).error
	assert_true(error.contains("p95"), "error names the unreported statistic: %s" % error)

func test_checked_in_policy_parses_and_validates() -> void:
	var path := ProjectSettings.globalize_path("res://harness/perf-policy.json")
	var text := FileAccess.get_file_as_string(path)
	assert_false(text.is_empty(), "harness/perf-policy.json exists")
	var parsed: Dictionary = PerfPolicy.parse_policy(text)
	assert_str(parsed.error, "", "checked-in policy parses")
	var policy: Dictionary = parsed.policy
	assert_int_equal(int(policy.sample_frames), 300, "smoke policy samples 300 frames")
	assert_int_equal(int(policy.resolution.width), 1152, "smoke policy width")
	assert_int_equal(int(policy.resolution.height), 648, "smoke policy height")

func test_percentiles_use_the_nearest_rank_rules() -> void:
	var one_to_ten: Array = []
	for value: int in range(1, 11):
		one_to_ten.append(float(value))
	var sorted: Array = one_to_ten.duplicate()
	sorted.sort()
	assert_float_equal(PerfPolicy.percentile(sorted, 50), 5.0, "p50 of 1..10 is the 5th order statistic")
	assert_float_equal(PerfPolicy.percentile(sorted, 95), 10.0, "p95 of 1..10 ceils to the maximum")
	assert_float_equal(PerfPolicy.percentile(sorted, 99), 10.0, "p99 of 1..10 ceils to the maximum")

func test_statistics_math_is_exact_on_a_known_vector() -> void:
	var samples: Array = []
	for value: int in range(1, 101):
		samples.append(float(value))
	var stats: Dictionary = PerfPolicy.stats_from_samples(samples)
	assert_int_equal(int(stats.count), 100, "count")
	assert_float_equal(stats.mean_ms, 50.5, "mean of 1..=100")
	assert_float_equal(stats.min_ms, 1.0, "min")
	assert_float_equal(stats.max_ms, 100.0, "max")
	assert_float_equal(stats.p50_ms, 50.0, "p50 rank 50")
	assert_float_equal(stats.p95_ms, 95.0, "p95 rank 95")
	assert_float_equal(stats.p99_ms, 99.0, "p99 rank 99")

func test_input_order_does_not_matter() -> void:
	var samples: Array = []
	for value: int in range(1, 11):
		samples.append(float(value))
	var forward: Dictionary = PerfPolicy.stats_from_samples(samples)
	samples.reverse()
	var backward: Dictionary = PerfPolicy.stats_from_samples(samples)
	assert_float_equal(forward.mean_ms, backward.mean_ms, "mean is order independent")
	assert_float_equal(forward.p95_ms, backward.p95_ms, "p95 is order independent")

func test_empty_samples_have_no_statistics() -> void:
	assert_true(PerfPolicy.stats_from_samples([]).is_empty(), "an empty window has no statistics")

func test_clean_statistics_pass_the_thresholds() -> void:
	var samples: Array = []
	for _index: int in range(600):
		samples.append(2.0)
	var thresholds := {"mean_ms_max": 25.0, "p95_ms_max": 50.0}
	assert_int_equal(PerfPolicy.violations(thresholds, PerfPolicy.stats_from_samples(samples)).size(), 0,
		"a 2ms window is inside both ceilings")

func test_mean_violation_is_named_with_observed_and_limit() -> void:
	var samples: Array = []
	for _index: int in range(600):
		samples.append(31.0)
	var thresholds := {"mean_ms_max": 25.0, "p95_ms_max": 50.0}
	var breaches: Array = PerfPolicy.violations(thresholds, PerfPolicy.stats_from_samples(samples))
	assert_int_equal(breaches.size(), 1, "only the mean breaches")
	assert_str(breaches[0].statistic, "mean_ms", "the breach names the statistic")
	assert_float_equal(float(breaches[0].observed_ms), 31.0, "the breach carries the observed value")
	assert_float_equal(float(breaches[0].limit_ms), 25.0, "the breach carries the limit")

func test_both_violations_report_in_policy_order() -> void:
	var samples: Array = []
	for _index: int in range(600):
		samples.append(60.0)
	var thresholds := {"mean_ms_max": 25.0, "p95_ms_max": 50.0}
	var breaches: Array = PerfPolicy.violations(thresholds, PerfPolicy.stats_from_samples(samples))
	assert_int_equal(breaches.size(), 2, "both thresholds breach")
	assert_str(breaches[0].statistic, "mean_ms", "mean comes first")
	assert_str(breaches[1].statistic, "p95_ms", "then p95")

func _shape_policy() -> Dictionary:
	return PerfPolicy.parse_policy(policy_json("25.0", "50.0", full_statistics())).policy

func test_verify_run_shape_accepts_an_honest_perf_section() -> void:
	var policy: Dictionary = _shape_policy()
	var perf := {
		"warmup_frames": int(policy.warmup_frames),
		"sample_frames": int(policy.sample_frames),
		"presentation": policy.presentation,
		"resolution": policy.resolution,
		"samples_ms": [],
		"stats": {},
	}
	for _index: int in range(int(policy.sample_frames)):
		perf.samples_ms.append(2.0)
	perf.stats = PerfPolicy.stats_from_samples(perf.samples_ms)
	assert_str(PerfPolicy.verify_run_shape(policy, perf), "", "an honest section verifies")

func test_verify_run_shape_rejects_missing_and_short_sections() -> void:
	var policy: Dictionary = _shape_policy()
	assert_true(PerfPolicy.verify_run_shape(policy, {}).contains("no perf section"),
		"a missing section fails")
	var short: Dictionary = {
		"warmup_frames": int(policy.warmup_frames),
		"sample_frames": int(policy.sample_frames),
		"resolution": policy.resolution,
		"samples_ms": [2.0],
		"stats": {"count": 1},
	}
	assert_true(PerfPolicy.verify_run_shape(policy, short).contains("sample count"),
		"a short sample list fails")
	assert_true(PerfPolicy.verify_run_shape(policy, {
		"warmup_frames": int(policy.warmup_frames),
		"sample_frames": int(policy.sample_frames),
		"resolution": {"width": 1, "height": 1},
		"samples_ms": [2.0],
		"stats": {"count": 1},
	}).contains("resolution"), "a wrong resolution fails")

func policy_json(mean_max: String, p95_max: String, statistics: String) -> String:
	return "{\"policy_version\": \"calibration-v1\", \"warmup_frames\": 12, \"sample_frames\": 100, \"presentation\": \"Uncapped\", \"camera_route\": \"static\", \"concurrent_effects\": \"none\", \"resolution\": {\"width\": 1920, \"height\": 1080}, \"statistics\": %s, \"thresholds\": {\"mean_ms_max\": %s, \"p95_ms_max\": %s}}" % [statistics, mean_max, p95_max]

func full_statistics() -> String:
	return "[\"Count\", \"MeanMs\", \"MinMs\", \"MaxMs\", \"P50Ms\", \"P95Ms\", \"P99Ms\"]"
