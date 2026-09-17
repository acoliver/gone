extends SimTestCase
## Engine-independent assertions for the calibration lane, ported from
## Rust harness/calibration.rs and calibration_lane/assertions.rs tests:
## parameter parse/validate invariants, plan helpers, the predeclared
## assertion table on synthetic sample sequences (pass and fail), and
## the mask-identity hashing contract.

const Calibration := preload("res://harness/calibration.gd")
const Assertions := preload("res://harness/calibration_assertions.gd")
const Protocol := preload("res://harness/protocol.gd")

func assert_str(actual: String, expected: String, message: String) -> void:
	if actual != expected:
		_fail("%s: expected `%s`, got `%s`" % [message, expected, actual])

func valid_params() -> Dictionary:
	return {
		"initial_level": 0.18,
		"step": {"tick": 30, "level": 0.36},
		"patch_area_fraction": 0.02,
		"patch": {"type": "center_then_edge", "at_tick": 60},
		"mask": "center_weighted",
		"auto_exposure": true,
		"cell": "A",
	}

func test_params_parse_from_the_documented_json_shape() -> void:
	var parsed: Dictionary = Calibration.parse_params(valid_params())
	assert_str(parsed.error, "", "valid params parse")
	var params: Dictionary = parsed.params
	assert_float_equal(float(params.initial_level), 0.18, "initial level")
	assert_int_equal(int(params.step.tick), 30, "step tick")
	assert_float_equal(float(params.step.level), 0.36, "step level")
	assert_str(params.patch.type, "center_then_edge", "patch plan")
	assert_str(params.mask, "center_weighted", "mask")
	assert_true(params.auto_exposure, "auto exposure arm")

func test_unknown_variants_are_rejected() -> void:
	var bad_mask: Dictionary = valid_params()
	bad_mask.mask = "spot"
	assert_true(Calibration.parse_params(bad_mask).error.contains("mask"), "unknown mask fails")
	var bad_plan: Dictionary = valid_params()
	bad_plan.patch = {"type": "diagonal"}
	assert_true(Calibration.parse_params(bad_plan).error.contains("patch"), "unknown plan fails")
	var bad_cell: Dictionary = valid_params()
	bad_cell.cell = "E"
	assert_true(Calibration.parse_params(bad_cell).error.contains("cell"), "unknown cell fails")
	var no_step: Dictionary = valid_params()
	no_step.erase("step")
	assert_true(Calibration.parse_params(no_step).error.contains("step"), "missing step fails")

func test_zero_and_negative_and_nonfinite_levels_are_rejected() -> void:
	for level: float in [0.0, -1.0, NAN, INF]:
		var params: Dictionary = valid_params()
		params.initial_level = level
		var error: String = Calibration.parse_params(params).error
		assert_true(error.contains("initial_level"), "level %s fails naming the field: %s" % [str(level), error])

func test_levels_above_the_cap_are_rejected() -> void:
	var over: Dictionary = valid_params()
	over.initial_level = Calibration.LEVEL_MAX * 1.5
	assert_true(Calibration.parse_params(over).error != "", "over the cap fails")
	var at_cap: Dictionary = valid_params()
	at_cap.initial_level = Calibration.LEVEL_MAX
	assert_str(Calibration.parse_params(at_cap).error, "", "the cap itself is allowed")

func test_step_and_move_at_tick_zero_are_rejected() -> void:
	var step_zero: Dictionary = valid_params()
	step_zero.step = {"tick": 0, "level": 0.36}
	assert_true(Calibration.parse_params(step_zero).error.contains("step tick"), "step at tick 0 fails")
	var move_zero: Dictionary = valid_params()
	move_zero.patch = {"type": "center_then_edge", "at_tick": 0}
	assert_true(Calibration.parse_params(move_zero).error.contains("move tick"), "move at tick 0 fails")

func test_patch_area_out_of_range_is_rejected() -> void:
	for fraction: float in [0.0, -0.01, Calibration.PATCH_AREA_FRACTION_MAX, 0.5, NAN]:
		var params: Dictionary = valid_params()
		params.patch_area_fraction = fraction
		var error: String = Calibration.parse_params(params).error
		assert_true(error.contains("patch_area_fraction"), "fraction %s fails: %s" % [str(fraction), error])

