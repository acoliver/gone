extends SimTestCase

func _player() -> Player:
	var game := Game.new(0)
	game.phase.wake_complete()
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	return player

func _stand(player: Player, step: GameStep) -> void:
	player.adapter.press(InputPlane.Buttons.ACTIVATE)
	for _tick: int in range(Exit.EXIT_POSE_COUNT):
		step.advance()
	player.adapter.look(-player.look_angles().x, -player.look_angles().y)
	step.advance()

func test_presented_eye_interpolates_without_mutating_sim() -> void:
	var player := _player()
	var step := GameStep.new(player.game, player)
	_stand(player, step)
	var before := player.motion.eye(player.game)
	player.adapter.hold(1, 0)
	step.advance()
	var after := player.motion.eye(player.game)
	var foot := player.motion.capsule().foot
	var speed := player.motion.walk_speed()
	var tick := step.logical_tick
	assert_true(after.distance_to(before) > 0.005, "the real fixed tick moves the eye")
	for fraction: float in [0.0, 0.25, 0.5, 1.0]:
		player.present_interpolated(fraction)
		assert_vec3_equal(player.position, before.lerp(after, fraction), "presented eye follows the fraction")
		assert_vec3_equal(player.motion.eye(player.game), after, "presentation never writes the sim eye")
		assert_vec3_equal(player.motion.capsule().foot, foot, "presentation never writes the capsule")
		assert_float_equal(player.motion.walk_speed(), speed, "presentation never advances the speed ramp")
		assert_int_equal(step.logical_tick, tick, "presentation never consumes a logical tick")
	player.free()

func test_look_interpolates_across_yaw_wrap_and_in_pitch() -> void:
	var player := _player()
	var step := GameStep.new(player.game, player)
	_stand(player, step)
	player.adapter.look(PI - 0.01, 0.1)
	step.advance()
	var before := player.look_angles()
	player.adapter.look(0.02, 0.2)
	step.advance()
	var after := player.look_angles()
	player.present_interpolated(0.5)
	assert_true(absf(absf(player.rotation.y) - PI) < 1e-5, "yaw takes the short arc across the wrap")
	assert_float_equal(player.camera.rotation.x, Vector2(0, 0.2).y, "pitch follows the fraction")
	assert_true(absf(InputPlane.wrap_angle(player.rotation.y - before.x)) < 0.011, "halfway yaw remains near the previous yaw")
	assert_true(player.look_angles() == after, "view interpolation leaves logical look unchanged")
	player.apply_wake_sway(Vector2.ZERO)
	assert_true(absf(absf(player.rotation.y) - PI) < 1e-5, "the completed wake presenter does not restore tick-stepped look")
	assert_float_equal(player.camera.rotation.x, Vector2(0, 0.2).y, "wake projection preserves presented pitch")
	player.free()

func test_rendered_pose_does_not_feed_the_next_tick() -> void:
	var rendered := _player()
	var exact := _player()
	var rendered_step := GameStep.new(rendered.game, rendered)
	var exact_step := GameStep.new(exact.game, exact)
	_stand(rendered, rendered_step)
	_stand(exact, exact_step)
	for index: int in range(20):
		for player: Player in [rendered, exact]:
			player.adapter.hold(1, 0)
			player.adapter.look(0.01, 0.005)
		rendered_step.advance()
		exact_step.advance()
		assert_vec3_equal(rendered.motion.eye(rendered.game), exact.motion.eye(exact.game), "frame count never affects accepted motion")
		assert_true(rendered.look_angles() == exact.look_angles(), "frame count never affects logical look")
		rendered.present_interpolated(float(index % 4) / 4.0)
		assert_vec3_equal(rendered.sim_forward(), exact.sim_forward(), "logical gaze is independent of presented pitch and yaw")
		assert_float_equal(rendered.motion.walk_speed(), exact.motion.walk_speed(), "frame count never affects ramp time")
	rendered.free()
	exact.free()

func test_harness_default_and_exact_presentation_remain_tick_pinned() -> void:
	var player := _player()
	var step := GameStep.new(player.game, player)
	_stand(player, step)
	player.adapter.hold(1, 0)
	player.adapter.look(0.1, 0.2)
	step.advance()
	player._process(0.001)
	assert_vec3_equal(player.position, player.motion.eye(player.game), "harness default stays at the exact tick")
	assert_float_equal(player.rotation.y, player.look_angles().x, "harness yaw stays at the exact tick")
	player.present_interpolated(0.25)
	player.present()
	assert_vec3_equal(player.position, player.motion.eye(player.game), "exact presentation restores the sim eye")
	assert_float_equal(player.rotation.y, player.look_angles().x, "exact presentation restores sim yaw")
	assert_float_equal(player.camera.rotation.x, player.look_angles().y, "exact presentation restores sim pitch")
	player.free()

func test_interpolation_is_initialized_at_spawn() -> void:
	var player := _player()
	player.present_interpolated(0.25)
	assert_vec3_equal(player.position, player.motion.eye(player.game), "the first frame never interpolates from the origin")
	assert_float_equal(player.rotation.y, player.look_angles().x, "the first frame has the authored yaw")
	assert_float_equal(player.camera.rotation.x, player.look_angles().y, "the first frame has the authored pitch")
	player.free()
