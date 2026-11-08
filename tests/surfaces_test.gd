extends SimTestCase
## Approved Round 5 material contracts, preserving shell/resource/side-effect checks.

func test_required_texture_loss_prevents_construction_without_assertions() -> void:
	var directory := "user://surfaces_missing_resource_%d_%d" % [OS.get_process_id(), Time.get_ticks_usec()]
	assert_int_equal(DirAccess.make_dir_recursive_absolute(directory), OK, "create per-run missing-resource directory")
	var source := FileAccess.get_file_as_string("res://app/surfaces.gd")
	source = source.replace("class_name Surfaces\n", "")
	source = source.replace("res://assets/surfaces/steel/", "res://missing-required-steel/")
	var lines := PackedStringArray()
	for line: String in source.split("\n"):
		lines.append(line.substr(0, line.length() - line.strip_edges().length()) + "pass" if line.strip_edges().begins_with("assert(") else line)
	FileAccess.open(directory + "/factory.gd", FileAccess.WRITE).store_string("\n".join(lines))
	var driver := "extends SceneTree\nfunc _initialize():\n\tvar factory = load(\"%s/factory.gd\")\n\tif factory == null or not factory.can_instantiate():\n\t\tquit(23)\n\t\treturn\n\tvar material = factory.material(&\"wall\")\n\tprint(\"MISSING_RESOURCE_CONSTRUCTION_CONTINUED\", material)\n\tquit(0)\n" % directory
	FileAccess.open(directory + "/driver.gd", FileAccess.WRITE).store_string(driver)
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", ProjectSettings.globalize_path(directory + "/driver.gd")], output, true)
	assert_int_equal(code, 23, "missing required texture stops script construction even with assertions removed")
	for file: String in Surfaces.IMAGES:
		assert_true("".join(output).contains('Preload file "res://missing-required-steel/%s" does not exist.' % file), "failure identifies the missing dependency: " + file)
	assert_false(str(output).contains("MISSING_RESOURCE_CONSTRUCTION_CONTINUED"), "never assign/cache null samplers")
	for file: String in ["factory.gd", "driver.gd"]:
		assert_int_equal(DirAccess.remove_absolute(directory.path_join(file)), OK, "remove generated script: " + file)
	assert_int_equal(DirAccess.remove_absolute(directory), OK, "remove per-run missing-resource directory")

func test_surface_materials_wear_the_approved_shared_scan_maps() -> void:
	for role: StringName in [&"wall", &"floor", &"ceiling"]:
		var material := Surfaces.material(role)
		assert_true(material.shader == Surfaces.STEEL, "approved shader: %s" % role)
		for index: int in range(Surfaces.SCANS.size()):
			var scan := Surfaces.SCANS[index]
			var suffix: String = ["a", "b", "c"][index]
			for kind: String in ["albedo", "normal", "orm"]:
				var file := "r4-%s-albedo.png" % scan if kind == "albedo" else "%s_%s.jpg" % [scan, kind]
				assert_true(material.get_shader_parameter(kind + "_" + suffix) == load(Surfaces.ROOT + file), "exact approved sampler: " + kind + "_" + suffix)
		assert_true(material.get_shader_parameter(&"oxide_grain") == load(Surfaces.ROOT + "r3-rust_coarse_01-albedo.jpg"), "approved oxide grain")
		assert_true(material.get_shader_parameter(&"oxide_normal") == load(Surfaces.ROOT + "r3-rust_coarse_01-normal.jpg"), "approved oxide normal")
		assert_true(material.get_shader_parameter(&"leaf_weather") == preload("res://assets/surfaces/hatch/leaf-weather.png"), "approved leaf weather")
		assert_float_equal(material.get_shader_parameter(&"gain"), 0.19, "approved wall reflectance")
		assert_float_equal(material.get_shader_parameter(&"contrast"), 0.65, "approved wall scan contrast")
		assert_float_equal(material.get_shader_parameter(&"seam_strength"), 0.36, "approved seam strength")

func test_room_shell_swaps_textured_materials_in_place() -> void:
	var room := RoomGeometry.build()
	var shell: Array[Placement.SolidPlacement] = Placement.room_shell()
	assert_int_equal(room.get_child_count(), 6, "six shell boxes only after removing the bay tray presenter")
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
		shell.size(),
		"removing three trays and six hangers leaves only shell meshes"
	)
	assert_false(room.has_node("CeilingDamage"), "no empty tray presenter remains")

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
