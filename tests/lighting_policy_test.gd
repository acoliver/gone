extends SimTestCase

func test_bay_uses_one_live_wall_source_per_existing_fixture_identity() -> void:
	var bay := Lighting.build(Game.new(91))
	assert_int_equal(bay.lights().size(), 8, "seven row lamps and the existing hatch lamp")
	assert_true(bay.find_children("EmergencyFill*", "Light3D", true, false).is_empty(), "no duplicate neutral cages")
	var total := 0.0
	for source: OmniLight3D in bay.lights(): total += source.light_energy / Lighting.FIXTURE_ENERGY
	assert_true(is_equal_approx(total, 21.84), "eight red shares, eight pod shares and all 5.84 former fill shares are conserved")
	bay.free()

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
		var station := String(spec.id).split("-")[3].to_int() if not hatch else 0
		assert_float_equal(key.omni_range, 5.5 if hatch else EmergencyFixtureProfile.BAY[station].z, "identity selects its consolidated range")
		assert_float_equal(key.omni_attenuation, 1.0 if hatch else EmergencyFixtureProfile.BAY[station].w, "identity selects its consolidated falloff")
		var isolated := Lighting.switched_key(spec.role, 1.0)
		assert_float_equal(isolated.omni_range, 5.5 if hatch else 3.5, "base role remains independent of wall profile")
		assert_float_equal(isolated.omni_attenuation, 1.0, "base role owns its original falloff")
		isolated.free()
	assert_true(ids.has(ShipLayout.BAY_HATCH_KEY_ID), "layout authors the hatch key explicitly")
	for role: int in [game.layout.section(&"D14-S-041").emergency_light_role(), game.layout.power_room().emergency_light_role()]:
		var key := Lighting.switched_key(role, 1.0)
		assert_float_equal(key.omni_range, 2.5, "hall and power share the unchanged short-pool range")
		assert_float_equal(key.omni_attenuation, 3.0, "hall and power share the unchanged falloff")
		key.free()
	lighting.free()

func test_power_near_wall_is_one_regular_row_without_far_wall_duplicates() -> void:
	var game := Game.new(91)
	var positions := game.layout.power_room().emergency_fill_positions()
	var room := PowerRoom.build(game)
	var fills := room.find_children("EmergencyFill*", "Light3D", true, false)
	assert_int_equal(positions.size(), 3, "only three distinct near-wall stations remain")
	assert_int_equal(fills.size(), 3, "far-wall fills merged into existing keys")
	for index: int in range(3):
		assert_vec3_equal(positions[index], Vector3(24 + 2 * index, 2.5, -1.9), "single regular wall pitch")
		assert_vec3_equal(fills[index].position, positions[index], "source follows the layout-owned station")
	room.free()

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
