extends SimTestCase

const MEDAL_SHADER := "res://app/shaders/quarters_medal.gdshader"

func test_enamel_padding_stays_blue_and_dielectric_at_every_mip() -> void:
	for state: StringName in QuartersProps.STATES:
		var source := (load(QuartersProps.TUNIC_SCENES[state]) as PackedScene).instantiate()
		var medal := source.find_child("Medal", true, false) as MeshInstance3D
		var brass := medal.mesh.surface_get_material(0) as StandardMaterial3D
		var enamel := medal.mesh.surface_get_material(1) as StandardMaterial3D
		assert_true(enamel.albedo_texture != brass.albedo_texture, "material-isolated albedo padding")
		assert_true(enamel.roughness_texture != brass.roughness_texture, "material-isolated ORM padding")
		var colour := enamel.albedo_texture.get_image()
		var orm := enamel.roughness_texture.get_image()
		if colour.is_compressed(): assert_int_equal(colour.decompress(), OK, "read enamel mip colours")
		if orm.is_compressed(): assert_int_equal(orm.decompress(), OK, "read enamel mip ORM")
		colour.convert(Image.FORMAT_RGB8)
		orm.convert(Image.FORMAT_RGB8)
		for level: int in range(colour.get_mipmap_count() + 1):
			var width := maxi(1, colour.get_width() >> level)
			var height := maxi(1, colour.get_height() >> level)
			var start := colour.get_mipmap_offset(level)
			var orm_start := orm.get_mipmap_offset(level)
			var image := Image.create_from_data(width, height, false, Image.FORMAT_RGB8,
				colour.get_data().slice(start, start + width * height * 3))
			var packed := Image.create_from_data(width, height, false, Image.FORMAT_RGB8,
				orm.get_data().slice(orm_start, orm_start + width * height * 3))
			for point: Vector2 in [Vector2.ZERO, Vector2(0.5, 0.5), Vector2(0.999, 0.999)]:
				var x := mini(int(point.x * image.get_width()), image.get_width() - 1)
				var y := mini(int(point.y * image.get_height()), image.get_height() - 1)
				var pixel := image.get_pixel(x, y)
				assert_true(pixel.b > pixel.r * 4.0, "enamel mip padding cannot sample brass colour")
				assert_true(packed.get_pixel(x, y).b < 0.01, "enamel mip padding cannot become metallic")
		source.free()
	var shader := FileAccess.get_file_as_string("res://app/shaders/quarters_ribbon.gdshader")
	assert_true("weave_uv * vec2(0.11, 0.071)" in shader, "larger photographic fibre field varies fold roughness")

func test_medal_ribbon_has_restrained_separate_sheen() -> void:
	for state: StringName in QuartersProps.STATES:
		var finish := QuartersProps.material(&"dress_uniform", state, &"Medal", 2)
		assert_true(finish.shader.resource_path.ends_with("quarters_ribbon.gdshader"), "only the medal ribbon uses this finish")
		assert_true("SPECULAR = 0.4;" in finish.shader.code, "retain the woven dielectric specular invariant")
		assert_true("ANISOTROPY = weave_enabled ? 0.38" in finish.shader.code, "retain restrained directional fibre sheen")
		assert_true("RIM = 0.08;" in finish.shader.code, "restrain the medal-only grazing lobe")
		assert_true("mix(vec3(0.97), texture(albedo_texture, weave_uv).rgb, 0.75)" in finish.shader.code, "medal-only weave colour contrast is reduced by one quarter")
		assert_true("xy *= 0.8;" in finish.shader.code, "medal-only weave normal slope is reduced by one fifth")

func test_generated_enamel_coat_texture_reaches_the_shader() -> void:
	for state: StringName in QuartersProps.STATES:
		var source := (load(QuartersProps.TUNIC_SCENES[state]) as PackedScene).instantiate()
		QuartersProps.apply(source, &"dress_uniform", state)
		var medal := source.find_child("Medal", true, false) as MeshInstance3D
		var finish := medal.get_surface_override_material(1) as ShaderMaterial
		var texture := load(QuartersProps.MEDAL_ROOT + String(state) + "_coat.png") as Texture2D
		assert_true(texture != null, "generated enamel has its state-specific coat-weight map")
		assert_true(finish.get_shader_parameter("coat_texture") == texture, "linear saved master reaches the shader despite native glTF dropping coat")
		assert_true(finish.get_shader_parameter("has_coat_texture") == true, "coat mask is enabled")
		assert_true("texture(coat_texture, UV).r" in finish.shader.code, "coat consumes the linear red channel")
		assert_false("coat_texture : source_color" in finish.shader.code, "coat is linear data")
		assert_true(texture.get_image().has_mipmaps(), "coat has filtered minification")
		source.free()

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
			assert_float_equal(finish.get_shader_parameter("coat"), 1.0 if slot == 1 else 0.0, "generated coat map uses a unit factor on enamel only")
			assert_true(finish == QuartersProps.material(&"dress_uniform", state, &"Medal", slot), "state/role cached")
			for parameter: String in ["normal_texture", "orm_texture"]:
				var missing := finish.duplicate() as ShaderMaterial
				missing.set_shader_parameter(parameter, null)
				assert_false(_bindings_valid(missing, imported), "missing binding negative: " + parameter)
			var swapped := finish.duplicate() as ShaderMaterial
			swapped.set_shader_parameter("normal_texture", imported.roughness_texture)
			assert_false(_bindings_valid(swapped, imported), "wrong texture-role negative")
			assert_true(imported.roughness_texture.get_image().has_mipmaps(), "ORM has filtered minification")
			if slot == 1: assert_float_equal(finish.get_shader_parameter("coat_roughness"), .30 if state == &"aged" else .09, "#130: Present coat matches the softer saved enamel finish")
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
