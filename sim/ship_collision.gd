class_name ShipCollision
extends RefCounted
## Pure collider assembly. Opening sets preserve the current insertion order;
## deck sets cache static recipes and rebuild only after an opening completes.

class Slice:
	extends RefCounted
	var colliders := ColliderSet.new()
	var ids: Array[StringName] = []

var _layout: ShipLayout
var _static: Dictionary = {}
var _assembled: Dictionary = {}
var _ids: Dictionary = {}
var _open_doors: Dictionary = {}
var _revisions: Dictionary = {}
var _well_boxes: Dictionary = {}

func _init(layout: ShipLayout) -> void:
	_layout = layout
	for deck: int in range(1, 31):
		layout.deck(deck)
		_revisions[deck] = 0

func cached_deck_count() -> int:
	return _static.size()

func revision(deck: int) -> int:
	_layout.deck(deck)
	return _revisions[deck]

func open_door(id: StringName) -> void:
	var door := _layout.door(id)
	assert(door.policy() != ShipLayout.Policy.NEVER_OPENS, "a never-opening door cannot complete opening")
	if _open_doors.has(id):
		return
	_open_doors[id] = true
	_revisions[door.deck_number()] += 1
	_assembled.erase(door.deck_number())
	_ids.erase(door.deck_number())

func commit(events: Array[Doors.Event]) -> void:
	for event: Doors.Event in events:
		if event.kind() == Doors.EventKind.OPENED:
			open_door(event.door_id())

func deck_set(deck: int) -> ColliderSet:
	_layout.deck(deck)
	if not _static.has(deck):
		_static[deck] = ShipGeometry.deck_static_solids(_layout, deck)
	if not _assembled.has(deck):
		var solids: Array[ShipGeometry.SolidSpec] = _static[deck].duplicate()
		for id: StringName in _layout.door_ids():
			var door := _layout.door(id)
			if door.deck_number() != deck or door.kind() == ShipLayout.DoorKind.SIDE:
				continue
			if id == ShipLayout.BAY_DOOR_ID:
				if not _open_doors.has(id):
					solids.append(ShipGeometry.doorway_block(_layout))
					solids[-1].id = &"D14-BAY-DOOR/BLOCKER"
					solids.append(ShipGeometry.transformed(ShipGeometry.hatch_solids()[4], _layout.bay_to_world(), &"D14-BAY-DOOR/LEAF"))
			elif id == ShipLayout.POWER_DOOR_ID:
				if not _open_doors.has(id):
					var leaf := ShipGeometry.power_door_leaf()
					leaf.id = &"D14-POWER-DOOR/LEAF"
					solids.append(leaf)
			else:
				solids.append_array(ShipGeometry.open_door_solids(door) if _open_doors.has(id) else ShipGeometry.door_blockers(door))
		solids.sort_custom(func(a: ShipGeometry.SolidSpec, b: ShipGeometry.SolidSpec) -> bool: return String(a.id) < String(b.id))
		var ids: Array[StringName] = []
		var set := ColliderSet.new()
		for solid: ShipGeometry.SolidSpec in solids:
			ids.append(solid.id)
			set.insert(ShipGeometry.box_aabb(solid))
		_ids[deck] = ids
		_assembled[deck] = set
	return _assembled[deck]

func solid_ids(deck: int) -> Array[StringName]:
	deck_set(deck)
	return _ids[deck].duplicate()

static func bay_set(registry: Pods.PodRegistry) -> ColliderSet:
	var set := ColliderSet.new()
	_insert_solids(set, ShipGeometry.room_shell())
	_insert_pods(set, registry)
	_insert_solids(set, ShipGeometry.hatch_solids())
	return set

