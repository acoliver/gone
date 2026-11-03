extends SimTestCase

class DevicePlayer extends Player:
	var now_usec := 1000000
	func _device_time_usec() -> int:
		return now_usec

func _player() -> DevicePlayer:
	var player := DevicePlayer.new()
	player.game = Game.new(0)
	player.game.phase.wake_complete()
	player.scripted = true
	player._ready()
	player.scripted = false
	return player

func _key(player: Player, code: Key, pressed: bool, echo := false) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = pressed
	event.echo = echo
	Input.parse_input_event(event)
	Input.flush_buffered_events()
	player._input(event)

func _collect(player: Player) -> void:
	player.plane.end_frame()
	player._collect_device_input(Sim.LOGICAL_TICK_SECS)

func test_brief_release_preserves_all_movement_axes() -> void:
	var player := _player()
	for code: Key in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT]:
		_key(player, code, true)
		_collect(player)
		var held := player.plane.take_movement()
		assert_true(held != Vector2.ZERO, "held arrow produces movement")
		_key(player, code, false)
		player.now_usec += 8333
		_collect(player)
		assert_true(player.plane.take_movement() == held, "an 8ms device gap preserves %s" % OS.get_keycode_string(code))
		player.now_usec += 60000
		_collect(player)
		assert_true(player.plane.take_movement() == Vector2.ZERO, "a real release expires")
	player.free()

func test_brief_release_preserves_keyboard_yaw_and_pitch() -> void:
	var player := _player()
	for code: Key in [KEY_A, KEY_D, KEY_COMMA, KEY_PERIOD, KEY_W, KEY_S]:
		_key(player, code, true)
		_collect(player)
		var held := player.plane.take_look()
		assert_true(held != Vector2.ZERO, "held look produces a rate")
		_key(player, code, false)
		player.now_usec += 10000
		_collect(player)
		assert_true(player.plane.take_look() == held, "a 10ms device gap preserves look")
		player.now_usec += 60000
		_collect(player)
		assert_true(player.plane.take_look() == Vector2.ZERO, "released look stops")
	player.free()

func test_release_grace_expires_at_sixty_real_milliseconds() -> void:
	var player := _player()
	_key(player, KEY_UP, true)
	_key(player, KEY_UP, false)
	player.now_usec += 59999
	_collect(player)
	assert_float_equal(player.plane.take_movement().x, -1.0, "release remains held before deadline")
	player.now_usec += 1
	_collect(player)
	assert_float_equal(player.plane.take_movement().x, 0.0, "release expires at deadline regardless of tick count")
	player.free()

func test_repress_cancels_release_deadline_and_echo_keeps_hold() -> void:
	var player := _player()
	_key(player, KEY_UP, true)
	_key(player, KEY_UP, false)
	player.now_usec += 8000
	_key(player, KEY_UP, true)
	player.now_usec += 70000
	_key(player, KEY_UP, true, true)
	_collect(player)
	assert_float_equal(player.plane.take_movement().x, -1.0, "repress and echo retain continuous hold past old deadline")
	_key(player, KEY_UP, false)
	player.now_usec += 60000
	_collect(player)
	assert_float_equal(player.plane.take_movement().x, 0.0, "final release still expires")
	player.free()

func test_opposing_device_keys_cancel_during_grace() -> void:
	var player := _player()
	_key(player, KEY_UP, true)
	_key(player, KEY_DOWN, true)
	_collect(player)
	assert_true(player.plane.take_movement() == Vector2.ZERO, "opposing holds cancel")
	_key(player, KEY_UP, false)
	_collect(player)
	assert_true(player.plane.take_movement() == Vector2.ZERO, "brief release does not pulse the opposing axis")
	player.now_usec += 60000
	_collect(player)
	assert_float_equal(player.plane.take_movement().x, 1.0, "opposite remains held after grace expires")
	_key(player, KEY_DOWN, false)
	player.free()

func test_scripted_input_ignores_device_hold_release_and_edges() -> void:
	var player := _player()
	player.scripted = true
	_key(player, KEY_UP, true)
	_key(player, KEY_UP, false)
	_key(player, KEY_SPACE, true)
	_collect(player)
	assert_true(player.plane.take_movement() == Vector2.ZERO, "scripted lane ignores device motion")
	assert_int_equal(player.plane.pending_edges(), 0, "scripted lane ignores device edges")
	var adapter := InputPlane.ScriptedAdapter.new()
	adapter.hold(1, 0)
	adapter.offer_tick(player.plane)
	assert_float_equal(player.plane.take_movement().x, 1.0, "scripted hold remains exact")
	adapter.release()
	adapter.offer_tick(player.plane)
	assert_true(player.plane.take_movement() == Vector2.ZERO, "scripted release has no grace")
	_key(player, KEY_SPACE, false)
	player.free()

func test_focus_loss_clears_release_grace() -> void:
	var player := _player()
	_key(player, KEY_UP, true)
	_key(player, KEY_UP, false)
	player.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	_collect(player)
	assert_true(player.plane.take_movement() == Vector2.ZERO, "unfocused game cannot coast on device grace")
	player.free()

func test_native_space_edges_ignore_echo_and_keep_action_press_support() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), [
		"--headless", "--fixed-fps", "60", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/device_input_checks.gd",
	], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_true(text.contains("DEVICE EDGE PASS"), "native key and action edges completed")
