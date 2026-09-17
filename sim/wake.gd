class_name Wake
extends RefCounted
## The authored eyelid wake timeline, ported from gone_sim wake.rs. The
## story beat: the player's eyes open in stages — the first blink is a
## smear of light and blur, the second resolves shapes, then the eye holds
## open. WakeTimeline authors the sequence as a beat table with durations
## in milliseconds encoded once to logical ticks; WakeState drives it
## behind a readiness contract that holds fully closed until readiness is
## marked, starts the timeline exactly once, and rests in the neutral hold
## from completion on. One sample is lid openness, blur, an exposure ramp,
## and a sway offset in radians; every sample is a pure function of the
## logical tick, eased linearly per beat with progress computed as one
## division, so tick batching cannot change a sample. Validation is
## fail-loud: malformed authoring constructs nothing, and a duration that
## cannot encode as a beat's tick width fails loudly rather than clamping.
## Pure logic: no clocks, no RNG, no render or input types.

## The game's logical tick rate, in ticks per second.
const LOGICAL_TICKS_PER_SECOND: int = 60

## One logical tick's duration in seconds.
const LOGICAL_TICK_SECS: float = 1.0 / 60.0

## The largest sway offset magnitude a validated timeline may author, in
## radians.
const SWAY_OFFSET_MAX_RADIANS: float = 0.05

enum WakeStart { STARTED, ALREADY_STARTED }

enum WakeField { LID_OPENNESS, BLUR, EXPOSURE_RAMP, SWAY_OFFSET }

## One sampled moment of the wake timeline: the four values the post pass
## and camera consumers read. Plain data; validation happens where the
## authoring is consumed (WakeTimeline.try_new).
class WakeSample:
	extends RefCounted

	var lid_openness: float = 0.0
	var blur: float = 0.0
	var exposure_ramp: float = 0.0
	var sway_offset: Vector2 = Vector2.ZERO

	func _init(p_lid_openness: float, p_blur: float, p_exposure_ramp: float, p_sway_offset: Vector2) -> void:
		lid_openness = p_lid_openness
		blur = p_blur
		exposure_ramp = p_exposure_ramp
		sway_offset = p_sway_offset

	## The neutral hold: fully open, sharp, ramp neutral, no sway. The
	## sample every completed wake returns, and the state the last
	## authored beat must land on exactly.
	static func neutral() -> Wake.WakeSample:
		return Wake.WakeSample.new(1.0, 0.0, 1.0, Vector2.ZERO)

	## The fully closed, fully smeared, dark rest state held before
	## readiness and sampled at tick zero.
	static func closed() -> Wake.WakeSample:
		return Wake.WakeSample.new(0.0, 1.0, 0.0, Vector2.ZERO)

	## Ease linearly from `from` toward `to` by `progress` in [0, 1]. At
	## zero the result is `from` bitwise: boundary ticks must sample
	## exactly the authored boundary states, with no interpolation error.
	static func _lerp(from: Wake.WakeSample, to: Wake.WakeSample, progress: float) -> Wake.WakeSample:
		return Wake.WakeSample.new(
			from.lid_openness + (to.lid_openness - from.lid_openness) * progress,
			from.blur + (to.blur - from.blur) * progress,
			from.exposure_ramp + (to.exposure_ramp - from.exposure_ramp) * progress,
			from.sway_offset + (to.sway_offset - from.sway_offset) * progress
		)

	func equals(other: Wake.WakeSample) -> bool:
		return other != null \
			and lid_openness == other.lid_openness \
			and blur == other.blur \
			and exposure_ramp == other.exposure_ramp \
			and sway_offset == other.sway_offset

	func _to_string() -> String:
		return "(lid_openness: %s, blur: %s, exposure_ramp: %s, sway_offset: %s)" % [
			str(lid_openness), str(blur), str(exposure_ramp), str(sway_offset)
		]

## One authored beat: an explicit duration in logical ticks and the
## sample state the beat eases toward at its end boundary.
class WakeBeat:
	extends RefCounted

	var ticks: int = 0
	var end: Wake.WakeSample = null

	func _init(p_ticks: int, p_end: Wake.WakeSample) -> void:
		ticks = p_ticks
		end = p_end

	func equals(other: Wake.WakeBeat) -> bool:
		return other != null and ticks == other.ticks and end.equals(other.end)

