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
		assert_true(room.remembered.has_node("Standin_" + item.id), "remembered small item " + item.id)
		assert_true(room.present.has_node("Standin_" + item.id), "present small item " + item.id)
	assert_true(room.remembered.has_node("Placement_wardrobe/Standin_wardrobe"), "wardrobe is explicitly a stand-in carcass")
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
