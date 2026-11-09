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
	var face_id: StringName
	var kind: int = Kind.DOOR
	var policy: int = Selection.LEGACY_PROXIMITY
	var priority: int = 0
	var deck: int = 14
	var center := Vector3.ZERO
	var reach: float = 2.2
	var frame := Transform3D.IDENTITY
	var size := Vector2(1.2, 2.4)
	var bounds := AABB()

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
var _remote_solids: Dictionary = {}
var _layout: ShipLayout

func _init(layout: ShipLayout, solids: Array[AABB] = []) -> void:
	_layout = layout
	_solids = solids.duplicate()
	_legacy(&"D14-BAY-ROD", Kind.PICKUP, layout.anchor(&"D14-BAY-ROD").origin, 1.3, 0)
	_legacy(ShipLayout.BAY_DOOR_ID, Kind.DOOR, layout.door(ShipLayout.BAY_DOOR_ID).frame().origin, 2.2, 1)
	_legacy(&"D14-HALL-SWITCH", Kind.SWITCH, layout.anchor(&"D14-HALL-SWITCH").origin, 2.2, 2)
	_legacy(ShipLayout.POWER_DOOR_ID, Kind.DOOR, layout.door(ShipLayout.POWER_DOOR_ID).frame().origin, 2.2, 3)
	_legacy(&"D14-POWER-CONSOLE", Kind.CONSOLE, layout.anchor(&"D14-POWER-CONSOLE").origin, 1.8, 4)
	var console := Target.new()
	console.id = QuartersLayout.CONSOLE
	console.kind = Kind.CONSOLE
	console.deck = QuartersLayout.DECK
	console.reach = CONSOLE_ACT_REACH
	for prop: Dictionary in QuartersInventory.props():
		if prop.id == "console": console.bounds = QuartersInventory.world_bounds(QuartersInventory.prop_bounds(prop))
	console.center = console.bounds.get_center()
	_targets.append(console)
	for id: StringName in layout.door_ids():
		if id not in [ShipLayout.BAY_DOOR_ID, ShipLayout.POWER_DOOR_ID]:
			register_door(id)
	var release := Target.new()
	release.id = QuartersLayout.RELEASE
	release.door_id = QuartersLayout.DOOR
	release.face_id = layout.door(QuartersLayout.DOOR).face_ids()[0]
	release.policy = Selection.FACE_RAY
	release.deck = QuartersLayout.DECK
	release.center = QuartersLayout.release_frame().origin
	release.size = QuartersLayout.RELEASE_SIZE
	release.frame = QuartersLayout.release_frame() * Transform3D(Basis(), Vector3(0, -release.size.y / 2, 0.08))
	release.bounds = QuartersLayout.release_frame() * AABB(Vector3(-release.size.x / 2, -release.size.y / 2, -0.015), Vector3(release.size.x, release.size.y, 0.095))
	_targets.append(release)

func register_door(id: StringName) -> void:
	var door := _layout.door(id)
	for face_id: StringName in door.face_ids():
		var target := Target.new()
		target.id = face_id
		target.door_id = id
		target.face_id = face_id
		target.policy = Selection.FACE_RAY
		target.deck = door.deck_number()
		target.frame = door.frame() * _layout.face(face_id).surface_frame()
		target.center = door.frame().origin
		target.size = door.aperture()
		if door.kind() == ShipLayout.DoorKind.SIDE:
			var leaf := ShipGeometry.box_aabb(ShipGeometry.side_door_leaf(door))
			target.bounds = AABB(leaf.min_corner(), leaf.max_corner() - leaf.min_corner())
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
	if kind == Kind.CONSOLE:
		var body := ShipGeometry.box_aabb(ShipGeometry.console_solid(ShipGeometry.console_stations()[1]))
		target.bounds = AABB(body.min_corner(), body.max_corner() - body.min_corner())
	_targets.append(target)

static func context_for(game: Game, motion: PlayerMotion, forward: Vector3 = Vector3.FORWARD) -> Context:
	var context := Context.new()
	context.game = game
	context.motion = motion
	context.walking = motion.state() == PlayerMotion.BodyState.WALK and not motion.mounted()
	context.deck = motion.deck()
	context.eye = motion.eye(game)
	context.forward = forward
	if motion.capsule() != null:
		context.foot = motion.capsule().foot
	return context