## Where an authored sample sits in the timeline, for error reporting.
class WakeAuthoring:
	extends RefCounted

	enum Kind { INITIAL, BEAT_END }

	var kind: int = Kind.INITIAL
	var index: int = 0

	static func initial() -> Wake.WakeAuthoring:
		var at: Wake.WakeAuthoring = Wake.WakeAuthoring.new()
		at.kind = Kind.INITIAL
		return at

	static func beat_end(p_index: int) -> Wake.WakeAuthoring:
		var at: Wake.WakeAuthoring = Wake.WakeAuthoring.new()
		at.kind = Kind.BEAT_END
		at.index = p_index
		return at

	func equals(other: Wake.WakeAuthoring) -> bool:
		if other == null or kind != other.kind:
			return false
		if kind == Kind.BEAT_END:
			return index == other.index
		return true

	func _to_string() -> String:
		match kind:
			Kind.INITIAL:
				return "the initial state"
			_:
				return "beat %d's end state" % index

## A rejected wake-timeline construction. Validation is fail-loud: every
## rejected construction leaves nothing behind to sample.
class WakeTimelineError:
	extends RefCounted

	enum Kind { NO_BEATS, ZERO_DURATION_BEAT, NON_FINITE_VALUE, VALUE_OUT_OF_RANGE, SWAY_OFFSET_TOO_LARGE, INITIAL_NOT_CLOSED, FINAL_NOT_NEUTRAL }

	var kind: int = Kind.NO_BEATS
	var at: Wake.WakeAuthoring = null
	var field: int = Wake.WakeField.LID_OPENNESS
	var got: float = 0.0
	var got_sample: Wake.WakeSample = null
	var max: float = 0.0
	var index: int = 0

	static func no_beats() -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.NO_BEATS
		return error

	static func zero_duration_beat(p_index: int) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.ZERO_DURATION_BEAT
		error.index = p_index
		return error

	static func non_finite_value(at: Wake.WakeAuthoring, field: int, got: float) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.NON_FINITE_VALUE
		error.at = at
		error.field = field
		error.got = got
		return error

	static func value_out_of_range(at: Wake.WakeAuthoring, field: int, got: float) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.VALUE_OUT_OF_RANGE
		error.at = at
		error.field = field
		error.got = got
		return error

	static func sway_offset_too_large(at: Wake.WakeAuthoring, got: float, max: float) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.SWAY_OFFSET_TOO_LARGE
		error.at = at
		error.got = got
		error.max = max
		return error

	static func initial_not_closed(got: float) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.INITIAL_NOT_CLOSED
		error.got = got
		return error

	static func final_not_neutral(got: Wake.WakeSample) -> Wake.WakeTimelineError:
		var error: Wake.WakeTimelineError = Wake.WakeTimelineError.new()
		error.kind = Kind.FINAL_NOT_NEUTRAL
		error.got_sample = got
		return error

	func equals(other: Wake.WakeTimelineError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.ZERO_DURATION_BEAT:
				return index == other.index
			Kind.NON_FINITE_VALUE, Kind.VALUE_OUT_OF_RANGE:
				return at.equals(other.at) and field == other.field and Wake._same_float(got, other.got)
			Kind.SWAY_OFFSET_TOO_LARGE:
				return at.equals(other.at) and Wake._same_float(got, other.got) and Wake._same_float(max, other.max)
			Kind.INITIAL_NOT_CLOSED:
				return Wake._same_float(got, other.got)
			Kind.FINAL_NOT_NEUTRAL:
				return got_sample != null and got_sample.equals(other.got_sample)
			_:
				return true

	func _to_string() -> String:
		match kind:
			Kind.NO_BEATS:
				return "a wake timeline needs at least one beat"
			Kind.ZERO_DURATION_BEAT:
				return "wake beat %d authored a zero-tick duration" % index
			Kind.NON_FINITE_VALUE:
				return "wake timeline %s carried a non-finite %s: %s" % [at._to_string(), _field_name(), str(got)]
			Kind.VALUE_OUT_OF_RANGE:
				return "wake timeline %s carried %s value %s outside [0, 1]" % [at._to_string(), _field_name(), str(got)]
			Kind.SWAY_OFFSET_TOO_LARGE:
				return "wake timeline %s authored sway offset magnitude %s, above the %s rad small-motion bound" % [at._to_string(), str(got), str(max)]
			Kind.INITIAL_NOT_CLOSED:
				return "wake timeline initial openness %s is not fully closed: the tick-zero sample must be the closed rest state" % str(got)
			_:
				return "wake timeline's last beat must end exactly neutral, got %s" % got_sample._to_string()

	func _field_name() -> String:
		match field:
			Wake.WakeField.LID_OPENNESS:
				return "LidOpenness"
			Wake.WakeField.BLUR:
				return "Blur"
			Wake.WakeField.EXPOSURE_RAMP:
				return "ExposureRamp"
			_:
				return "SwayOffset"

class Result:
	extends RefCounted

	var timeline: Wake.WakeTimeline = null
	var error: Wake.WakeTimelineError = null

	static func with_timeline(valid: Wake.WakeTimeline) -> Wake.Result:
		var result: Wake.Result = Wake.Result.new()
		result.timeline = valid
		return result

	static func with_error(failure: Wake.WakeTimelineError) -> Wake.Result:
		var result: Wake.Result = Wake.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

## The named tick boundaries of the authored timeline: the ticks the
## harness's temporal captures and the app's consumers pin.
class AuthoredBoundaries:
	extends RefCounted

	var first_opening_start: int = 0
	var first_blink_start: int = 0
	var second_opening_start: int = 0
	var second_blink_start: int = 0
	var final_opening_start: int = 0
	var complete_tick: int = 0

	func equals(other: Wake.AuthoredBoundaries) -> bool:
		return other != null \
			and first_opening_start == other.first_opening_start \
			and first_blink_start == other.first_blink_start \
			and second_opening_start == other.second_opening_start \
			and second_blink_start == other.second_blink_start \
			and final_opening_start == other.final_opening_start \
			and complete_tick == other.complete_tick

## The authored beat durations, in explicit milliseconds: the production
## timing of the opening beat. Total: 4700 ms, 282 logical ticks.
const _AUTHORED_BEAT_MILLIS: Array = [1250, 700, 450, 900, 400, 1000]

## The validated wake timeline: an initial state plus a beat table with
## cumulative boundaries. Built only through try_new, which validates the
## authoring, or authored, the canonical opening-beat instance.
class WakeTimeline:
	extends RefCounted

	var _initial: Wake.WakeSample = null
	var _beats: Array[Wake.WakeBeat] = []
	var _beat_starts: Array[int] = []
	var _complete_tick: int = 0

	## The canonical opening-beat timeline: the closed rest hold, the
	## first opening to a narrow smear of light, the first blink shut, the
	## second opening wider with shapes resolving, the second blink shut,
	## and the final opening to the neutral hold.
	static func authored() -> Wake.WakeTimeline:
		return _build(Wake._authored_initial(), Wake._authored_beats())

	static func try_new(initial: Wake.WakeSample, beats: Array[Wake.WakeBeat]) -> Wake.Result:
		if beats.is_empty():
			return Wake.Result.with_error(Wake.WakeTimelineError.no_beats())
		var bad_initial: Wake.WakeTimelineError = Wake._validate_sample(initial, Wake.WakeAuthoring.initial())
		if bad_initial != null:
			return Wake.Result.with_error(bad_initial)
		if initial.lid_openness != 0.0:
			return Wake.Result.with_error(Wake.WakeTimelineError.initial_not_closed(initial.lid_openness))
		for index: int in range(beats.size()):
			if beats[index].ticks == 0:
				return Wake.Result.with_error(Wake.WakeTimelineError.zero_duration_beat(index))
			var bad_end: Wake.WakeTimelineError = Wake._validate_sample(beats[index].end, Wake.WakeAuthoring.beat_end(index))
			if bad_end != null:
				return Wake.Result.with_error(bad_end)
		if not beats[beats.size() - 1].end.equals(Wake.WakeSample.neutral()):
			return Wake.Result.with_error(Wake.WakeTimelineError.final_not_neutral(beats[beats.size() - 1].end))
		return Wake.Result.with_timeline(_build(initial, beats))

	## Build without re-validating: the caller has checked the table.
	static func _build(initial: Wake.WakeSample, beats: Array[Wake.WakeBeat]) -> Wake.WakeTimeline:
		var timeline: Wake.WakeTimeline = Wake.WakeTimeline.new()
		timeline._initial = initial
		timeline._beats = beats
		var complete_tick: int = 0
		for beat: Wake.WakeBeat in beats:
			timeline._beat_starts.append(complete_tick)
			complete_tick += beat.ticks
		timeline._complete_tick = complete_tick
		return timeline

	## The beat table's start ticks, ascending, one per beat. The first is
	## always 0; the completion tick is the first tick past the last.
	func boundaries() -> Array[int]:
		return _beat_starts

	## The first fully complete tick: the first tick past the last beat.
	func complete_tick() -> int:
		return _complete_tick

	## The named boundaries of the authored timeline, for temporal capture
	## and consumer pinning.
	static func authored_boundaries() -> Wake.AuthoredBoundaries:
		var timeline: Wake.WakeTimeline = authored()
		var starts: Array[int] = timeline._beat_starts
		var named: Wake.AuthoredBoundaries = Wake.AuthoredBoundaries.new()
		named.first_opening_start = starts[1]
		named.first_blink_start = starts[2]
		named.second_opening_start = starts[3]
		named.second_blink_start = starts[4]
		named.final_opening_start = starts[5]
		named.complete_tick = timeline._complete_tick
		return named

	## The sample at logical tick `tick`: the held initial state at the
	## timeline's start, the eased beat state through the table, and the
	## neutral hold from the completion tick on. A pure function of the
	## tick: no accumulated state, so any batching of ticks produces the
	## same sample.
	func sample_at(tick: int) -> Wake.WakeSample:
		if tick >= _complete_tick:
			return Wake.WakeSample.neutral()
		var index: int = _beat_index_for(tick)
		var start: int = _beat_starts[index]
		var beat: Wake.WakeBeat = _beats[index]
		var from: Wake.WakeSample = _initial if index == 0 else _beats[index - 1].end
		var progress: float = float(tick - start) / float(beat.ticks)
		return Wake.WakeSample._lerp(from, beat.end, progress)

	## The index of the beat whose tick range covers `tick`. `tick` is
	## strictly below the completion tick here, so the scan always lands.
	func _beat_index_for(tick: int) -> int:
		var index: int = 0
		for candidate: int in range(_beat_starts.size()):
			if _beat_starts[candidate] > tick:
				break
			index = candidate
		return index

	func equals(other: Wake.WakeTimeline) -> bool:
		if other == null or not _initial.equals(other._initial):
			return false
		if _beats.size() != other._beats.size():
			return false
		for index: int in range(_beats.size()):
			if not _beats[index].equals(other._beats[index]):
				return false
		return _beat_starts == other._beat_starts and _complete_tick == other._complete_tick

## The tick-driven wake machine over one WakeTimeline: holds closed until
## readiness, runs the table one logical tick per tick, and rests in the
## neutral hold from completion on. Before readiness the machine consumes
## nothing: ticks arrive, the sample holds fully closed, and the tick
## counter stays at zero, so a readiness barrier that opens late cannot
## shorten the authored sequence.
class WakeState:
	extends RefCounted

	var _timeline: Wake.WakeTimeline = null
	var _tick: int = 0
	var _started: bool = false

	func _init(timeline: Wake.WakeTimeline) -> void:
		_timeline = timeline

	## Mark the readiness barrier open. The first poll starts the timeline
	## at tick zero (whose sample is the fully closed rest state); every
	## later poll returns ALREADY_STARTED and changes nothing.
	func mark_ready() -> int:
		if _started:
			return Wake.WakeStart.ALREADY_STARTED
		_started = true
		return Wake.WakeStart.STARTED

	func is_started() -> bool:
		return _started

	## The current logical tick: zero until readiness starts the timeline,
	## one per tick after.
	func current_tick() -> int:
		return _tick

	func is_complete() -> bool:
		return _started and _tick >= _timeline._complete_tick

	## The sample at the current logical tick, without advancing.
	func sample() -> Wake.WakeSample:
		return _timeline.sample_at(_tick)

	## Consume one logical tick. Before readiness this consumes nothing:
	## the sample holds fully closed and the counter stays at zero. After
	## readiness the counter advances by exactly one and the returned
	## sample is the new tick's; after completion every tick samples the
	## neutral hold.
	func tick() -> Wake.WakeSample:
		if _started:
			_tick += 1
		return sample()

	## Return the machine to its fresh state: not started, tick zero,
	## holding fully closed, restartable. The timeline data is kept.
	func reset() -> void:
		_tick = 0
		_started = false

## The authored timeline's initial state: the closed rest state.
static func _authored_initial() -> Wake.WakeSample:
	return Wake.WakeSample.closed()

## The authored beat table, in walk order: the closed hold, a drowsy
## first opening to a narrow smear, the first blink shut, a wider second
## opening with shapes resolving, the shorter second blink, and the final
## opening to the neutral hold. The two blinks differ in duration and in
## their value arcs, so a temporal capture can tell them apart.
static func _authored_beats() -> Array[Wake.WakeBeat]:
	var beats: Array[Wake.WakeBeat] = [
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[0]), Wake.WakeSample.closed()),
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[1]), Wake.WakeSample.new(0.35, 0.85, 0.35, Vector2(0.012, 0.008))),
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[2]), Wake.WakeSample.new(0.0, 1.0, 0.35, Vector2(0.010, 0.007))),
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[3]), Wake.WakeSample.new(0.70, 0.45, 0.75, Vector2(0.010, 0.006))),
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[4]), Wake.WakeSample.new(0.0, 0.60, 0.75, Vector2(0.008, 0.005))),
		Wake.WakeBeat.new(_ticks_for(_AUTHORED_BEAT_MILLIS[5]), Wake.WakeSample.neutral()),
	]
	return beats

