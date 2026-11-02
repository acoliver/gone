class_name Interactions
extends RefCounted
## Selection is pure geometry; dispatch is the single owner of interaction edges.

const HATCH_INTERACT_REACH: float = 2.2
const ROD_PICKUP_REACH: float = 1.3
const SWITCH_ACT_REACH: float = 2.2
const POWER_DOOR_REACH: float = 2.2
const CONSOLE_ACT_REACH: float = 1.8

enum Kind { PICKUP, DOOR, SWITCH, CONSOLE, LADDER }
enum Selection { LEGACY_PROXIMITY, FACE_RAY }

class Target:
	extends RefCounted
	var id: StringName
	var door_id: StringName
	var kind: int = Kind.DOOR
	var policy: int = Selection.LEGACY_PROXIMITY
	var priority: int = 0
	var deck: int = 14
	var center := Vector3.ZERO
	var reach: float = 2.2
	var frame := Transform3D.IDENTITY
	var size := Vector2(1.2, 2.4)

class Context:
	extends RefCounted
	var game: Game
	var motion: PlayerMotion
	var deck: int = 14
	var walking: bool = false
	var foot := Vector3.ZERO
	var eye := Vector3.ZERO
	var forward := Vector3.FORWARD

var _targets: Array[Target] = []
var _solids: Array[AABB] = []
var _layout: ShipLayout

func _init(layout: ShipLayout, solids: Array[AABB] = []) -> void:
	_layout = layout
	_solids = solids.duplicate()
	_legacy(&"D14-BAY-ROD", Kind.PICKUP, layout.anchor(&"D14-BAY-ROD").origin, 1.3, 0)
	_legacy(ShipLayout.BAY_DOOR_ID, Kind.DOOR, layout.door(ShipLayout.BAY_DOOR_ID).frame().origin, 2.2, 1)
	_legacy(&"D14-HALL-SWITCH", Kind.SWITCH, layout.anchor(&"D14-HALL-SWITCH").origin, 2.2, 2)
	_legacy(ShipLayout.POWER_DOOR_ID, Kind.DOOR, layout.door(ShipLayout.POWER_DOOR_ID).frame().origin, 2.2, 3)
	_legacy(&"D14-POWER-CONSOLE", Kind.CONSOLE, layout.anchor(&"D14-POWER-CONSOLE").origin, 1.8, 4)
	for id: StringName in layout.door_ids():
		if id not in [ShipLayout.BAY_DOOR_ID, ShipLayout.POWER_DOOR_ID]:
			register_door(id)

func register_door(id: StringName) -> void:
	var door := _layout.door(id)
	for face_id: StringName in door.face_ids():
		var target := Target.new()
		target.id = face_id
		target.door_id = id
		target.policy = Selection.FACE_RAY
		target.deck = door.deck_number()
		target.frame = door.frame() * _layout.face(face_id).surface_frame()
		target.center = door.frame().origin
		target.size = door.aperture()
		assert(not _targets.any(func(existing: Target) -> bool: return existing.id == face_id), "face registered once")
		_targets.append(target)

func _legacy(id: StringName, kind: int, center: Vector3, reach: float, priority: int) -> void:
	var target := Target.new()
	target.id = id
	target.door_id = id
	target.kind = kind
	target.center = center
	target.reach = reach
	target.priority = priority
	_targets.append(target)

static func context_for(game: Game, motion: PlayerMotion, forward: Vector3 = Vector3.FORWARD) -> Context:
	var context := Context.new()
	context.game = game
	context.motion = motion
	context.walking = motion.state() == PlayerMotion.BodyState.WALK
	context.eye = motion.eye(game)
	context.forward = forward
	if motion.capsule() != null:
		context.foot = motion.capsule().foot
	return context

func process(plane: InputPlane, context: Context) -> StringName:
	if not plane.has_press(InputPlane.Buttons.INTERACT):
		return &""
	for target: Target in eligible(_targets, context, _solids):
		if _dispatch(target, context):
			var consumed := plane.take_press(InputPlane.Buttons.INTERACT)
			assert(consumed)
			return target.id
	return &""

