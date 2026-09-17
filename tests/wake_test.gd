extends SimTestCase
## Port of the wake.rs inline test module: the readiness contract, the
## exact authored boundaries through both blinks, batching-independent
## sampling, the neutral completion tail, and every fail-loud authoring
## rejection.

const EASE_EPSILON: float = 1e-6

## The named boundaries of the authored table: the authored milliseconds
## [1250, 700, 450, 900, 400, 1000] encode at the 60 Hz logical rate to
## beats of 75, 42, 27, 54, 24, and 60 ticks.
func frozen_boundaries() -> Wake.AuthoredBoundaries:
	var frozen: Wake.AuthoredBoundaries = Wake.AuthoredBoundaries.new()
	frozen.first_opening_start = 75
	frozen.first_blink_start = 117
	frozen.second_opening_start = 144
	frozen.second_blink_start = 198
	frozen.final_opening_start = 222
	frozen.complete_tick = 282
	return frozen

func authored_state() -> Wake.WakeState:
	return Wake.WakeState.new(Wake.WakeTimeline.authored())

## Run the authored timeline from readiness, collecting the sample at
## every logical tick through `ticks` inclusive.
func ready_run(ticks: int) -> Array[Wake.WakeSample]:
	var state: Wake.WakeState = authored_state()
	assert_int_equal(state.mark_ready(), Wake.WakeStart.STARTED, "the run starts")
	var samples: Array[Wake.WakeSample] = [state.sample()]
	for _tick: int in range(ticks):
		samples.append(state.tick())
	return samples

## Boundary values must land bitwise: 0.0 against -0.0 would pass == while
## differing in sign, so the zero case is told apart by reciprocal sign.
func assert_bits_equal(actual: float, expected: float, label: String) -> void:
	var matches: bool = actual == expected
	if matches and actual == 0.0:
		matches = (1.0 / actual < 0.0) == (1.0 / expected < 0.0)
	if not matches:
		_fail("%s: expected %s, got %s" % [label, str(expected), str(actual)])

## Two samples are bitwise identical, field by field: boundary ticks must
## land on authored states with no interpolation error.
func assert_bitwise_equal(actual: Wake.WakeSample, expected: Wake.WakeSample, label: String) -> void:
	assert_bits_equal(actual.lid_openness, expected.lid_openness, "%s lid openness" % label)
	assert_bits_equal(actual.blur, expected.blur, "%s blur" % label)
	assert_bits_equal(actual.exposure_ramp, expected.exposure_ramp, "%s exposure ramp" % label)
	assert_bits_equal(actual.sway_offset.x, expected.sway_offset.x, "%s sway x" % label)
	assert_bits_equal(actual.sway_offset.y, expected.sway_offset.y, "%s sway y" % label)

## Per-component closeness for an eased sample.
func assert_sample_close(actual: Wake.WakeSample, expected: Wake.WakeSample, label: String) -> void:
	var openness: float = absf(actual.lid_openness - expected.lid_openness)
	var blur: float = absf(actual.blur - expected.blur)
	var ramp: float = absf(actual.exposure_ramp - expected.exposure_ramp)
	var sway_drift: Vector2 = (actual.sway_offset - expected.sway_offset).abs()
	var sway: float = maxf(sway_drift.x, sway_drift.y)
	if not (openness < EASE_EPSILON and blur < EASE_EPSILON and ramp < EASE_EPSILON and sway < EASE_EPSILON):
		_fail("%s: expected %s, got %s" % [label, expected._to_string(), actual._to_string()])

func assert_sample_vectors_equal(actual: Array, expected: Array, label: String) -> void:
	if actual.size() != expected.size():
		_fail("%s: expected %d samples, got %d" % [label, expected.size(), actual.size()])
		return
	for index: int in range(expected.size()):
		if not actual[index].equals(expected[index]):
			_fail("%s: sample %d expected %s, got %s" % [label, index, expected[index]._to_string(), actual[index]._to_string()])
			return

