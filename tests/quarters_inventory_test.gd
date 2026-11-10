extends SimTestCase

func test_both_states_cover_approved_inventory_and_share_placements() -> void:
	var room := QuartersRoom.build(Game.new(0))
	for prop: Dictionary in QuartersInventory.props():
		var clean := room.remembered.get_node("Placement_" + prop.id) as Node3D
		var aged := room.present.get_node("Placement_" + prop.id) as Node3D
		assert_true(clean != null and aged != null, "both states contain " + prop.id)
		assert_true(clean.transform == aged.transform, "shared placement " + prop.id)
		if prop.id == "sofa":
			assert_true(clean.get_child(0).transform == aged.get_child(0).transform, "aged sofa keeps clean source fit, including collapsed mesh")
	for item: Dictionary in QuartersInventory.small_items():
		var prefix := "Standin_" if item.id == "her_jacket" else "Item_"
		assert_true(room.remembered.has_node(prefix + item.id), "remembered small item " + item.id)
		assert_true(room.present.has_node(prefix + item.id), "present small item " + item.id)
	assert_true(room.remembered.has_node("Placement_wardrobe/wardrobe"), "wardrobe uses the accepted carcass")
	assert_true(room.present.has_node("Placement_wardrobe/HangingUniform") and room.present.has_node("Placement_wardrobe/UniformFragments"), "aged hanging uniform and detached fragments")
	for screen: MeshInstance3D in room.screens:
		assert_true(screen.material_override.emission_enabled, "console emissive in both states")
	room.free()

func test_approved_walkways_fit_player_capsule_and_minimum_width() -> void:
	assert_float_equal(Controller.CAPSULE_RADIUS, QuartersInventory.plan().player.capsule_radius, "plan uses production capsule radius")
	var targets: Array = QuartersInventory.plan().reach_targets
	for radius: float in [Controller.CAPSULE_RADIUS, float(QuartersInventory.plan().walkway_min_m) / 2]:
		var reached := _flood(radius)
		for target: Dictionary in targets:
			var point := Vector2(target.point[0], target.point[1])
			var tolerance := 0.035 if radius == Controller.CAPSULE_RADIUS else 0.35
			var found := false
			for key: Vector2i in reached:
				if (Vector2(key) * 0.05).distance_to(point) <= tolerance:
					found = true
					break
			assert_true(found, "walkway reaches %s with radius %.2f" % [target.id, radius])

func test_every_prop_has_one_shared_collider_not_one_per_state() -> void:
	var layout := ShipLayout.authored().layout
	var ids := ShipCollision.new(layout).solid_ids(16)
	for prop: Dictionary in QuartersInventory.props():
		assert_int_equal(ids.count(StringName("D16-QUARTERS/PROP/" + prop.id)), 1, "one furniture collider " + prop.id)
	for item: Dictionary in QuartersInventory.small_items():
		assert_int_equal(ids.count(StringName("D16-QUARTERS/ITEM/" + item.id)), 1, "one small item collider " + item.id)

func test_present_fibre_dust_and_fragments_rest_on_wardrobe_shelf() -> void:
	var furnishings := QuartersFurnishings.build(&"aged")
	var wardrobe := furnishings.get_node("Placement_wardrobe")
	var shelf: MeshInstance3D = wardrobe.get_node("wardrobe").find_child("BottomPanel", true, false)
	var floor_bounds := ShipScene._world_frame(shelf) * shelf.get_aabb()
	var fragments := wardrobe.get_node("UniformFragments")
	var bottom := INF
	var found_dust := false
	for piece: MeshInstance3D in fragments.find_children("*", "MeshInstance3D", true, false):
		if not piece.visible: continue
		var bounds := ShipScene._world_frame(piece) * piece.get_aabb()
		bottom = minf(bottom, bounds.position.y)
		assert_true(bounds.position.y >= floor_bounds.end.y - 0.00001, "no debris clips below the shelf")
		assert_true(bounds.position.x >= floor_bounds.position.x and bounds.end.x <= floor_bounds.end.x, "debris fits shelf width")
		assert_true(bounds.position.z >= floor_bounds.position.z and bounds.end.z <= floor_bounds.end.z, "debris fits shelf depth")
		if piece.name == &"FibreDust":
			found_dust = true
			assert_float_in_range(bounds.position.y - floor_bounds.end.y, 0.0, 0.001, "fibre-dust heap rests within 1 mm of wardrobe floor")
	assert_true(found_dust, "pale patch is the named fibre-dust mesh")
	assert_float_in_range(bottom - floor_bounds.end.y, 0.0, 0.001, "fragment group is seated, not floating")
	furnishings.free()

func _flood(radius: float) -> Dictionary:
	var obstacles: Array[AABB] = []
	for solid: ShipGeometry.SolidSpec in QuartersGeometry.furniture():
		if solid.center.y - solid.size.y / 2 >= QuartersLayout.FLOOR_Y + Controller.CAPSULE_STANDING_HEIGHT: continue
		var local := QuartersLayout.from_world(solid.center)
		obstacles.append(AABB(local - solid.size / 2, solid.size))
	var start := Vector2i(80, ceili(maxf(0.35, radius + 0.01) / 0.05))
	var queue: Array[Vector2i] = [start]
	var reached := {start: true}
	var visited := {start: true}
	var index := 0
	while index < queue.size():
		var key := queue[index]
		index += 1
		for offset: Vector2i in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
			var next := key + offset
			if visited.has(next): continue
			visited[next] = true
			var point := Vector2(next) * 0.05
			if point.x < radius or point.x > 8 - radius or point.y < radius or point.y > 6 - radius: continue
			var free := true
			for box: AABB in obstacles:
				var nearest := Vector2(clampf(point.x, box.position.x, box.end.x), clampf(point.y, box.position.z, box.end.z))
				if nearest.distance_squared_to(point) < radius * radius:
					free = false
					break
			if free:
				reached[next] = true
				queue.append(next)
	return reached
