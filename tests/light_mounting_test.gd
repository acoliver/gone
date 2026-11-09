extends SimTestCase

const MAX_CEILING_DROP := 0.15
const CONTACT := 0.002

func test_whole_ship_fixtures_are_wall_mounted_or_within_150_mm_of_ceiling() -> void:
	var game := Game.new(91)
	var layout := game.layout
	var world := Node3D.new()
	var scene := ShipScene.build_into(world, game)
	scene.prepare_near(Vector3(10, 0, 0))
	scene.prepare_near(Vector3(26, 0, 0))
	var checked := _check(scene.bay_root, layout.bay_to_world() * layout.bay().local_bounds(), _walls(layout, 14))
	checked += _check(scene.hallway, layout.section(&"D14-S-041").bounds(), _walls(layout, 14))
	checked += _check(scene.power_room, layout.power_room().bounds(), _walls(layout, 14))
	for id: StringName in layout.connector_ids():
		var spec := layout.connector(id)
		var node := ShipConnector.build(layout, spec)
		checked += _check(node, spec.bounds(), _walls(layout, spec.deck_number()))
		node.free()
	for number: int in [40, 42]:
		var spec := layout.section(ShipLayout.section_id(14, number))
		var node := ShipSection.build(layout, spec)
		checked += _check(node, spec.bounds(), _walls(layout, 14))
		node.free()
	print("MOUNTED FIXTURES ", checked)
	assert_int_equal(checked, 239, "all standalone cages and beams across the ship are checked")
	world.free()

func test_mount_gate_rejects_a_centreline_drop_and_accepts_only_wall_contact_or_flush_depth() -> void:
	var layout := ShipLayout.authored().layout
	var light := Lighting.emergency_fill(Vector3(9, 2.5, 0), 1, 1)
	FixtureEmitter.wall_source(light, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"), "emergency", light.lens_material, 0.0)
	DressingMounts.ceiling_stem(light, 3.2, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	FixtureEmitter.combine_mount(light)
	var housing: MeshInstance3D = light.get_meta(&"fixture_housing")
	var walls := _walls(layout, 14)
	assert_false(_allowed(housing, 3.2, walls), "a continuously supported pendant still violates the ceiling rule")
	light.free()
	var box := MeshInstance3D.new()
	box.mesh = BoxMesh.new()
	box.mesh.size = Vector3(0.1, 0.15, 0.1)
	box.position = Vector3(9, 3.125, 0)
	assert_true(_allowed(box, 3.2, walls), "150 mm flush ceiling fixture passes")
	box.position.y -= 0.01
	assert_false(_allowed(box, 3.2, walls), "160 mm ceiling fixture fails")
	box.position = Vector3(9, 2.4, -1.5)
	assert_true(_allowed(box, 3.2, walls), "a real wall contact permits a lower fixture")
	box.free()

func test_relocated_emergency_cages_clear_services_frames_and_door_sweeps() -> void:
	var game := Game.new(91)
	for room: Node3D in [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]:
		var id: StringName = ShipLayout.BAY_ID if room is Lighting else (&"D14-S-041" if room is Hallway else ShipLayout.POWER_ID)
		var services := game.layout.ceiling_services(id)
		var walls := _walls(game.layout, 14)
		var to_world := game.layout.bay_to_world() if room is Lighting else Transform3D.IDENTITY
		var sources := room.find_children("EmergencyFill*", "Light3D", true, false)
		if room is Lighting:
			for light: OmniLight3D in room.lights():
				if light.get_parent() != room.fixture(ShipLayout.BAY_HATCH_KEY_ID): sources.append(light)
		for light: Light3D in sources:
			if light.name == "EmergencyFillEnd": continue
			var housing: MeshInstance3D = light.get_meta(&"fixture_housing")
			var box := to_world * Surfaces.world_frame(housing) * housing.mesh.get_aabb()
			assert_true(_wall_contact(housing, walls, to_world), "%s/%s has a physical wall bracket" % [room.name, light.name])
			assert_true(box.position.y >= 2.2, "cage stays above the standing envelope")
			for obstacle: ShipLayout.DressingClearance in services.reservations():
				assert_false(box.intersects(to_world * obstacle.bounds), "%s/%s clears %s" % [room.name, light.name, obstacle.id])
			for obstacle: AABB in services.detector_exclusions:
				assert_false(box.intersects(to_world * obstacle), "%s/%s clears hatch services, frames, labels and door sweeps" % [room.name, light.name])
		room.free()

func _check(node: Node3D, bounds: AABB, walls: Array[AABB]) -> int:
	var housings: Array[MeshInstance3D] = []
	for light: Light3D in node.find_children("*", "Light3D", true, false):
		if light.has_meta(&"spark_emitter"): continue
		assert_true(light.has_meta(&"fixture_emitter") and light.has_meta(&"fixture_housing"), "every non-spark source has a mounted housing")
		if not light.has_meta(&"fixture_emitter") or not light.has_meta(&"fixture_housing"): continue
		var emitter: MeshInstance3D = light.get_meta(&"fixture_emitter")
		# Pod belts and generator rings are installed machinery, not ceiling fixtures.
		if emitter.name == "PodStrips" or (light.name == "Glow" and light.get_parent().name == "Generator"): continue
		var housing: MeshInstance3D = light.get_meta(&"fixture_housing")
		if housing in housings: continue
		housings.append(housing)
		if not _allowed(housing, bounds.end.y, walls): print("UNMOUNTED ", node.name, " ", Surfaces.world_frame(light).origin)
		assert_true(_allowed(housing, bounds.end.y, walls), "%s/%s projects more than 150 mm below ceiling without wall contact" % [node.name, light.name])
	return housings.size()

func _allowed(housing: MeshInstance3D, ceiling_y: float, walls: Array[AABB]) -> bool:
	var box := Surfaces.world_frame(housing) * housing.mesh.get_aabb()
	return box.position.y >= ceiling_y - MAX_CEILING_DROP - 0.000001 or _wall_contact(housing, walls)

func _wall_contact(housing: MeshInstance3D, walls: Array[AABB], frame: Transform3D = Transform3D.IDENTITY) -> bool:
	var pieces: Array = housing.mesh.get_meta(&"service_bounds", [housing.mesh.get_aabb()])
	for piece: AABB in pieces:
		var box := frame * Surfaces.world_frame(housing) * piece
		for wall: AABB in walls:
			if box.grow(CONTACT).intersects(wall): return true
	return false

func _walls(layout: ShipLayout, deck: int) -> Array[AABB]:
	var walls: Array[AABB] = []
	for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(layout, deck):
		if solid.material_role != &"wall": continue
		for box: AABB in SlidingDoorParts.wall_boxes(layout, solid):
			walls.append(solid.transform * box)
	return walls
