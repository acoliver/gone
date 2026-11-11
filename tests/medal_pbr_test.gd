extends SimTestCase

const MEDAL_SHADER := "res://app/shaders/quarters_medal.gdshader"

func _bindings_valid(finish: ShaderMaterial, imported: StandardMaterial3D) -> bool:
	return finish.shader.resource_path == MEDAL_SHADER and finish.get_shader_parameter("has_normal") == true and finish.get_shader_parameter("normal_texture") != null and finish.get_shader_parameter("orm_texture") != null and finish.get_shader_parameter("normal_texture") == imported.normal_texture and finish.get_shader_parameter("orm_texture") == imported.roughness_texture

func test_medal_pbr_bindings_and_negative_controls() -> void:
	for state: StringName in QuartersProps.STATES:
		var source := (load(QuartersProps.TUNIC_SCENES[state]) as PackedScene).instantiate()
		QuartersProps.apply(source, &"dress_uniform", state)
		var medal := source.find_child("Medal", true, false) as MeshInstance3D
		for slot: int in [0, 1]:
			var imported := medal.mesh.surface_get_material(slot) as StandardMaterial3D
			var finish := medal.get_surface_override_material(slot) as ShaderMaterial
			assert_true(_bindings_valid(finish, imported), "#130 both metal/enamel slots consume normal and ORM")
			assert_true(finish.get_shader_parameter("albedo_texture") == imported.albedo_texture, "imported sRGB albedo retained")
			assert_true(finish.get_shader_parameter("normal_texture") == imported.normal_texture, "imported normal retained")
			assert_true(finish.get_shader_parameter("orm_texture") == imported.roughness_texture, "imported packed ORM retained")
			assert_int_equal(imported.roughness_texture_channel, BaseMaterial3D.TEXTURE_CHANNEL_GREEN, "roughness G")
			assert_int_equal(imported.metallic_texture_channel, BaseMaterial3D.TEXTURE_CHANNEL_BLUE, "metallic B")
			assert_int_equal(imported.ao_texture_channel, BaseMaterial3D.TEXTURE_CHANNEL_RED, "occlusion R")
			assert_float_equal(finish.get_shader_parameter("roughness"), 1.0, "final atlas roughness multiplied once")
			assert_float_equal(finish.get_shader_parameter("metallic"), 1.0, "final atlas metallic multiplied once")
			assert_float_equal(finish.get_shader_parameter("specular"), .5, "enamel is exempt from generic aged specular")
			assert_float_equal(finish.get_shader_parameter("coat"), .65 if slot == 1 else 0.0, "coat only on enamel")
			assert_true(finish == QuartersProps.material(&"dress_uniform", state, &"Medal", slot), "state/role cached")
			for parameter: String in ["normal_texture", "orm_texture"]:
				var missing := finish.duplicate() as ShaderMaterial
				missing.set_shader_parameter(parameter, null)
				assert_false(_bindings_valid(missing, imported), "missing binding negative: " + parameter)
			var swapped := finish.duplicate() as ShaderMaterial
			swapped.set_shader_parameter("normal_texture", imported.roughness_texture)
			assert_false(_bindings_valid(swapped, imported), "wrong texture-role negative")
			assert_true(imported.roughness_texture.get_image().has_mipmaps(), "ORM has filtered minification")
			if slot == 1: assert_float_equal(finish.get_shader_parameter("coat_roughness"), .23 if state == &"aged" else .13, "state enamel coat")
			var ignored := finish.duplicate() as ShaderMaterial
			ignored.set_shader_parameter("has_normal", false)
			assert_false(_bindings_valid(ignored, imported), "ignored normal negative")
		var buttons := source.find_child("Buttons", true, false) as MeshInstance3D
		assert_true(buttons.get_surface_override_material(0) != medal.get_surface_override_material(0), "shared imported brass never leaks medal adapter")
		assert_true((buttons.get_surface_override_material(0) as ShaderMaterial).shader.resource_path.ends_with("quarters_tunic_opaque.gdshader"), "buttons retain their shader")
		assert_true((medal.get_surface_override_material(2) as ShaderMaterial).shader.resource_path.ends_with("quarters_tunic_opaque.gdshader"), "ribbon retains its shader")
		for piece: MeshInstance3D in source.find_children("*", "MeshInstance3D", true, false):
			for slot: int in range(piece.mesh.get_surface_count()):
				if piece.name == &"Medal" and slot < 2: continue
				var imported := piece.mesh.surface_get_material(slot) as StandardMaterial3D
				assert_true(imported.roughness_texture == null and imported.metallic_texture == null and imported.ao_texture == null, "non-medal slots retain constant ORM")
		source.free()

func test_medal_sampling_roles_and_normal_decode() -> void:
	var shader := FileAccess.get_file_as_string(MEDAL_SHADER)
	assert_true("albedo_texture : source_color" in shader, "sRGB albedo")
	assert_true("normal_texture : hint_normal" in shader, "linear normal")
	assert_true("orm_texture : filter_linear_mipmap" in shader, "linear mipmapped ORM without source_color")
	assert_false("orm_texture : source_color" in shader, "ORM never gamma decoded")
	for output: String in ["NORMAL_MAP", "NORMAL_MAP_DEPTH", "ROUGHNESS", "METALLIC", "AO", "AO_LIGHT_AFFECT", "SPECULAR", "CLEARCOAT", "CLEARCOAT_ROUGHNESS"]:
		assert_true(output in shader, "required PBR output: " + output)
	assert_true("sqrt(max(0.0, 1.0 - dot" in shader, "BC5 tangent Z reconstructed")

func test_cloth_contact_is_opt_in_and_part_local() -> void:
	var shader := FileAccess.get_file_as_string("res://app/shaders/quarters_tunic.gdshaderinc")
	assert_true("uv.y = 1.0 - uv.y" in shader, "Blender bottom-origin contact patch maps to PNG top-origin")
	for state: StringName in QuartersProps.STATES:
		var body := QuartersProps.material(&"dress_uniform", state, &"TunicBody", 0)
		assert_true(body.get_shader_parameter("contact_enabled") == true, "front cloth contact bound")
		assert_true(body.get_shader_parameter("contact_texture") != null, "state-specific cloth AO")
		assert_float_equal(float(body.get_shader_parameter("contact_light_affect")), .75 if state == &"as_built" else .35, "measured local direct-light contact calibration")
		for part: StringName in [&"Placket", &"Collar", &"RibbonBar"]:
			var finish := QuartersProps.material(&"dress_uniform", state, part, 0)
			assert_false(finish.get_shader_parameter("contact_enabled") == true, "shared cloth never leaks contact to " + part)
