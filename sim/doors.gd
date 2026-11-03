class_name Doors
extends RefCounted
## Persistent door state, independent of scene residency and observers.

const Policy = ShipLayout.Policy
enum State { CLOSED, CRANKING, OPENING, OPEN }
enum Outcome { NOT_APPLICABLE, MOVED, STALLED, RELEASED, REFUSED }
enum EventKind { CRANK_MOVED, CRANK_STALLED, RELEASED, OPENED, REFUSED }
const WHEEL_TICKS: int = 6
const SWING_TICKS: int = 48
const BAY_RETRACT_TICKS: int = 12
const BAY_SLIDE_TICKS: int = 36
const BAY_RETRACT: float = 0.17
const BAY_SLIDE: float = 1.2
const POWER_SLIDE: float = 1.15

class Context:
	extends RefCounted
	var rod_carried: bool = false
	var face_id: StringName

class PressResult:
	extends RefCounted
	var outcome: int
	func _init(value: int) -> void:
		outcome = value
	func accepted() -> bool:
		return outcome != Outcome.NOT_APPLICABLE

class Event:
	extends RefCounted
	var _sequence: int
	var _tick: int
	var _door_id: StringName
	var _face_id: StringName
	var _attempt: int
	var _kind: int
	var _outcome: int
	var _angle_delta: float
	var _audio_variant: int
	func sequence() -> int:
		return _sequence
	func tick() -> int:
		return _tick
	func door_id() -> StringName:
		return _door_id
	func face_id() -> StringName:
		return _face_id
	func attempt() -> int:
		return _attempt
	func kind() -> int:
		return _kind
	func outcome() -> int:
		return _outcome
	func angle_delta() -> float:
		return _angle_delta
	func audio_variant() -> int:
		return _audio_variant
	func copy() -> Event:
		var event := Event.new()
		event._sequence = _sequence
		event._tick = _tick
		event._door_id = _door_id
		event._face_id = _face_id
		event._attempt = _attempt
		event._kind = _kind
		event._outcome = _outcome
		event._angle_delta = _angle_delta
		event._audio_variant = _audio_variant
		return event

class Snapshot:
	extends RefCounted
	var id: StringName
	var state: int = State.CLOSED
	var attempt: int = 0
	var work: int = 0
	var wheel_angle: float = 0.0
	var target_angle: float = 0.0
	var refusal_offset: float = 0.0
	var shudder: float = 0.0
	var leaf_fraction: float = 0.0
	var offset := Vector3.ZERO
	var releases: int = 0

class Record:
	extends RefCounted
	var spec: ShipLayout.DoorSpec
	var schedule: HatchResistance.Schedule
	var state: int = State.CLOSED
	var attempt: int = 0
	var work: int = 0
	var wheel: float = 0.0
	var target: float = 0.0
	var wheel_start: float = 0.0
	var wheel_elapsed: int = WHEEL_TICKS
	var opening_elapsed: int = 0
	var releases: int = 0
	var face_id: StringName
	var jerk_start: float = 0.0
	var jerk: float = 0.0
	var jerk_elapsed: int = 9