## The timeline holds fully closed before readiness, and pre-ready ticks
## consume nothing: the sample and the counter both stay put.
func test_holds_closed_before_readiness_and_pre_ready_ticks_consume_nothing() -> void:
	var state: Wake.WakeState = authored_state()
	assert_false(state.is_started(), "a fresh machine has not started")
	assert_false(state.is_complete(), "a fresh machine is not complete")
	assert_int_equal(state.current_tick(), 0, "a fresh machine sits at tick zero")
	assert_bitwise_equal(state.sample(), Wake.WakeSample.closed(), "fresh hold")
	for _tick: int in range(5):
		assert_bitwise_equal(state.tick(), Wake.WakeSample.closed(), "pre-ready tick")
	assert_int_equal(state.current_tick(), 0, "pre-ready ticks never count")
	assert_false(state.is_started(), "still not started")
	assert_false(state.is_complete(), "still not complete")

## The first readiness poll starts the machine, and the sample at logical
## tick zero is bitwise the closed rest state.
func test_first_readiness_starts_and_tick_zero_is_fully_closed() -> void:
	var state: Wake.WakeState = authored_state()
	assert_int_equal(state.mark_ready(), Wake.WakeStart.STARTED, "the first poll starts")
	assert_true(state.is_started(), "started")
	assert_false(state.is_complete(), "not complete at tick zero")
	assert_int_equal(state.current_tick(), 0, "tick zero")
	assert_bitwise_equal(state.sample(), Wake.WakeSample.closed(), "tick zero")

## Duplicate readiness never restarts the timeline: the machine runs on
## from where it is, and completion still lands on the first start's
## schedule.
func test_duplicate_readiness_is_a_no_op_and_never_restarts() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var state: Wake.WakeState = authored_state()
	assert_int_equal(state.mark_ready(), Wake.WakeStart.STARTED, "the first poll starts")
	for _tick: int in range(7):
		state.tick()
	assert_int_equal(state.current_tick(), 7, "seven ticks consumed")
	for _poll: int in range(3):
		assert_int_equal(state.mark_ready(), Wake.WakeStart.ALREADY_STARTED, "duplicate polls are no-ops")
	assert_int_equal(state.current_tick(), 7, "duplicate polls never reset")
	for _tick: int in range(7, boundaries.complete_tick + 4):
		state.tick()
	assert_true(state.is_complete(), "complete on the first start's schedule")
	assert_int_equal(state.mark_ready(), Wake.WakeStart.ALREADY_STARTED, "a post-completion poll is a no-op")
	assert_bitwise_equal(state.sample(), Wake.WakeSample.neutral(), "still complete")

## A readiness barrier that opens late produces exactly the immediate
## timeline: pre-ready ticks consume nothing, so both runs' sample
## vectors match tick for tick.
func test_delayed_readiness_produces_the_immediate_timeline() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var immediate: Array[Wake.WakeSample] = ready_run(boundaries.complete_tick + 2)

	var delayed: Wake.WakeState = authored_state()
	for _tick: int in range(10):
		assert_bitwise_equal(delayed.tick(), Wake.WakeSample.closed(), "held")
	assert_int_equal(delayed.mark_ready(), Wake.WakeStart.STARTED, "the late poll starts")
	assert_int_equal(delayed.current_tick(), 0, "the timeline starts at zero")
	var late: Array[Wake.WakeSample] = [delayed.sample()]
	for _tick: int in range(boundaries.complete_tick + 2):
		late.append(delayed.tick())

	assert_sample_vectors_equal(late, immediate, "delayed readiness cannot shorten the wake")

