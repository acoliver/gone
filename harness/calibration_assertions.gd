class_name CalibrationAssertions
extends RefCounted
## The calibration lane's predeclared assertion table, ported from Rust
## calibration_lane/assertions.rs: named bounds whose constants state the
## physical reason for each, evaluated over the measured (tick, mean)
## sequence. The sample layout each cell expects: samples 0-1 the settled
## pre window, sample 2 the first post-perturbation sample, the rest the
## settling window. Pure logic; tests cover it headless.

const PRE_FLAT_EPSILON: float = 0.01
const STEP_JUMP_MIN_LINEAR: float = 0.05
const CONVERGENCE_EPSILON: float = 0.01
const NO_ADAPTATION_EPSILON: float = 0.01
const TRACKS_STEP_MIN_LINEAR: float = 0.05
const PLACEMENT_DIFFERENCE_MIN_LINEAR: float = 0.02
const DIFFERENCE_REMOVED_EPSILON: float = 0.01
const EDGE_SETTLED_EPSILON: float = 0.01
const PLACEMENT_WINDOW: int = 2

static func _mean_of(samples: Array, from: int, to: int) -> float:
	var total: float = 0.0
	var counted: int = 0
	for index: int in range(from, to):
		total += float(samples[index].mean_linear)
		counted += 1
	return total / float(counted) if counted > 0 else 0.0

static func pre_flat(samples: Array, before_tick: int, label: String) -> Dictionary:
	var window: Array = []
	for sample: Dictionary in samples:
		if int(sample.tick) < before_tick:
			window.append(sample)
		else:
			break
	var first: float = float(window[0].mean_linear)
	var worst: float = 0.0
	for sample: Dictionary in window:
		worst = maxf(worst, absf(float(sample.mean_linear) - first))
	return {
		"name": label,
		"passed": worst <= PRE_FLAT_EPSILON,
		"expected": "every pre-perturbation mean within %.3f of the first (%.6f; exposure is settled before the perturbation)" % [PRE_FLAT_EPSILON, first],
		"measured": "max |delta| %.6f over ticks %d-%d" % [worst, int(window[0].tick), int(window[window.size() - 1].tick)],
	}

static func step_moves_mean_up(samples: Array) -> Dictionary:
	var last_pre: float = float(samples[1].mean_linear)
	var first_post: float = float(samples[2].mean_linear)
	var rise: float = first_post - last_pre
	return {
		"name": "step-moves-mean-up",
		"passed": rise >= STEP_JUMP_MIN_LINEAR,
		"expected": "first post-step mean - last pre-step mean >= %.3f (the +1 f-stop raw step doubles the radiance before adaptation)" % STEP_JUMP_MIN_LINEAR,
		"measured": "%.6f - %.6f = %.6f (tick %d vs tick %d)" % [first_post, last_pre, rise, int(samples[2].tick), int(samples[1].tick)],
	}

static func converges_back(samples: Array) -> Dictionary:
	var baseline: float = float(samples[0].mean_linear)
	var last: float = float(samples[samples.size() - 1].mean_linear)
	var delta: float = absf(last - baseline)
	return {
		"name": "converges-back",
		"passed": delta <= CONVERGENCE_EPSILON,
		"expected": "|last post-step mean - first pre-step mean| <= %.3f (AE ON adapts the +1 f-stop back; baseline %.6f)" % [CONVERGENCE_EPSILON, baseline],
		"measured": "|%.6f - %.6f| = %.6f (last post tick %d)" % [last, baseline, delta, int(samples[samples.size() - 1].tick)],
	}

static func no_adaptation(samples: Array) -> Dictionary:
	var first_post: float = float(samples[2].mean_linear)
	var worst: float = 0.0
	for index: int in range(2, samples.size()):
		worst = maxf(worst, absf(float(samples[index].mean_linear) - first_post))
	return {
		"name": "no-adaptation",
		"passed": worst <= NO_ADAPTATION_EPSILON,
		"expected": "every post-step mean within %.3f of the first post-step (%.6f; AE OFF cannot adapt)" % [NO_ADAPTATION_EPSILON, first_post],
		"measured": "max |delta| %.6f over ticks %d-%d" % [worst, int(samples[2].tick), int(samples[samples.size() - 1].tick)],
	}

