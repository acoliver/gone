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

static func hallway_set(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout = ShipLayout.authored().layout) -> ColliderSet:
	var set := ColliderSet.new()
	_insert_solids(set, hallway_solids(registry, door_open, layout))
	return set

static func hallway_solids(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout) -> Array[ShipGeometry.SolidSpec]:
	var solids: Array[ShipGeometry.SolidSpec] = []
	var frame := layout.bay_to_world()
	var shell := ShipGeometry.room_shell()
	for index: int in range(shell.size()):
		if index != ShipGeometry.ROOM_SHELL_EAST_WALL_INDEX:
			solids.append(ShipGeometry.transformed(shell[index], frame, StringName("D14-BAY/SHELL/%03d" % index)))
	if not door_open:
		var block := ShipGeometry.doorway_block(layout)
		block.id = &"D14-BAY-DOOR/BLOCKER"
		solids.append(block)
	for pod: Pods.Pod in registry.pods():
		var pod_frame := ShipGeometry.pod_world_transform(pod.placement())
		var pieces := PodGeometry.pod_solids(pod.state())
		for index: int in range(pieces.size()):
			var piece: PodGeometry.PodSolid = pieces[index]
			var rotation: Quaternion = pod_frame[0] * Quaternion(Vector3.RIGHT, piece.roll_radians)
			var center: Vector3 = pod_frame[0] * piece.center + pod_frame[1]
			solids.append(ShipGeometry.transformed(ShipGeometry.SolidSpec.new(center, piece.size, rotation), frame, StringName("D14-BAY/POD-%03d/%03d" % [pod.id().index(), index])))
	var hatch := ShipGeometry.hatch_solids()
	for index: int in range(4):
		solids.append(ShipGeometry.transformed(hatch[index], frame, StringName("D14-BAY/FRAME/%03d" % index)))
	if not door_open:
		solids.append(ShipGeometry.transformed(hatch[4], frame, &"D14-BAY-DOOR/LEAF"))
	_named_solids(solids, ShipGeometry.hallway_solids(layout), "D14-S-041/SHELL")
	_named_solids(solids, ShipGeometry.side_door_solids(), "D14-S-041/SIDE-LEAF")
	return solids

static func opening_solids(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout) -> Array[ShipGeometry.SolidSpec]:
	var solids := hallway_solids(registry, door_open, layout)
	_named_solids(solids, ShipGeometry.power_room_solids(), "D14-POWER/SHELL")
	var stations := ShipGeometry.console_stations()
	for index: int in range(stations.size()):
		var solid := ShipGeometry.console_solid(stations[index])
		solid.id = StringName("D14-POWER/CONSOLE/%03d" % index)
		solids.append(solid)
	var generator := ShipGeometry.generator_solid()
	generator.id = &"D14-POWER/GENERATOR"
	solids.append(generator)
	if not power_door_open:
		var leaf := ShipGeometry.power_door_leaf()
		leaf.id = &"D14-POWER-DOOR/LEAF"
		solids.append(leaf)
	return solids

static func opening_set(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout = ShipLayout.authored().layout) -> ColliderSet:
	var set := ColliderSet.new()
	_insert_solids(set, opening_solids(registry, door_open, power_door_open, layout))
	return set

static func _named_solids(target: Array[ShipGeometry.SolidSpec], pieces: Array[ShipGeometry.SolidSpec], owner: String) -> void:
	for index: int in range(pieces.size()):
		pieces[index].id = StringName("%s/%03d" % [owner, index])
		target.append(pieces[index])

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