## Every named boundary samples bitwise the authored state crossing into
## it: tick zero and the closed hold, both blink bottoms, both peek
## apexes, and the neutral completion.
func test_named_boundaries_sample_exactly_through_both_blinks() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var timeline: Wake.WakeTimeline = Wake.WakeTimeline.authored()
	var closed: Wake.WakeSample = Wake.WakeSample.closed()

	assert_bitwise_equal(timeline.sample_at(0), closed, "tick zero (the readiness sample)")
	assert_bitwise_equal(timeline.sample_at(boundaries.first_opening_start), closed, "the boundary the first opening eases from")
	assert_bitwise_equal(
		timeline.sample_at(boundaries.first_blink_start),
		Wake.WakeSample.new(0.35, 0.85, 0.35, Vector2(0.012, 0.008)),
		"the first peek's widest sample"
	)
	assert_bitwise_equal(
		timeline.sample_at(boundaries.second_opening_start),
		Wake.WakeSample.new(0.0, 1.0, 0.35, Vector2(0.010, 0.007)),
		"the first blink fully shut, smear at peak"
	)
	assert_bitwise_equal(
		timeline.sample_at(boundaries.second_blink_start),
		Wake.WakeSample.new(0.70, 0.45, 0.75, Vector2(0.010, 0.006)),
		"the second peek's widest sample, shapes resolving"
	)
	assert_bitwise_equal(
		timeline.sample_at(boundaries.final_opening_start),
		Wake.WakeSample.new(0.0, 0.60, 0.75, Vector2(0.008, 0.005)),
		"the second blink fully shut, half-resolved blur"
	)
	assert_bitwise_equal(timeline.sample_at(boundaries.complete_tick), Wake.WakeSample.neutral(), "the completion tick is neutral")

## Interior ticks ease linearly between their beat's boundary states: the
## first opening one tick into its 42-tick ease, and the final opening two
## ticks into its 60-tick ease.
func test_interior_ticks_ease_linearly_within_their_beat() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var timeline: Wake.WakeTimeline = Wake.WakeTimeline.authored()
	var one_of_42: float = 1.0 / 42.0
	assert_sample_close(
		timeline.sample_at(boundaries.first_opening_start + 1),
		Wake.WakeSample.new(
			0.35 * one_of_42,
			1.0 - (1.0 - 0.85) * one_of_42,
			0.35 * one_of_42,
			Vector2(0.012 * one_of_42, 0.008 * one_of_42)
		),
		"first opening, one tick in"
	)
	# The final opening eases from the second blink's bottom toward
	# neutral: two ticks into its sixty-tick ease, progress is 2/60.
	var two_of_60: float = 2.0 / 60.0
	assert_sample_close(
		timeline.sample_at(boundaries.final_opening_start + 2),
		Wake.WakeSample.new(
			Wake.WakeSample.neutral().lid_openness * two_of_60,
			0.60 * (1.0 - two_of_60),
			0.75 + (1.0 - 0.75) * two_of_60,
			Vector2(0.008 * (1.0 - two_of_60), 0.005 * (1.0 - two_of_60))
		),
		"final opening, two ticks in"
	)

## A sample is a pure function of the logical tick: consuming the same
## span in uneven bursts lands on exactly the same samples as consuming
## it one tick at a time.
func test_sampling_is_independent_of_tick_batching() -> void:
	var one_by_one: Array[Wake.WakeSample] = ready_run(30)
	var timeline: Wake.WakeTimeline = Wake.WakeTimeline.authored()

	# 3 + 7 + 1 + 5 + 2 + 8 + 4 = 30 ticks, consumed in seven bursts.
	var bursty: Wake.WakeState = authored_state()
	bursty.mark_ready()
	var burst: Array[Wake.WakeSample] = [bursty.sample()]
	var span: Array[int] = [3, 7, 1, 5, 2, 8, 4]
	for ticks: int in span:
		for _tick: int in range(ticks):
			burst.append(bursty.tick())
	assert_int_equal(burst.size(), 31, "the bursts covered the whole span")
	assert_sample_vectors_equal(burst, one_by_one, "the burst run matches the one-by-one run")

	# The pure mapping agrees with every consumed step.
	for tick: int in range(one_by_one.size()):
		assert_true(timeline.sample_at(tick).equals(one_by_one[tick]), "tick %d: the pure mapping agrees" % tick)

