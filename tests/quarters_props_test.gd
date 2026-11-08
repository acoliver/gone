extends SimTestCase

func test_generated_face_atlas_is_direct_and_has_no_analytic_trails() -> void:
	var factory := _factory()
	if factory == null: return
	var aged: ShaderMaterial = factory.material(&"storage_locker_module", &"aged")
	var clean: ShaderMaterial = factory.material(&"storage_locker_module", &"as_built")
	var atlas: Texture2D = aged.get_shader_parameter(&"face_albedo")
	assert_true(atlas != null and atlas.get_width() == 2048 and atlas.get_height() == 4096, "full face atlas")
	assert_true(aged.get_shader_parameter(&"aged_finish"), "aged state selects generated face colour")
	assert_false(clean.get_shader_parameter(&"aged_finish"), "as-built stays on its original atlas")
	assert_false("gravity_trails" in aged.shader.code, "analytic streak pattern is removed")
	assert_false("oxide_field" in aged.shader.code, "procedural colour-boundary reconstruction is removed")

func test_dust_controls_do_not_mutate_cached_materials() -> void:
	var factory := _factory()
	if factory == null: return
	var aged: ShaderMaterial = factory.material(&"storage_locker_module", &"aged")
	var control := aged.duplicate() as ShaderMaterial
	control.set_shader_parameter(&"dust_enabled", false)
	assert_false(control.get_shader_parameter(&"dust_enabled"), "control disables dust")
	assert_true(aged.get_shader_parameter(&"dust_enabled"), "runtime cache keeps visible dust")
	assert_true(aged.get_shader_parameter(&"region_masks") is Texture2D, "capture masks are exported dependencies")

func test_diagnostic_copies_do_not_contaminate_runtime_cache() -> void:
	var factory := _factory()
	if factory == null: return
	var clean: ShaderMaterial = factory.material(&"storage_locker_module", &"as_built")
	var control := clean.duplicate() as ShaderMaterial
	control.set_shader_parameter(&"diagnostic", 5)
	control.set_shader_parameter(&"diagnostic_door", true)
	assert_int_equal(clean.get_shader_parameter(&"diagnostic"), 0, "runtime shader stays lit")
	assert_false(clean.get_shader_parameter(&"diagnostic_door"), "door ID stays preview-only")

func test_packed_atlases_preserve_colour_independent_of_alpha() -> void:
	for state: String in ["as_built", "aged"]:
		for kind: String in ["albedo", "normal", "orm"]:
			var path := "res://assets/props/quarters/storage_locker_module/%s_%s.png.import" % [state, kind]
			var settings := ConfigFile.new()
			assert_int_equal(settings.load(path), OK, "atlas has explicit import settings")
			assert_false(settings.get_value("params", "process/fix_alpha_border"), "alpha is packed data, never transparency")
			assert_true(settings.get_value("params", "mipmaps/generate"), "atlas has minification mipmaps")

func _factory() -> GDScript:
	assert_true(ResourceLoader.exists("res://app/quarters_props.gd"), "quarters material factory exists")
	return load("res://app/quarters_props.gd") if ResourceLoader.exists("res://app/quarters_props.gd") else null

func test_two_finishes_are_cached_and_distinct() -> void:
	var factory := _factory()
	if factory == null: return
	var clean: ShaderMaterial = factory.material(&"storage_locker_module", &"as_built")
	var aged: ShaderMaterial = factory.material(&"storage_locker_module", &"aged")
	assert_true(clean != aged, "states have distinct material resources")
	for state: StringName in [&"as_built", &"aged"]:
		var first: ShaderMaterial = factory.material(&"storage_locker_module", state)
		assert_true(first == factory.material(&"storage_locker_module", state), "cache shares each finish")
		for kind: String in ["albedo", "normal", "orm"]:
			var texture: Texture2D = first.get_shader_parameter("baked_" + kind)
			assert_true(texture != null and texture.get_width() == 2048, "full baked atlas: " + kind)
			assert_true(clean.get_shader_parameter("baked_" + kind) != aged.get_shader_parameter("baked_" + kind), "state atlases differ: " + kind)
	assert_int_equal(factory.cache_size(), 2, "one material per prop and state")

