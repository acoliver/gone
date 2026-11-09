extends SimTestCase

const Samples = preload("res://tests/hatch_soffit_samples.gd")

func test_soffit_capture_gate_rejects_black_or_leaf_bright_samples() -> void:
	var image := Image.create(4, 2, false, Image.FORMAT_RGB8)
	image.fill(Color(0.2, 0.1, 0.05))
	var soffit := PackedVector2Array([Vector2(0, 0), Vector2(1, 0)])
	var leaf := PackedVector2Array([Vector2(2, 0), Vector2(3, 0)])
	assert_false(Samples.evaluate(image, soffit, leaf).passed, "soffit must be darker than leaf")
	image.set_pixel(0, 0, Color.BLACK)
	image.set_pixel(1, 0, Color(0.04, 0.01, 0.01))
	assert_false(Samples.evaluate(image, soffit, leaf).passed, "one pure black soffit sample fails")
	image.set_pixel(0, 0, Color(0.04, 0.01, 0.01))
	assert_true(Samples.evaluate(image, soffit, leaf).passed, "fill-lit soffit remains above floor and below leaf")

func test_zero_ao_cannot_extinguish_direct_light() -> void:
	assert_true(Surfaces.STEEL.code.contains("AO_LIGHT_AFFECT = 0.0;"), "baked AO affects ambient only, even at a zero-AO texel")

func test_regular_hatch_bounce_follows_white_fade_without_relighting_emergency() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var hall := Hallway.build(game)
	var fill := hall.get_node_or_null("RegularFillEnd") as OmniLight3D
	assert_true(fill != null, "white ceiling keys need a below-soffit end bounce")
	if fill == null:
		hall.free()
		return
	assert_true(fill.position == game.layout.section(&"D14-S-041").emergency_end_fill_position() - Vector3(0, 0, 2.6), "reuse the layout-owned bounce position")
	assert_int_equal(fill.light_cull_mask, Lighting.HALL_FILL_MASK, "bounce stays in the switched hall")
	assert_false(fill.shadow_enabled, "bounce has no shadow pass")
	assert_float_equal(fill.light_energy, 0, "regular bounce starts off on emergency")
	game.press_console()
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		hall.process_frame(Sim.LOGICAL_TICK_SECS)
		var expected := PackedFloat32Array([Lighting.regular_energy() * hall.white_level() * 0.12])[0]
		assert_float_equal(fill.light_energy, expected, "native float32 bounce energy follows the white fade clock")
	assert_true(fill.light_color == Lighting.REGULAR_WHITE and fill.light_energy > 0, "regular colour and energy after handoff")
	assert_float_equal((hall.get_node("EmergencyFillEnd") as OmniLight3D).light_energy, 0, "emergency bounce remains extinguished")
	hall.free()