## From the completion tick on, the machine rests in the neutral hold:
## fully open, zero residual blur and sway, the ramp neutral, forever.
func test_completion_holds_neutral_forever() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var state: Wake.WakeState = authored_state()
	state.mark_ready()
	for _tick: int in range(boundaries.complete_tick - 1):
		state.tick()
	assert_false(state.is_complete(), "the last authored tick is not done")
	state.tick()
	assert_int_equal(state.current_tick(), boundaries.complete_tick, "the completion tick")
	assert_true(state.is_complete(), "complete")
	assert_bitwise_equal(state.sample(), Wake.WakeSample.neutral(), "completion")

	for _tick: int in range(50):
		state.tick()
		assert_true(state.is_complete(), "still complete")
		assert_bitwise_equal(state.tick(), Wake.WakeSample.neutral(), "neutral hold")

## Reset returns the machine to its fresh restartable state, and a second
## run over the reset machine reproduces the first run bitwise.
func test_reset_returns_to_a_fresh_restartable_state() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var first: Array[Wake.WakeSample] = ready_run(boundaries.complete_tick + 2)
	var state: Wake.WakeState = authored_state()
	state.mark_ready()
	for _tick: int in range(boundaries.complete_tick + 2):
		state.tick()
	assert_true(state.is_complete(), "the first run completed")

	state.reset()
	assert_false(state.is_started(), "reset clears the start")
	assert_false(state.is_complete(), "reset clears completion")
	assert_int_equal(state.current_tick(), 0, "reset returns to tick zero")
	assert_bitwise_equal(state.sample(), Wake.WakeSample.closed(), "reset hold")

	assert_int_equal(state.mark_ready(), Wake.WakeStart.STARTED, "reset restarts")
	var second: Array[Wake.WakeSample] = [state.sample()]
	for _tick: int in range(boundaries.complete_tick + 2):
		second.append(state.tick())
	assert_sample_vectors_equal(second, first, "a reset run reproduces the first")

## Reset works mid-run too: a machine interrupted partway and restarted
## never carries state across.
func test_reset_mid_run_restarts_cleanly() -> void:
	var canonical: Array[Wake.WakeSample] = ready_run(10)
	var state: Wake.WakeState = authored_state()
	state.mark_ready()
	for _tick: int in range(4):
		state.tick()
	state.reset()
	state.mark_ready()
	var restarted: Array[Wake.WakeSample] = [state.sample()]
	for _tick: int in range(10):
		restarted.append(state.tick())
	assert_sample_vectors_equal(restarted, canonical, "an interrupted run restarts clean")

## The two authored blinks are distinguishable: the first runs 0.45 s and
## smears fully shut from a narrow peek, the second runs 0.40 s and closes
## from the wider shapes-resolving opening on half-resolved blur.
func test_authored_blinks_are_distinguishable() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var first_blink: int = boundaries.second_opening_start - boundaries.first_blink_start
	var second_blink: int = boundaries.final_opening_start - boundaries.second_blink_start
	assert_int_equal(first_blink, 27, "the first blink's duration")
	assert_int_equal(second_blink, 24, "the second blink's duration")
	assert_true(first_blink != second_blink, "the durations differ")

	var timeline: Wake.WakeTimeline = Wake.WakeTimeline.authored()
	var first_bottom: Wake.WakeSample = timeline.sample_at(boundaries.second_opening_start)
	var second_bottom: Wake.WakeSample = timeline.sample_at(boundaries.final_opening_start)
	assert_true(first_bottom.blur > second_bottom.blur, "the first blink smears fully, the second stays half-resolved")
	assert_bits_equal(first_bottom.blur, 1.0, "the first blink's bottom blur")
	assert_bits_equal(second_bottom.blur, 0.60, "the second blink's bottom blur")

	var first_apex: Wake.WakeSample = timeline.sample_at(boundaries.first_blink_start)
	var second_apex: Wake.WakeSample = timeline.sample_at(boundaries.second_blink_start)
	assert_true(first_apex.lid_openness < second_apex.lid_openness, "the first peek is narrow, the second resolves shapes")

