extends SimTestCase

func test_bay_hatch_identity_selects_its_profile_even_when_fixture_order_changes() -> void:
	var game := Game.new(91)
	var specs := game.layout.bay().emergency_fixtures(game.registry)
	assert_int_equal(specs.size(), 8, "seven pod keys and the hatch key")
	specs.reverse()
	var lighting := Lighting.new()
	lighting._game = game
	lighting._lens_material = Lighting.emergency_lens_material(1.0)
	for spec: ShipLayout.EmergencyFixtureSpec in specs:
		lighting.add_child(lighting._fixture(spec, 1.0))
	var ids: Dictionary = {}
	for spec: ShipLayout.EmergencyFixtureSpec in specs:
		assert_false(ids.has(spec.id), "fixture identities are unique")
		ids[spec.id] = true
		var fixture := lighting.fixture(spec.id)
		assert_true(fixture.get_meta(&"fixture_id") == spec.id, "built fixture retains layout identity")
		assert_int_equal(fixture.get_meta(&"light_role"), spec.role, "built fixture retains layout role")
		var key := fixture.get_child(0) as OmniLight3D
		var hatch := spec.id == ShipLayout.BAY_HATCH_KEY_ID
		assert_int_equal(spec.role, ShipLayout.EmergencyLightRole.BAY_HATCH if hatch else ShipLayout.EmergencyLightRole.BAY_POOL, "identity selects semantic role")
		assert_float_equal(key.omni_range, 5.5 if hatch else 3.5, "identity selects unchanged range")
		assert_float_equal(key.omni_attenuation, 1.0, "bay falloff stays unchanged")
		var isolated := Lighting.switched_key(spec.role, 1.0)
		assert_float_equal(isolated.omni_range, key.omni_range, "profile resolution does not depend on enumeration order")
		assert_float_equal(isolated.omni_attenuation, key.omni_attenuation, "central profile owns falloff")
		isolated.free()
	assert_true(ids.has(ShipLayout.BAY_HATCH_KEY_ID), "layout authors the hatch key explicitly")
	for role: int in [game.layout.section(&"D14-S-041").emergency_light_role(), game.layout.power_room().emergency_light_role()]:
		var key := Lighting.switched_key(role, 1.0)
		assert_float_equal(key.omni_range, 2.5, "hall and power share the unchanged short-pool range")
		assert_float_equal(key.omni_attenuation, 3.0, "hall and power share the unchanged falloff")
		key.free()
	lighting.free()

func test_bay_and_power_wall_cages_use_layout_owned_clear_mounts() -> void:
	var game := Game.new(91)
	var bay_expected: Array[Vector3] = [
		Vector3(-4, 2.5, -3.8), Vector3(-4, 2.5, 3.8),
		Vector3(0, 2.5, -3.8), Vector3(0, 2.5, 3.8),
		Vector3(4, 2.5, -3.8), Vector3(4, 2.5, 3.8),
	]
	var power_expected: Array[Vector3] = [
		Vector3(24, 2.5, -1.9), Vector3(24, 2.5, -9.5),
		Vector3(26, 2.5, -1.9), Vector3(27, 2.5, -9.5),
		Vector3(30, 2.5, -1.9), Vector3(30, 2.5, -9.5),
	]
	var rooms: Array[Node3D] = [Lighting.build(game), PowerRoom.build(game)]
	var positions := [game.layout.bay().emergency_fill_positions(), game.layout.power_room().emergency_fill_positions()]
	for index: int in range(rooms.size()):
		var expected := bay_expected if index == 0 else power_expected
		assert_int_equal(positions[index].size(), 6, "layout supplies all six final positions")
		for station: int in range(expected.size()):
			assert_vec3_equal(positions[index][station], expected[station], "layout fixes the wall coordinate")
		var fills := rooms[index].find_children("EmergencyFill*", "OmniLight3D", true, false)
		assert_int_equal(fills.size(), 6, "six existing fills per room")
		for station: int in range(fills.size()):
			assert_vec3_equal(fills[station].position, expected[station], "source follows its layout-owned wall mount")
		rooms[index].free()

func test_smoke_shader_requires_an_explicit_emission_binding_without_a_palette_default() -> void:
	var source := FileAccess.get_file_as_string("res://app/smoke_puff.gdshader")
	var declaration := RegEx.new()
	assert_int_equal(declaration.compile("uniform\\s+vec4\\s+emission_tint\\s*:\\s*source_color\\s*;"), OK, "binding pattern compiles")
	assert_true(declaration.search(source) != null, "smoke emission uniform must have no authored fallback")
	var hazards := Hazards.build()
	var smoke: GPUParticles3D = hazards.get_node("CeilingSmoke")
	var material := smoke.draw_pass_1.material as ShaderMaterial
	var bound := false
	for property: Dictionary in material.get_property_list():
		if property.name == "shader_parameter/emission_tint":
			bound = material.property_can_revert(property.name)
	assert_true(bound, "material explicitly overrides emission_tint rather than using a shader default")
	var emission: Color = material.get_shader_parameter("emission_tint")
	assert_true(emission.is_equal_approx(Color(0.03, 0.0084, 0.0036, 1.0)), "bound smoke emission is unchanged")
	hazards.free()
