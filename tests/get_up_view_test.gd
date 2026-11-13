extends SimTestCase

func _player() -> Player:
	var game := Game.new(91)
	game.phase.wake_complete()
	var player := Player.build(game, null)
	player.scripted = true
	player._ready()
	return player

func _exit(player: Player) -> void:
	player.plane.offer_press(InputPlane.Buttons.ACTIVATE)
	for tick: int in range(Exit.EXIT_POSE_COUNT): player.step()

func _forward_yaw(game: Game) -> float:
	var poses := game.exit_path.poses()
	var direction := poses[3].foot() - poses[2].foot()
	return atan2(-direction.x, -direction.z)

func test_get_up_eases_to_level_exit_direction_in_thirty_ticks() -> void:
	var player := _player()
	_exit(player)
	var start := player.look_angles()
	var target := _forward_yaw(player.game)
	var yaw_travel := absf(InputPlane.wrap_angle(target - start.x))
	var previous := start
	for tick: int in range(1, 31):
		player.plane.offer_look(0.1, 0.1)
		player.step()
		var actual := player.look_angles()
		var t := float(tick) / 30
		var eased := t * t * (3 - 2 * t)
		assert_true(absf(InputPlane.wrap_angle(actual.x - lerp_angle(start.x, target, eased))) < 0.00001, "yaw follows the fixed-tick ease")
		assert_true(absf(actual.y - lerpf(start.y, 0, eased)) < 0.00001, "pitch follows the fixed-tick ease")
		assert_true(absf(InputPlane.wrap_angle(actual.x - previous.x)) <= yaw_travel * 1.5 / 30 + 0.00001, "no yaw snap beyond the ease's per-tick derivative")
		assert_true(absf(actual.y - previous.y) <= absf(start.y) * 1.5 / 30 + 0.00001, "no pitch snap beyond the ease's per-tick derivative")
		previous = actual
	assert_true(absf(InputPlane.wrap_angle(player.look_angles().x - target)) <= deg_to_rad(0.5), "faces out of the pod toward the wall")
	assert_true(absf(player.look_angles().y) <= deg_to_rad(0.5), "ends level")
	player.step()
	assert_true(player.look_angles().is_equal_approx(previous), "look offered during the ease was consumed, never buffered")
	player.plane.offer_look(0.1, -0.1)
	player.step()
	assert_true(absf(InputPlane.wrap_angle(player.look_angles().x - previous.x) - 0.1) < 0.00001, "normal yaw resumes")
	assert_true(absf(player.look_angles().y + 0.1) < 0.00001, "normal pitch resumes")
	player.free()

func test_render_frame_count_does_not_advance_get_up_ease() -> void:
	var first := _player()
	var second := _player()
	_exit(first)
	_exit(second)
	for tick: int in range(30):
		for frame: int in range(tick % 5): first.present_interpolated(0.5)
		first.step()
		second.step()
		assert_true(first.look_angles() == second.look_angles(), "ease advances only on the logical tick")
	first.free()
	second.free()
