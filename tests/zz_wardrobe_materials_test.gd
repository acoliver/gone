extends SimTestCase
## Keep the per-face wardrobe reference stable for matched library comparisons.

func test_wardrobe_states_are_built_cached_and_isolated_from_pilots() -> void:
	var before := QuartersProps.cache_size()
	var clean: ShaderMaterial = QuartersProps._wardrobe_material(&"as_built")
	var aged: ShaderMaterial = QuartersProps._wardrobe_material(&"aged")
	assert_true(clean != aged, "distinct wardrobe states")
	assert_true(clean == QuartersProps._wardrobe_material(&"as_built"), "clean is shared")
	assert_true(aged == QuartersProps._wardrobe_material(&"aged"), "aged is shared")
	assert_true(QuartersProps.cache_size() <= before + 2, "only two wardrobe resources")
	assert_false(clean.get_shader_parameter(&"aged_finish"), "clean recipe")
	assert_true(aged.get_shader_parameter(&"aged_finish"), "aged recipe")
	assert_true(aged.shader != QuartersProps.material(&"storage_locker_module", &"aged").shader, "pilot shader is unchanged")
	var atlas: Texture2D = aged.get_shader_parameter(&"face_albedo")
	assert_true(atlas != null and atlas.get_size() == Vector2(2048, 4096), "per-face atlas is built")
	assert_true(atlas.resource_path.begins_with("res://assets/props/quarters/wardrobe_"), "wardrobe owns its atlas")
	var diagnostic := aged.duplicate() as ShaderMaterial
	diagnostic.set_shader_parameter(&"diagnostic", 2)
	assert_int_equal(aged.get_shader_parameter(&"diagnostic"), 0, "preview controls never change the runtime material")

func test_every_wardrobe_slot_swaps_without_mesh_or_pose_changes() -> void:
	var model := (load("res://assets/props/quarters/wardrobe.glb") as PackedScene).instantiate()
	var parts := model.find_children("*", "MeshInstance3D", true, false)
	assert_true(parts.size() > 40, "exercise panels, rail, hinges, vents and fasteners")
	QuartersProps._apply_wardrobe(model, &"as_built")
	for part: MeshInstance3D in parts:
		var mesh := part.mesh
		var pose := part.transform
		var bounds := part.get_aabb()
		assert_true(part.material_override == QuartersProps._wardrobe_material(&"as_built"), "all clean slots replaced")
		QuartersProps._apply_wardrobe(model, &"aged")
		assert_true(part.material_override == QuartersProps._wardrobe_material(&"aged"), "all aged slots replaced")
		assert_true(part.mesh == mesh and part.transform == pose and part.get_aabb() == bounds, "state does not change fitted geometry")
		QuartersProps._apply_wardrobe(model, &"as_built")
	model.free()

func test_door_sides_use_independent_images_and_hardware_has_physical_pitch() -> void:
	var model := (load("res://assets/props/quarters/wardrobe.glb") as PackedScene).instantiate()
	QuartersProps._apply_wardrobe(model, &"aged")
	var door := model.find_child("Door", true, false) as MeshInstance3D
	assert_true(door.get_instance_shader_parameter(&"face_front") != door.get_instance_shader_parameter(&"face_back"), "inner and outer door have independent images")
	for name: String in ["SidePanel_L", "SidePanel_R", "TopPanel"]:
		var piece := model.find_child(name, true, false) as MeshInstance3D
		assert_true(piece.get_instance_shader_parameter(&"face_front") != piece.get_instance_shader_parameter(&"face_back"), "visible inner and outer faces are independent: " + name)
	for name: String in ["Rail", "Hinges", "DoorLatch", "CarcassRivets"]:
		var part := model.find_child(name, true, false) as MeshInstance3D
		var projection: Vector4 = part.get_instance_shader_parameter(&"projection")
		assert_true(projection.w == 2, "bare hardware retains its steel class: " + name)
	for name: String in ["KickPlate", "DoorLatchPocket", "InnerLatchPocket"]:
		var part := model.find_child(name, true, false) as MeshInstance3D
		var projection: Vector4 = part.get_instance_shader_parameter(&"projection")
		assert_true(projection.w == 3, "dark trim retains its separate steel class: " + name)
	assert_true("metres / .2" in QuartersProps._wardrobe_material(&"aged").shader.code, "hardware pitch is 0.2 m on both axes")
	model.free()

func test_wardrobe_packed_imports_preserve_colour_and_minification() -> void:
	for image: String in ["aged_albedo", "aged_normal", "aged_orm", "as_built_paint"]:
		var settings := ConfigFile.new()
		assert_int_equal(settings.load("res://assets/props/quarters/wardrobe_%s.png.import" % image), OK, "explicit import settings")
		assert_false(settings.get_value("params", "process/fix_alpha_border"), "packed oxide alpha cannot overwrite RGB")
		assert_true(settings.get_value("params", "mipmaps/generate"), "distance views use mipmaps")
