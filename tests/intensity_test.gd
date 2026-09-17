extends SimTestCase
## Port of the intensity.rs inline test module.

const EASE_EPSILON: float = 1e-6
const F32_MAX: float = 3.4028234663852886e38

func fade_or_fail(result: Intensity.Result, label: String) -> Intensity.FixtureFade:
	assert_true(result.is_ok(), label)
	if result.fade == null:
		return Intensity.FixtureFade.holding(0.0).fade
	return result.fade

## Boundary values must land bitwise: 0.0 against -0.0 would pass == while
## differing in sign, so the zero case is told apart by reciprocal sign.
func assert_bits_equal(actual: float, expected: float, label: String) -> void:
	var matches: bool = actual == expected
	if matches and actual == 0.0:
		matches = (1.0 / actual < 0.0) == (1.0 / expected < 0.0)
	if not matches:
		_fail("%s: expected %s, got %s" % [label, str(expected), str(actual)])

func assert_float_close(actual: float, expected: float, label: String) -> void:
	if not (absf(actual - expected) < EASE_EPSILON):
		_fail("%s: expected %s, got %s" % [label, str(expected), str(actual)])

func test_initial_endpoint_preserves_signed_zero() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(-0.0, 1.0, 1), "valid fade")
	assert_bits_equal(fade.intensity(), -0.0, "initial endpoint")

func test_one_tick_settle_has_no_interior_sample() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(7.0, 2.0, 1), "valid fade")
	assert_bits_equal(fade.intensity(), 7.0, "initial endpoint")
	assert_false(fade.is_settled(), "not settled before the tick")
	assert_bits_equal(fade.tick(), 2.0, "one-tick target")
	assert_true(fade.is_settled(), "settled at the tick")

func test_maximum_duration_settles_without_counter_overflow() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.0, 1.0, 65535), "valid duration")
	var previous := fade.intensity()
	for _tick: int in range(1, 65535):
		var next := fade.tick()
		assert_true(next >= previous and next < 1.0, "interior samples ease toward the target")
		assert_false(fade.is_settled(), "not settled before the settle tick")
		previous = next
	assert_bits_equal(fade.tick(), 1.0, "maximum settle tick")
	assert_true(fade.is_settled(), "settled at the maximum duration")
	for _hold: int in range(65536):
		assert_bits_equal(fade.tick(), 1.0, "hold cannot wrap counter")

func test_zero_duration_retarget_cuts_immediately() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.0, 8.0, 4), "valid fade")
	fade.tick()
	assert_true(fade.retarget(3.0, 0) == null, "valid cut")
	assert_bits_equal(fade.intensity(), 3.0, "immediate target")
	assert_true(fade.is_settled(), "a zero settle is settled at once")
	assert_bits_equal(fade.tick(), 3.0, "cut holds")

func test_extreme_valid_intensities_remain_finite_and_monotone() -> void:
	var pairs: Array = [[0.0, F32_MAX], [F32_MAX, 0.0]]
	for pair: Array in pairs:
		var initial: float = pair[0]
		var target: float = pair[1]
		var fade := fade_or_fail(Intensity.FixtureFade.try_new(initial, target, 256), "valid endpoints")
		var previous := initial
		for _tick: int in range(256):
			var next := fade.tick()
			assert_true(is_finite(next) and next >= 0.0, "interior samples stay finite and non-negative")
			if target > initial:
				assert_true(next >= previous, "a rising fade does not fall")
			else:
				assert_true(next <= previous, "a falling fade does not rise")
			previous = next
		assert_bits_equal(fade.intensity(), target, "extreme endpoint")

func test_fade_hits_exact_linear_steps_and_settles_stably() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.0, 8.0, 4), "valid fade")
	assert_bits_equal(fade.intensity(), 0.0, "pre-fade hold")
	assert_false(fade.is_settled(), "not settled at construction")
	assert_bits_equal(fade.target(), 8.0, "target")
	assert_float_close(fade.tick(), 2.0, "step 1")
	assert_float_close(fade.tick(), 4.0, "step 2")
	assert_float_close(fade.tick(), 6.0, "step 3")
	assert_bits_equal(fade.tick(), 8.0, "settle tick")
	assert_true(fade.is_settled(), "settled")
	for _hold: int in range(100):
		assert_bits_equal(fade.tick(), 8.0, "post-settle hold")

func test_rising_fade_is_monotone_between_endpoints() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.5, 2.0, 8), "valid fade")
	var previous := fade.intensity()
	for _tick: int in range(8):
		var next := fade.tick()
		assert_true(next > previous, "a rising fade must increase: %s to %s" % [str(previous), str(next)])
		assert_true(next <= 2.0, "the fade must not overshoot the target: %s" % str(next))
		previous = next
	assert_bits_equal(fade.intensity(), 2.0, "settled at target")

func test_falling_fade_is_monotone_between_endpoints() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(2.0, 0.5, 8), "valid fade")
	var previous := fade.intensity()
	for _tick: int in range(8):
		var next := fade.tick()
		assert_true(next < previous, "a falling fade must decrease: %s to %s" % [str(previous), str(next)])
		assert_true(next >= 0.5, "the fade must not undershoot the target: %s" % str(next))
		previous = next
	assert_bits_equal(fade.intensity(), 0.5, "settled at target")