## A targeted adapter for isolated handler tests; production always uses process.
func process_id(id: StringName, plane: InputPlane, game: Game, motion: PlayerMotion) -> bool:
	if not plane.has_press(InputPlane.Buttons.INTERACT):
		return false
	var context := context_for(game, motion)
	for target: Target in _targets:
		if target.id == id and hit_distance(target, context, []) >= 0 and _dispatch(target, context):
			var consumed := plane.take_press(InputPlane.Buttons.INTERACT)
			assert(consumed)
			return true
	return false

func _dispatch(target: Target, context: Context) -> bool:
	var game := context.game
	var motion := context.motion
	match target.kind:
		Kind.PICKUP:
			if motion.rod_carried:
				return false
			motion.rod_carried = true
		Kind.SWITCH:
			if game.hallway_lit:
				return false
			game.light_hallway()
			motion.hallway_switch_flips += 1
		Kind.CONSOLE:
			if not game.press_console():
				return false
			motion.console_presses += 1
		Kind.DOOR:
			var press := Doors.Context.new()
			press.rod_carried = motion.rod_carried
			press.face_id = target.id if target.policy == Selection.FACE_RAY else _layout.door(target.door_id).face_ids()[0]
			return game.doors.press(target.door_id, press).accepted()
		_:
			assert(false, "interaction kind has a dispatcher")
	return true

static func eligible(targets: Array[Target], context: Context, solids: Array[AABB]) -> Array[Target]:
	var hits: Dictionary = {}
	var result: Array[Target] = []
	for target: Target in targets:
		var distance := hit_distance(target, context, solids)
		if distance >= 0:
			hits[target.id] = distance
			result.append(target)
	result.sort_custom(func(a: Target, b: Target) -> bool:
		if a.policy != b.policy:
			return a.policy == Selection.FACE_RAY
		if a.policy == Selection.LEGACY_PROXIMITY and a.priority != b.priority:
			return a.priority < b.priority
		if hits[a.id] != hits[b.id]:
			return hits[a.id] < hits[b.id]
		return String(a.id) < String(b.id))
	return result

static func hit_distance(target: Target, context: Context, solids: Array[AABB]) -> float:
	if not context.walking or target.deck != context.deck:
		return -1.0
	if Vector2(context.foot.x - target.center.x, context.foot.z - target.center.z).length() > target.reach:
		return -1.0
	if target.policy == Selection.LEGACY_PROXIMITY:
		return 0.0
	var eye := target.frame.affine_inverse() * context.eye
	var direction := target.frame.basis.inverse() * context.forward
	if eye.y < -0.2 or eye.y > target.size.y + 0.2 or eye.z <= 0 or direction.z >= 0:
		return -1.0
	var distance := -eye.z / direction.z
	var hit := eye + direction * distance
	if absf(hit.x) > target.size.x / 2.0 + 0.2 or hit.y < -0.2 or hit.y > target.size.y + 0.2:
		return -1.0
	var end := context.eye + context.forward * distance
	for solid: AABB in solids:
		var fraction := segment_hit(context.eye, end, solid)
		if fraction >= 0 and fraction < 1.0 - 0.00001:
			return -1.0
	return distance

## Slab intersection, including starts inside a solid; stable input ordering.
static func segment_hit(start: Vector3, end: Vector3, box: AABB) -> float:
	var delta := end - start
	var near: float = 0.0
	var far: float = 1.0
	for axis: int in range(3):
		if delta[axis] == 0.0:
			if start[axis] < box.position[axis] or start[axis] > box.end[axis]:
				return -1.0
		else:
			var a: float = (box.position[axis] - start[axis]) / delta[axis]
			var b: float = (box.end[axis] - start[axis]) / delta[axis]
			near = maxf(near, minf(a, b))
			far = minf(far, maxf(a, b))
			if near > far:
				return -1.0
	return near
