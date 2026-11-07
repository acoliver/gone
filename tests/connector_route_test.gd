extends SimTestCase
# New pod #88: regenerated ordinary-input routes retain exact schedule/digest checks.

const Driver := preload("res://tests/connector_route_driver.gd")

func test_both_wells_full_real_player_journey_and_replay_digest() -> void:
	var digests: Array[String] = []
	for _replay: int in range(2):
		var game := Game.new(0)
		var player := Player.build(game, null)
		player.scripted = true
		player.adapter = InputPlane.ScriptedAdapter.new()
		player._ready()
		game.wake_state.mark_ready()
		var route := Driver.new(player, 40000)
		route.opening()
		route.trip(1)
		route.trip(0)
		var opened: Array[StringName] = []
		for id: StringName in game.layout.door_ids():
			var spec := game.layout.door(id)
			if spec.kind() == ShipLayout.DoorKind.HATCH and game.doors.snapshot(id).state == Doors.State.OPEN:
				opened.append(id)
		assert_true(opened == [&"D14-C-000-H-AFT", &"D14-C-000-H-FORE", &"D14-C-001-H-AFT", &"D14-C-001-H-FORE"], "exactly the four D14 internal hatches opened")
		assert_true(game.power_active and game.door_open and game.power_door_open and player.motion.rod_carried, "opening state survives both complete trips")
		assert_int_equal(player.motion.console_presses, 1, "console state not replayed or reset")
		digests.append("\n".join(route.digest_lines).sha256_text())
		player.free()
	assert_true(digests[0] == digests[1], "fixed seed/input event digest repeats")
	# Whole generated hardware changes parked collision and journey timing.
	# Both complete real-input replays must match the newly compiled digest.
	assert_true(digests[0] == "46cdf6adef8be9376f4168dc9e5f02e4945613c1333b3ef4ad9cb2b18d475266", "pinned full journey event digest")
	print("connector route digest: ", digests[0])

func test_climb_channel_is_single_consumption_and_scenario_validated() -> void:
	var plane := InputPlane.new()
	var adapter := InputPlane.ScriptedAdapter.new()
	adapter.climb(1)
	adapter.offer_tick(plane)
	assert_float_equal(plane.take_climb(), 1, "dedicated positive intent ascends")
	assert_true(plane.take_climb() == null, "channel consumed exactly once")
	adapter.climb(-1)
	adapter.offer_tick(plane)
	plane.end_frame()
	assert_true(plane.take_climb() == null, "unconsumed climb expires")
	var parsed := HarnessScenario.parse('{"name":"climb","actions":[{"tick":0,"type":"climb","value":1}]}')
	assert_true(parsed.error.is_empty(), "scenario accepts climb")
	var invalid := HarnessScenario.parse('{"name":"bad","actions":[{"tick":0,"type":"climb","value":2}]}')
	assert_false(invalid.error.is_empty(), "scenario rejects excessive climb")

func test_dedicated_actions_keep_on_foot_pitch_bindings() -> void:
	for fixture: Array in [[KEY_W, "climb_up", "look_up"], [KEY_S, "climb_down", "look_down"]]:
		var event := InputEventKey.new()
		event.physical_keycode = fixture[0]
		assert_true(InputMap.event_is_action(event, fixture[1]), "dedicated mounted action")
		assert_true(InputMap.event_is_action(event, fixture[2]), "on-foot pitch retained")

func test_real_device_climbing_suppresses_letter_pitch_but_keeps_mouse() -> void:
	var game := Game.new(0)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := Driver.new(player, 6000)
	route.opening()
	route.enter_well(1)
	route.dismount(14)
	route.look_at(player.motion.eye(game) + Vector3.FORWARD, 85)
	route.press()
	assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.WALK, "looking above the ladder cannot mount")
	route.mount()
	assert_false(Interactions.context_for(game, player.motion).walking, "doors are disabled while mounted")
	player.scripted = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	var height := player.motion.locomotion.ladder_state().height()
	var pitch := player.look_angles().y
	for action: String in ["climb_up", "look_up", "move_forward"]:
		Input.action_press(action)
	player.step()
	for action: String in ["climb_up", "look_up", "move_forward"]:
		Input.action_release(action)
	var q := exp(-log(20.0) / 9)
	var velocity := 1.5 * (1 - q)
	var expected_height := height + velocity / 60
	assert_float_equal(player.motion.locomotion.ladder_state().height(), expected_height, "W plus Up eases up once, never twice")
	assert_float_equal(player.look_angles().y, pitch, "mounted W does not pitch")
	var event := InputEventMouseMotion.new()
	event.relative = Vector2(5, -8)
	# Headless DisplayServer cannot capture a cursor; inject the same mouse-pixel channel.
	player.scripted = true
	player.plane.offer_look_pixels(event.relative)
	player.step()
	player.scripted = false
	assert_float_in_range(player.look_angles().y - pitch, 8 * InputPlane.LOOK_SENSITIVITY - 1e-8, 8 * InputPlane.LOOK_SENSITIVITY + 1e-8, "mouse pitch remains available while mounted")
	var before_capture := expected_height
	expected_height = height + (expected_height - height) * q
	if absf(expected_height - height) <= Controller.PENETRATION_TOLERANCE:
		expected_height = height
	velocity = (expected_height - before_capture) * 60
	var ladder := player.motion.locomotion.ladder_state()
	assert_true(absf(ladder.height() - expected_height) < 1e-10, "mouse-only tick captures toward nearby landing")
	Input.action_press("climb_down")
	Input.action_press("look_down")
	player.step()
	Input.action_release("climb_down")
	Input.action_release("look_down")
	velocity = -1.5 + (velocity + 1.5) * q
	expected_height += velocity / 60
	assert_true(velocity < 0, "S reverses climb speed downward")
	assert_true(absf(ladder.height() + ladder.pending() - expected_height) < 1e-10, "S preserves eased signed height")
	player.scripted = true
	player.adapter.hold(-1, 0)
	player.step()
	velocity = 1.5 + (velocity - 1.5) * q
	expected_height += velocity / 60
	assert_true(absf(ladder.height() + ladder.pending() - expected_height) < 1e-10, "legacy negative simulation forward eases upward")
	player.adapter.climb(-1)
	var before := player.motion.capsule().foot
	# Check rejection at the state boundary without invoking Player's process-exit policy.
	player.adapter.offer_tick(player.plane)
	player.motion.advance(player.plane, game, player.look_angles().x, Sim.LOGICAL_TICK_SECS)
	assert_false(player.motion.failure().is_empty(), "contradictory scripted channels fail fast")
	assert_close(player.motion.capsule().foot, before, "contradiction cannot mutate pose")
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	player.free()
