extends SimTestCase

const CONTACT := 0.002

func test_no_decorative_ceiling_rings_remain() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(Placement.wire_loops().is_empty(), "bay's unattached tori are removed")
	assert_true(layout.section(&"D14-S-041").ceiling_loops().is_empty(), "hall's unattached tori are removed")
	for batch: ShipLayout.DressingBatch in layout.dressing(&"D14-S-041").batches:
		assert_false(batch.shape == &"ring", "pipe tori are replaced by attached solid hangers")

func test_remote_fixture_housings_and_call_panels_connect_to_structure() -> void:
	var layout := ShipLayout.authored().layout
	for deck: int in [1, 14, 30]:
		var structure := _solid_bounds(ShipGeometry.deck_static_solids(layout, deck))
		for id: StringName in layout.deck(deck).connector_ids():
			var node := ShipConnector.build(layout, layout.connector(id))
			var pieces: Dictionary = {}
			_collect(node, pieces, ["CorridorDressing"])
			_check_graph(structure, pieces)
			node.free()

func test_every_corridor_dressing_instance_connects_to_structure() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.deck(14).section_ids() + layout.connector_ids():
		var space: ShipLayout.Spec = layout.section(id) if id in layout.deck(14).section_ids() else layout.connector(id)
		var solids := ShipGeometry.deck_static_solids(layout, space.deck_number())
		var structure: Array[AABB] = []
		for solid: ShipGeometry.SolidSpec in solids:
			if solid.material_role == &"door": continue
			for box: AABB in SlidingDoorParts.wall_boxes(layout, solid): structure.append(solid.transform * box)
		var pieces: Dictionary = {}
		for batch: ShipLayout.DressingBatch in layout.dressing(id).batches:
			for index: int in range(batch.poses.size()):
				pieces["%s/%s/%d" % [id, batch.family, index]] = batch.poses[index] * CorridorDressing._mesh(batch.shape).get_aabb()
		_check_graph(structure, pieces)

func test_hall_ceiling_damage_connects_to_structure() -> void:
	var game := Game.new(91)
	var hall := Hallway.build(game)
	var structure := _solid_bounds(ShipGeometry.hallway_solids(game.layout))
	var pieces: Dictionary = {}
	_collect(hall.get_node("HallCeilingDamage"), pieces)
	_check_graph(structure, pieces)
	hall.free()

func test_hall_tray_hangers_reach_ceiling_and_enter_the_rotated_trays() -> void:
	var game := Game.new(91)
	var hall := Hallway.build(game)
	var spec := game.layout.section(&"D14-S-041")
	var damage := hall.get_node("HallCeilingDamage")
	var trays := spec.ceiling_trays()
	assert_int_equal(trays.size(), 2, "long cable tray and transverse stub remain covered")
	assert_int_equal(damage.get_child_count(), trays.size() * 3, "each rendered tray has two rendered hangers")
	for index: int in range(trays.size()):
		var tray := trays[index]
		var mounts := DressingMounts.tray_hangers(tray, spec.bounds().end.y)
		assert_int_equal(mounts.size(), 2, "both ends have a ceiling hanger")
		for station: int in range(mounts.size()):
			var hanger := damage.get_child(index * 3 + station + 1) as MeshInstance3D
			var bounds := Surfaces.world_frame(hanger) * hanger.mesh.get_aabb()
			var expected := ShipGeometry.box_aabb(mounts[station])
			assert_close(bounds.position, expected.min_corner(), "rendered hanger follows its attachment recipe")
			assert_close(bounds.end, expected.max_corner(), "rendered hanger bounds follow the recipe")
			assert_true(absf(bounds.end.y - spec.bounds().end.y) <= CONTACT, "hanger top touches the actual ceiling")
			var bottom := Vector3(bounds.get_center().x, bounds.position.y, bounds.get_center().z)
			var local := tray.transform.affine_inverse() * bottom
			assert_true(AABB(-tray.size / 2, tray.size).has_point(local), "hanger bottom enters the rotated tray, not just its world AABB")
	hall.free()

func test_bay_and_power_dressing_connects_to_structure() -> void:
	var game := Game.new(91)
	var world := Node3D.new()
	var scene := ShipScene.build_into(world, game)
	var structure := _solid_bounds(ShipGeometry.opening_scene_solids(game.registry, false, false, game.layout))
	var pieces: Dictionary = {}
	_collect(scene.room.get_node("CeilingDamage"), pieces)
	_collect(scene.bay_root.get_node("HangingWires"), pieces)
	_collect(scene.lighting, pieces)
	_collect(scene.hallway, pieces, ["CorridorDressing", "HallCeilingDamage", "HallSideDoors"])
	_collect(scene.power_room, pieces)
	_check_graph(structure, pieces)
	world.free()

func test_hatch_service_parts_connect_individually_to_walls() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE"]:
		var spec := layout.door(id)
		var structure := _solid_bounds(ShipGeometry.hatch_wall_solids(spec) + ShipGeometry.hatch_frame_solids(spec))
		var pieces: Dictionary = {}
		for side: int in range(2):
			var root := HatchServices.build(spec, side, 1)
			root.transform = spec.frame()
			_collect(root, pieces)
			root.free()
		_check_graph(structure, pieces)

func _solid_bounds(solids: Array[ShipGeometry.SolidSpec]) -> Array[AABB]:
	var boxes: Array[AABB] = []
	for solid: ShipGeometry.SolidSpec in solids:
		# Console/generator collider hulls cannot stand in for their drawn parts.
		if "CONSOLE" in String(solid.id) or "GENERATOR" in String(solid.id): continue
		boxes.append(solid.transform * AABB(-solid.size / 2, solid.size))
	return boxes

func _collect(node: Node, pieces: Dictionary, skip: Array[String] = []) -> void:
	if String(node.name) in skip: return
	if node is Node3D and not node.visible: return
	if node is MeshInstance3D and node.mesh != null:
		var frame := Surfaces.world_frame(node)
		var key := str(node.get_instance_id()) + "/" + String(node.name)
		if node.mesh.has_meta(&"service_bounds"):
			var bounds: Array = node.mesh.get_meta(&"service_bounds")
			for index: int in range(bounds.size()): pieces[key + "/%d" % index] = frame * bounds[index]
		else: pieces[key] = frame * node.mesh.get_aabb()
	for child: Node in node.get_children(): _collect(child, pieces, skip)

func _check_graph(structure: Array[AABB], pieces: Dictionary) -> void:
	var connected := structure.duplicate()
	var pending := pieces.keys()
	while not pending.is_empty():
		var before := pending.size()
		for key: String in pending.duplicate():
			var bounds: AABB = pieces[key]
			for support: AABB in connected:
				if _touches(bounds, support):
					connected.append(bounds)
					pending.erase(key)
					break
		if pending.size() == before: break
	if not pending.is_empty():
		for key: String in pending: print("FLOATER ", key, " ", pieces[key])
	assert_true(pending.is_empty(), "%d dressing pieces lack a structural contact within 2 mm: %s" % [pending.size(), str(pending)])

func _touches(a: AABB, b: AABB) -> bool:
	var gap := (a.position - b.end).max(b.position - a.end).max(Vector3.ZERO)
	return gap.length() <= CONTACT