class Store:
	extends RefCounted
	var _records: Dictionary = {}
	var _ids: Array[StringName] = []
	var _tick: int = 0
	var _sequence: int = 0
	var _events: Array[Event] = []

	func _init(layout: ShipLayout, run_seed: int) -> void:
		_ids = layout.door_ids()
		for id: StringName in _ids:
			var record := Record.new()
			record.spec = layout.door(id)
			_validate(record.spec)
			if record.spec.policy() == Policy.CRANK:
				record.schedule = HatchResistance.schedule(run_seed, id)
			_records[id] = record

	func _validate(spec: ShipLayout.DoorSpec) -> void:
		match spec.policy():
			Policy.CRANK:
				assert(spec.animation() == ShipLayout.AnimationRecipe.HINGE and spec.has_wheel(), "crank requires a hinged wheel hatch")
			Policy.NEVER_OPENS:
				assert(spec.animation() in [ShipLayout.AnimationRecipe.HINGE, ShipLayout.AnimationRecipe.FIXED], "locked recipe must support refusal")
			Policy.ROD_PRY:
				assert(spec.animation() == ShipLayout.AnimationRecipe.RETRACT_SLIDE, "rod uses retract/slide")
			Policy.PRESS_SLIDE:
				assert(spec.animation() == ShipLayout.AnimationRecipe.SLIDE, "press uses slide")
			_:
				assert(false, "unknown door policy")

	func _record(id: StringName) -> Record:
		assert(_records.has(id), "door id is registered: %s" % id)
		return _records[id]

	func count() -> int:
		return _ids.size()

	func press(id: StringName, context: Context) -> PressResult:
		var record := _record(id)
		assert(record.spec.face_ids().has(context.face_id), "press face belongs to door")
		if record.state in [State.OPENING, State.OPEN]:
			return PressResult.new(Outcome.NOT_APPLICABLE)
		if record.spec.policy() == Policy.CRANK and record.work == record.schedule.total_weight:
			return PressResult.new(Outcome.NOT_APPLICABLE)
		if record.spec.policy() == Policy.ROD_PRY and not context.rod_carried:
			return PressResult.new(Outcome.NOT_APPLICABLE)
		record.face_id = context.face_id
		record.attempt += 1
		match record.spec.policy():
			Policy.NEVER_OPENS:
				_jerk(record)
				_emit(record, EventKind.REFUSED, Outcome.REFUSED, 0.0)
				return PressResult.new(Outcome.REFUSED)
			Policy.CRANK:
				record.state = State.CRANKING
				var weight := record.schedule.weights[record.attempt - 1]
				if weight == 0:
					_jerk(record)
					_emit(record, EventKind.CRANK_STALLED, Outcome.STALLED, 0.0)
					return PressResult.new(Outcome.STALLED)
				var previous_target := record.target
				record.work += weight
				record.target = HatchResistance.OPEN_ANGLE * float(record.work) / float(record.schedule.total_weight)
				record.wheel_start = record.wheel
				record.wheel_elapsed = 0
				_emit(record, EventKind.CRANK_MOVED, Outcome.MOVED, record.target - previous_target)
				return PressResult.new(Outcome.MOVED)
			_:
				_release(record)
				return PressResult.new(Outcome.RELEASED)

	func _jerk(record: Record) -> void:
		record.jerk_start = record.jerk
		record.jerk_elapsed = 0

	func _release(record: Record) -> void:
		record.state = State.OPENING
		record.releases += 1
		_emit(record, EventKind.RELEASED, Outcome.RELEASED, 0.0)

	func tick() -> Array[Event]:
		_tick += 1
		_events.clear()
		for id: StringName in _ids:
			var record := _record(id)
			if record.jerk_elapsed < 9:
				record.jerk_elapsed += 1
				if record.jerk_elapsed <= 3:
					record.jerk = lerpf(record.jerk_start, 4.0, float(record.jerk_elapsed) / 3.0)
				else:
					record.jerk = 4.0 * (1.0 - float(record.jerk_elapsed - 3) / 6.0)
			if record.state == State.OPENING:
				record.opening_elapsed += 1
				if record.opening_elapsed == SWING_TICKS:
					record.state = State.OPEN
					_emit(record, EventKind.OPENED, Outcome.RELEASED, 0.0)
			elif record.state == State.CRANKING and record.wheel_elapsed < WHEEL_TICKS:
				record.wheel_elapsed += 1
				record.wheel = lerpf(record.wheel_start, record.target, float(record.wheel_elapsed) / float(WHEEL_TICKS))
				if record.wheel_elapsed == WHEEL_TICKS and record.work == record.schedule.total_weight:
					_release(record)
		return events()

	## Fresh objects plus a read-only array give each observer an independent
	## cursor without granting it ownership of another observer's event batch.
	func events() -> Array[Event]:
		var batch: Array[Event] = []
		for event: Event in _events:
			batch.append(event.copy())
		batch.make_read_only()
		return batch

	func _emit(record: Record, kind: int, outcome: int, delta: float) -> void:
		_sequence += 1
		var event := Event.new()
		event._sequence = _sequence
		event._tick = _tick
		event._door_id = record.spec.id()
		event._face_id = record.face_id
		event._attempt = record.attempt
		event._kind = kind
		event._outcome = outcome
		event._angle_delta = delta
		event._audio_variant = HatchResistance.hash_bytes("door-audio-v1|%s|%d" % [event._door_id, event._attempt]) % 4
		_events.append(event)

	func snapshot(id: StringName) -> Snapshot:
		var record := _record(id)
		var result := Snapshot.new()
		result.id = id
		result.state = record.state
		result.attempt = record.attempt
		result.work = record.work
		result.wheel_angle = record.wheel
		result.target_angle = record.target
		result.refusal_offset = record.jerk if record.spec.has_wheel() else 0.0
		result.shudder = record.jerk / 4.0 if not record.spec.has_wheel() else 0.0
		result.releases = record.releases
		var progress := float(record.opening_elapsed) / float(SWING_TICKS)
		result.leaf_fraction = progress * progress * (3.0 - 2.0 * progress)
		match record.spec.animation():
			ShipLayout.AnimationRecipe.RETRACT_SLIDE:
				result.offset = Vector3(BAY_RETRACT * minf(float(record.opening_elapsed) / BAY_RETRACT_TICKS, 1.0), 0, -BAY_SLIDE * clampf(float(record.opening_elapsed - BAY_RETRACT_TICKS) / BAY_SLIDE_TICKS, 0.0, 1.0))
			ShipLayout.AnimationRecipe.SLIDE:
				result.offset = Vector3(-POWER_SLIDE * progress, 0, 0)
		return result