## The authored table is exactly what the general constructor accepts,
## and authored builds it: the frozen instance cannot drift from the
## validated path.
func test_authored_table_is_valid_by_the_general_constructor() -> void:
	var rebuilt: Wake.Result = Wake.WakeTimeline.try_new(Wake._authored_initial(), Wake._authored_beats())
	assert_true(rebuilt.is_ok(), "the authored table passes its own validation")
	assert_true(rebuilt.timeline.equals(Wake.WakeTimeline.authored()), "the rebuilt timeline is the authored one")

## The authored boundaries match the frozen table's derived boundaries
## field for field, start at zero, and ascend to the completion tick.
func test_authored_boundaries_match_the_authored_table() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	var timeline: Wake.WakeTimeline = Wake.WakeTimeline.authored()
	var starts: Array[int] = timeline.boundaries()
	var named: Wake.AuthoredBoundaries = Wake.WakeTimeline.authored_boundaries()

	assert_int_equal(starts.size(), 6, "one boundary per authored beat")
	assert_int_equal(starts[0], 0, "the first boundary is tick zero")
	var from_starts: Wake.AuthoredBoundaries = Wake.AuthoredBoundaries.new()
	from_starts.first_opening_start = starts[1]
	from_starts.first_blink_start = starts[2]
	from_starts.second_opening_start = starts[3]
	from_starts.second_blink_start = starts[4]
	from_starts.final_opening_start = starts[5]
	from_starts.complete_tick = timeline.complete_tick()
	assert_true(named.equals(from_starts), "the named boundaries are the table's boundaries")
	assert_true(named.equals(boundaries), "the authored boundaries are the frozen numbers")
	for index: int in range(starts.size() - 1):
		assert_true(starts[index] < starts[index + 1], "boundaries ascend")
	assert_int_equal(starts[starts.size() - 1], boundaries.final_opening_start, "the last start is the final opening")

## Malformed scalar authoring is rejected with its typed error, naming
## the location and the offending value.
func test_malformed_scalars_are_rejected_with_typed_errors() -> void:
	var nan_initial: Wake.WakeSample = Wake.WakeSample.closed()
	nan_initial.blur = NAN
	var nan_result: Wake.Result = Wake.WakeTimeline.try_new(nan_initial, Wake._authored_beats())
	# NaN never equals itself, so the rejection is matched structurally.
	assert_true(nan_result.error != null and nan_result.error.kind == Wake.WakeTimelineError.Kind.NON_FINITE_VALUE, "a NaN blur is a non-finite rejection")
	assert_true(nan_result.error.at.equals(Wake.WakeAuthoring.initial()), "the rejection names the initial state")
	assert_int_equal(nan_result.error.field, Wake.WakeField.BLUR, "the rejection names blur")
	assert_true(is_nan(nan_result.error.got), "the rejection carries the NaN")

	var inf_initial: Wake.WakeSample = Wake.WakeSample.closed()
	inf_initial.exposure_ramp = INF
	var inf_result: Wake.Result = Wake.WakeTimeline.try_new(inf_initial, Wake._authored_beats())
	assert_true(inf_result.error != null and inf_result.error.equals(Wake.WakeTimelineError.non_finite_value(Wake.WakeAuthoring.initial(), Wake.WakeField.EXPOSURE_RAMP, INF)), "an infinite ramp is rejected with its value")

	var ramp_beats: Array[Wake.WakeBeat] = Wake._authored_beats()
	ramp_beats[1].end.exposure_ramp = 1.5
	var ramp_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), ramp_beats)
	assert_true(ramp_result.error != null and ramp_result.error.equals(Wake.WakeTimelineError.value_out_of_range(Wake.WakeAuthoring.beat_end(1), Wake.WakeField.EXPOSURE_RAMP, 1.5)), "an out-of-range ramp is rejected with its location and value")

	var sway_beats: Array[Wake.WakeBeat] = Wake._authored_beats()
	sway_beats[4].end.sway_offset = Vector2(Wake.SWAY_OFFSET_MAX_RADIANS * 2.0, 0.0)
	var sway_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), sway_beats)
	assert_true(sway_result.error != null and sway_result.error.kind == Wake.WakeTimelineError.Kind.SWAY_OFFSET_TOO_LARGE, "an oversized sway is rejected")
	assert_true(sway_result.error.at.equals(Wake.WakeAuthoring.beat_end(4)), "the rejection names beat 4's end state")

