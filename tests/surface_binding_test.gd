extends SimTestCase

func _factory() -> GDScript:
	assert_true(ResourceLoader.exists("res://app/surfaces.gd"), "one presentation-owned Surfaces factory exists")
	return load("res://app/surfaces.gd") if ResourceLoader.exists("res://app/surfaces.gd") else null

func test_versioned_utf8_fnv_known_answers() -> void:
	var factory = _factory()
	if factory == null: return
	for vector: Array in [[&"D14-S-041", &"PORT", 1308812220], [&"D01-C-001", &"FLOOR", 4271094197], [&"D14-C-001-H-FORE", &"LEAF", 3777346565], [&"óxido", &"PORT", 3482473891]]:
		assert_int_equal(factory.weather_seed(vector[0], vector[1]), vector[2], "UTF-8 FNV-1a known answer")

func test_recipe_plane_identity_and_deck_relative_coordinates() -> void:
	var factory = _factory()
	if factory == null: return
	var layout := ShipLayout.authored().layout
	var hall := ShipGeometry.hallway_solids(layout)
	var a = factory.frame_for_solid(layout, hall[2])
	var b = factory.frame_for_solid(layout, hall[3])
	assert_true(a.key == &"D14-S-041/PORT" and a.key == b.key, "split port plane deliberately shares weather")
	assert_vec3_equal(a.seed_offset, b.seed_offset, "split plane shares bounded seed offset")
	for deck: int in [1, 14, 30]:
		var id := ShipLayout.connector_id(deck, 1)
		var frame = factory.surface_frame(layout, id, &"PORT")
		var floor_point := Vector3(layout.connector(id).bounds().get_center().x, layout.floor_y(deck), 0)
		assert_float_equal((frame.world_from_surface.affine_inverse() * floor_point).y - frame.floor_datum, 0.0, "grime starts at each deck floor")
		var piece := MeshInstance3D.new()
		piece.mesh = BoxMesh.new()
		factory.bind(piece, &"wall", frame)
		var local: Vector3 = frame.world_from_surface.affine_inverse() * (floor_point + Vector3(0.2, 0.4, 0.5))
		assert_vec3_equal(factory.sample_position(piece, floor_point + Vector3(0.2, 0.4, 0.5)), local, "instance rows reconstruct rigid frame")
		piece.free()

func test_moving_leaf_and_wheel_keep_their_own_weather_without_shared_mutation() -> void:
	var factory = _factory()
	if factory == null: return
	var game := Game.new(91)
	var first := DoorView.build(game.layout.door(&"D14-C-001-H-FORE"))
	var second := DoorView.build(game.layout.door(&"D01-C-001-H-FORE"))
	var leaf: GeometryInstance3D = first.get_node("Hinge/Leaf/ForeSteel")
	var wheel: GeometryInstance3D = first.get_node("Hinge/Leaf/Wheel").get_child(0)
	var other: GeometryInstance3D = second.get_node("Hinge/Leaf/ForeSteel")
	var local := Vector3(0.2, 1.0, 0.01)
	var wheel_local := Vector3(0.15, 0.0, 0.0)
	var initial: Vector3 = factory.sample_position(leaf, factory.world_frame(first.label_leaf()) * local)
	var wheel_initial: Vector3 = factory.sample_position(wheel, factory.world_frame(wheel.get_parent()) * wheel_local)
	var other_row: Vector4 = other.get_instance_shader_parameter(&"surface_x")
	var material := leaf.material_override
	var cache_before: int = factory.cache_size()
	var pose := game.doors.snapshot(first.door_id())
	pose.leaf_fraction = 0.53
	pose.wheel_angle = 149.0
	for index: int in range(20): first.present(pose)
	assert_true(factory.sample_position(leaf, factory.world_frame(first.label_leaf()) * local).is_equal_approx(initial), "leaf scan follows hinge within float32 transform precision")
	assert_true(factory.sample_position(wheel, factory.world_frame(wheel.get_parent()) * wheel_local).is_equal_approx(wheel_initial), "wheel scan follows rotation within float32 transform precision")
	assert_true(other.get_instance_shader_parameter(&"surface_x") == other_row, "another deck's instance rows remain unchanged")
	assert_true(leaf.material_override == material and material == other.material_override, "independent movement shares material")
	assert_int_equal(factory.cache_size(), cache_before, "presentation allocates no materials")
	assert_true(factory.cache_size() <= factory.ROLES.size() + 1, "cache bounded by finite roles, never doors")
	first.free()
	second.free()

func test_all_shell_and_door_consumers_bind_shared_roles() -> void:
	var factory = _factory()
	if factory == null: return
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(10, 0, 0))
	scene.prepare_near(Vector3(26, 0, 0))
	var remote := scene.build_remote(game.layout.connector(&"D30-C-001"))
	for node: Node3D in [scene.room, scene.hallway, scene.power_room, remote]:
		var bound := _bound_count(node, factory)
		assert_true(bound > 0, "consumer has bound architectural surfaces: " + node.name)
	for leaf: Node3D in scene.hallway.side_leaves.values():
		assert_true(leaf.material_override == factory.material(&"hatch_leaf"), "side leaves share hatch role")
		assert_true(leaf.has_meta(&"surface_frame"), "side leaves carry layout identity")
	var power: GeometryInstance3D = scene.power_room.get_node("PowerDoorLeaf")
	var before: Vector3 = factory.sample_position(power, factory.world_frame(power).origin)
	scene.power_room.set_door_offset(Vector3(0.5, 0, 0))
	assert_vec3_equal(factory.sample_position(power, factory.world_frame(power).origin), before, "power leaf scan follows slide")
	root.free()

func _bound_count(node: Node, factory: GDScript) -> int:
	var count := 0
	if node is GeometryInstance3D and node.material_override is ShaderMaterial and node.material_override.shader == factory.material(&"wall").shader:
		assert_true(node.has_meta(&"surface_frame"), "every steel instance has an explicit frame: %s/%s" % [node.get_parent().name, node.name])
		assert_true(node.get_instance_shader_parameter(&"surface_x") is Vector4, "every steel instance supplies inverse rows")
		count += 1
	for child: Node in node.get_children(): count += _bound_count(child, factory)
	return count
