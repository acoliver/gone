class_name Ladder
extends RefCounted
## Fixed-tick constrained transfers and scalar-height climbing. No input devices
## or presentation state participate in these transitions.

const TRANSFER_TICKS: int = 24
const CLIMB_SPEED: float = 1.5
const DISMOUNT_REACH: float = 0.15
const MOUNT_REACH: float = 2.2
const FACING_DOT: float = 0.7071067811865476
const HEIGHT_EPSILON: float = 1e-10

enum Mode { MOUNTING, CLIMBING, DISMOUNTING, LANDED }
enum EventKind { MOUNT, CLIMB, LANDING, DISMOUNT, LANDED }

class LadderError:
	extends RefCounted
	enum Kind { UNKNOWN_WELL, INVALID_DECK, NON_FINITE_INPUT, NOT_ON_LANDING, OUT_OF_REACH, NOT_FACING, INVALID_INTENT, INVALID_TICK, STEP_ALREADY_TAKEN, WRONG_MODE, PATH_BLOCKED }
	var kind: int
	var collider_id: StringName
	var resolver: Resolve.ResolveError
	func _init(p_kind: int, p_id: StringName = &"", p_resolver: Resolve.ResolveError = null) -> void:
		kind = p_kind
		collider_id = p_id
		resolver = p_resolver

class Event:
	extends RefCounted
	var kind: int
	var well_id: StringName
	var deck: int
	func _init(p_kind: int, p_well: StringName, p_deck: int) -> void:
		kind = p_kind
		well_id = p_well
		deck = p_deck

class Result:
	extends RefCounted
	var state: Ladder.State
	var error: Ladder.LadderError
	var events: Array[Ladder.Event] = []
	func is_ok() -> bool:
		return error == null

