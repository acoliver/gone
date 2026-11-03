extends SimTestCase
## Approved Round 5 material contracts, preserving shell/resource/side-effect checks.

func test_surface_materials_wear_the_approved_shared_scan_maps() -> void:
	for role: StringName in [&"wall", &"floor", &"ceiling"]:
		var material := Surfaces.material(role)
		assert_true(material.shader == Surfaces.STEEL, "approved shader: %s" % role)
		for suffix: String in ["a", "b", "c"]:
			for kind: String in ["albedo", "normal", "orm"]:
				assert_true(material.get_shader_parameter(kind + "_" + suffix) is Texture2D, "imported scan channel")
		assert_float_equal(material.get_shader_parameter(&"gain"), 0.19, "approved wall reflectance")
		assert_float_equal(material.get_shader_parameter(&"contrast"), 0.65, "approved wall scan contrast")
		assert_float_equal(material.get_shader_parameter(&"seam_strength"), 0.36, "approved seam strength")

func test_room_shell_swaps_textured_materials_in_place() -> void:
	var room := RoomGeometry.build()
	var shell: Array[Placement.SolidPlacement] = Placement.room_shell()
	assert_int_equal(room.get_child_count(), 7, "six shell boxes plus the ceiling damage group")
	for index: int in range(shell.size()):
		var box: MeshInstance3D = room.get_child(index)
		var expected := RoomGeometry.wall_material()
		if index == 0:
			expected = RoomGeometry.floor_material()
		elif index == 1:
			expected = RoomGeometry.ceiling_material()
		assert_true(
			box.material_override == expected,
			"shell box %d swaps in its surface material by reference" % index
		)
	assert_true(
		RoomGeometry.floor_material() != RoomGeometry.wall_material()
			and RoomGeometry.wall_material() != RoomGeometry.ceiling_material()
			and RoomGeometry.ceiling_material() != RoomGeometry.floor_material(),
		"each surface owns one distinct material instance"
	)
	assert_int_equal(
		_count_instances(room, MeshInstance3D),
		shell.size() + Placement.cable_trays().size() + Placement.wire_loops().size(),
		"the pass swaps materials in place; no meshes are added"
	)
	var damage := room.get_child(shell.size())
	for child: Node in damage.get_children():
		var dressing: MeshInstance3D = child
		assert_true(
			dressing.material_override is StandardMaterial3D
				and dressing.material_override.albedo_texture == null,
			"tray and wire dressing keeps its flat grey material"
		)

	room.free()

func test_surface_local_mapping_and_panel_pitch_are_pinned() -> void:
	for role: StringName in [&"floor", &"wall", &"ceiling"]:
		assert_true(Surfaces.material(role).get_shader_parameter(&"panel_pitch") == Vector2(1.5, 1.0), "one 1.5 x 1.0 m panel pitch")
	var room := RoomGeometry.build()
	for index: int in range(6):
		var piece: GeometryInstance3D = room.get_child(index)
		assert_true(piece.has_meta(&"surface_frame"), "shell has explicit local coordinates")
		assert_true(piece.get_instance_shader_parameter(&"surface_x") is Vector4, "inverse coordinate rows are instance data")
	room.free()

func test_two_builds_yield_identical_material_references_and_params() -> void:
	var first := RoomGeometry.build()
	var second := RoomGeometry.build()
	for slot: int in range(6):
		var a: ShaderMaterial = first.get_child(slot).material_override
		var b: ShaderMaterial = second.get_child(slot).material_override
		assert_true(a == b, "both builds share cached material")
		for kind: String in ["albedo", "normal", "orm"]:
			for suffix: String in ["a", "b", "c"]:
				assert_true(a.get_shader_parameter(kind + "_" + suffix) == b.get_shader_parameter(kind + "_" + suffix), "scan resources never reload across builds")
	first.free()
	second.free()

func test_room_geometry_adds_no_lights_or_colliders() -> void:
	var room := RoomGeometry.build()
	assert_int_equal(
		_count_instances(room, Light3D),
		0,
		"the texture pass introduces no light of any kind"
	)
	assert_int_equal(
		_count_instances(room, CollisionShape3D),
		0,
		"the texture pass introduces no colliders"
	)

	room.free()

func _count_instances(node: Node, native_type: Variant) -> int:
	var total := 0
	if is_instance_of(node, native_type):
		total += 1
	for child: Node in node.get_children():
		total += _count_instances(child, native_type)
	return total
