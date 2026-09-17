class_name Intensity
extends RefCounted
## Deterministic fixture-intensity interpolation, ported from gone_sim
## intensity.rs. A fixture driven by the power state eases from its current
## value toward a target over an explicit settle duration in logical
## ticks. A fade holds its start value before the first tick, eases
## linearly between the endpoints, lands on the target bitwise at exactly
## the settle tick, and holds it forever after; progress is one division
## by the settle duration, never a running sum, so batching ticks cannot
## change a value. A settle of zero is the immediate hard cut. Validation
## is fail-loud: non-finite and negative intensities construct nothing.
## Intensities are unbounded; settle durations are unsigned counts in
## 0..=65535. Pure logic: no clocks, no RNG, no render types.

class FixtureFadeError:
	extends RefCounted

	enum Kind { NON_FINITE_INTENSITY, NEGATIVE_INTENSITY }

	var kind: int = Kind.NON_FINITE_INTENSITY
	var got: float = 0.0

	static func non_finite_intensity(value: float) -> Intensity.FixtureFadeError:
		var error: Intensity.FixtureFadeError = Intensity.FixtureFadeError.new()
		error.kind = Kind.NON_FINITE_INTENSITY
		error.got = value
		return error

	static func negative_intensity(value: float) -> Intensity.FixtureFadeError:
		var error: Intensity.FixtureFadeError = Intensity.FixtureFadeError.new()
		error.kind = Kind.NEGATIVE_INTENSITY
		error.got = value
		return error

	func equals(other: Intensity.FixtureFadeError) -> bool:
		return other != null and kind == other.kind and _same_float(got, other.got)

	static func _same_float(a: float, b: float) -> bool:
		return a == b or (is_nan(a) and is_nan(b))

	func _to_string() -> String:
		match kind:
			Kind.NON_FINITE_INTENSITY:
				return "fixture intensity carried a non-finite value: %s" % str(got)
			_:
				return "fixture intensity %s is negative: intensities count up from dark" % str(got)

class Result:
	extends RefCounted

	var fade: Intensity.FixtureFade = null
	var error: Intensity.FixtureFadeError = null

	static func with_fade(valid: Intensity.FixtureFade) -> Intensity.Result:
		var result: Intensity.Result = Intensity.Result.new()
		result.fade = valid
		return result

	static func with_error(failure: Intensity.FixtureFadeError) -> Intensity.Result:
		var result: Intensity.Result = Intensity.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class FixtureFade:
	extends RefCounted
	## One fixture's intensity fade: the pure, tick-driven crossfade
	## helper. Built only through try_new and holding, which validate
	## their inputs; the fade changes only through tick and retarget.

	var _from: float = 0.0
	var _target: float = 0.0
	var _settle_ticks: int = 0
	var _elapsed_ticks: int = 0

	static func try_new(initial: float, target: float, settle_ticks: int) -> Intensity.Result:
		var bad_initial: Intensity.FixtureFadeError = _validate(initial)
		if bad_initial != null:
			return Intensity.Result.with_error(bad_initial)
		var bad_target: Intensity.FixtureFadeError = _validate(target)
		if bad_target != null:
			return Intensity.Result.with_error(bad_target)
		var fade: Intensity.FixtureFade = Intensity.FixtureFade.new()
		fade._from = initial
		fade._target = target
		fade._settle_ticks = settle_ticks
		fade._elapsed_ticks = 0
		return Intensity.Result.with_fade(fade)

	## A fixture holding value, settled, with no fade in flight.
	static func holding(value: float) -> Intensity.Result:
		return try_new(value, value, 0)

	## Retarget the fade toward target over settle_ticks, starting from
	## the fixture's actual current intensity, so a mid-fade retarget
	## never jumps. A rejected retarget leaves the fade exactly as it was;
	## null means success.
	func retarget(target: float, settle_ticks: int) -> Intensity.FixtureFadeError:
		var bad_target: Intensity.FixtureFadeError = _validate(target)
		if bad_target != null:
			return bad_target
		_from = intensity()
		_target = target
		_settle_ticks = settle_ticks
		_elapsed_ticks = 0
		return null

	## The current intensity, without advancing. From the settle tick on
	## it is the target, returned bitwise rather than through the
	## interpolation arithmetic.
	func intensity() -> float:
		if _elapsed_ticks >= _settle_ticks:
			return _target
		if _elapsed_ticks == 0:
			return _from
		var progress: float = float(_elapsed_ticks) / float(_settle_ticks)
		return _from + (_target - _from) * progress

	func target() -> float:
		return _target

	func is_settled() -> bool:
		return _elapsed_ticks >= _settle_ticks

	## Consume one logical tick and return the intensity at the new tick.
	## From the settle tick on, every tick returns the target bitwise and
	## the counter stands still.
	func tick() -> float:
		if _elapsed_ticks < _settle_ticks:
			_elapsed_ticks += 1
		return intensity()

	static func _validate(value: float) -> Intensity.FixtureFadeError:
		if not is_finite(value):
			return Intensity.FixtureFadeError.non_finite_intensity(value)
		if value < 0.0:
			return Intensity.FixtureFadeError.negative_intensity(value)
		return null
