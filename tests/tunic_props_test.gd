extends SimTestCase

const ROOT := "res://assets/props/quarters/"

func test_tunic_finishes_are_cached_shared_and_distinct() -> void:
	var clean: Material = QuartersProps.material(&"dress_uniform", &"as_built")
	var aged: Material = QuartersProps.material(&"dress_uniform", &"aged")
	assert_true(clean != aged, "tunic states have distinct materials")
	for state: StringName in QuartersProps.STATES:
		assert_true(QuartersProps.material(&"dress_uniform", state) == QuartersProps.material(&"dress_uniform", state), "each tunic finish is cached")
	assert_true((clean as ShaderMaterial).get_shader_parameter("base_colour").b > (clean as ShaderMaterial).get_shader_parameter("base_colour").r, "clean wool stays navy")
	assert_true((aged as ShaderMaterial).get_shader_parameter("albedo_texture") != null, "aged wool retains calibrated texture")

func test_both_states_keep_every_node_mesh_name_and_transform() -> void:
	for state: StringName in QuartersProps.STATES:
		var first := _model(state)
		var second := _model(state)
		var before := _parts(first)
		QuartersProps.apply(first, &"dress_uniform", state)
		QuartersProps.apply(second, &"dress_uniform", state)
		var count := QuartersProps.cache_size()
		for repeat: int in range(3): QuartersProps.apply(first, &"dress_uniform", state)
		assert_true(_parts(first) == before, "application never moves, renames or replaces any geometry")
		assert_int_equal(QuartersProps.cache_size(), count, "repeat applications allocate no materials")
		for piece: MeshInstance3D in first.find_children("*", "MeshInstance3D", true, false):
			var other := second.find_child(String(piece.name), true, false) as MeshInstance3D
			assert_true(piece.material_override == null, "multi-surface meshes retain independent slots")
			for surface: int in range(piece.mesh.get_surface_count()):
				var finish := piece.get_surface_override_material(surface)
				assert_true(finish != null and finish == other.get_surface_override_material(surface), "instances share each surface finish")
		assert_true(first.find_child("Hanger", true, false) != null and first.find_child("TunicBody", true, false) != null, "named tunic parts retained")
		first.free()
		second.free()

func test_imported_alpha_modes_two_sided_cards_and_pbr_survive() -> void:
	for state: StringName in QuartersProps.STATES:
		var data := _gltf(state)
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		for node: Dictionary in data.nodes:
			if not node.has("mesh"): continue
			var piece := model.find_child(node.name, true, false) as MeshInstance3D
			var primitives: Array = data.meshes[node.mesh].primitives
			assert_int_equal(piece.mesh.get_surface_count(), primitives.size(), "all exported slots retained: " + node.name)
			for surface: int in range(primitives.size()):
				var source: Dictionary = data.materials[primitives[surface].material]
				var finish := piece.get_surface_override_material(surface) as ShaderMaterial
				var mode: String = source.get("alphaMode", "OPAQUE")
				var expected: String = {"OPAQUE": "opaque", "MASK": "mask", "BLEND": "blend"}[mode]
				assert_true(finish.shader.resource_path.ends_with("quarters_tunic_%s.gdshader" % expected), "exported alpha mode: " + source.name)
				assert_true("cull_disabled" in finish.shader.code, "two-sided cloth/cards")
				if mode == "MASK": _near(finish.get_shader_parameter("alpha_cutoff"), source.get("alphaCutoff", .5), .00001, "cloth alpha cutoff")
				_near(finish.get_shader_parameter("metallic"), source.pbrMetallicRoughness.get("metallicFactor", 1.0), .00001, "metallic retained")
				_near(finish.get_shader_parameter("roughness"), source.pbrMetallicRoughness.get("roughnessFactor", 1.0), .00001, "roughness retained")
				var specular: Dictionary = source.get("extensions", {}).get("KHR_materials_specular", {})
				_near(finish.get_shader_parameter("specular"), specular.get("specularFactor", 1.0) * .5, .00001, "glTF specular factor retained")
		model.free()

