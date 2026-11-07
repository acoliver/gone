extends SimTestCase

func test_capture_identity_pins_build_resources_and_lighting_policy() -> void:
	var capture: GDScript = load("res://tools/capture_ship_surfaces.gd")
	var methods: Array[String] = []
	for method: Dictionary in capture.get_script_method_list(): methods.append(method.name)
	assert_true(methods.has("capture_identity"), "capture setup records build and lighting identity")
	if not methods.has("capture_identity"): return
	var identity: Dictionary = capture.capture_identity()
	assert_true(identity.app_hash == load("res://harness/protocol.gd").app_hash(ProjectSettings.globalize_path("res://")), "same app identity as harness")
	for path: String in ["app/lighting.gd", "app/hallway.gd", "app/power_room.gd", "app/ship_scene.gd", "tools/capture_ship_surfaces.gd", "app/shaders/weathered_steel.gdshader", "assets/surfaces/hatch/leaf-weather.png"]:
		assert_true(identity.resources.get(path) == FileAccess.get_sha256("res://" + path), "capture resource identity: " + path)
	for file: String in Surfaces.IMAGES:
		for suffix: String in ["", ".import"]:
			var path := "assets/surfaces/steel/" + file + suffix
			assert_true(identity.resources.get(path) == FileAccess.get_sha256("res://" + path), "scan/import identity: " + path)
	for path: String in [HatchAsset.SOURCE, HatchAsset.SOURCE + ".import", HatchAsset.MANIFEST]:
		assert_true(identity.resources.get(path.trim_prefix("res://")) == FileAccess.get_sha256(path), "imported hatch identity: " + path)
	var hatch_textures: Array = Surfaces.HATCH_TEXTURES.values() + Surfaces.HATCH_DETAIL_TEXTURES.values() + [Surfaces.HATCH_PAINTED]
	for texture: Texture2D in hatch_textures:
		for suffix: String in ["", ".import"]:
			var path := texture.resource_path + suffix
			assert_true(identity.resources.get(path.trim_prefix("res://")) == FileAccess.get_sha256(path), "baked hatch texture identity: " + path)
	var policy: Dictionary = identity.lighting
	assert_true(policy.key_color == [Lighting.EMERGENCY_RED.r, Lighting.EMERGENCY_RED.g, Lighting.EMERGENCY_RED.b], "key palette")
	assert_true(policy.fill_color == [Lighting.EMERGENCY_FILL_COLOR.r, Lighting.EMERGENCY_FILL_COLOR.g, Lighting.EMERGENCY_FILL_COLOR.b], "fill palette")
	assert_float_equal(policy.key_energy, Lighting.emergency_energy(), "key energy")
	assert_float_equal(policy.fill_energy, Lighting.emergency_energy() * Lighting.EMERGENCY_FILL_SHARE, "fill energy")
	assert_float_equal(policy.no_fill_multiplier, Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER, "independent key multiplier")
	assert_false(policy.fill_shadows, "fill shadow policy")
	assert_false(policy.key_shadows, "key shadow policy")
	assert_true(policy.fill_masks == [Lighting.BAY_FILL_MASK, Lighting.HALL_FILL_MASK, Lighting.POWER_FILL_MASK], "room isolation policy")

func test_native_probe_covers_independent_channels_and_signed_normals() -> void:
	var probe: GDScript = load("res://tools/capture_steel_probe.gd")
	var methods: Array[String] = []
	for method: Dictionary in probe.get_script_method_list(): methods.append(method.name)
	for method: String in ["_channel_behavior", "_normal_direction"]:
		assert_true(methods.has(method), "native production-shader behavior probe: " + method)

func test_regular_end_fill_policy_belongs_to_lighting() -> void:
	var origin := Vector3(3, 1, -2)
	var fill := Lighting.regular_end_fill(origin, 0.5)
	assert_true(fill.position == origin, "layout supplies the fill placement")
	assert_true(fill.light_color == Lighting.REGULAR_WHITE, "regular palette")
	assert_float_equal(fill.light_energy, PackedFloat32Array([Lighting.regular_energy() * 0.12 * 0.5])[0], "unchanged regular share and native float32 energy")
	assert_float_equal(fill.omni_range, Lighting.EMERGENCY_FILL_RANGE, "unchanged fill range")
	assert_int_equal(fill.light_cull_mask, Lighting.HALL_FILL_MASK, "hall-only fill")
	assert_false(fill.shadow_enabled, "no fill shadows")
	fill.apply_level(0.0)
	assert_float_equal(fill.light_energy, 0.0, "dark before white handoff")
	fill.free()
