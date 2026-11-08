extends SimTestCase

func test_player_lens_is_ninety_degrees_horizontal_at_sixteen_nine() -> void:
	var game := Game.new(91)
	var player := Player.build(game, null)
	player.scripted = true
	player._ready()
	assert_int_equal(player.camera.keep_aspect, Camera3D.KEEP_HEIGHT, "vertical lens stays fixed as the viewport changes")
	var horizontal := rad_to_deg(2 * atan(tan(deg_to_rad(player.camera.fov / 2)) * 16.0 / 9.0))
	assert_true(absf(horizontal - 90.0) < 0.001, "16:9 horizontal field of view")
	assert_float_equal(PlacementTruth.STANDING_EYE_HEIGHT, 1.6, "eye height remains unchanged")
	player.free()