func test_state_swap_preserves_shared_mesh_pivots_names_and_footprint() -> void:
	var factory := _factory()
	if factory == null: return
	var scene: PackedScene = load("res://assets/props/quarters/storage_locker_module.glb")
	var first: Node3D = scene.instantiate()
	var second: Node3D = scene.instantiate()
	factory.apply(first, &"storage_locker_module", &"as_built")
	factory.apply(second, &"storage_locker_module", &"aged")
	_compare_parts(first, second)
	var meshes := first.find_children("*", "MeshInstance3D", true, false)
	for node: Node in meshes:
		var piece := node as MeshInstance3D
		var original := piece.mesh
		var pose := piece.transform
		for index: int in range(10):
			factory.apply(first, &"storage_locker_module", &"aged" if index % 2 == 0 else &"as_built")
		assert_true(piece.mesh == original and piece.transform == pose, "state swap never mutates geometry")
	assert_true(meshes.size() > 10, "all named locker parts are exercised")
	assert_int_equal(factory.cache_size(), 2, "swaps allocate no additional materials")
	first.free()
	second.free()

func _compare_parts(a: Node, b: Node) -> void:
	assert_true(a.name == b.name, "part names identical")
	assert_int_equal(a.get_child_count(), b.get_child_count(), "same hierarchy")
	if a is Node3D:
		assert_true(a.transform == b.transform, "same local origins and pivots")
	if a is MeshInstance3D:
		assert_true(a.mesh == b.mesh, "one shared mesh resource")
		assert_true(a.get_aabb() == b.get_aabb(), "same footprint")
		assert_true(a.material_override != b.material_override, "all surfaces swap finish")
	for index: int in range(a.get_child_count()):
		_compare_parts(a.get_child(index), b.get_child(index))

func test_hardware_swatch_has_equal_physical_pitch_on_both_axes() -> void:
	var root := (load("res://assets/props/quarters/storage_locker_module.glb") as PackedScene).instantiate()
	QuartersProps.apply(root, &"storage_locker_module", &"aged")
	for part: String in ["Handle", "Rivets", "DoorVents"]:
		var piece := root.find_child(part, true, false) as MeshInstance3D
		var size: Vector4 = piece.get_instance_shader_parameter(&"face_size")
		assert_true(is_equal_approx(size.x, .2) and is_equal_approx(size.y, .2), "hardware image keeps a 0.2 m square physical pitch: " + part)
	root.free()

func test_aged_face_rectangles_and_hardware_mapping_are_explicit() -> void:
	var factory := _factory()
	if factory == null: return
	var scene: PackedScene = load("res://assets/props/quarters/storage_locker_module.glb")
	var model: Node3D = scene.instantiate()
	factory.apply(model, &"storage_locker_module", &"aged")
	var door := model.find_child("Door", true, false) as MeshInstance3D
	var hinge := model.find_child("Hinges", true, false) as MeshInstance3D
	var handle := model.find_child("Handle", true, false) as MeshInstance3D
	assert_true(is_equal_approx(door.get_instance_shader_parameter(&"face_size").x, .514), "door has physical face size")
	assert_true(hinge.get_instance_shader_parameter(&"face_size").z == 1.0, "hinge uses continuous cylindrical projection")
	assert_true(handle.get_instance_shader_parameter(&"face_size").w > .5, "handle pitting comes from hardware image")
	var clean: ShaderMaterial = factory.material(&"storage_locker_module", &"as_built")
	assert_true(clean.get_shader_parameter(&"baked_albedo").resource_path.ends_with("as_built_albedo.png"), "clean paint source unchanged")
	model.free()

func test_material_reuses_hatch_detail_scans_without_changing_hatch() -> void:
	var factory := _factory()
	if factory == null: return
	var material: ShaderMaterial = factory.material(&"storage_locker_module", &"aged")
	for parameter: String in Surfaces.HATCH_DETAIL_TEXTURES:
		assert_true(material.get_shader_parameter(parameter) == Surfaces.HATCH_DETAIL_TEXTURES[parameter], "shared hatch scan: " + parameter)
	assert_true(material.shader != Surfaces.STEEL, "quarters do not alter the shared steel shader")
	assert_true(Surfaces.material(&"modelled_hatch").get_shader_parameter(&"baked_hatch"), "hatch keeps its existing recipe")

func test_face_imports_preserve_packed_data_and_closeup_mips() -> void:
	for kind: String in ["albedo", "normal", "orm"]:
		var settings := ConfigFile.new()
		assert_int_equal(settings.load("res://tools/quarters_aging/locker_material/aged-face-%s.png.import" % kind), OK, "face image import")
		assert_false(settings.get_value("params", "process/fix_alpha_border"), "oxide alpha must never erase painted RGB")
		assert_true(settings.get_value("params", "mipmaps/generate"), "close-up atlas also supports distant views")
		assert_int_equal(settings.get_value("params", "compress/mode"), 2, "bounded GPU atlas storage")