## Malformed timeline structure is rejected: no beats, a zero-tick beat,
## a non-closed initial state, and a landing off the neutral hold.
func test_malformed_structure_is_rejected_with_typed_errors() -> void:
	var no_beats: Array[Wake.WakeBeat] = []
	var empty_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), no_beats)
	assert_true(empty_result.error != null and empty_result.error.equals(Wake.WakeTimelineError.no_beats()), "an empty table has no timeline")

	var zero_beats: Array[Wake.WakeBeat] = Wake._authored_beats()
	zero_beats[3].ticks = 0
	var zero_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), zero_beats)
	assert_true(zero_result.error != null and zero_result.error.equals(Wake.WakeTimelineError.zero_duration_beat(3)), "a zero-tick beat is rejected by index")

	var open_initial: Wake.WakeSample = Wake.WakeSample.closed()
	open_initial.lid_openness = 0.5
	var open_result: Wake.Result = Wake.WakeTimeline.try_new(open_initial, Wake._authored_beats())
	assert_true(open_result.error != null and open_result.error.equals(Wake.WakeTimelineError.initial_not_closed(0.5)), "a non-closed initial state is rejected")

	var landing_beats: Array[Wake.WakeBeat] = Wake._authored_beats()
	landing_beats[5].end.blur = 0.25
	var landing_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), landing_beats)
	assert_true(landing_result.error != null and landing_result.error.equals(Wake.WakeTimelineError.final_not_neutral(Wake.WakeSample.new(1.0, 0.25, 1.0, Vector2.ZERO))), "an off-neutral landing is rejected with its state")

## Rejection text names the location and the offending value, so a bad
## authoring edit fails with something readable.
func test_rejections_display_their_location_and_value() -> void:
	var blur_beats: Array[Wake.WakeBeat] = Wake._authored_beats()
	blur_beats[2].end.blur = -0.1
	var blur_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), blur_beats)
	assert_true(blur_result.error != null, "a negative blur must be rejected")
	var blur_text: String = blur_result.error._to_string()
	assert_true(blur_text.find("beat 2's end state") != -1, "display: %s" % blur_text)
	assert_true(blur_text.find("-0.1") != -1, "display: %s" % blur_text)

	var open_initial: Wake.WakeSample = Wake.WakeSample.closed()
	open_initial.lid_openness = 0.2
	var open_result: Wake.Result = Wake.WakeTimeline.try_new(open_initial, Wake._authored_beats())
	assert_true(open_result.error != null, "a non-closed initial state must be rejected")
	var open_text: String = open_result.error._to_string()
	assert_true(open_text.find("not fully closed") != -1, "display: %s" % open_text)
	assert_true(open_text.find("0.2") != -1, "display: %s" % open_text)

## The duration table: the authored milliseconds encode at the logical
## rate to the frozen tick counts, the completion tick is their sum, and
## the rate is the production logical clock's.
func test_authored_durations_sum_to_the_frozen_boundaries() -> void:
	var boundaries: Wake.AuthoredBoundaries = frozen_boundaries()
	assert_int_equal(Wake.LOGICAL_TICKS_PER_SECOND, 60, "the logical rate")
	var ticks: Array[int] = []
	for beat: Wake.WakeBeat in Wake._authored_beats():
		ticks.append(beat.ticks)
	var frozen_ticks: Array[int] = [75, 42, 27, 54, 24, 60]
	assert_sample_free_int_vectors_equal(ticks, frozen_ticks, "the encoded beat table")
	for index: int in range(Wake._AUTHORED_BEAT_MILLIS.size()):
		assert_int_equal(Wake._ticks_for(Wake._AUTHORED_BEAT_MILLIS[index]), frozen_ticks[index], "authored %d ms must encode to its documented tick count" % Wake._AUTHORED_BEAT_MILLIS[index])
	var total: int = 0
	for encoded: int in ticks:
		total += encoded
	assert_int_equal(total, boundaries.complete_tick, "the completion tick is the tick sum")
	assert_int_equal(Wake.WakeTimeline.authored().complete_tick(), boundaries.complete_tick, "the authored timeline completes at the sum")
	# The authored wall-clock total is the sum of the milliseconds table:
	# 4700 ms, the 4.70 s the opening beat is written to.
	var total_millis: int = 0
	for millis: int in Wake._AUTHORED_BEAT_MILLIS:
		total_millis += millis
	assert_int_equal(total_millis, 4700, "authored total in milliseconds")

