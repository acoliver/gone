extends SimTestCase

func test_exact_quarter_turn_aabb_uses_unexpanded_corners() -> void:
	var solid := ShipGeometry.SolidSpec.new(Vector3(1, 2, 3), Vector3(2, 4, 6))
	var frame := Transform3D(Basis(Vector3(0, 0, -1), Vector3.UP, Vector3.RIGHT), Vector3(15, 0, 7.7))
	var box := ShipGeometry.box_aabb(solid, frame)
	assert_vec3_equal(box.center(), Vector3(18, 2, 6.7), "transformed center")
	assert_vec3_equal(box.half_extents(), Vector3(3, 2, 1), "one exact quarter turn")
	var tipped := ShipGeometry.SolidSpec.new(Vector3.ZERO, Vector3(2, 2, 4), Quaternion(Vector3.UP, PI / 4))
	var hull := ShipGeometry.box_aabb(tipped)
	assert_close(hull.half_extents(), Vector3(2.1213203, 1, 2.1213203), "eight-corner hull")

func test_wall_split_tiles_one_shared_wall_without_aperture_solids() -> void:
	var frame := Transform3D(Basis(), Vector3(27, 0, -1.5))
	var pieces := ShipGeometry.portal_wall(&"shared", frame, Vector2(-6, 6), 3.2, Vector2(1, 2.2))
	assert_int_equal(pieces.size(), 3, "two sides and a lintel")
	assert_vec3_equal(pieces[0].center, Vector3(23.75, 1.6, -1.4), "west interval")
	assert_vec3_equal(pieces[1].center, Vector3(30.25, 1.6, -1.4), "east interval")
	assert_vec3_equal(pieces[2].center, Vector3(27, 2.7, -1.4), "lintel")
	var volume := 0.0
	var ids: Array[StringName] = []
	for piece: ShipGeometry.SolidSpec in pieces:
		volume += piece.size.x * piece.size.y * piece.size.z
		ids.append(piece.id)
	assert_float_in_range(volume, 7.24 - 1e-5, 7.24 + 1e-5, "whole wall minus aperture")
	assert_true(ids == [&"shared/000", &"shared/001", &"shared/002"], "stable local piece order")

func test_extracted_opening_recipes_match_presentation_placements() -> void:
	_assert_solids(ShipGeometry.room_shell(), Placement.room_shell(), "bay shell")
	_assert_solids(ShipGeometry.hatch_solids(), Placement.hatch_solids(), "bay hatch")
	_assert_solids(ShipGeometry.hallway_solids(), Hallway.hallway_solids(), "hall shell")
	_assert_solids(ShipGeometry.doorway_wall_solids(), Hallway.doorway_wall_solids(), "bay pierce")
	_assert_solids(ShipGeometry.power_room_solids(), PowerRoom.room_solids(), "power shell")
	assert_int_equal(ShipGeometry.hallway_solids().size(), 8, "eight hall slabs; rounded openings no longer add corner filler solids")
	assert_int_equal(ShipGeometry.power_room_solids().size(), 5, "five power pieces; hall owns the shared south wall")
	assert_vec3_equal(ShipGeometry.power_doorway_wall_solids()[1].center, Vector3(30.35, 1.6, -1.6), "shared power wall reaches X=33.2")
	assert_vec3_equal(ShipGeometry.generator_solid().size, Vector3(1.6, 2.6, 1.6), "generator hull")
	for index: int in range(6):
		var actual := ShipGeometry.console_solid(ShipGeometry.console_stations()[index])
		var rendered := PowerRoom.console_solid(PowerRoom.console_stations()[index])
		assert_vec3_equal(actual.center, rendered.center, "console hull center")
		assert_vec3_equal(actual.size, rendered.size, "console hull extent")

func test_pod_geometry_preserves_cavity_tray_and_top_recipes() -> void:
	assert_float_equal(PodGeometry.TRAY_FLOOR_Y, 0.240, "new pod #88 couch plateau")
	assert_int_equal(PodGeometry.cavity_solids().size(), 5, "five cavity pieces")
	assert_vec3_equal(PodGeometry.cavity_solids()[0].size, Vector3(0.55, 0.228, 1.9), "base slab")
	for state: int in [Pods.PodState.PLAYER, Pods.PodState.EMPTY_OPEN, Pods.PodState.SEALED]:
		var pure := PodGeometry.pod_solids(state)
		var adapter := PodBody.pod_solids(state)
		assert_int_equal(pure.size(), adapter.size(), "pod piece count")
		for index: int in range(pure.size()):
			assert_vec3_equal(pure[index].center, adapter[index].center, "pod local center")
			assert_vec3_equal(pure[index].size, adapter[index].size, "pod full size")
			assert_float_equal(pure[index].roll_radians, adapter[index].roll_radians, "pod local roll")

