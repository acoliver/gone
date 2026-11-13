extends SimTestCase

func test_one_source_conserves_the_summed_energy_and_linear_colour_of_its_channels() -> void:
	var light := OmniLight3D.new()
	var row := Vector4(0.56, 1.0, 6.0, 1.5)
	EmergencyFixtureProfile.apply(light, row, 0.5)
	assert_true(is_equal_approx(light.get_meta(&"energy_share"), 2.56), "red, neutral and pod shares are summed at native vector precision")
	assert_true(is_equal_approx(light.light_energy, Lighting.emergency_energy() * 2.56 * 0.5), "source carries every channel's energy")
	var expected := (Lighting.EMERGENCY_RED.srgb_to_linear() + Lighting.EMERGENCY_FILL_COLOR.srgb_to_linear() * 0.56 + Lighting.POD_STATUS_RED.srgb_to_linear()) / 2.56
	assert_true(light.light_color.srgb_to_linear().is_equal_approx(expected), "linear RGB weighting preserves the channel mixture")
	assert_float_equal(light.omni_range, 6.0, "authored consolidated throw")
	assert_float_equal(light.omni_attenuation, 1.5, "authored consolidated falloff")
	light.free()

func test_original_key_and_fill_output_is_conserved_in_every_switched_space() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var rooms := [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]
	var expected := [21.84, 11.62, 9.6]
	for index: int in range(rooms.size()):
		var share := 0.0
		for light: OmniLight3D in rooms[index].lights(): share += light.light_energy / Lighting.FIXTURE_ENERGY
		for light: Light3D in rooms[index].find_children("EmergencyFill*", "Light3D", true, false): share += light.light_energy / Lighting.FIXTURE_ENERGY
		assert_true(is_equal_approx(share, expected[index]), "room %d retains its original key, pod and fill shares" % index)
		rooms[index].free()
