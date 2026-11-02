extends SimTestCase

func test_d14_topology_and_exact_openability() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(layout.deck(14).section_ids() == [&"D14-S-040", &"D14-S-041", &"D14-S-042"], "three ordered sections")
	for fixture: Vector3 in [Vector3(40, -24, 0), Vector3(41, 6, 30), Vector3(42, 36, 60)]:
		var section := layout.section(ShipLayout.section_id(14, int(fixture.x)))
		assert_float_equal(section.bounds().position.x, fixture.y, "independent fore bound")
		assert_float_equal(section.bounds().end.x, fixture.z, "independent aft bound")
		assert_int_equal(section.side_door_ids().size(), 5 if fixture.x == 41 else 6, "exact side leaf count")
		for id: StringName in section.side_door_ids():
			assert_int_equal(layout.door(id).policy(), ShipLayout.Policy.NEVER_OPENS, "side leaf refuses")
	var cranks: Array[StringName] = []
	for id: StringName in layout.door_ids():
		if layout.door(id).policy() == ShipLayout.Policy.CRANK:
			cranks.append(id)
	assert_true(cranks == [&"D14-C-000-H-AFT", &"D14-C-000-H-FORE", &"D14-C-001-H-AFT", &"D14-C-001-H-FORE"], "only four inner hatches crank")

func test_section_41_endcaps_are_replaced_by_owned_portal_solids() -> void:
	var game := Game.new(0)
	for x: float in [6, 30]:
		var probe := ColliderSet.Aabb.try_new(Vector3(x + 0.1, 1.2, 0), Vector3(0.04, 0.4, 0.2)).box
		var owners: Array[StringName] = []
		for solid: ShipGeometry.SolidSpec in ShipCollision.opening_solids(game.registry, false, false, game.layout):
			if ShipGeometry.box_aabb(solid).overlaps(probe):
				owners.append(solid.id)
		assert_true(owners == ([&"D14-C-000-H-AFT/BLOCKER", &"D14-C-000-H-AFT/SWING"] if x == 6 else [&"D14-C-001-H-FORE/BLOCKER", &"D14-C-001-H-FORE/SWING"]), "aperture contains only the named hatch blockers, no old endcap: %s" % [owners])

func test_new_geometry_contains_landings_and_no_duplicate_power_wall() -> void:
	var layout := ShipLayout.authored().layout
	var solids := ShipGeometry.deck_static_solids(layout, 14)
	var shared_hits := 0
	var probe := Vector3(31.0, 1.2, -1.6)
	for solid: ShipGeometry.SolidSpec in solids:
		var box := ShipGeometry.box_aabb(solid)
		if AABB(box.min_corner(), box.max_corner() - box.min_corner()).has_point(probe):
			shared_hits += 1
	assert_int_equal(shared_hits, 1, "power south wall has exactly one owner")
	var set := ShipCollision.new(layout).deck_set(14)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(34.5, 0.417, -0.8)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var result := Resolve.resolve_motion(capsule, Vector3(0, 0, -2.1), set)
	assert_true(result.is_ok(), "aft landing approach is valid")
	assert_close(result.motion.displacement, Vector3(0, 0, -2.1), "open port doorway clears unchanged power wall")
	var ids := ShipCollision.new(layout).solid_ids(14)
	assert_true(&"D14-C-001/LANDING/PORT/000" in ids and &"D14-C-000/LANDING/PORT/000" in ids, "both landing side walls exist")

func test_real_scene_has_shared_hatch_details_and_lazy_red_rooms() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	var hatches: Array[DoorView] = []
	for view: DoorView in scene.door_views:
		if game.layout.door(view.door_id()).kind() == ShipLayout.DoorKind.HATCH:
			hatches.append(view)
	assert_int_equal(hatches.size(), 2, "opening contains only its two boundary hatch views")
	for view: DoorView in hatches:
		for path: String in ["Frame", "Coaming", "Hinge/Leaf", "Hinge/Wheel", "Hinge/ReverseWheel", "Hinges", "Hinge/Lugs", "ForePanel/Button", "ForePanel/CardReader", "AftPanel/Button", "AftPanel/CardReader"]:
			assert_true(view.has_node(NodePath(path)), "shared hatch detail: " + path)
	root.free()

