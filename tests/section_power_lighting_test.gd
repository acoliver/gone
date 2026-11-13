extends SimTestCase

func test_d16_secondary_switches_every_emergency_key_off_at_build() -> void:
	var game := Game.new(114)
	game.light_hallway()
	game.press_console()
	var section := ShipSection.build(game.layout, game.layout.section(QuartersLayout.SECTION))
	var circuit := SectionPowerLighting.build(game, game.layout.section(QuartersLayout.SECTION), section)
	section.add_child(circuit)
	var red := _red_keys(section)
	assert_int_equal(red.size(), 8, "all emergency keys measured, regardless of Godot node renaming")
	assert_int_equal(circuit._red_lights.size(), red.size(), "every emergency key belongs to the circuit")
	for tick: int in range(120): circuit.process_frame()
	for key: OmniLight3D in red:
		assert_float_equal(key.light_energy, 0, "no live red key under settled secondary power")
		assert_true(key in circuit._red_lights, "no unmanaged key")
	section.free()

func test_d16_matches_d14_profiles_and_levels_through_both_power_handoffs() -> void:
	var game := Game.new(114)
	game.light_hallway()
	var hallway := Hallway.build(game)
	var spec := game.layout.section(QuartersLayout.SECTION)
	var section := ShipSection.build(game.layout, spec)
	var circuit := SectionPowerLighting.build(game, spec, section)
	section.add_child(circuit)
	_check_lights(_red_keys(section), hallway.lights(), "emergency keys")
	_check_lights(circuit._white_lights, hallway.white_lights(), "regular strips")
	var fills := section.find_children("EmergencyFill*", "OmniLight3D", true, false)
	assert_int_equal(fills.size(), hallway._fill_lights.size(), "same fill count")
	for index: int in range(mini(fills.size(), hallway._fill_lights.size())):
		assert_true((fills[index].position - spec.bounds().position).is_equal_approx(hallway._fill_lights[index].position - game.layout.section(&"D14-S-041").bounds().position), "same local fill station within float transform precision")
		assert_float_equal(fills[index].light_energy, hallway._fill_lights[index].light_energy, "same emergency fill energy")
	var end_fills := section.find_children("RegularFillEnd*", "OmniLight3D", true, false)
	assert_int_equal(end_fills.size(), 1, "regular end bounce exists")
	var emergency_end := section.get_node("PowerLighting/EmergencyFillEnd") as OmniLight3D
	assert_true(emergency_end.has_meta(&"fixture_emitter") and emergency_end.has_meta(&"fixture_housing"), "emergency end fill has its physical-source binding")
	assert_true(circuit._white_end_fill.has_meta(&"fixture_emitter") and circuit._white_end_fill.has_meta(&"fixture_housing"), "regular end fill has its physical-source binding")
	assert_true(is_equal_approx(circuit._white_end_fill.position.z, spec.emergency_end_fill_position().z - 2.6), "regular end source occupies the opposite wall position")
	for key: OmniLight3D in circuit._red_lights:
		assert_true(key.has_meta(&"fixture_emitter") and key.has_meta(&"fixture_housing"), "adapted emergency key retains its caged-source binding")
		assert_true(key.get_meta(&"energy_share") > 0.0, "emergency profile share remains present")
	for strip: SpotLight3D in circuit._white_lights:
		assert_true(strip.spot_angle == 90.0 and strip.spot_angle_attenuation == 0.0, "regular strip uses the mounted downward beam")
		assert_true(strip.has_meta(&"fixture_emitter") and strip.has_meta(&"fixture_housing"), "regular strip is seated in its fixture")
	for active: bool in [true, false]:
		game.power_active = active
		for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS + 1):
			circuit.process_frame()
			hallway.process_frame(Sim.LOGICAL_TICK_SECS)
			assert_float_equal(circuit.red_level(), hallway.level(), "same emergency fade at each logical tick")
			assert_float_equal(circuit.white_level(), hallway.white_level(), "same regular fade at each logical tick")
			_check_lights(_red_keys(section), hallway.lights(), "handoff emergency keys")
			_check_lights(circuit._white_lights, hallway.white_lights(), "handoff regular strips")
			for lens: StandardMaterial3D in circuit._red_lenses:
				assert_true(is_equal_approx(lens.emission.r, Lighting.emergency_emission(circuit.red_level()).r), "caged emergency lens follows the electrical fade")
			for fill: OmniLight3D in end_fills:
				assert_float_equal(fill.light_energy, hallway._white_end_fill.light_energy, "same regular end bounce")
	section.free()
	hallway.free()

func test_quarters_reveal_bounce_is_local_and_follows_the_same_power_handoff() -> void:
	var game := Game.new(114)
	game.light_hallway()
	var spec := game.layout.section(QuartersLayout.SECTION)
	var section := ShipSection.build(game.layout, spec)
	var circuit := SectionPowerLighting.build(game, spec, section)
	section.add_child(circuit)
	var regular := circuit.find_children("QuartersRevealRegular", "OmniLight3D", true, false)
	var emergency := circuit.find_children("QuartersRevealEmergency", "OmniLight3D", true, false)
	assert_int_equal(regular.size(), 1, "one local white reveal bounce")
	assert_int_equal(emergency.size(), 1, "one local emergency reveal bounce")
	for active: bool in [false, true]:
		game.power_active = active
		for tick: int in range(31): circuit.process_frame()
		for light: OmniLight3D in regular + emergency:
			assert_int_equal(light.light_cull_mask, Lighting.QUARTERS_MASK, "bounce cannot illuminate corridor surfaces without the quarters receiver layer")
			assert_true(is_equal_approx(light.omni_range, 1.8), "bounce remains local to the entrance hardware")
		for light: OmniLight3D in regular:
			assert_true(is_equal_approx(light.light_energy, Lighting.regular_energy() * 0.72 if active else 0.0), "local reveal-bounce energy follows secondary")
		for light: OmniLight3D in emergency:
			assert_true(is_equal_approx(light.light_energy, 0.0 if active else Lighting.emergency_energy() * Lighting.EMERGENCY_END_FILL_SHARE), "emergency end-bounce profile follows emergency")
	section.free()

func _check_lights(actual: Array, expected: Array, context: String) -> void:
	assert_int_equal(actual.size(), expected.size(), context + " count")
	for index: int in range(mini(actual.size(), expected.size())):
		var actual_light: Light3D = actual[index]
		var expected_light: Light3D = expected[index]
		assert_float_equal(actual_light.light_energy, expected_light.light_energy, context + " energy")
		if actual_light is OmniLight3D and expected_light is OmniLight3D:
			assert_float_equal(actual_light.omni_range, expected_light.omni_range, context + " range")
			assert_float_equal(actual_light.omni_attenuation, expected_light.omni_attenuation, context + " attenuation")
		elif actual_light is SpotLight3D and expected_light is SpotLight3D:
			assert_float_equal(actual_light.spot_range, expected_light.spot_range, context + " range")
			assert_float_equal(actual_light.spot_attenuation, expected_light.spot_attenuation, context + " attenuation")
		else:
			assert_true(false, context + " matching light types")
		assert_true(actual_light.light_color == expected_light.light_color, context + " colour")

func _red_keys(section: Node3D) -> Array[OmniLight3D]:
	var result: Array[OmniLight3D] = []
	for fixture: Node in section.get_children():
		for child: Node in fixture.get_children():
			if child is OmniLight3D and child.has_meta(&"energy_share"): result.append(child)
	return result