static func tracks_step(samples: Array) -> Dictionary:
	var baseline: float = float(samples[0].mean_linear)
	var last: float = float(samples[samples.size() - 1].mean_linear)
	var rise: float = last - baseline
	return {
		"name": "tracks-step",
		"passed": rise >= TRACKS_STEP_MIN_LINEAR,
		"expected": "last post-step mean - first pre-step mean >= %.3f (AE OFF tracks the step exactly; baseline %.6f)" % [TRACKS_STEP_MIN_LINEAR, baseline],
		"measured": "%.6f - %.6f = %.6f (last post tick %d)" % [last, baseline, rise, int(samples[samples.size() - 1].tick)],
	}

static func edge_settled(samples: Array) -> Dictionary:
	var older: float = float(samples[samples.size() - 2].mean_linear)
	var newest: float = float(samples[samples.size() - 1].mean_linear)
	var delta: float = absf(newest - older)
	return {
		"name": "edge-settled",
		"passed": delta <= EDGE_SETTLED_EPSILON,
		"expected": "|last two edge-window means| <= %.3f (the adaptation tail at the sampled horizon is small)" % EDGE_SETTLED_EPSILON,
		"measured": "|%.6f - %.6f| = %.6f (ticks %d vs %d)" % [newest, older, delta, int(samples[samples.size() - 1].tick), int(samples[samples.size() - 2].tick)],
	}

static func _placement_windows(samples: Array) -> Dictionary:
	var edge_start: int = samples.size() - PLACEMENT_WINDOW
	return {
		"center": _mean_of(samples, 0, PLACEMENT_WINDOW),
		"edge": _mean_of(samples, edge_start, samples.size()),
		"center_range": [int(samples[0].tick), int(samples[PLACEMENT_WINDOW - 1].tick)],
		"edge_range": [int(samples[edge_start].tick), int(samples[samples.size() - 1].tick)],
	}

static func edge_brighter_than_center(samples: Array) -> Dictionary:
	var windows: Dictionary = _placement_windows(samples)
	var diff: float = float(windows.edge) - float(windows.center)
	var range: Array = windows.edge_range
	var center_range: Array = windows.center_range
	return {
		"name": "edge-brighter-than-center",
		"passed": diff >= PLACEMENT_DIFFERENCE_MIN_LINEAR,
		"expected": "edge-window mean - center-window mean >= %.3f (the center-weighted mask meters the centered patch harder, so the edge placement's exposure is higher and it renders brighter)" % PLACEMENT_DIFFERENCE_MIN_LINEAR,
		"measured": "edge %.6f (ticks %d-%d) - center %.6f (ticks %d-%d) = %.6f" % [float(windows.edge), int(range[0]), int(range[1]), float(windows.center), int(center_range[0]), int(center_range[1]), diff],
	}

static func difference_removed(samples: Array) -> Dictionary:
	var windows: Dictionary = _placement_windows(samples)
	var diff: float = absf(float(windows.edge) - float(windows.center))
	var range: Array = windows.edge_range
	var center_range: Array = windows.center_range
	return {
		"name": "difference-removed",
		"passed": diff <= DIFFERENCE_REMOVED_EPSILON,
		"expected": "|edge-window mean - center-window mean| <= %.3f (the uniform mask weights both slots identically)" % DIFFERENCE_REMOVED_EPSILON,
		"measured": "|edge %.6f (ticks %d-%d) - center %.6f (ticks %d-%d)| = %.6f" % [float(windows.edge), int(range[0]), int(range[1]), float(windows.center), int(center_range[0]), int(center_range[1]), diff],
	}

## Evaluate one cell's predeclared assertions over the measured sequence.
## `perturb_tick` is the scenario's step tick (cells A/B) or patch move
## tick (cells C/D).
static func evaluate_cell(cell: String, samples: Array, perturb_tick: int) -> Array:
	match cell:
		"A":
			return [pre_flat(samples, perturb_tick, "pre-step-flat"),
				step_moves_mean_up(samples), converges_back(samples)]
		"B":
			return [pre_flat(samples, perturb_tick, "pre-step-flat"),
				step_moves_mean_up(samples), no_adaptation(samples), tracks_step(samples)]
		"C":
			return [pre_flat(samples, perturb_tick, "pre-move-flat"),
				edge_settled(samples), edge_brighter_than_center(samples)]
		_:
			return [pre_flat(samples, perturb_tick, "pre-move-flat"),
				edge_settled(samples), difference_removed(samples)]

static func summarize(outcomes: Array) -> Array[String]:
	var lines: Array[String] = []
	for outcome: Dictionary in outcomes:
		lines.append("calibration `%s`: %s (%s)" % [outcome.name,
			"pass" if outcome.passed else "FAIL", outcome.measured])
	return lines