func test_shared_scene_seam_preserves_structure_and_identity_frame() -> void:
	var production := Node3D.new()
	var harness := Node3D.new()
	var main_scene := ShipScene.build_into(production, Game.new(0), true)
	var harness_scene := ShipScene.build_into(harness, Game.new(0), false)
	for node_name: String in ["RoomGeometry", "StasisPods", "Hatch", "Lighting", "Hazards", "Rod", "Hallway", "PowerRoom"]:
		assert_true(production.has_node(NodePath(node_name if node_name in ["Hallway", "PowerRoom"] else "BayRoot/" + node_name)), "production structural node: " + node_name)
		assert_true(harness.has_node(NodePath(node_name if node_name in ["Hallway", "PowerRoom"] else "BayRoot/" + node_name)), "harness structural node: " + node_name)
	assert_true(main_scene.pods_node.transform == Transform3D.IDENTITY, "pods stay local")
	assert_true(main_scene.bay_root.transform == ShipLayout.authored().layout.bay_to_world(), "single bay frame")
	assert_true(production.has_node("RoomEnvironment"), "one root environment")
	assert_true(main_scene.hallway.transform == harness_scene.hallway.transform, "same hallway frame")
	assert_true(production.has_node("BayRoot/HangingWires"), "production keeps wires")
	assert_false(harness.has_node("BayRoot/HangingWires"), "audio-free harness keeps existing dressing policy")
	assert_true(main_scene.power_room == production.get_node("PowerRoom"), "typed handles point to common tree")
	production.free()
	harness.free()

func test_surface_roles_travel_with_the_pure_recipe() -> void:
	for solids: Array[ShipGeometry.SolidSpec] in [ShipGeometry.room_shell(), ShipGeometry.hallway_solids(), ShipGeometry.power_room_solids()]:
		assert_true(solids[0].material_role == &"floor", "floor role is placement data")
		assert_true(solids[1].material_role == &"ceiling", "ceiling role is placement data")
		assert_true(solids[2].material_role == &"wall", "wall role is placement data")
		assert_true(solids[0].collision_role == &"static", "static collision role")
	var blocker := ShipGeometry.door_blockers(ShipLayout.authored().layout.door(&"D14-C-000-H-FORE"))[0]
	assert_true(blocker.material_role == &"door" and blocker.collision_role == &"door_blocker", "door blocker roles")

func _assert_solids(actual: Array[ShipGeometry.SolidSpec], expected: Array[ShipGeometry.SolidSpec], context: String) -> void:
	assert_int_equal(actual.size(), expected.size(), context + " count")
	for index: int in range(actual.size()):
		assert_vec3_equal(actual[index].center, expected[index].center, context + " center")
		assert_vec3_equal(actual[index].size, expected[index].size, context + " size")
		assert_true(actual[index].rotation == expected[index].rotation, context + " rotation")

func test_lid_collision_slabs_follow_the_same_hidden_pivot() -> void:
	# New pod #88: independent closed section centers and sizes, not
	# expectations obtained by calling the production recipe.
	var pivot := Vector3(0, 0.437, -1.17250931263)
	var centers: Array[Vector3] = [Vector3(0, 0.73, -0.79), Vector3(0, 0.84, 0), Vector3(0, 0.73, 0.79)]
	var sizes: Array[Vector3] = [Vector3(0.40, 0.04, 0.38), Vector3(0.64, 0.10, 1.2), Vector3(0.40, 0.04, 0.38)]
	# #88: the seam hinge's rear sweep and 2.5 m walkway limit both open states.
	for state: int in [Pods.PodState.SEALED, Pods.PodState.EMPTY_OPEN, Pods.PodState.PLAYER]:
		var angle: float = {Pods.PodState.SEALED: 0.0, Pods.PodState.EMPTY_OPEN: deg_to_rad(-67.7295), Pods.PodState.PLAYER: deg_to_rad(-67.7295)}[state]
		var expected_centers := centers
		var expected_sizes := sizes
		if state == Pods.PodState.PLAYER:
			# #88: upper-panel proxies leave the conservative body sweep open below the lid.
			expected_centers = [Vector3(0, 0.84, 0.225), Vector3(0, 0.84, 0.45), Vector3(0, 0.73, 0.79)]
			expected_sizes = [Vector3(0.64, 0.10, 0.15), Vector3(0.64, 0.10, 0.15), Vector3(0.40, 0.04, 0.38)]
		var solids := PodGeometry.pod_solids(state)
		assert_int_equal(solids.size(), 8, "five tray pieces plus three articulated lid slabs")
		for section: int in range(3):
			var solid := solids[5 + section]
			assert_close(solid.center, pivot + Basis(Vector3.RIGHT, angle) * (expected_centers[section] - pivot), "rotated section")
			assert_vec3_equal(solid.size, expected_sizes[section], "section size")
			assert_float_equal(solid.roll_radians, angle, "lid rotation")