func test_placements_follow_the_plan_in_tick_order() -> void:
	var fixed: Array = [{"tick": 0, "slot": "center"}]
	assert_vec_dict_equal(Calibration.patch_placements({"type": "fixed_center"}), fixed, "fixed center")
	assert_vec_dict_equal(Calibration.patch_placements({"type": "fixed_edge"}),
		[{"tick": 0, "slot": "edge"}], "fixed edge")
	assert_vec_dict_equal(Calibration.patch_placements({"type": "center_then_edge", "at_tick": 60}),
		[{"tick": 0, "slot": "center"}, {"tick": 60, "slot": "edge"}], "center then edge")

func assert_vec_dict_equal(actual: Array, expected: Array, message: String) -> void:
	if actual.size() != expected.size():
		_fail("%s: expected %d placements, got %d" % [message, expected.size(), actual.size()])
		return
	for index: int in range(expected.size()):
		if actual[index] != expected[index]:
			_fail("%s: expected %s, got %s" % [message, str(expected[index]), str(actual[index])])
			return

func test_patch_slots_follow_the_plan_per_tick() -> void:
	var plan := {"type": "center_then_edge", "at_tick": 60}
	assert_str(Calibration.patch_slot_at(plan, 0), "center", "before the move")
	assert_str(Calibration.patch_slot_at(plan, 59), "center", "still before the move")
	assert_str(Calibration.patch_slot_at(plan, 60), "edge", "move lands on its tick")
	assert_str(Calibration.patch_slot_at(plan, 61), "edge", "and stays")
	assert_str(Calibration.patch_slot_at({"type": "fixed_center"}, 120), "center", "fixed center never moves")
	assert_str(Calibration.patch_slot_at({"type": "fixed_edge"}, 0), "edge", "fixed edge")

func test_move_tick_is_null_for_fixed_plans() -> void:
	assert_true(Calibration.move_tick({"type": "fixed_center"}) == null, "fixed center has no move")
	assert_true(Calibration.move_tick({"type": "fixed_edge"}) == null, "fixed edge has no move")
	assert_int_equal(int(Calibration.move_tick({"type": "center_then_edge", "at_tick": 7})), 7,
		"the move plan carries its tick")

func test_wall_level_steps_at_the_step_tick() -> void:
	var params: Dictionary = valid_params()
	assert_float_equal(Calibration.wall_level(params, 0), 0.18, "initial level at tick 0")
	assert_float_equal(Calibration.wall_level(params, 29), 0.18, "still initial before the step")
	assert_float_equal(Calibration.wall_level(params, 30), 0.36, "the step lands on its tick")
	assert_float_equal(Calibration.wall_level(params, 31), 0.36, "and holds")

func test_auto_exposure_evidence_shape() -> void:
	var off: Dictionary = Calibration.auto_exposure_evidence(false)
	assert_false(off.enabled, "off arm is disabled")
	assert_true(off.settings == null, "off arm carries no settings")
	var on: Dictionary = Calibration.auto_exposure_evidence(true)
	assert_true(on.enabled, "on arm is enabled")
	var settings: Dictionary = on.settings
	assert_float_equal(settings.speed_brighten, 3.0, "brighten speed")
	assert_float_equal(settings.speed_darken, 1.0, "darken speed")
	assert_float_equal(settings.range_min, -8.0, "range min")
	assert_float_equal(settings.range_max, 8.0, "range max")

func _sample(tick: int, mean: float) -> Dictionary:
	return {"tick": tick, "mean_linear": mean}

func cell_a_adapted_samples() -> Array:
	return [_sample(90, 0.35), _sample(120, 0.35), _sample(181, 0.68),
		_sample(270, 0.36), _sample(360, 0.35), _sample(450, 0.35)]

func test_cell_a_passes_when_auto_exposure_adapts() -> void:
	var outcomes: Array = Assertions.evaluate_cell("A", cell_a_adapted_samples(), 180)
	assert_int_equal(outcomes.size(), 3, "cell A carries three assertions")
	for outcome: Dictionary in outcomes:
		assert_true(outcome.passed, "cell A `%s` passes: %s" % [outcome.name, outcome.measured])

func test_cell_a_fails_converges_back_without_adaptation() -> void:
	var samples: Array = cell_a_adapted_samples()
	samples[5] = _sample(450, 0.68)
	var outcomes: Array = Assertions.evaluate_cell("A", samples, 180)
	var failed := {}
	for outcome: Dictionary in outcomes:
		if not outcome.passed:
			failed[outcome.name] = outcome.measured
	assert_true(failed.has("converges-back"), "converges-back fails without adaptation")
	assert_true(str(failed["converges-back"]).contains("0.330000"),
		"the failure carries the measured delta: %s" % failed["converges-back"])