func target_for(id: StringName, deck: int, foot: Vector3) -> Target:
	for target: Target in _targets:
		if target.id == id:
			return target
	# A door id in a script chooses the face on the approach side.
	for target: Target in _targets:
		if target.door_id == id and target.deck == deck and (target.frame.affine_inverse() * foot).z > 0:
			return target
	if id in _layout.well_ids():
		return ladder_target(_layout, id, deck)
	return null

static func ladder_target(layout: ShipLayout, id: StringName, deck: int, exiting: bool = false) -> Target:
	var well := layout.well(id)
	var doorway := layout.ladder_doorway_frame(id, deck)
	var target := Target.new()
	target.id = id
	target.kind = Kind.LADDER
	target.policy = Selection.FACE_RAY
	target.deck = deck
	target.center = well.climb_line().origin
	target.center.y = doorway.origin.y
	target.frame = Transform3D(doorway.basis, target.center)
	if exiting:
		target.center = doorway.origin
		target.frame = doorway * Transform3D(Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3.ZERO)
	target.size = well.doorway_size()
	return target

func targets_on_deck(deck: int) -> Array[Target]:
	var result: Array[Target] = []
	for target: Target in _targets:
		if target.deck == deck:
			result.append(target)
	for id: StringName in _layout.well_ids():
		result.append(target_for(id, deck, Vector3.ZERO))
	return result

func target_visible(target: Target, eye: Vector3, collision: ShipCollision) -> bool:
	var end := target.center
	if target.policy == Selection.FACE_RAY:
		var local_eye := target.frame.affine_inverse() * eye
		end = target.frame * Vector3(0, clampf(local_eye.y, 0, target.size.y), 0)
	elif target.kind == Kind.DOOR:
		var door := _layout.door(target.door_id)
		end.y = clampf(eye.y, end.y, end.y + door.aperture().y)
	elif target.kind == Kind.CONSOLE:
		end = target.bounds.get_center()
	if target.bounds.has_volume():
		var fraction := segment_hit(eye, end, target.bounds)
		if fraction >= 0:
			end = eye.lerp(end, fraction)
	var boxes := collision.deck_set(target.deck).boxes()
	var ids := collision.solid_ids(target.deck)
	for index: int in range(boxes.size()):
		var id := ids[index]
		# A requested door's leaf, passage block and reserved swing are its own geometry.
		if target.kind == Kind.DOOR and id in [StringName("%s/LEAF" % target.door_id), StringName("%s/BLOCKER" % target.door_id), StringName("%s/SWING" % target.door_id)]:
			continue
		var box := boxes[index]
		var fraction := segment_hit(eye, end, AABB(box.min_corner(), box.max_corner() - box.min_corner()))
		if fraction >= 0 and fraction < 1.0 - 0.00001:
			return false
	return true

func selection_solids(deck: int) -> Array[AABB]:
	if deck == 14:
		return _solids
	if not _remote_solids.has(deck):
		var boxes: Array[AABB] = []
		for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(_layout, deck):
			var box := ShipGeometry.box_aabb(solid)
			boxes.append(AABB(box.min_corner(), box.max_corner() - box.min_corner()))
		_remote_solids[deck] = boxes
	return _remote_solids[deck]

func process(plane: InputPlane, context: Context, requested: StringName = &"") -> StringName:
	if not plane.has_press(InputPlane.Buttons.INTERACT):
		return &""
	for target: Target in eligible(_targets, context, selection_solids(context.deck)):
		if requested != &"" and target.id != requested:
			continue
		if requested != &"" and not target_visible(target, context.eye, context.game.collision):
			continue
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
			if not (game.quarters.press_console() if target.id == QuartersLayout.CONSOLE else game.press_console()):
				return false
			motion.console_presses += 1
		Kind.DOOR:
			var press := Doors.Context.new()
			press.rod_carried = motion.rod_carried
			press.face_id = target.face_id if target.policy == Selection.FACE_RAY else _layout.door(target.door_id).face_ids()[0]
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
