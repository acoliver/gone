class_name ShipCollision
extends RefCounted
## Pure collider assembly. Opening sets preserve the current insertion order;
## layout sets are lazy, stable-id ordered fixtures pending S03 adoption.

var _layout: ShipLayout
var _static: Dictionary = {}
var _assembled: Dictionary = {}
var _ids: Dictionary = {}
var _open_doors: Dictionary = {}
var _revisions: Dictionary = {}

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

func deck_set(deck: int) -> ColliderSet:
	_layout.deck(deck)
	if not _static.has(deck):
		_static[deck] = ShipGeometry.deck_static_solids(_layout, deck)
	if not _assembled.has(deck):
		var solids: Array[ShipGeometry.SolidSpec] = _static[deck].duplicate()
		for id: StringName in _layout.door_ids():
			var door := _layout.door(id)
			if door.deck_number() == deck and not _open_doors.has(id):
				solids.append_array(ShipGeometry.door_blockers(door))
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

static func hallway_set(registry: Pods.PodRegistry, door_open: bool) -> ColliderSet:
	var set := ColliderSet.new()
	var shell := ShipGeometry.room_shell()
	for index: int in range(shell.size()):
		if index != ShipGeometry.ROOM_SHELL_EAST_WALL_INDEX:
			set.insert(ShipGeometry.box_aabb(shell[index]))
	_insert_solids(set, ShipGeometry.doorway_wall_solids())
	if not door_open:
		set.insert(ShipGeometry.box_aabb(ShipGeometry.doorway_block()))
	_insert_pods(set, registry)
	var hatch := ShipGeometry.hatch_solids()
	for index: int in range(4):
		set.insert(ShipGeometry.box_aabb(hatch[index]))
	if not door_open:
		set.insert(ShipGeometry.box_aabb(hatch[4]))
	_insert_solids(set, ShipGeometry.hallway_solids())
	_insert_solids(set, ShipGeometry.side_door_solids())
	return set

static func opening_set(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool) -> ColliderSet:
	var set := hallway_set(registry, door_open)
	_insert_solids(set, ShipGeometry.power_room_solids())
	for station: ShipGeometry.ConsoleStation in ShipGeometry.console_stations():
		set.insert(ShipGeometry.box_aabb(ShipGeometry.console_solid(station)))
	set.insert(ShipGeometry.box_aabb(ShipGeometry.generator_solid()))
	if not power_door_open:
		set.insert(ShipGeometry.box_aabb(ShipGeometry.power_door_leaf()))
	return set

static func _insert_solids(set: ColliderSet, solids: Array[ShipGeometry.SolidSpec]) -> void:
	for solid: ShipGeometry.SolidSpec in solids:
		set.insert(ShipGeometry.box_aabb(solid))

static func _insert_pods(set: ColliderSet, registry: Pods.PodRegistry) -> void:
	for pod: Pods.Pod in registry.pods():
		var frame := ShipGeometry.pod_world_transform(pod.placement())
		for piece: PodGeometry.PodSolid in PodGeometry.pod_solids(pod.state()):
			var rotation: Quaternion = frame[0] * Quaternion(Vector3.RIGHT, piece.roll_radians)
			var center: Vector3 = frame[0] * piece.center + frame[1]
			set.insert(ShipGeometry.box_aabb(ShipGeometry.SolidSpec.new(center, piece.size, rotation)))