func test_zero_settle_is_an_immediate_hard_cut() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(1.0, 0.0, 0), "valid fade")
	assert_bits_equal(fade.intensity(), 0.0, "hard cut")
	assert_bits_equal(fade.target(), 0.0, "hard-cut target")
	assert_true(fade.is_settled(), "settled from construction")
	for _tick: int in range(4):
		assert_bits_equal(fade.tick(), 0.0, "hard cut holds")
		assert_true(fade.is_settled(), "still settled")

func test_holding_keeps_the_value_forever() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.holding(3.0), "valid hold")
	assert_bits_equal(fade.target(), 3.0, "hold target")
	assert_true(fade.is_settled(), "a held fixture is settled")
	for _tick: int in range(8):
		assert_bits_equal(fade.tick(), 3.0, "hold")

func test_mid_fade_retarget_continues_without_a_jump() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.0, 8.0, 8), "valid fade")
	for _tick: int in range(4):
		fade.tick()
	assert_float_close(fade.intensity(), 4.0, "halfway")
	assert_true(fade.retarget(2.0, 4) == null, "valid retarget")
	assert_bits_equal(fade.intensity(), 4.0, "the retarget must not jump")
	assert_bits_equal(fade.target(), 2.0, "new target")
	assert_float_close(fade.tick(), 3.5, "retarget step 1")
	assert_float_close(fade.tick(), 3.0, "retarget step 2")
	assert_float_close(fade.tick(), 2.5, "retarget step 3")
	assert_bits_equal(fade.tick(), 2.0, "retarget settle tick")
	assert_true(fade.is_settled(), "settled at the new settle tick")
	assert_bits_equal(fade.tick(), 2.0, "post-settle hold")

func test_retarget_onto_the_current_value_holds_it() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.holding(1.5), "valid hold")
	assert_true(fade.retarget(1.5, 4) == null, "valid retarget")
	assert_false(fade.is_settled(), "a constant fade still runs")
	for _tick: int in range(4):
		assert_bits_equal(fade.tick(), 1.5, "constant fade")
	assert_true(fade.is_settled(), "settled after the new settle")

func test_rejected_retarget_leaves_the_fade_untouched() -> void:
	var fade := fade_or_fail(Intensity.FixtureFade.try_new(0.0, 8.0, 8), "valid fade")
	fade.tick()
	assert_float_close(fade.intensity(), 1.0, "one tick in")
	var bad_targets: Array[float] = [NAN, INF, -INF, -0.5]
	for target: float in bad_targets:
		var failure := fade.retarget(target, 4)
		assert_true(failure != null, "target %s must be rejected" % str(target))
		assert_bits_equal(fade.target(), 8.0, "target unchanged")
		assert_float_close(fade.intensity(), 1.0, "progress unchanged")
		assert_false(fade.is_settled(), "still mid-fade")

func test_construction_rejects_non_finite_and_negative_intensities() -> void:
	var non_finite: Array[float] = [NAN, INF, -INF]
	for value: float in non_finite:
		var bad_initial := Intensity.FixtureFade.try_new(value, 1.0, 4)
		assert_true(bad_initial.error != null and bad_initial.error.kind == Intensity.FixtureFadeError.Kind.NON_FINITE_INTENSITY, "a non-finite initial must be rejected")
		var bad_target := Intensity.FixtureFade.try_new(1.0, value, 4)
		assert_true(bad_target.error != null and bad_target.error.kind == Intensity.FixtureFadeError.Kind.NON_FINITE_INTENSITY, "a non-finite target must be rejected")
	var negative_initial := Intensity.FixtureFade.try_new(-1.0, 1.0, 4)
	assert_true(negative_initial.error != null and negative_initial.error.kind == Intensity.FixtureFadeError.Kind.NEGATIVE_INTENSITY, "a negative initial must be rejected")
	var negative_target := Intensity.FixtureFade.try_new(1.0, -1.0, 4)
	assert_true(negative_target.error != null and negative_target.error.kind == Intensity.FixtureFadeError.Kind.NEGATIVE_INTENSITY, "a negative target must be rejected")
	var negative_hold := Intensity.FixtureFade.holding(-1.0)
	assert_true(negative_hold.error != null and negative_hold.error.kind == Intensity.FixtureFadeError.Kind.NEGATIVE_INTENSITY, "a negative hold must be rejected")
	assert_true(negative_initial.error != null and negative_initial.error.equals(Intensity.FixtureFadeError.negative_intensity(-1.0)), "the rejection carries the offending value")
	assert_true(negative_hold.error != null and negative_hold.error.equals(Intensity.FixtureFadeError.negative_intensity(-1.0)), "the hold rejection carries the offending value")
	var nan_rejection := Intensity.FixtureFade.try_new(NAN, 1.0, 4)
	assert_true(nan_rejection.error != null and nan_rejection.error._to_string().contains("non-finite"), "the display text names the rule")
	var negative_display := Intensity.FixtureFade.try_new(1.0, -0.25, 4)
	assert_true(negative_display.error != null and negative_display.error._to_string().contains("negative"), "the display text names the rule")