## Convert an authored duration in milliseconds to its logical tick count
## at LOGICAL_TICKS_PER_SECOND, rounded to the nearest whole tick in
## exact integer arithmetic: the 500 added below is half a tick in
## milliseconds, so a half tick rounds up into the beat that carries it.
## An authored duration that overflows the conversion, encodes above a
## beat's 65535 tick width, or rounds to zero ticks fails loudly: there
## is no clamping fallback for malformed authoring.
static func _ticks_for(millis: int) -> int:
	var failure: String = _duration_failure(millis)
	assert(failure.is_empty(), failure)
	return (millis * LOGICAL_TICKS_PER_SECOND + 500) / 1000

## The rejection a duration would fail with, or "" when it encodes. Split
## out so the guards are observable: GDScript has no catchable panic.
static func _duration_failure(millis: int) -> String:
	if millis > (9223372036854775807 - 500) / LOGICAL_TICKS_PER_SECOND:
		return "an authored wake duration must not overflow the tick conversion"
	var ticks: int = (millis * LOGICAL_TICKS_PER_SECOND + 500) / 1000
	if ticks > 65535:
		return "an authored duration encodes to %d ticks: above a beat's 65535 tick width" % ticks
	if ticks < 1:
		return "an authored wake duration encodes to zero ticks: shorter than half a logical tick"
	return ""