func test_embedded_textures_have_mips_and_correct_colour_roles() -> void:
	for state: StringName in QuartersProps.STATES:
		var settings := ConfigFile.new()
		assert_int_equal(settings.load(ROOT + "dress_uniform%s.glb.import" % ("_aged" if state == &"aged" else "")), OK, "explicit tunic import settings")
		assert_int_equal(settings.get_value("params", "gltf/embedded_image_handling"), 2, "textures embedded in scene without generated external PNG dependencies")
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		for piece: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(piece.mesh.get_surface_count()):
				var finish := piece.get_surface_override_material(surface) as ShaderMaterial
				assert_true("filter_linear_mipmap" in FileAccess.get_file_as_string("res://app/shaders/quarters_tunic.gdshaderinc"), "filtered minification")
				for texture: Texture2D in [finish.get_shader_parameter("albedo_texture"), finish.get_shader_parameter("normal_texture")]:
					if texture != null: assert_true(texture.get_image().has_mipmaps(), "embedded colour/data texture has mips")
				var shader := FileAccess.get_file_as_string("res://app/shaders/quarters_tunic.gdshaderinc")
				assert_true("albedo_texture : source_color" in shader, "sRGB albedo")
				assert_true("normal_texture : hint_normal" in shader, "linear normal data")
				if finish.get_shader_parameter("normal_texture") != null: assert_true(finish.get_shader_parameter("has_normal"), "normal data enabled")
		model.free()

func test_brass_ribbon_and_soft_shoulder_remain_separate() -> void:
	for state: StringName in QuartersProps.STATES:
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		var medal := model.find_child("Medal", true, false) as MeshInstance3D
		assert_int_equal(medal.mesh.get_surface_count(), 3, "issue #130 keeps brass, enamel and sewn ribbon distinct")
		assert_true(medal.get_surface_override_material(0) != medal.get_surface_override_material(1), "brass never replaces ribbon")
		var enamel := medal.get_surface_override_material(1) as ShaderMaterial
		var ribbon := medal.get_surface_override_material(2) as ShaderMaterial
		var blue := (enamel.get_shader_parameter("base_colour") as Color).srgb_to_linear()
		assert_true(blue.b > blue.r * 4.0, "issue #130 enamel remains navy in both states")
		_near(enamel.get_shader_parameter("roughness"), .38 if state == &"aged" else .22, .00001, "enamel has its own dry aging")
		_near(enamel.get_shader_parameter("metallic"), 0, .00001, "enamel remains dielectric")
		assert_true(enamel.get_shader_parameter("pigment_gain") == Vector3.ONE, "wool calibration never tints enamel")
		assert_true(ribbon.get_shader_parameter("vertex_colour"), "woven ribbon retains authored colours")
		var brass := medal.get_surface_override_material(0) as ShaderMaterial
		_near(brass.get_shader_parameter("metallic"), .15 if state == &"aged" else .8, .00001, "bright/dull brass")
		if state == &"aged":
			var body := model.find_child("TunicBody", true, false) as MeshInstance3D
			assert_int_equal(body.mesh.get_surface_count(), 3, "soft shoulder rim is not merged into masked cloth")
			assert_true((body.get_surface_override_material(2) as ShaderMaterial).shader.resource_path.ends_with("_blend.gdshader"), "shoulder keeps fractional alpha")
			assert_true(model.find_child("HeapFibres", true, false) != null, "fibre heap loads")
		model.free()

func test_tunic_does_not_mutate_sofa_or_locker_resources() -> void:
	var existing := {}
	for prop: StringName in [&"sofa", &"storage_locker_module"]:
		for state: StringName in QuartersProps.STATES:
			var finish := QuartersProps.material(prop, state) as ShaderMaterial
			var parameters := {}
			for uniform: Dictionary in finish.shader.get_shader_uniform_list(): parameters[uniform.name] = finish.get_shader_parameter(uniform.name)
			existing["%s/%s" % [prop, state]] = {"material": finish, "shader": finish.shader, "parameters": parameters}
	for state: StringName in QuartersProps.STATES:
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		model.free()
	for identity: String in existing:
		var saved: Dictionary = existing[identity]
		assert_true(saved.material.shader == saved.shader, "sofa/locker shader identity unchanged")
		for parameter: String in saved.parameters:
			assert_true(saved.material.get_shader_parameter(parameter) == saved.parameters[parameter], "sofa/locker parameters untouched: " + parameter)