func test_four_open_hatches_allow_both_directions_and_locked_faces_contain() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for id: StringName in [&"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		collision.open_door(id)
	var set := collision.deck_set(14)
	for x: float in [0, 6, 30, 36]:
		for direction: float in [-1, 1]:
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(x - direction * 1.7, 0.417, 0)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var delta := Vector3(direction * 3.4, 0, 0)
			var result := Resolve.resolve_motion(capsule, delta, set)
			assert_true(result.is_ok(), "complete horizontal sweep accepted")
			assert_close(result.motion.displacement, delta, "open hatch traversed from both directions")
	for fixture: Vector3 in [Vector3(-22, 0, 0), Vector3(58, 0, 0), Vector3(39, 0, 0), Vector3(33, 0, 0)]:
		var capsule := Resolve.Capsule.new()
		capsule.foot = fixture + Vector3.UP * 0.417
		capsule.head = capsule.foot + Vector3.UP * 1.15
		var delta := Vector3(-4, 0, 0) if fixture.x < 0 else (Vector3(4, 0, 0) if fixture.x == 58 else Vector3(0, 0, 3))
		var result := Resolve.resolve_motion(capsule, delta, set)
		assert_true(result.is_ok(), "locked-door containment sweep accepted")
		assert_true(result.motion.displacement.length() < delta.length(), "side, lift and boundary doors contain")

func test_prefetch_and_independent_red_light_masks() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	for x: float in [18, 25.9]:
		scene.prepare_near(Vector3(x, 0, 0))
		assert_false(root.has_node("D14-C-001"), "no connector construction before final four meters")
	scene.prepare_near(Vector3(26, 0, 0))
	assert_true(root.has_node("D14-C-001") and root.has_node("D14-S-042"), "aft rooms ready before exposure")
	assert_false(root.has_node("D14-C-000"), "fore room is not prebuilt")
	var count := root.get_child_count()
	scene.prepare_near(Vector3(34, 0, 0))
	assert_int_equal(root.get_child_count(), count, "no duplicate rooms or portal owners")
	game.power_active = true
	var lights: Array[OmniLight3D] = []
	_collect_lights(root.get_node("D14-C-001"), lights)
	assert_int_equal(lights.size(), 3, "connector and landing have three steady fixtures")
	for light: OmniLight3D in lights:
		assert_int_equal(light.light_cull_mask, 16, "isolated aft connector mask")
		assert_float_in_range(light.light_energy, Lighting.FIXTURE_ENERGY - 1e-5, Lighting.FIXTURE_ENERGY + 1e-5, "red independent of power activation")
		assert_true(light.light_color == Lighting.EMERGENCY_RED, "steady emergency red")
		assert_true(light.omni_range <= 3, "local fixture range")
	scene.prepare_near(Vector3(10, 0, 0))
	assert_true(root.has_node("D14-C-000") and root.has_node("D14-S-040"), "fore rooms prepare at their own threshold")
	var hatches := 0
	for view: DoorView in scene.door_views:
		if game.layout.door(view.door_id()).kind() == ShipLayout.DoorKind.HATCH:
			hatches += 1
	assert_int_equal(hatches, 6, "four crank and two boundary views")
	root.free()

func test_hatch_projects_model_wheel_and_leaf_without_advancing_them() -> void:
	var layout := ShipLayout.authored().layout
	var id: StringName = &"D14-C-001-H-FORE"
	var view := DoorView.build(layout.door(id), 1, 16)
	var store := Doors.Store.new(layout, 0)
	var context := Doors.Context.new()
	context.face_id = layout.door(id).face_ids()[0]
	for _attempt: int in range(HatchResistance.schedule(0, id).weights.size()):
		store.press(id, context)
		for _tick: int in range(6):
			store.tick()
			var snapshot := store.snapshot(id)
			view.present(snapshot)
			assert_float_in_range(view.get_node("Hinge/Wheel").rotation.z, deg_to_rad(snapshot.wheel_angle + snapshot.refusal_offset) - 1e-5, deg_to_rad(snapshot.wheel_angle + snapshot.refusal_offset) + 1e-5, "exact model wheel interpolation")
	for _tick: int in range(48):
		store.tick()
		view.present(store.snapshot(id))
	assert_float_in_range(view.get_node("Hinge").rotation.y, -PI / 2 - 1e-5, -PI / 2 + 1e-5, "leaf swings into connector")
	var before := store.snapshot(id).wheel_angle
	view.present(store.snapshot(id))
	assert_float_equal(store.snapshot(id).wheel_angle, before, "presentation never advances model")
	view.free()

func _collect_lights(node: Node, lights: Array[OmniLight3D]) -> void:
	if node is OmniLight3D:
		lights.append(node)
	for child: Node in node.get_children():
		_collect_lights(child, lights)