func assert_sample_free_int_vectors_equal(actual: Array[int], expected: Array[int], label: String) -> void:
	if actual.size() != expected.size():
		_fail("%s: expected %d ticks, got %d" % [label, expected.size(), actual.size()])
		return
	for index: int in range(expected.size()):
		if actual[index] != expected[index]:
			_fail("%s: expected %d, got %d" % [label, expected[index], actual[index]])
			return

## A duration that cannot fill one logical tick encodes to zero ticks and
## fails construction loudly: there is no clamp-to-one fallback. GDScript
## has no catchable panic, so the rejection is observed through the
## guard the encoder asserts on.
func test_a_duration_shorter_than_half_a_tick_fails_explicitly() -> void:
	# 8 ms at 60 Hz is 0.48 ticks: it cannot carry a boundary.
	var failure: String = Wake._duration_failure(8)
	assert_true(failure != "", "8 ms must not encode")
	assert_true(failure.find("encodes to zero ticks") != -1, "the rejection names its reason: %s" % failure)

## The seconds-per-tick constant is exactly one over the tick rate,
## computed through the same IEEE-754 division, so the pair cannot drift.
func test_the_tick_secs_constant_is_one_over_the_tick_rate() -> void:
	assert_bits_equal(Wake.LOGICAL_TICK_SECS, 1.0 / float(Wake.LOGICAL_TICKS_PER_SECOND), "the seconds-per-tick constant")

## A duration encoding past a beat's 65535 tick width fails construction
## loudly: there is no clamp-to-max fallback (long holds are chained
## beats).
func test_a_duration_wider_than_a_beat_fails_explicitly() -> void:
	# 2,000,000 ms at 60 Hz encodes to 120,000 ticks: chain beats instead.
	var failure: String = Wake._duration_failure(2_000_000)
	assert_true(failure != "", "2,000,000 ms must not encode as one beat")
	assert_true(failure.find("above a beat's 65535 tick width") != -1, "the rejection names its reason: %s" % failure)

## A beat authored to end exactly neutral is accepted even when earlier
## beats carry the wake's dynamics: validation constrains the landing,
## not the arc.
func test_a_two_beat_timeline_with_a_neutral_landing_is_valid() -> void:
	var one_beats: Array[Wake.WakeBeat] = [
		Wake.WakeBeat.new(1, Wake.WakeSample.new(0.5, 0.5, 0.5, Vector2(0.01, 0.0))),
	]
	var one_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), one_beats)
	assert_true(one_result.error != null and one_result.error.kind == Wake.WakeTimelineError.Kind.FINAL_NOT_NEUTRAL, "one beat cannot both move and land neutral")

	var two_beats: Array[Wake.WakeBeat] = [
		Wake.WakeBeat.new(1, Wake.WakeSample.new(0.5, 0.5, 0.5, Vector2(0.01, 0.0))),
		Wake.WakeBeat.new(1, Wake.WakeSample.neutral()),
	]
	var two_result: Wake.Result = Wake.WakeTimeline.try_new(Wake.WakeSample.closed(), two_beats)
	assert_true(two_result.is_ok(), "the landing beat is exactly neutral")
	assert_int_equal(two_result.timeline.complete_tick(), 2, "the two-beat completion tick")
	var starts: Array[int] = two_result.timeline.boundaries()
	assert_sample_free_int_vectors_equal(starts, [0, 1], "the two-beat boundaries")
	assert_bitwise_equal(two_result.timeline.sample_at(2), Wake.WakeSample.neutral(), "landed")