static func hallway_set(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout = ShipLayout.authored().layout) -> ColliderSet:
	var set := ColliderSet.new()
	_insert_solids(set, hallway_solids(registry, door_open, layout))
	for id: StringName in [&"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
		_insert_solids(set, ShipGeometry.hatch_wall_solids(layout.door(id)))
		_insert_solids(set, ShipGeometry.hatch_frame_solids(layout.door(id)))
		_insert_solids(set, ShipGeometry.door_blockers(layout.door(id)))
	return set

static func hallway_solids(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout) -> Array[ShipGeometry.SolidSpec]:
	return ShipGeometry.opening_hall_solids(registry, door_open, layout)

static func opening_solids(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout, open_ids: Dictionary = {}, include_blockers: bool = true) -> Array[ShipGeometry.SolidSpec]:
	return ShipGeometry.opening_scene_solids(registry, door_open, power_door_open, layout, open_ids, include_blockers)

static func opening_sight_solids(registry: Pods.PodRegistry, layout: ShipLayout) -> Array[AABB]:
	var boxes: Array[AABB] = []
	for solid: ShipGeometry.SolidSpec in opening_solids(registry, true, true, layout):
		if solid.material_role == &"door" or String(solid.id).begins_with("D14-S-041/SIDE-LEAF/"):
			continue
		var box := ShipGeometry.box_aabb(solid)
		boxes.append(AABB(box.min_corner(), box.max_corner() - box.min_corner()))
	return boxes

static func opening_set(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout = ShipLayout.authored().layout) -> ColliderSet:
	var set := ColliderSet.new()
	_insert_solids(set, opening_solids(registry, door_open, power_door_open, layout))
	return set

static func _insert_solids(set: ColliderSet, solids: Array[ShipGeometry.SolidSpec]) -> void:
	for solid: ShipGeometry.SolidSpec in solids:
		set.insert(ShipGeometry.box_aabb(solid))

static func _insert_pods(set: ColliderSet, registry: Pods.PodRegistry, parent: Transform3D = Transform3D.IDENTITY) -> void:
	for pod: Pods.Pod in registry.pods():
		var frame := ShipGeometry.pod_world_transform(pod.placement())
		for piece: PodGeometry.PodSolid in PodGeometry.pod_solids(pod.state()):
			var rotation: Quaternion = frame[0] * Quaternion(Vector3.RIGHT, piece.roll_radians)
			var center: Vector3 = frame[0] * piece.center + frame[1]
			set.insert(ShipGeometry.box_aabb(ShipGeometry.SolidSpec.new(center, piece.size, rotation), parent))

func supported_walk(capsule: Resolve.Capsule, displacement: Vector3) -> Vector3:
	return supported_walk_on_deck(14, capsule, displacement)

func supported_walk_on_deck(deck: int, capsule: Resolve.Capsule, displacement: Vector3) -> Vector3:
	var result := displacement
	for id: StringName in _layout.deck(deck).connector_ids():
		var connector := _layout.connector(id)
		var landing := _layout.well(connector.well_id()).landing_bounds(deck)
		var inset := Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
		var end := capsule.foot + result
		if end.x >= landing.position.x - inset and end.x <= landing.end.x + inset and end.z < landing.end.z:
			result.z = maxf(end.z, landing.position.z + inset) - capsule.foot.z
	return result


## Select with the entire swept capsule, including the head and both radii.
func well_slice(well_id: StringName, capsule: Resolve.Capsule, displacement: Vector3) -> Slice:
	var radius := Controller.CAPSULE_RADIUS
	var low := minf(capsule.foot.y, capsule.head.y) + minf(0, displacement.y) - radius
	var high := maxf(capsule.foot.y, capsule.head.y) + maxf(0, displacement.y) + radius
	var boxes: Dictionary = {}
	for deck: int in range(1, 31):
		var floor_y := _layout.floor_y(deck)
		if high < floor_y - ShipLayout.WALL or low > floor_y + ShipLayout.CLEAR_HEIGHT + ShipLayout.WALL:
			continue
		var set := deck_set(deck)
		var ids := solid_ids(deck)
		for index: int in range(ids.size()):
			boxes[ids[index]] = set.boxes()[index]
	if not _well_boxes.has(well_id):
		var shell: Dictionary = {}
		for solid: ShipGeometry.SolidSpec in ShipGeometry.well_solids(_layout.well(well_id)):
			shell[solid.id] = ShipGeometry.box_aabb(solid)
		_well_boxes[well_id] = shell
	boxes.merge(_well_boxes[well_id], true)
	var slice := Slice.new()
	slice.ids.assign(boxes.keys())
	slice.ids.sort()
	for id: StringName in slice.ids:
		slice.colliders.insert(boxes[id])
	return slice
