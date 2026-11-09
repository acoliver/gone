class_name ShipScene
extends RefCounted
## Shared structural construction and snapshot adapters. Roots pass these
## presenters to GameStep; scene nodes never advance door state.

var stream: ShipStream
var door_views: Array[DoorView] = []
var _parent: Node3D
var _game: Game
var _prepared: Dictionary = {}
var _hatches: Dictionary = {}
var text_cache: ShipTextCache
var labels: Dictionary = {}
var _spaces: Dictionary = {ShipLayout.BAY_ID: true, &"D14-S-041": true, ShipLayout.POWER_ID: true}
var _initial_labels: bool = false
var _opening_nodes: Array[Node3D] = []
var _sight_set: ColliderSet
var _sight_solids: Array[AABB] = []
var _sight_hatches: Dictionary = {}
var bay_root: Node3D
var room: RoomGeometry
var pods_node: StasisPods
var hatch: Hatch
var lighting: Lighting
var hazards: Hazards
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
	scene._add_opening_node(scene.bay_root)
	scene.room = RoomGeometry.build(true, game.layout)
	scene.room.name = "RoomGeometry"
	scene.bay_root.add_child(scene.room)
	scene.bay_root.add_child(CeilingProps.build(game.layout, ShipLayout.BAY_ID))
	scene.pods_node = StasisPods.build(game.registry)
	scene.bay_root.add_child(scene.pods_node)
	scene.lighting = Lighting.build(game)
	scene.bay_root.add_child(scene.lighting)
	scene.hazards = Hazards.build(game.ventilation, game.layout.bay())
	scene.bay_root.add_child(scene.hazards)
	if production_wires:
		scene.bay_root.add_child(Wires.build())
	scene.rod = Rod.build()
	scene.bay_root.add_child(scene.rod)
	Lighting.mesh_layers(scene.bay_root, 1 | Lighting.BAY_FILL_MASK)
	# Pod lighting keeps main's pure-red, long-throw look; architectural fills
	# and short orange keys remain on the bay walls and hatch.
	Lighting.mesh_layers(scene.pods_node, Lighting.POD_STATUS_MASK)
	# The shared hatch is split by visible room, including its collar returns.
	scene.hatch = Hatch.build(game.layout, 1 | Lighting.HALL_FILL_MASK, 1 | Lighting.BAY_FILL_MASK)
	scene.hatch.name = "Hatch"
	scene.bay_root.add_child(scene.hatch)
	var environment := scene.lighting.get_node("RoomEnvironment")
	scene.lighting.remove_child(environment)
	parent.add_child(environment)
	scene.hallway = Hallway.build(game)
	scene._add_opening_node(scene.hallway)
	scene.text_cache = ShipTextCache.new()
	scene.text_cache.name = "ShipTextCache"
	scene.text_cache.pair_ready.connect(scene._labels_ready)
	parent.add_child(scene.text_cache)
	scene.power_room = PowerRoom.build(game, scene.text_cache)
	scene._add_opening_node(scene.power_room)
	HatchServices.bind_lens(scene.hatch.view, 0, scene.hallway.lens_material())
	HatchServices.bind_lens(scene.hatch.view, 1, scene.lighting.lens_material())
	var bay_hatch_key := scene.lighting.fixture(ShipLayout.BAY_HATCH_KEY_ID)
	assert(bay_hatch_key.get_meta(&"light_role") == ShipLayout.EmergencyLightRole.BAY_HATCH, "seat the authored bay hatch key")
	HatchServices.seat_fixture(scene.hatch.view, 1, bay_hatch_key)
	HatchServices.seat_nearest(scene.hatch.view, 0, scene.hallway.lights())
	scene.lighting.bind_pod_keys()
	scene.lighting.bind_status_belts(scene.pods_node)
	scene.door_views.append(scene.hatch.view)
	scene.door_views.append(DoorView.adapter(game.layout.door(ShipLayout.POWER_DOOR_ID), scene.power_room.set_door_offset))
	for id: StringName in scene.hallway.side_leaves:
		scene.door_views.append(DoorView.bind_leaf(game.layout.door(id), scene.hallway.side_leaves[id]))
	for view: DoorView in scene.door_views:
		if view.get_parent() == null:
			scene._add_opening_node(view)
		else:
			scene._opening_nodes.append(view)
		view.present(game.doors.snapshot(view.door_id()))
	for id: StringName in [&"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
		scene._add_hatch(id, null, scene.hallway)
	scene.stream = ShipStream.build(scene, game, parent)
	parent.add_child(scene.stream)
	return scene

func prepare_near(foot: Vector3) -> void:
	if not _initial_labels:
		_initial_labels = true
		_sync_labels()
		_sync_sliding_labels()
	for id: StringName in _game.layout.deck(14).connector_ids():
		var spec := _game.layout.connector(id)
		var hall := _game.layout.section(&"D14-S-041").bounds()
		var threshold := hall.end.x - 4 if spec.pitch_index() == 1 else hall.position.x + 4
		if (spec.pitch_index() == 1 and foot.x >= threshold) or (spec.pitch_index() == 0 and foot.x <= threshold):
			_prepare_connector(spec)
			stream.ensure_shaft(spec.well_id())

func _prepare_connector(spec: ShipLayout.ConnectorSpec) -> void:
	if _prepared.has(spec.id()):
		return
	_prepared[spec.id()] = true
	var connector := ShipConnector.build(_game.layout, spec)
	_add_opening_node(connector)
	var lift := _game.layout.door(_game.layout.lift(spec.lift_id()).door_id())
	var lift_view := DoorView.bind_leaf(lift, connector.lift_leaf)
	_add_opening_node(lift_view)
	door_views.append(lift_view)
	var number := 40 if spec.pitch_index() == 0 else 42
	var section_spec := _game.layout.section(ShipLayout.section_id(14, number))
	var section := ShipSection.build(_game.layout, section_spec)
	_add_opening_node(section)
	for id: StringName in section.side_leaves:
		var view := DoorView.bind_leaf(_game.layout.door(id), section.side_leaves[id])
		_add_opening_node(view)
		door_views.append(view)
	for id: StringName in section_spec.opening_ids():
		if _game.layout.door(id).kind() == ShipLayout.DoorKind.HATCH:
			_add_hatch(id, null, hallway)
	for id: StringName in spec.hatch_ids():
		_add_hatch(id, null, hallway)
	_seat_connector_lamps(spec, connector)
	_seat_section_lamps(section_spec, section)
	_spaces[spec.id()] = true
	_spaces[section_spec.id()] = true
	_sync_labels()
	_sync_sliding_labels()
	_add_lift_label(spec, connector.lift_leaf)

func _sync_labels() -> void:
	for id: StringName in _game.layout.door_ids():
		var door := _game.layout.door(id)
		if door.deck_number() != 14 or door.kind() not in [ShipLayout.DoorKind.HATCH, ShipLayout.DoorKind.BAY]:
			continue
		for face_id: StringName in door.face_ids():
			var face := _game.layout.face(face_id)
			if _spaces.has(face.source_space()):
				_add_hatch_label(door, face)

static func _world_frame(node: Node3D) -> Transform3D:
	return Surfaces.world_frame(node)

func _add_hatch_label(door: ShipLayout.DoorSpec, face: ShipLayout.FaceSpec) -> void:
	var leaf: Node3D = hatch.door_piece() if door.kind() == ShipLayout.DoorKind.BAY else _hatches[door.id()].label_leaf()
	var local := face.leaf_label_frame(door)
	_add_label(face.id(), door.deck_number(), face.source_space(), door.frame() * face.label_frame(), face.label_size(), ShipText.hatch_label(door.deck_number(), face.destination_section()), leaf, local)

func _sync_sliding_labels() -> void:
	for view: DoorView in door_views:
		var door := _game.layout.door(view.door_id())
		if not SlidingDoorParts.applies(door): continue
		var leaf := power_room._door_leaf if door.kind() == ShipLayout.DoorKind.POWER else view.label_leaf()
		for side: int in range(door.face_ids().size()):
			var face := _game.layout.face(door.face_ids()[side])
			if not _spaces.has(face.source_space()): continue
			var local := SlidingDoorParts.label_frame(door, side)
			_add_label(face.id(), door.deck_number(), face.source_space(), _world_frame(leaf) * local, SlidingDoorParts.LABEL_SIZE, ShipText.sliding_label(_game.layout, door), leaf, local)

func _add_lift_label(spec: ShipLayout.ConnectorSpec, leaf: Node3D) -> void:
	var lift := _game.layout.lift(spec.lift_id())
	var local := _game.layout.door(lift.door_id()).frame().affine_inverse() * lift.label_anchor()
	_add_label(lift.id(), spec.deck_number(), spec.id(), lift.label_anchor(), lift.label_size(), ShipText.deck_label(spec.deck_number()), leaf, local)

func _add_label(id: StringName, deck: int, space: StringName, anchor: Transform3D, size: Vector2, text: ShipText.LabelText, parent: Node3D, local: Transform3D) -> void:
	if labels.has(id):
		return
	var state := _game.label_attention.register_face(id, deck, space, anchor, size)
	var label := ShipLabel.build(text_cache, text, id, local, size, state)
	label.tree_exiting.connect(_game.label_attention.unload.bind(id))
	parent.add_child(label)
	labels[id] = label
	if not label.pair.ready():
		_game.label_attention.unload(id)

func _labels_ready(key: String) -> void:
	for label: ShipLabel in labels.values():
		if label.pair.key == key:
			_game.label_attention.load_face(label.face_id)

func tick_attention(eye: Vector3, forward: Vector3, deck: int = 14) -> void:
	for label: ShipLabel in labels.values():
		_game.label_attention.move_face(label.face_id, _world_frame(label))
	var set := _game.collision.deck_set(deck)
	if _sight_set != set:
		_sight_set = set
		_sight_solids.clear()
		var ids := _game.collision.solid_ids(deck)
		var boxes := _sight_set.boxes()
		var wall_returns: Dictionary = {}
		for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(_game.layout, deck):
			if solid.material_role != &"wall": continue
			var drawn := SlidingDoorParts.wall_boxes(_game.layout, solid)
			if drawn.size() == 1 and drawn[0] == AABB(-solid.size / 2, solid.size): continue
			var bounds: Array[AABB] = []
			for box: AABB in drawn: bounds.append(solid.transform * box)
			var key := solid.id if ShipGeometry.collision_boxes(solid).size() == 1 else StringName("%s/CELL/0000" % solid.id)
			wall_returns[key] = bounds
		for index: int in range(boxes.size()):
			var id := String(ids[index])
			if wall_returns.has(ids[index]):
				_sight_solids.append_array(wall_returns[ids[index]])
				continue
			if id.ends_with("/SWING"):
				continue
			if id.ends_with("/BLOCKER") or id.ends_with("/PARKED"):
				var owner := StringName(id.get_slice("/", 0))
				if _game.layout.door(owner).animation() == ShipLayout.AnimationRecipe.HINGE:
					continue
			var box: ColliderSet.Aabb = boxes[index]
			_sight_solids.append(AABB(box.min_corner(), box.max_corner() - box.min_corner()))
		for id: StringName in _game.layout.door_ids():
			var door := _game.layout.door(id)
			if door.deck_number() != deck or door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
			for detail: ShipGeometry.SolidSpec in ShipGeometry.hatch_fixed_hardware(door):
				_sight_solids.append(detail.transform * AABB(-detail.size / 2, detail.size))
	var sight: Array[ShipGeometry.SightBox] = []
	for id: StringName in _game.layout.door_ids():
		var spec := _game.layout.door(id)
		if spec.deck_number() == deck and spec.animation() == ShipLayout.AnimationRecipe.HINGE:
			var snapshot := _game.doors.snapshot(id)
			var angle := snapshot.open_radians * snapshot.leaf_fraction
			var wheel := snapshot.wheel_angle + snapshot.refusal_offset
			if not _sight_hatches.has(id) or _sight_hatches[id][0] != angle or _sight_hatches[id][1] != wheel:
				_sight_hatches[id] = [angle, wheel, ShipGeometry.hatch_sight_boxes(spec, angle, wheel)]
			sight.append_array(_sight_hatches[id][2])
	_game.label_attention.tick(deck, eye, forward, _sight_solids, sight)
	for label: ShipLabel in labels.values():
		label.present()

func _add_hatch(id: StringName, parent: Node3D = null, circuit: Hallway = null) -> void:
	if _hatches.has(id):
		return
	var spec := _game.layout.door(id)
	var masks: Array[int] = []
	for face: StringName in spec.face_ids():
		var space := _game.layout.face(face).source_space()
		var mask := Lighting.space_mask(_game.layout, space)
		masks.append(mask | Lighting.HALL_FILL_MASK if space == &"D14-S-041" else mask)
	var view := DoorView.build(spec, masks[0], masks[1])
	for side: int in range(2):
		if _game.layout.face(spec.face_ids()[side]).source_space() == &"D14-S-041" and circuit != null:
			HatchServices.bind_lens(view, side, circuit.lens_material())
			HatchServices.seat_nearest(view, side, circuit.lights())
	if parent == null:
		_add_opening_node(view)
	else:
		parent.add_child(view)
	# The wall and frame recipes also supply the collision manifest.
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(spec):
		var wall := DoorView.split_surface(solid, spec.frame(), masks[0], masks[1], _game.layout)
		wall.transform = spec.frame()
		wall.set_meta(&"solid_id", solid.id)
		if parent == null:
			_add_opening_node(wall)
		else:
			parent.add_child(wall)
	door_views.append(view)
	_hatches[id] = view
	view.present(_game.doors.snapshot(id))

func connector_prepared(id: StringName) -> bool:
	return _prepared.has(id)

func build_remote(spec: ShipLayout.ConnectorSpec) -> Node3D:
	assert(spec.deck_number() != 14, "D14 keeps its original room set")
	var root := ShipConnector.build(_game.layout, spec)
	root.set_meta(&"remote_connector", true)
	_parent.add_child(root)
	var lift := _game.layout.lift(spec.lift_id())
	var view := DoorView.bind_leaf(_game.layout.door(lift.door_id()), root.lift_leaf)
	root.add_child(view)
	door_views.append(view)
	view.present(_game.doors.snapshot(lift.door_id()))
	for id: StringName in spec.hatch_ids():
		_add_hatch(id, root)
		var door := _game.layout.door(id)
		for face_id: StringName in door.face_ids():
			var face := _game.layout.face(face_id)
			if face.source_space() == spec.id():
				_add_hatch_label(door, face)
	_seat_connector_lamps(spec, root)
	_add_lift_label(spec, root.lift_leaf)
	return root

func remove_remote(spec: ShipLayout.ConnectorSpec, root: Node3D) -> void:
	for view: DoorView in door_views.duplicate():
		if view.get_parent() == root:
			door_views.erase(view)
	for id: StringName in spec.hatch_ids():
		_hatches.erase(id)
	for id: StringName in labels.keys():
		if root.is_ancestor_of(labels[id]):
			_game.label_attention.unload(id)
			labels.erase(id)
	root.free()

func _add_opening_node(node: Node3D) -> void:
	_parent.add_child(node)
	_opening_nodes.append(node)

func set_opening_visible(show: bool) -> void:
	for node: Node3D in _opening_nodes:
		node.visible = show
		node.process_mode = Node.PROCESS_MODE_INHERIT if show else Node.PROCESS_MODE_DISABLED
	for id: StringName in _game.layout.well_ids():
		stream.show_d14_shell(id, not show)

func _seat_connector_lamps(spec: ShipLayout.ConnectorSpec, connector: ShipConnector) -> void:
	var lights := _fixture_lights(connector)
	assert(lights.size() == 3, "connector retains two hatch keys and one landing key")
	for id: StringName in spec.hatch_ids():
		var door := _game.layout.door(id)
		var side := door.spaces().find(spec.id())
		assert(side >= 0, "hatch has a connector-facing cage")
		HatchServices.seat_nearest(_hatches[id], side, lights)

static func _fixture_lights(owner: Node3D) -> Array[OmniLight3D]:
	var lights: Array[OmniLight3D] = []
	for fixture: Node in owner.get_children():
		for child: Node in fixture.get_children():
			if child is OmniLight3D: lights.append(child)
	return lights

func _seat_section_lamps(spec: ShipLayout.SectionSpec, section: ShipSection) -> void:
	var lights := _fixture_lights(section)
	for id: StringName in spec.opening_ids():
		var door := _game.layout.door(id)
		if door.kind() != ShipLayout.DoorKind.HATCH: continue
		HatchServices.seat_nearest(_hatches[id], door.spaces().find(spec.id()), lights)