class State:
	extends RefCounted
	var _layout: ShipLayout
	var _well: ShipLayout.LadderWellSpec
	var _mode: int = Ladder.Mode.MOUNTING
	var _capsule: Resolve.Capsule
	var _height: float = 0.0
	var _pending: float = 0.0
	var _velocity: float = 0.0
	var _foot_offset: float
	var _head_offset: Vector3
	var _approach: Vector3
	var _landing_deck: int
	var _destination_deck: int
	var _transfer_tick: int = 0
	var _transfer_start: Resolve.Capsule
	var _transfer_end: Resolve.Capsule
	var _tick_stepped: bool = false
	var _tick: int = 0
	var _crossed_deck: int = 0
	var _crossed_tick: int = -2

	func mode() -> int:
		return _mode
	func capsule() -> Resolve.Capsule:
		return Walk._copy_capsule(_capsule)
	func height() -> float:
		return _height
	func pending() -> float:
		return _pending
	func well_id() -> StringName:
		return _well.id()
	func landing_deck() -> int:
		return _landing_deck
	func nearest_landing() -> int:
		return clampi(roundi(14.0 - _height / ShipLayout.DECK_PITCH), _well.top_deck(), _well.bottom_deck())
	func end_tick() -> void:
		_tick_stepped = false

	func step(intent: float, space: bool, collision: ShipCollision, dt: float = Sim.LOGICAL_TICK_SECS) -> Ladder.Result:
		if _tick_stepped:
			return Ladder._failure(Ladder.LadderError.Kind.STEP_ALREADY_TAKEN)
		if not is_finite(dt) or dt != Sim.LOGICAL_TICK_SECS:
			return Ladder._failure(Ladder.LadderError.Kind.INVALID_TICK)
		if not is_finite(intent) or absf(intent) > 1.0:
			return Ladder._failure(Ladder.LadderError.Kind.INVALID_INTENT)
		var result: Ladder.Result
		match _mode:
			Ladder.Mode.MOUNTING, Ladder.Mode.DISMOUNTING:
				result = _transfer(collision)
			Ladder.Mode.CLIMBING:
				var deck := _dismount_deck() if space else 0
				result = _begin_dismount(deck, collision) if deck != 0 else _climb(intent, collision)
			_:
				return Ladder._failure(Ladder.LadderError.Kind.WRONG_MODE)
		if result.is_ok():
			_tick_stepped = true
			_tick += 1
		return result

	func _pose(height: float) -> Resolve.Capsule:
		var pose := Resolve.Capsule.new()
		pose.foot = Vector3(_well.climb_line().origin.x, height + _foot_offset, _well.climb_line().origin.z)
		pose.head = pose.foot + _head_offset
		return pose

	func _sweep(start: Resolve.Capsule, target: Resolve.Capsule, collision: ShipCollision, exact: bool) -> Ladder.LadderError:
		var delta := target.foot - start.foot
		var slice := collision.well_slice(_well.id(), start, delta)
		var resolved := Resolve.resolve_constrained_motion(start, delta, slice.colliders) if exact else Resolve.resolve_motion(start, delta, slice.colliders)
		if not resolved.is_ok():
			var id: StringName = slice.ids[resolved.error.index] if resolved.error.kind == Resolve.ResolveError.Kind.START_PENETRATION else &""
			return Ladder.LadderError.new(Ladder.LadderError.Kind.PATH_BLOCKED, id, resolved.error)
		if not resolved.motion.collider_indices.is_empty():
			return Ladder.LadderError.new(Ladder.LadderError.Kind.PATH_BLOCKED, slice.ids[resolved.motion.collider_indices[0]])
		assert((resolved.motion.displacement - delta).length() <= Controller.PENETRATION_TOLERANCE, "a free constrained sweep reaches its target within resolver tolerance")
		return null

	func _transfer(collision: ShipCollision) -> Ladder.Result:
		var next_tick := _transfer_tick + 1
		var target := Resolve.Capsule.new()
		var fraction := float(next_tick) / Ladder.TRANSFER_TICKS
		target.foot = _transfer_start.foot.lerp(_transfer_end.foot, fraction)
		target.head = target.foot + _head_offset
		var error := _sweep(_capsule, target, collision, true)
		if error != null:
			return Ladder._with_error(error)
		_capsule = target
		_transfer_tick = next_tick
		var events: Array[Ladder.Event] = []
		if next_tick == Ladder.TRANSFER_TICKS:
			if _mode == Ladder.Mode.MOUNTING:
				_mode = Ladder.Mode.CLIMBING
				events.append(Ladder.Event.new(Ladder.EventKind.CLIMB, _well.id(), _landing_deck))
			else:
				_mode = Ladder.Mode.LANDED
				_landing_deck = _destination_deck
				events.append(Ladder.Event.new(Ladder.EventKind.LANDED, _well.id(), _landing_deck))
		return _success(events)

	func _climb(intent: float, collision: ShipCollision) -> Ladder.Result:
		var top := _layout.floor_y(_well.top_deck())
		var bottom := _layout.floor_y(_well.bottom_deck())
		var alpha := 1.0 - exp(-Controller.INTENT_EASE_EXPONENT * Sim.LOGICAL_TICK_SECS / Controller.CLIMB_EASE_SECONDS)
		var velocity := _velocity + (intent * Ladder.CLIMB_SPEED - _velocity) * alpha
		var target_height := clampf(_height + _pending + velocity * Sim.LOGICAL_TICK_SECS, bottom, top)
		if absf(target_height - top) < Ladder.HEIGHT_EPSILON:
			target_height = top
		elif absf(target_height - bottom) < Ladder.HEIGHT_EPSILON:
			target_height = bottom
		var travel := target_height - _height
		var endpoint := target_height == top or target_height == bottom
		if absf(travel) <= Controller.PENETRATION_TOLERANCE and not endpoint:
			_pending = travel
			_velocity = velocity
			return _success()
		var target := _pose(target_height)
		var error := _sweep(_capsule, target, collision, endpoint)
		if error != null:
			return Ladder._with_error(error)
		var events: Array[Ladder.Event] = []
		for deck: int in range(_well.top_deck(), _well.bottom_deck() + 1):
			var floor_y := _layout.floor_y(deck)
			var crossed := (_height < floor_y - Ladder.HEIGHT_EPSILON and target_height >= floor_y - Ladder.HEIGHT_EPSILON) or (_height > floor_y + Ladder.HEIGHT_EPSILON and target_height <= floor_y + Ladder.HEIGHT_EPSILON)
			if crossed:
				_crossed_deck = deck
				_crossed_tick = _tick
				events.append(Ladder.Event.new(Ladder.EventKind.LANDING, _well.id(), deck))
		_capsule = target
		_height = target_height
		_pending = 0.0
		_velocity = 0.0 if endpoint else velocity
		return _success(events)

	func _dismount_deck() -> int:
		var nearest := nearest_landing()
		if absf(_height - _layout.floor_y(nearest)) <= Ladder.DISMOUNT_REACH + Ladder.HEIGHT_EPSILON:
			return nearest
		if _tick - _crossed_tick <= 1:
			return _crossed_deck
		return 0

	func _begin_dismount(deck: int, collision: ShipCollision) -> Ladder.Result:
		var corrected := _pose(_layout.floor_y(deck))
		var destination := Walk._copy_capsule(corrected)
		destination.foot.x = _approach.x
		destination.foot.z = _approach.z
		destination.head = destination.foot + _head_offset
		var first := Walk._copy_capsule(corrected)
		first.foot = corrected.foot.lerp(destination.foot, 1.0 / Ladder.TRANSFER_TICKS)
		first.head = first.foot + _head_offset
		var error := _sweep(_capsule, corrected, collision, true)
		if error == null:
			error = _sweep(corrected, first, collision, true)
		if error != null:
			return Ladder._with_error(error)
		_mode = Ladder.Mode.DISMOUNTING
		_height = _layout.floor_y(deck)
		_pending = 0.0
		_destination_deck = deck
		_transfer_start = corrected
		_transfer_end = destination
		_transfer_tick = 1
		_capsule = first
		return _success([Ladder.Event.new(Ladder.EventKind.DISMOUNT, _well.id(), deck)])

	func _success(events: Array[Ladder.Event] = []) -> Ladder.Result:
		var result := Ladder.Result.new()
		result.state = self
		result.events = events
		return result