func test_wool_display_calibration_does_not_tint_brass_or_clean_wool() -> void:
	for state: StringName in QuartersProps.STATES:
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		for piece: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(piece.mesh.get_surface_count()):
				var finish := piece.get_surface_override_material(surface) as ShaderMaterial
				var gain: Vector3 = finish.get_shader_parameter(&"pigment_gain")
				var source := piece.mesh.surface_get_material(surface) as StandardMaterial3D
				var wool := state == &"aged" and is_zero_approx(source.metallic) and source.resource_name != "RibbonFabric" and not source.resource_name.begins_with("MedalEnamel")
				assert_true(gain == (QuartersProps.TUNIC_AGED_WOOL_GAIN if wool else Vector3.ONE), "calibration is confined to aged wool/dust/fibres")
				assert_true(finish.get_shader_parameter(&"albedo_texture") == source.albedo_texture, "no texture is copied or recoloured")
				_near(finish.get_shader_parameter(&"normal_scale"), source.normal_scale, .00001, "normal strength retained")
				assert_true(finish.get_shader_parameter(&"vertex_colour") == source.vertex_color_use_as_albedo, "ribbon vertex colours retained")
		model.free()

func test_export_uses_constant_orm_and_linear_normal_data() -> void:
	for state: StringName in QuartersProps.STATES:
		var data := _gltf(state)
		for source: Dictionary in data.materials:
			assert_false(source.pbrMetallicRoughness.has("metallicRoughnessTexture"), "this tunic export uses constant metallic/roughness, not an ORM atlas")
			assert_false(source.has("occlusionTexture"), "ambient occlusion is baked into the supplied colour")
		var model := _model(state)
		QuartersProps.apply(model, &"dress_uniform", state)
		for piece: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(piece.mesh.get_surface_count()):
				var finish := piece.get_surface_override_material(surface) as ShaderMaterial
				var source := piece.mesh.surface_get_material(surface) as StandardMaterial3D
				assert_true(finish.get_shader_parameter(&"normal_texture") == source.normal_texture, "linear normal texture retained")
		model.free()

func test_two_sided_normals_are_flipped_only_by_the_renderer() -> void:
	for mode: String in ["opaque", "mask", "blend"]:
		var shader := FileAccess.get_file_as_string("res://app/shaders/quarters_tunic_%s.gdshader" % mode)
		assert_true("cull_disabled" in shader, "Godot enables its two-sided normal correction")
		assert_false("NORMAL = -NORMAL" in shader, "do not undo Godot's backface correction")

func test_baked_maps_use_remapped_uvs_and_generated_tangents() -> void:
	var model := _model(&"aged")
	var data := _gltf(&"aged")
	for node: Dictionary in data.nodes:
		if not node.has("mesh"): continue
		var piece := model.find_child(node.name, true, false) as MeshInstance3D
		var primitives: Array = data.meshes[node.mesh].primitives
		for surface: int in range(primitives.size()):
			var source: Dictionary = data.materials[primitives[surface].material]
			var imported := piece.mesh.surface_get_material(surface) as StandardMaterial3D
			if not source.has("normalTexture"): continue
			var coordinates: int = source.normalTexture.get("texCoord", 0)
			assert_int_equal(imported.get_meta("_gltf_primary_texture_coord"), coordinates, "normal and colour use the importer's primary UV remapping")
			var arrays := piece.mesh.surface_get_arrays(surface)
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
			assert_int_equal(tangents.size(), normals.size() * 4, "normal-mapped vertices have generated tangent frames")
			for index: int in range(normals.size()):
				var offset := index * 4
				var tangent := Vector3(tangents[offset], tangents[offset + 1], tangents[offset + 2])
				_near(tangent.length(), 1.0, .002, "unit tangent")
				_near(tangent.dot(normals[index]), 0, .002, "tangent orthogonal to normal")
				_near(absf(tangents[offset + 3]), 1.0, .00001, "tangent handedness")
	model.free()

func _model(state: StringName) -> Node3D:
	return (load(ROOT + "dress_uniform%s.glb" % ("_aged" if state == &"aged" else "")) as PackedScene).instantiate()

func _parts(node: Node) -> Dictionary:
	var result := {"name": node.name, "children": []}
	if node is Node3D: result.transform = node.transform
	if node is MeshInstance3D:
		result.mesh = node.mesh
		result.bounds = node.get_aabb()
	for child: Node in node.get_children(): result.children.append(_parts(child))
	return result

func _gltf(state: StringName) -> Dictionary:
	var file := FileAccess.open(ROOT + "dress_uniform%s.glb" % ("_aged" if state == &"aged" else ""), FileAccess.READ)
	file.seek(12)
	var length := file.get_32()
	file.get_32()
	return JSON.parse_string(file.get_buffer(length).get_string_from_utf8())

func _near(actual: float, expected: float, tolerance: float, message: String) -> void:
	assert_true(absf(actual - expected) <= tolerance, message)
