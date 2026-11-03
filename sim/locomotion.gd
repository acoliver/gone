class_name Locomotion
extends RefCounted
## Standing locomotion shared by PlayerMotion and pure simulation tests.

enum Mode { WALK, MOUNTING, CLIMBING, DISMOUNTING }

class Intent:
	extends RefCounted
	var walk: Walk.MoveIntent
	var has_climb: bool = false
	var climb: float = 0.0
	var space: bool = false
	var well_id: StringName
	var facing := Vector3.FORWARD

class LocomotionError:
	extends RefCounted
	enum Kind { INVALID_DECK, INVALID_TICK, STEP_ALREADY_TAKEN, INPUT_CONFLICT, INVALID_CLIMB, WALK, LADDER }
	var kind: int
	var walk: Walk.WalkError
	var ladder: Ladder.LadderError
	func _init(p_kind: int) -> void:
		kind = p_kind

class Result:
	extends RefCounted
	var state: Locomotion
	var error: Locomotion.LocomotionError
	var events: Array[Ladder.Event] = []
	func is_ok() -> bool:
		return error == null

var _layout: ShipLayout
var _collision: ShipCollision
var _deck: int
var _walk: Walk.WalkState
var _ladder: Ladder.State
var _tick_stepped: bool = false

static func start(layout: ShipLayout, collision: ShipCollision, deck: int, walk: Walk.WalkState) -> Result:
	if deck < 1 or deck > 30:
		return _failure(LocomotionError.Kind.INVALID_DECK)
	var state := Locomotion.new()
	state._layout = layout
	state._collision = collision
	state._deck = deck
	state._walk = walk
	return state._success()

func mode() -> int:
	if _ladder == null:
		return Mode.WALK
	match _ladder.mode():
		Ladder.Mode.MOUNTING:
			return Mode.MOUNTING
		Ladder.Mode.CLIMBING:
			return Mode.CLIMBING
		_:
			return Mode.DISMOUNTING

func deck() -> int:
	return _deck

func capsule() -> Resolve.Capsule:
	return _walk.capsule() if _ladder == null else _ladder.capsule()

func eye() -> Vector3:
	return capsule().foot + Vector3.UP * (1.6 - Controller.CAPSULE_RADIUS)

func walk_speed() -> float:
	return _walk.speed()

func ladder_state() -> Ladder.State:
	return _ladder

func step(input: Intent, dt: float = Sim.LOGICAL_TICK_SECS) -> Result:
	if _tick_stepped:
		return _failure(LocomotionError.Kind.STEP_ALREADY_TAKEN)
	if not is_finite(dt) or dt != Sim.LOGICAL_TICK_SECS:
		return _failure(LocomotionError.Kind.INVALID_TICK)
	if input.has_climb and (not is_finite(input.climb) or absf(input.climb) > 1):
		return _failure(LocomotionError.Kind.INVALID_CLIMB)
	var events: Array[Ladder.Event] = []
	if _ladder == null:
		if input.space and input.well_id != &"":
			var mounted := Ladder.try_mount(_layout, input.well_id, _deck, _walk.capsule(), input.facing)
			if not mounted.is_ok():
				return _ladder_failure(mounted.error)
			_ladder = mounted.state
			events = mounted.events
		else:
			var support := func(pose: Resolve.Capsule, delta: Vector3) -> Vector3: return _collision.supported_walk_on_deck(_deck, pose, delta)
			var walked := _walk.step(input.walk, dt, _collision.deck_set(_deck), support)
			if not walked.is_ok():
				var failure := LocomotionError.new(LocomotionError.Kind.WALK)
				failure.walk = walked.error
				return _with_error(failure)
	else:
		var legacy := clampf(-input.walk.forward_input(), -1, 1)
		if input.has_climb and legacy != 0 and input.climb != 0 and signf(legacy) != signf(input.climb):
			return _failure(LocomotionError.Kind.INPUT_CONFLICT)
		var climbed := _ladder.step(input.climb if input.has_climb else legacy, input.space, _collision, dt)
		if not climbed.is_ok():
			return _ladder_failure(climbed.error)
		events = climbed.events
		if _ladder.mode() == Ladder.Mode.LANDED:
			var resumed := _walk.resume(_ladder.capsule())
			assert(resumed.is_ok(), "a completed swept transfer resumes the suspended walk")
			_deck = _ladder.landing_deck()
			_ladder = null
	_tick_stepped = true
	return _success(events)

func end_tick() -> void:
	_tick_stepped = false
	_walk.end_tick()
	if _ladder != null:
		_ladder.end_tick()

func _success(events: Array[Ladder.Event] = []) -> Result:
	var result := Result.new()
	result.state = self
	result.events = events
	return result

static func _ladder_failure(error: Ladder.LadderError) -> Result:
	var failure := LocomotionError.new(LocomotionError.Kind.LADDER)
	failure.ladder = error
	return _with_error(failure)

static func _failure(kind: int) -> Result:
	return _with_error(LocomotionError.new(kind))

static func _with_error(error: LocomotionError) -> Result:
	var result := Result.new()
	result.error = error
	return result
