class_name ShipScene
extends RefCounted
## Shared structural construction and snapshot adapters. Roots pass these
## presenters to GameStep; scene nodes never advance door state.

var door_views: Array[DoorView] = []
var _parent: Node3D
var _game: Game
var _prepared: Dictionary = {}
var _hatches: Dictionary = {}
var bay_root: Node3D
var room: RoomGeometry
var pods_node: StasisPods
var hatch: Hatch
var lighting: Lighting
var rod: Rod
var hallway: Hallway
var power_room: PowerRoom

static func build_into(parent: Node3D, game: Game, production_wires: bool = true) -> ShipScene:
	var scene := ShipScene.new()
	scene._parent = parent
	scene._game = game
	scene.bay_root = Node3D.new()
	scene.bay_root.name = "BayRoot"
	scene.bay_root.transform = game.layout.bay_to_world()
	parent.add_child(scene.bay_root)
	scene.room = RoomGeometry.build(true)
	scene.room.name = "RoomGeometry"
	scene.bay_root.add_child(scene.room)
	scene.pods_node = StasisPods.build(game.registry)
	scene.bay_root.add_child(scene.pods_node)
	scene.hatch = Hatch.build()
	scene.hatch.name = "Hatch"
	scene.bay_root.add_child(scene.hatch)
	scene.lighting = Lighting.build(game)
	scene.bay_root.add_child(scene.lighting)
	scene.bay_root.add_child(Hazards.build())
	if production_wires:
		scene.bay_root.add_child(Wires.build())
	scene.rod = Rod.build()
	scene.bay_root.add_child(scene.rod)
	var environment := scene.lighting.get_node("RoomEnvironment")
	scene.lighting.remove_child(environment)
	parent.add_child(environment)
	scene.hallway = Hallway.build(game)
	parent.add_child(scene.hallway)
	scene.power_room = PowerRoom.build(game)
	parent.add_child(scene.power_room)
	scene.door_views.append(DoorView.adapter(game.layout.door(ShipLayout.BAY_DOOR_ID), scene.hatch.set_door_offset))
	scene.door_views.append(DoorView.adapter(game.layout.door(ShipLayout.POWER_DOOR_ID), scene.power_room.set_door_offset))
	for id: StringName in scene.hallway.side_leaves:
		scene.door_views.append(DoorView.bind_leaf(game.layout.door(id), scene.hallway.side_leaves[id]))
	for view: DoorView in scene.door_views:
		parent.add_child(view)
		view.present(game.doors.snapshot(view.door_id()))
	Lighting.isolate_lights(scene.bay_root, 1)
	Lighting.isolate_lights(scene.hallway, 1)
	Lighting.isolate_lights(scene.power_room, 1)
	for id: StringName in [&"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
		scene._add_hatch(id)
	return scene

func prepare_near(foot: Vector3) -> void:
	for id: StringName in _game.layout.deck(14).connector_ids():
		var spec := _game.layout.connector(id)
		var hall := _game.layout.section(&"D14-S-041").bounds()
		var threshold := hall.end.x - 4 if spec.pitch_index() == 1 else hall.position.x + 4
		if (spec.pitch_index() == 1 and foot.x >= threshold) or (spec.pitch_index() == 0 and foot.x <= threshold):
			_prepare_connector(spec)

func _prepare_connector(spec: ShipLayout.ConnectorSpec) -> void:
	if _prepared.has(spec.id()):
		return
	_prepared[spec.id()] = true
	var connector := ShipConnector.build(_game.layout, spec)
	_parent.add_child(connector)
	var lift := _game.layout.door(_game.layout.lift(spec.lift_id()).door_id())
	var lift_view := DoorView.bind_leaf(lift, connector.lift_leaf)
	_parent.add_child(lift_view)
	door_views.append(lift_view)
	var number := 40 if spec.pitch_index() == 0 else 42
	var section_spec := _game.layout.section(ShipLayout.section_id(14, number))
	var section := ShipSection.build(_game.layout, section_spec)
	_parent.add_child(section)
	for id: StringName in section.side_leaves:
		var view := DoorView.bind_leaf(_game.layout.door(id), section.side_leaves[id])
		_parent.add_child(view)
		door_views.append(view)
	for id: StringName in section_spec.opening_ids():
		if _game.layout.door(id).kind() == ShipLayout.DoorKind.HATCH:
			_add_hatch(id)
	for id: StringName in spec.hatch_ids():
		_add_hatch(id)

func _add_hatch(id: StringName) -> void:
	if _hatches.has(id):
		return
	var spec := _game.layout.door(id)
	var masks: Array[int] = []
	for face: StringName in spec.face_ids():
		masks.append(Lighting.space_mask(_game.layout, _game.layout.face(face).source_space()))
	var view := DoorView.build(spec, masks[0], masks[1])
	_parent.add_child(view)
	# The wall and frame recipes also supply the collision manifest.
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(spec):
		var wall := DoorView.split_surface(solid, spec.frame(), masks[0], masks[1])
		wall.transform = spec.frame()
		wall.set_meta(&"solid_id", solid.id)
		_parent.add_child(wall)
	door_views.append(view)
	_hatches[id] = view
	view.present(_game.doors.snapshot(id))
