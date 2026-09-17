class_name Walk
extends RefCounted
## The steadying walk: post-get-up movement out of Standing, ported from
## gone_sim walk.rs. From a full stop the walk speed ramps from the frozen
## STEADY_INITIAL_SPEED_FACTOR share of SURVIVAL_WALK_SPEED toward full
## survival pace with the frozen exponential STEADYING_TIME_CONSTANT, and
## every tick's intended motion is swept through the static ColliderSet by
## the landed resolver: walking slides along walls and never tunnels
## through geometry. The ramp is temporal, not directional: the steadying
## clock accumulates per consumed tick whichever way the intent points.
## Units: meters, seconds, up is positive Y. Pure logic: no Node, scene,
## rendering, or input types.

## Which look-frame axis carried a non-finite component.
enum IntentAxis { FORWARD, STRAFE, YAW }

## How one stepped tick met the world.
enum WalkContact { FREE, SLIDING, STOPPED }

class WalkError:
	extends RefCounted

	enum Kind { WRONG_PHASE, NON_FINITE_INTENT_AXIS, NON_FINITE_INTENT_MAGNITUDE, INVALID_TICK_SECONDS, STEP_ALREADY_TAKEN, NON_FINITE_CAPSULE, RESOLVER }

	var kind: int = Kind.WRONG_PHASE
	var expected: int = Phase.Wake.WAKING
	var current: int = Phase.Wake.WAKING
	var axis: int = Walk.IntentAxis.FORWARD
	var got: float = 0.0
	var resolver: Resolve.ResolveError = null

	static func wrong_phase(p_expected: int, p_current: int) -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.WRONG_PHASE
		error.expected = p_expected
		error.current = p_current
		return error

	static func non_finite_intent_axis(p_axis: int, p_got: float) -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.NON_FINITE_INTENT_AXIS
		error.axis = p_axis
		error.got = p_got
		return error

	static func non_finite_intent_magnitude(p_got: float) -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.NON_FINITE_INTENT_MAGNITUDE
		error.got = p_got
		return error

	static func invalid_tick_seconds(p_got: float) -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.INVALID_TICK_SECONDS
		error.got = p_got
		return error

	static func step_already_taken() -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.STEP_ALREADY_TAKEN
		return error

	static func non_finite_capsule() -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.NON_FINITE_CAPSULE
		return error

	static func resolver_error(failure: Resolve.ResolveError) -> Walk.WalkError:
		var error: Walk.WalkError = Walk.WalkError.new()
		error.kind = Kind.RESOLVER
		error.resolver = failure
		return error

	func equals(other: Walk.WalkError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.WRONG_PHASE:
				return expected == other.expected and current == other.current
			Kind.NON_FINITE_INTENT_AXIS:
				return axis == other.axis and Walk._same_float(got, other.got)
			Kind.NON_FINITE_INTENT_MAGNITUDE, Kind.INVALID_TICK_SECONDS:
				return Walk._same_float(got, other.got)
			Kind.RESOLVER:
				return resolver != null and resolver.equals(other.resolver)
			_:
				return true

	func _to_string() -> String:
		match kind:
			Kind.WRONG_PHASE:
				return "walk expected phase %s, found %s: the call is rejected and nothing moved" % [Phase.phase_name(expected), Phase.phase_name(current)]
			Kind.NON_FINITE_INTENT_AXIS:
				return "move intent axis %s carried %s, which is not finite" % [_axis_name(), str(got)]
			Kind.NON_FINITE_INTENT_MAGNITUDE:
				return "move intent magnitude overflowed to %s; the input cap scale is uncomputable" % str(got)
			Kind.INVALID_TICK_SECONDS:
				return "tick seconds must be finite and strictly positive, got %s" % str(got)
			Kind.STEP_ALREADY_TAKEN:
				return "one walk step is consumed per fixed tick; close the tick with end_tick before stepping again"
			Kind.NON_FINITE_CAPSULE:
				return "the starting capsule carried a non-finite endpoint"
			_:
				return "walk sweep rejected by the resolver: %s" % resolver._to_string()

	func _axis_name() -> String:
		match axis:
			Walk.IntentAxis.FORWARD:
				return "Forward"
			Walk.IntentAxis.STRAFE:
				return "Strafe"
			_:
				return "Yaw"

class IntentResult:
	extends RefCounted

	var intent: Walk.MoveIntent = null
	var error: Walk.WalkError = null

	static func with_intent(valid: Walk.MoveIntent) -> Walk.IntentResult:
		var result: Walk.IntentResult = Walk.IntentResult.new()
		result.intent = valid
		return result

	static func with_error(failure: Walk.WalkError) -> Walk.IntentResult:
		var result: Walk.IntentResult = Walk.IntentResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class StartResult:
	extends RefCounted

	var state: Walk.WalkState = null
	var error: Walk.WalkError = null

	static func with_state(started: Walk.WalkState) -> Walk.StartResult:
		var result: Walk.StartResult = Walk.StartResult.new()
		result.state = started
		return result

	static func with_error(failure: Walk.WalkError) -> Walk.StartResult:
		var result: Walk.StartResult = Walk.StartResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class StepResult:
	extends RefCounted

	var outcome: Walk.WalkOutcome = null
	var error: Walk.WalkError = null

	static func with_outcome(stepped: Walk.WalkOutcome) -> Walk.StepResult:
		var result: Walk.StepResult = Walk.StepResult.new()
		result.outcome = stepped
		return result

	static func with_error(failure: Walk.WalkError) -> Walk.StepResult:
		var result: Walk.StepResult = Walk.StepResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

## One tick's movement input, framed in the player's look frame. Built only
## through try_new, which validates finiteness and applies the frozen
## MAX_INPUT_LENGTH policy, so an intent in existence always resolves to a
## finite planar direction of length at most one.
class MoveIntent:
	extends RefCounted

	var _forward: float = 0.0
	var _strafe: float = 0.0
	var _yaw: float = 0.0

	static func try_new(p_yaw: float, p_forward: float, p_strafe: float) -> Walk.IntentResult:
		if not is_finite(p_yaw):
			return Walk.IntentResult.with_error(Walk.WalkError.non_finite_intent_axis(Walk.IntentAxis.YAW, p_yaw))
		if not is_finite(p_forward):
			return Walk.IntentResult.with_error(Walk.WalkError.non_finite_intent_axis(Walk.IntentAxis.FORWARD, p_forward))
		if not is_finite(p_strafe):
			return Walk.IntentResult.with_error(Walk.WalkError.non_finite_intent_axis(Walk.IntentAxis.STRAFE, p_strafe))
		var magnitude: float = sqrt(p_forward * p_forward + p_strafe * p_strafe)
		if not is_finite(magnitude):
			return Walk.IntentResult.with_error(Walk.WalkError.non_finite_intent_magnitude(magnitude))
		var forward: float = p_forward
		var strafe: float = p_strafe
		if magnitude > Controller.MAX_INPUT_LENGTH:
			var scale: float = Controller.MAX_INPUT_LENGTH / magnitude
			forward = p_forward * scale
			strafe = p_strafe * scale
		var valid: Walk.MoveIntent = Walk.MoveIntent.new()
		valid._forward = forward
		valid._strafe = strafe
		valid._yaw = p_yaw
		return Walk.IntentResult.with_intent(valid)

	## The intent as a world-space planar direction: the look-frame axes
	## rotated by the intent's yaw. Y is always zero.
	func world_direction() -> Vector3:
		var sin_yaw: float = sin(_yaw)
		var cos_yaw: float = cos(_yaw)
		var look := Vector3(sin_yaw, 0.0, cos_yaw)
		var right := Vector3(cos_yaw, 0.0, -sin_yaw)
		return look * _forward + right * _strafe

## What one stepped walk tick did.
class WalkOutcome:
	extends RefCounted

	var displacement: Vector3 = Vector3.ZERO
	var contact: int = Walk.WalkContact.FREE
	var contact_normals: Array[Vector3] = []
	var grounded: bool = false

## The steadying walk state: the standing capsule, the steadying clock,
## and the current tick's consumption budget. Built only through start,
## which requires the machine to sit in Standing: locomotion exists only
## after the get-up completes.
class WalkState:
	extends RefCounted

	var _capsule: Resolve.Capsule = null
	var _steadied_seconds: float = 0.0
	var _tick_stepped: bool = false

	static func start(phase: Phase.Machine, capsule: Resolve.Capsule) -> Walk.StartResult:
		if not phase.in_phase(Phase.Wake.STANDING):
			return Walk.StartResult.with_error(Walk.WalkError.wrong_phase(Phase.Wake.STANDING, phase.current()))
		if not capsule.foot.is_finite() or not capsule.head.is_finite():
			return Walk.StartResult.with_error(Walk.WalkError.non_finite_capsule())
		var state: Walk.WalkState = Walk.WalkState.new()
		state._capsule = Walk._copy_capsule(capsule)
		return Walk.StartResult.with_state(state)

	func capsule() -> Resolve.Capsule:
		return Walk._copy_capsule(_capsule)

	## The walk speed the next consumed tick will move at, in meters per
	## second: the exact frozen initial product at a full stop, thereafter
	## the frozen exponential approach toward SURVIVAL_WALK_SPEED.
	func speed() -> float:
		return Walk._steadied_speed(_steadied_seconds)

	## Consume the tick: sweep the intent's displacement through the
	## colliders with the landed resolver, land the capsule at the
	## resolved position, and advance the steadying clock by dt. The tick
	## moves at the speed the ramp held when the call arrived; the clock
	## advances after the sweep. Errors never mutate.
	func step(intent: Walk.MoveIntent, dt: float, colliders: ColliderSet) -> Walk.StepResult:
		if _tick_stepped:
			return Walk.StepResult.with_error(Walk.WalkError.step_already_taken())
		if not is_finite(dt) or dt <= 0.0:
			return Walk.StepResult.with_error(Walk.WalkError.invalid_tick_seconds(dt))
		var direction: Vector3 = intent.world_direction()
		var intended: Vector3 = direction * (speed() * dt)
		var resolved: Resolve.Result = Resolve.resolve_motion(_capsule, intended, colliders)
		if not resolved.is_ok():
			return Walk.StepResult.with_error(Walk.WalkError.resolver_error(resolved.error))
		var contact: int = Walk._classify_contact(resolved.motion.displacement, direction, resolved.motion.contact_normals)
		_capsule.foot += resolved.motion.displacement
		_capsule.head += resolved.motion.displacement
		_steadied_seconds += dt
		_tick_stepped = true
		var outcome: Walk.WalkOutcome = Walk.WalkOutcome.new()
		outcome.displacement = resolved.motion.displacement
		outcome.contact = contact
		outcome.contact_normals = resolved.motion.contact_normals
		outcome.grounded = resolved.motion.grounded
		return Walk.StepResult.with_outcome(outcome)

	## Close the fixed tick: the next step belongs to a fresh tick.
	## Idempotent and infallible.
	func end_tick() -> void:
		_tick_stepped = false

## Classify the tick's contact from the resolver's report: free when no
## face constrained the sweep; otherwise sliding when tangential progress
## survived the contact, stopped when the planar motion was absorbed into
## the struck face. Tangential progress within the penetration tolerance
## counts as none: the tolerance is the house semantic band for touching.
static func _classify_contact(applied: Vector3, direction: Vector3, normals: Array[Vector3]) -> int:
	if normals.is_empty():
		return WalkContact.FREE
	var planar := Vector3(direction.x, 0.0, direction.z)
	var ahead := planar / planar.length()
	var aside := Vector3(-ahead.z, 0.0, ahead.x)
	var planar_applied := Vector3(applied.x, 0.0, applied.z)
	if absf(planar_applied.dot(aside)) > Controller.PENETRATION_TOLERANCE:
		return WalkContact.SLIDING
	return WalkContact.STOPPED

## The steadying ramp at `seconds` of accumulated sim time. At zero the
## frozen initial product is returned exactly: the ramp must start on the
## numbers the controller brief froze.
static func _steadied_speed(seconds: float) -> float:
	if seconds == 0.0:
		return Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED
	var multiplier: float = 1.0 - (1.0 - Controller.STEADY_INITIAL_SPEED_FACTOR) * exp(-seconds / Controller.STEADYING_TIME_CONSTANT)
	return Controller.SURVIVAL_WALK_SPEED * multiplier

static func _copy_capsule(capsule: Resolve.Capsule) -> Resolve.Capsule:
	var copy: Resolve.Capsule = Resolve.Capsule.new()
	copy.foot = capsule.foot
	copy.head = capsule.head
	return copy

## Component equality where a NaN payload still matches itself, mirroring
## the Rust total-order payload comparison.
static func _same_float(a: float, b: float) -> bool:
	return a == b or (is_nan(a) and is_nan(b))