static func try_mount(layout: ShipLayout, well_id: StringName, deck: int, capsule: Resolve.Capsule, facing: Vector3) -> Result:
	if not well_id in layout.well_ids():
		return _failure(LadderError.Kind.UNKNOWN_WELL)
	if deck < 1 or deck > 30:
		return _failure(LadderError.Kind.INVALID_DECK)
	if not capsule.foot.is_finite() or not capsule.head.is_finite() or not facing.is_finite():
		return _failure(LadderError.Kind.NON_FINITE_INPUT)
	var well := layout.well(well_id)
	var landing := well.landing_bounds(deck)
	var inset := Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
	var foot_offset := capsule.foot.y - layout.floor_y(deck)
	var supported := capsule.foot.x >= landing.position.x + inset and capsule.foot.x <= landing.end.x - inset and capsule.foot.z >= landing.position.z + inset and capsule.foot.z <= landing.end.z
	var standing := foot_offset >= Controller.CAPSULE_RADIUS - Controller.PENETRATION_TOLERANCE and foot_offset <= inset + DISMOUNT_REACH and capsule.head.y > capsule.foot.y
	if not supported or not standing:
		return _failure(LadderError.Kind.NOT_ON_LANDING)
	var toward := well.climb_line().origin - capsule.foot
	toward.y = 0
	if toward.length() > MOUNT_REACH:
		return _failure(LadderError.Kind.OUT_OF_REACH)
	var planar_facing := Vector3(facing.x, 0, facing.z)
	if planar_facing.length_squared() == 0 or planar_facing.normalized().dot(toward.normalized()) < FACING_DOT:
		return _failure(LadderError.Kind.NOT_FACING)
	var state := State.new()
	state._layout = layout
	state._well = well
	state._capsule = Walk._copy_capsule(capsule)
	state._head_offset = capsule.head - capsule.foot
	state._foot_offset = foot_offset
	state._height = layout.floor_y(deck)
	state._approach = capsule.foot
	state._landing_deck = deck
	state._transfer_start = Walk._copy_capsule(capsule)
	state._transfer_end = state._pose(state._height)
	return state._success([Event.new(EventKind.MOUNT, well_id, deck)])

static func _failure(kind: int) -> Result:
	return _with_error(LadderError.new(kind))

static func _with_error(error: LadderError) -> Result:
	var result := Result.new()
	result.error = error
	return result