## Validate one authored sample: every scalar finite and in [0, 1], the
## sway offset finite and within the small-motion bound.
static func _validate_sample(sample: Wake.WakeSample, at: Wake.WakeAuthoring) -> Wake.WakeTimelineError:
	var bad_scalar: Wake.WakeTimelineError = _check_ranged(sample.lid_openness, Wake.WakeField.LID_OPENNESS, at)
	if bad_scalar != null:
		return bad_scalar
	bad_scalar = _check_ranged(sample.blur, Wake.WakeField.BLUR, at)
	if bad_scalar != null:
		return bad_scalar
	bad_scalar = _check_ranged(sample.exposure_ramp, Wake.WakeField.EXPOSURE_RAMP, at)
	if bad_scalar != null:
		return bad_scalar
	if not (is_finite(sample.sway_offset.x) and is_finite(sample.sway_offset.y)):
		return Wake.WakeTimelineError.non_finite_value(at, Wake.WakeField.SWAY_OFFSET, sample.sway_offset.x + sample.sway_offset.y)
	var magnitude: float = sample.sway_offset.length()
	if magnitude > SWAY_OFFSET_MAX_RADIANS:
		return Wake.WakeTimelineError.sway_offset_too_large(at, magnitude, SWAY_OFFSET_MAX_RADIANS)
	return null

## Check one authored scalar: finite, then within [0, 1].
static func _check_ranged(value: float, field: int, at: Wake.WakeAuthoring) -> Wake.WakeTimelineError:
	if not is_finite(value):
		return Wake.WakeTimelineError.non_finite_value(at, field, value)
	if not (0.0 <= value and value <= 1.0):
		return Wake.WakeTimelineError.value_out_of_range(at, field, value)
	return null

static func _same_float(a: float, b: float) -> bool:
	return a == b or (is_nan(a) and is_nan(b))
