extends SimTestCase

const MEDAL_SHADER := "res://app/shaders/quarters_medal.gdshader"

func test_asset_capture_hides_the_aiming_overlay_only() -> void:
	var main := Node3D.new()
	var dot := ClickIndicators.new()
	main.add_child(dot)
	var other := Control.new()
	main.add_child(other)
	preload("res://tools/medal_capture.gd").hide_aiming_dot(main)
	assert_false(dot.visible, "the screen-centre dot is not a medal bake defect")
	assert_true(other.visible, "capture does not hide unrelated UI")
	main.free()

func test_ribbon_ribs_are_resolved_and_directional() -> void:
	var finish := QuartersProps.material(&"dress_uniform", &"as_built", &"Medal", 2)
	assert_true((finish.get_shader_parameter("weave_scale") as Vector2).is_equal_approx(Vector2(260,260)), "0.256 mm ribs instead of subpixel weave")
	assert_true("ANISOTROPY_FLOW" in finish.shader.code, "ribbon fibre sheen follows its tangent")

func test_wardrobe_reflection_captures_lights_without_changing_receiver_layers() -> void:
	var game := Game.new(114)
	var room := QuartersRoom.build(game)
	for furnishing: Node3D in [room.remembered, room.present]:
		var probe := furnishing.get_node_or_null("Placement_wardrobe/MedalReflection") as ReflectionProbe
		assert_true(probe != null, "medal needs a wardrobe-interior native reflection capture")
		if probe == null: continue
		assert_int_equal(probe.cull_mask, Lighting.QUARTERS_MASK | 1, "capture light instances on layer 1 and quarters receivers")
		assert_int_equal(probe.reflection_mask, Lighting.QUARTERS_MASK, "reflection stays on quarters receivers")
		assert_true(probe.size.is_equal_approx(Vector3(.65, 2.2, 1.0)), "volume follows the carcass, not the open door")
		assert_true(AABB(-probe.size * .5, probe.size).has_point(probe.origin_offset), "capture origin stays inside the wardrobe")
		assert_true(probe.max_distance >= QuartersLayout.bounds().size.length(), "far range includes reflected room surfaces")
		assert_true(probe.interior and probe.box_projection, "interior parallax correction")
		assert_int_equal(probe.ambient_mode, ReflectionProbe.AMBIENT_ENVIRONMENT, "inherit the existing disabled black ambient")
		for mesh: MeshInstance3D in furnishing.find_children("*", "MeshInstance3D", true, false):
			assert_int_equal(mesh.layers, Lighting.QUARTERS_MASK, "no extra receiver layer may admit unrelated lights")
	game.power_active = not game.power_active
	room.process_frame()
	for furnishing: Node3D in [room.remembered, room.present]:
		var probe := furnishing.get_node_or_null("Placement_wardrobe/MedalReflection") as ReflectionProbe
		if probe == null: continue
		assert_int_equal(probe.update_mode, ReflectionProbe.UPDATE_ALWAYS, "local reflection refreshes during power fade")
	for tick: int in range(60): room.process_frame()
	for furnishing: Node3D in [room.remembered, room.present]:
		var probe := furnishing.get_node_or_null("Placement_wardrobe/MedalReflection") as ReflectionProbe
		if probe != null: assert_int_equal(probe.update_mode, ReflectionProbe.UPDATE_ONCE, "settled lighting stops repeated cubemap renders")
	room.free()

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
			assert_float_equal(finish.get_shader_parameter("coat"), .35 if slot == 1 else 0.0, "coat only on enamel")
			assert_true(finish == QuartersProps.material(&"dress_uniform", state, &"Medal", slot), "state/role cached")
			for parameter: String in ["normal_texture", "orm_texture"]:
				var missing := finish.duplicate() as ShaderMaterial
				missing.set_shader_parameter(parameter, null)
				assert_false(_bindings_valid(missing, imported), "missing binding negative: " + parameter)
			var swapped := finish.duplicate() as ShaderMaterial
			swapped.set_shader_parameter("normal_texture", imported.roughness_texture)
			assert_false(_bindings_valid(swapped, imported), "wrong texture-role negative")
			assert_true(imported.roughness_texture.get_image().has_mipmaps(), "ORM has filtered minification")
			if slot == 1: assert_float_equal(finish.get_shader_parameter("coat_roughness"), .26 if state == &"aged" else .18, "state enamel coat")
			var ignored := finish.duplicate() as ShaderMaterial
			ignored.set_shader_parameter("has_normal", false)
			assert_false(_bindings_valid(ignored, imported), "ignored normal negative")
		var buttons := source.find_child("Buttons", true, false) as MeshInstance3D
		assert_true(buttons.get_surface_override_material(0) != medal.get_surface_override_material(0), "shared imported brass never leaks medal adapter")
		assert_true((buttons.get_surface_override_material(0) as ShaderMaterial).shader.resource_path.ends_with("quarters_tunic_opaque.gdshader"), "buttons retain their shader")
		assert_true((medal.get_surface_override_material(2) as ShaderMaterial).shader.resource_path.ends_with("quarters_ribbon.gdshader"), "ribbon has its own woven finish")
		for piece: MeshInstance3D in source.find_children("*", "MeshInstance3D", true, false):
			for slot: int in range(piece.mesh.get_surface_count()):
				if piece.name == &"Medal":
					if slot == 2:
						var ribbon := piece.mesh.surface_get_material(slot) as StandardMaterial3D
						assert_true(ribbon.roughness_texture != null, "ribbon source retains woven roughness")
						assert_int_equal(ribbon.roughness_texture_channel, BaseMaterial3D.TEXTURE_CHANNEL_GREEN, "exported ribbon roughness G")
					continue
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
		assert_float_equal(float(body.get_shader_parameter("contact_light_affect")), .85 if state == &"as_built" else .35, "measured local direct-light contact calibration")
		for part: StringName in [&"Placket", &"Collar", &"RibbonBar"]:
			var finish := QuartersProps.material(&"dress_uniform", state, part, 0)
			assert_false(finish.get_shader_parameter("contact_enabled") == true, "shared cloth never leaks contact to " + part)