func test_cell_a_fails_when_the_step_does_not_move_the_mean() -> void:
	var samples: Array = cell_a_adapted_samples()
	samples[2] = _sample(181, 0.36)
	var outcomes: Array = Assertions.evaluate_cell("A", samples, 180)
	var names: Array = []
	for outcome: Dictionary in outcomes:
		if not outcome.passed:
			names.append(outcome.name)
	assert_true(names.has("step-moves-mean-up"), "a flat step fails the jump assertion")

func test_cell_b_passes_on_a_control_run() -> void:
	var samples: Array = [_sample(90, 0.35), _sample(120, 0.35), _sample(181, 0.68),
		_sample(270, 0.68), _sample(360, 0.68), _sample(450, 0.68)]
	var outcomes: Array = Assertions.evaluate_cell("B", samples, 180)
	assert_int_equal(outcomes.size(), 4, "cell B carries four assertions")
	for outcome: Dictionary in outcomes:
		assert_true(outcome.passed, "cell B `%s` passes: %s" % [outcome.name, outcome.measured])

func test_cell_c_passes_when_the_mask_meters_placement() -> void:
	var samples: Array = [_sample(90, 0.35), _sample(120, 0.35), _sample(181, 0.36),
		_sample(270, 0.40), _sample(420, 0.45), _sample(540, 0.45)]
	var outcomes: Array = Assertions.evaluate_cell("C", samples, 180)
	for outcome: Dictionary in outcomes:
		assert_true(outcome.passed, "cell C `%s` passes: %s" % [outcome.name, outcome.measured])

func test_cell_c_fails_when_the_difference_is_below_the_floor() -> void:
	var samples: Array = [_sample(90, 0.35), _sample(120, 0.35), _sample(181, 0.35),
		_sample(270, 0.35), _sample(420, 0.36), _sample(540, 0.36)]
	var outcomes: Array = Assertions.evaluate_cell("C", samples, 180)
	var names: Array = []
	for outcome: Dictionary in outcomes:
		if not outcome.passed:
			names.append(outcome.name)
	assert_true(names.has("edge-brighter-than-center"), "a 0.01 difference is below the 0.02 floor")

func test_cell_d_passes_when_the_uniform_mask_removes_the_difference() -> void:
	var samples: Array = [_sample(90, 0.35), _sample(120, 0.35), _sample(181, 0.35),
		_sample(270, 0.35), _sample(420, 0.35), _sample(540, 0.35)]
	var outcomes: Array = Assertions.evaluate_cell("D", samples, 180)
	for outcome: Dictionary in outcomes:
		assert_true(outcome.passed, "cell D `%s` passes: %s" % [outcome.name, outcome.measured])

func test_pre_flat_fails_on_a_drifting_pre_window() -> void:
	var samples: Array = [_sample(90, 0.35), _sample(120, 0.37), _sample(181, 0.68),
		_sample(270, 0.35), _sample(360, 0.35), _sample(450, 0.35)]
	var outcome: Dictionary = Assertions.pre_flat(samples, 180, "pre-step-flat")
	assert_false(outcome.passed, "a 0.02 drift exceeds the 0.01 epsilon")
	assert_true(outcome.measured.contains("0.020000"), "the failure carries the drift: %s" % outcome.measured)

func test_shipped_masks_exist_and_hash_distinctly() -> void:
	var hashes: Array[String] = []
	for path: String in [Calibration.MASK_CENTER_PATH, Calibration.MASK_UNIFORM_PATH]:
		var image := Image.new()
		var bytes := FileAccess.get_file_as_bytes(ProjectSettings.globalize_path(path))
		assert_false(bytes.is_empty(), "mask %s exists" % path)
		assert_int_equal(image.load_png_from_buffer(bytes), OK, "mask %s decodes" % path)
		assert_int_equal(image.get_width(), 48, "mask width")
		assert_int_equal(image.get_height(), 27, "mask height")
		hashes.append(Protocol.sha256_hex(image.get_data()))
	assert_true(hashes[0] != hashes[1], "the two masks hash differently")

func test_sha256_known_vectors() -> void:
	assert_str(Protocol.sha256_hex(PackedByteArray()),
		"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "empty bytes")
	assert_str(Protocol.sha256_hex("abc".to_ascii_buffer()),
		"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "abc bytes")
