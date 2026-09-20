extends SimTestCase
## Input fix tests for issues #31/#32/#33/#47/#55: the arrow keys alone
## ride the movement actions through the same synthetic input plane the
## harness uses, the forward key bridges the camera's -Z view onto the
## sim's +Z walk frame (issue #47's inverted axis), the look keys
## (comma/period, and the letters A/D for yaw and W/S for pitch) ride
## the same look channel and clamps as the mouse with per-tick delta
## summation, and Space and a left click are the act keys (E, Q, and R
## unused).

const DT: float = 1.0 / 60.0
const NEAR: float = 1e-4

const ScenarioModule := preload("res://harness/scenario.gd")

func _awake_game() -> Game:
	var game := Game.new()
	game.phase.wake_complete()
	return game

func _stand(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	for _segment: int in range(Exit.EXIT_POSE_COUNT - 1):
		motion.advance(plane, game, 0.0, DT)

func _key(physical: Key) -> InputEventKey:
	var event := InputEventKey.new()
	event.physical_keycode = physical
	return event

func _held_key(physical: Key, pressed: bool) -> InputEventKey:
	var event := _key(physical)
	event.pressed = pressed
	return event

func _click() -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	return event

func _near_float(actual: float, expected: float, message: String) -> void:
	if absf(actual - expected) >= NEAR:
		_fail("%s: expected %s, got %s" % [message, str(expected), str(actual)])

func _walk_to_hatch(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	var hatch := game.registry.hatch().center
	var adapter := InputPlane.ScriptedAdapter.new()
	for _tick: int in range(1400):
		var foot: Vector3 = motion.capsule().foot
		var to_hatch := Vector2(hatch.x - foot.x, hatch.y - foot.z)
		if to_hatch.length() <= PlayerMotion.HATCH_INTERACT_REACH * 0.9:
			break
		adapter.hold(1.0, 0.0)
		adapter.offer_tick(plane)
		motion.advance(plane, game, atan2(to_hatch.x, to_hatch.y), DT)
		plane.end_frame()
	assert_true(motion.failure().is_empty(), motion.failure())
	assert_float_in_range(Vector2(motion.capsule().foot.x - hatch.x, motion.capsule().foot.z - hatch.y).length(), 0.0, PlayerMotion.HATCH_INTERACT_REACH, "the walk arrived at the door")

func test_arrow_keys_map_onto_the_movement_actions() -> void:
	assert_true(InputMap.event_is_action(_key(KEY_UP), "move_forward"), "up arrow is move_forward")
	assert_true(InputMap.event_is_action(_key(KEY_DOWN), "move_back"), "down arrow is move_back")
	assert_true(InputMap.event_is_action(_key(KEY_LEFT), "move_left"), "left arrow is move_left")
	assert_true(InputMap.event_is_action(_key(KEY_RIGHT), "move_right"), "right arrow is move_right")

func test_wasd_no_longer_maps_onto_the_movement_actions() -> void:
	# Issue #55: the letters swivel the head, the arrows move; W/S/A/D
	# must not fire any movement action.
	for key: Key in [KEY_W, KEY_A, KEY_S, KEY_D]:
		for action: String in ["move_forward", "move_back", "move_left", "move_right"]:
			assert_false(InputMap.event_is_action(_key(key), action), "%s does not fire %s" % [OS.get_keycode_string(key), action])

func test_wasd_produces_no_movement_axis() -> void:
	# Each letter pressed and held leaves both movement axes at zero, so
	# the device producer offers no movement intent whatever the letter.
	for key: Key in [KEY_W, KEY_A, KEY_S, KEY_D]:
		Input.parse_input_event(_held_key(key, true))
		var forward: float = -Input.get_axis("move_back", "move_forward")
		var strafe: float = Input.get_axis("move_left", "move_right")
		Input.parse_input_event(_held_key(key, false))
		_near_float(forward, 0.0, "%s produces no forward axis" % OS.get_keycode_string(key))
		_near_float(strafe, 0.0, "%s produces no strafe axis" % OS.get_keycode_string(key))

func test_arrows_drive_movement_through_the_input_plane() -> void:
	# The device producer reads the action axes; an arrow press moves
	# them, and the plane carries the intent to the walk. The rig's
	# camera looks along Godot's -Z at the yaw while the sim's walk frame
	# steps along +Z, so the forward key offers the negative sim axis
	# and forward walks where the player looks.
	Input.action_press("move_forward")
	Input.action_press("move_right")
	var plane := InputPlane.new()
	plane.offer_movement(
		-Input.get_axis("move_back", "move_forward"),
		Input.get_axis("move_left", "move_right")
	)
	Input.action_release("move_forward")
	Input.action_release("move_right")
	var movement := plane.take_movement()
	_near_float(movement.x, -1.0, "the forward axis reached the plane as the negative sim axis")
	_near_float(movement.y, 1.0, "the strafe axis reached the plane")
	_near_float(plane.take_movement().x, 0.0, "the intent is taken once per tick")

func test_held_forward_walks_where_the_camera_looks() -> void:
	# Issue #47: the camera looks along the rig's -Z while the sim's walk
	# frame steps along +Z, so a forward key that reached the walk
	# unbridged stepped the capsule behind the view (up read as back).
	# With the yaw the rig carries while facing the hatch, a held forward
	# must step the capsule toward the hatch, not away from it.
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	var hatch := game.registry.hatch().center
	var foot: Vector3 = motion.capsule().foot
	var to_hatch := Vector2(hatch.x - foot.x, hatch.y - foot.z).normalized()
	var yaw := atan2(to_hatch.x, to_hatch.y) + PI
	var camera_forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
	Input.action_press("move_forward")
	plane.offer_movement(
		-Input.get_axis("move_back", "move_forward"),
		Input.get_axis("move_left", "move_right")
	)
	Input.action_release("move_forward")
	motion.advance(plane, game, yaw, DT)
	plane.end_frame()
	var stepped: Vector3 = motion.capsule().foot - foot
	assert_true(stepped.dot(camera_forward) > 0.002, "a held forward steps toward the camera's forward, not behind it: dot %s" % str(stepped.dot(camera_forward)))
	assert_true(motion.failure().is_empty(), motion.failure())

func test_look_keys_map_onto_yaw_actions_without_collisions() -> void:
	assert_true(InputMap.has_action("look_left"), "look_left exists")
	assert_true(InputMap.has_action("look_right"), "look_right exists")
	assert_true(InputMap.event_is_action(_key(KEY_COMMA), "look_left"), "comma turns left")
	assert_true(InputMap.event_is_action(_key(KEY_PERIOD), "look_right"), "period turns right")
	assert_true(InputMap.event_is_action(_key(KEY_A), "look_left"), "A turns left")
	assert_true(InputMap.event_is_action(_key(KEY_D), "look_right"), "D turns right")
	for action: String in ["move_forward", "move_back", "move_left", "move_right", "interact", "activate", "look_up", "look_down"]:
		assert_false(InputMap.event_is_action(_key(KEY_COMMA), action), "comma does not fire %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_PERIOD), action), "period does not fire %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_A), action), "A does not fire %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_D), action), "D does not fire %s" % action)
	for key: Key in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_W, KEY_S, KEY_E, KEY_SPACE, KEY_Q, KEY_R]:
		assert_false(InputMap.event_is_action(_key(key), "look_left"), "%s does not turn left" % OS.get_keycode_string(key))
		assert_false(InputMap.event_is_action(_key(key), "look_right"), "%s does not turn right" % OS.get_keycode_string(key))

func test_letter_pitch_keys_map_onto_the_pitch_actions() -> void:
	# Issue #55: W/S are the letters' pitch swivel, riding their own
	# actions without touching yaw, movement, or the act keys.
	assert_true(InputMap.has_action("look_up"), "look_up exists")
	assert_true(InputMap.has_action("look_down"), "look_down exists")
	assert_true(InputMap.event_is_action(_key(KEY_W), "look_up"), "W looks up")
	assert_true(InputMap.event_is_action(_key(KEY_S), "look_down"), "S looks down")
	for action: String in ["move_forward", "move_back", "move_left", "move_right", "interact", "activate", "look_left", "look_right"]:
		assert_false(InputMap.event_is_action(_key(KEY_W), action), "W does not fire %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_S), action), "S does not fire %s" % action)
	for key: Key in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_A, KEY_D, KEY_COMMA, KEY_PERIOD, KEY_E, KEY_SPACE, KEY_Q, KEY_R]:
		assert_false(InputMap.event_is_action(_key(key), "look_up"), "%s does not look up" % OS.get_keycode_string(key))
		assert_false(InputMap.event_is_action(_key(key), "look_down"), "%s does not look down" % OS.get_keycode_string(key))

func test_unused_letters_fire_no_game_actions() -> void:
	# Issue #55: Q, E, and R are deliberately unused.
	var game_actions: Array[String] = ["move_forward", "move_back", "move_left", "move_right",
		"look_left", "look_right", "look_up", "look_down", "activate", "interact"]
	for key: Key in [KEY_Q, KEY_E, KEY_R]:
		for action: String in game_actions:
			assert_false(InputMap.event_is_action(_key(key), action), "%s does not fire %s" % [OS.get_keycode_string(key), action])

func test_keyboard_look_yaw_rides_the_same_clamps_as_the_mouse() -> void:
	# Two seconds of held period: 240 degrees of right turn in per-tick
	# keyboard deltas, wrapping and clamping exactly like one equal mouse
	# delta through the same integrate path.
	var yaw := 0.0
	var pitch := InputPlane.PITCH_LIMIT
	for _tick: int in range(120):
		var angles := InputPlane.integrate_look(yaw, pitch, Vector2(-InputPlane.TURN_SPEED * DT, 0.0))
		yaw = angles.x
		pitch = angles.y
	_near_float(yaw, TAU / 3.0, "240 degrees of right turn wraps to +120 degrees")
	var mouse := InputPlane.integrate_look(0.0, InputPlane.PITCH_LIMIT, Vector2(-deg_to_rad(240.0), 0.0))
	_near_float(yaw, mouse.x, "per-tick keyboard turn equals one equal mouse delta")
	_near_float(pitch, InputPlane.PITCH_LIMIT, "keyboard look never touches pitch")
	_near_float(mouse.y, InputPlane.PITCH_LIMIT, "the mouse delta clamps pitch at the same stop")

func test_keyboard_pitch_rides_the_same_clamps_as_the_mouse() -> void:
	# Two seconds of held W: 180 degrees of up pitch in per-tick
	# keyboard deltas, clamping at the vertical stop exactly like one
	# equal mouse delta through the same integrate path; held S clamps
	# at the lower stop.
	var pitch := 0.0
	for _tick: int in range(120):
		var angles := InputPlane.integrate_look(0.0, pitch, Vector2(0.0, InputPlane.PITCH_SPEED * DT))
		pitch = angles.y
	_near_float(pitch, InputPlane.PITCH_LIMIT, "180 degrees of up pitch clamps at the vertical stop")
	var mouse := InputPlane.integrate_look(0.0, 0.0, Vector2(0.0, deg_to_rad(180.0)))
	_near_float(pitch, mouse.y, "per-tick keyboard pitch equals one equal mouse delta")
	_near_float(mouse.x, 0.0, "the mouse delta never touches yaw")
	var down := 0.0
	for _tick: int in range(120):
		var angles := InputPlane.integrate_look(0.0, down, Vector2(0.0, -InputPlane.PITCH_SPEED * DT))
		down = angles.y
	_near_float(down, -InputPlane.PITCH_LIMIT, "held S clamps at the lower stop")

func test_opposing_look_keys_cancel_like_opposing_movement_keys() -> void:
	Input.action_press("look_left")
	Input.action_press("look_right")
	var axis := Input.get_axis("look_left", "look_right")
	Input.action_release("look_left")
	Input.action_release("look_right")
	_near_float(axis, 0.0, "comma and period held together cancel")
	Input.action_press("look_down")
	Input.action_press("look_up")
	var pitch_axis := Input.get_axis("look_down", "look_up")
	Input.action_release("look_down")
	Input.action_release("look_up")
	_near_float(pitch_axis, 0.0, "W and S held together cancel")

func test_mouse_and_keyboard_deltas_sum_in_one_tick() -> void:
	var plane := InputPlane.new()
	# One tick of the device producer: ten pixels of mouse right plus the
	# held period key, both offered onto the same look channel.
	plane.offer_look_pixels(Vector2(10.0, 0.0))
	plane.offer_look(-1.0 * InputPlane.TURN_SPEED * DT, 0.0)
	var taken := plane.take_look()
	_near_float(taken.x, -(10.0 * InputPlane.LOOK_SENSITIVITY + InputPlane.TURN_SPEED * DT), "the tick's mouse and keyboard yaw sum")
	_near_float(taken.y, 0.0, "neither channel moves pitch")
	_near_float(plane.take_look().x, 0.0, "the merged delta is taken once")

func test_letters_and_mouse_deltas_sum_in_one_tick() -> void:
	# One tick of the device producer with the mouse moving and the
	# letters held: every producer lands on the one look channel and the
	# single take_look drains all of it.
	Input.action_press("look_right")
	Input.action_press("look_up")
	var turn := Input.get_axis("look_left", "look_right")
	var pitch := Input.get_axis("look_down", "look_up")
	Input.action_release("look_right")
	Input.action_release("look_up")
	var plane := InputPlane.new()
	plane.offer_look_pixels(Vector2(10.0, -4.0))
	plane.offer_look(-turn * InputPlane.TURN_SPEED * DT, pitch * InputPlane.PITCH_SPEED * DT)
	var taken := plane.take_look()
	_near_float(taken.x, -(10.0 * InputPlane.LOOK_SENSITIVITY + InputPlane.TURN_SPEED * DT), "the tick's mouse and D yaw sum")
	_near_float(taken.y, 4.0 * InputPlane.LOOK_SENSITIVITY + InputPlane.PITCH_SPEED * DT, "the tick's mouse and W pitch sum")
	_near_float(plane.take_look().x, 0.0, "the merged yaw is taken once")
	_near_float(plane.take_look().y, 0.0, "both axes drain together")

func test_left_click_and_space_are_the_act_keys() -> void:
	# Issue #55: Space and a left click are the act keys; E is not.
	assert_true(InputMap.event_is_action(_click(), "interact"), "a left click is an interact")
	assert_true(InputMap.event_is_action(_click(), "activate"), "a left click is an activate")
	assert_true(InputMap.event_is_action(_key(KEY_SPACE), "activate"), "Space activates")
	assert_true(InputMap.event_is_action(_key(KEY_SPACE), "interact"), "Space interacts")
	for action: String in ["interact", "activate"]:
		assert_false(InputMap.event_is_action(_key(KEY_E), action), "E does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_COMMA), action), "comma does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_PERIOD), action), "period does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_W), action), "W does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_A), action), "A does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_S), action), "S does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_D), action), "D does not %s" % action)
		assert_false(InputMap.event_is_action(_key(KEY_UP), action), "up arrow does not %s" % action)

func test_click_edges_start_the_authored_get_up_after_wake() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	# The two edges one click produces, offered the way the device
	# producer offers them and consumed in the player's order.
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	plane.offer_press(InputPlane.Buttons.INTERACT)
	motion.advance(plane, game, 0.0, DT)
	assert_int_equal(motion.state(), PlayerMotion.BodyState.GET_UP, "the click's activate edge starts the get-up")
	assert_false(motion.interact_with_hatch(plane, game), "the same click's interact edge does not refuse mid-get-up")
	var early_game := Game.new()
	var early_motion := PlayerMotion.new()
	var early_plane := InputPlane.new()
	early_plane.offer_press(InputPlane.Buttons.ACTIVATE)
	early_motion.advance(early_plane, early_game, 0.0, DT)
	assert_int_equal(early_motion.state(), PlayerMotion.BodyState.LYING, "a click before wake completes starts nothing")

func test_click_edge_refuses_at_the_hatch() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	_walk_to_hatch(motion, game, plane)
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(plane, game), "the click's interact edge refuses at the door")
	assert_int_equal(motion.refusals, 1, "one click, one refusal")

func test_click_edges_consume_exactly_once_interleaved() -> void:
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the first click edge is consumed")
	assert_false(plane.take_press(InputPlane.Buttons.INTERACT), "the first click edge is consumed exactly once")
	plane.end_frame()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the click edge on a later tick is consumed")
	assert_false(plane.take_press(InputPlane.Buttons.INTERACT), "the later click edge is consumed exactly once")
	plane.end_frame()
	# Space and click in the same tick transition each action state once,
	# so the producer offers one edge per button whatever the press order.
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "Space and click in one tick deliver one edge")
	assert_false(plane.take_press(InputPlane.Buttons.INTERACT), "no second edge whatever the order")
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var hatch_plane := InputPlane.new()
	_stand(motion, game, hatch_plane)
	_walk_to_hatch(motion, game, hatch_plane)
	hatch_plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(hatch_plane, game), "a click refuses")
	hatch_plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(hatch_plane, game), "the click on the next tick refuses again")
	hatch_plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(hatch_plane, game), "the same-tick Space and click pair refuses once")
	assert_false(motion.interact_with_hatch(hatch_plane, game), "nothing is left to consume")
	assert_int_equal(motion.refusals, 3, "three edges across the ticks, three refusals")

func test_scenario_accepts_key_turn_actions() -> void:
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify({
		"name": "key-turn-probe", "seed": 1,
		"actions": [
			{"tick": 0, "type": "key_turn", "dir": "right"},
			{"tick": 1, "type": "key_turn", "dir": "left"},
			{"tick": 2, "type": "key_turn", "dir": "right"},
			{"tick": 2, "type": "key_turn", "dir": "right"},
		],
		"beats": [],
	}))
	assert_true(parsed.error.is_empty(), parsed.error)
	if parsed.error.is_empty():
		var adapter := ScenarioModule.InputAdapter.new(parsed.scenario.actions, 60)
		assert_float_equal(adapter.step().key_turn, 1.0, "right is the positive turn axis")
		assert_float_equal(adapter.step().key_turn, -1.0, "left is the negative turn axis")
		assert_float_equal(adapter.step().key_turn, 2.0, "same-tick key turns sum")

func test_scenario_rejects_a_malformed_key_turn_dir() -> void:
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify({
		"name": "bad", "actions": [{"tick": 0, "type": "key_turn", "dir": "up"}], "beats": []}))
	assert_false(parsed.error.is_empty(), "an unknown turn direction fails")

func test_scripted_key_turn_matches_the_device_look_offer() -> void:
	# The app lane converts the tick's key_turn axis with the device
	# producer's exact expression, so scripted and held-key turns agree.
	var input := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "key_turn", "dir": "right"},
	], 60)
	var axis: float = input.step().key_turn
	var scripted := InputPlane.ScriptedAdapter.new()
	scripted.look(-axis * InputPlane.TURN_SPEED / 60.0, 0.0)
	var scripted_plane := InputPlane.new()
	scripted.offer_tick(scripted_plane)
	var device_plane := InputPlane.new()
	device_plane.offer_look(-1.0 * InputPlane.TURN_SPEED * DT, 0.0)
	_near_float(scripted_plane.take_look().x, device_plane.take_look().x, "one scripted key-turn tick equals the device offer")
	_near_float(scripted_plane.take_look().x, 0.0, "the scripted turn is offered for exactly one tick")

func test_scenario_accepts_key_pitch_actions() -> void:
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify({
		"name": "key-pitch-probe", "seed": 1,
		"actions": [
			{"tick": 0, "type": "key_pitch", "dir": "up"},
			{"tick": 1, "type": "key_pitch", "dir": "down"},
			{"tick": 2, "type": "key_pitch", "dir": "up"},
			{"tick": 2, "type": "key_pitch", "dir": "up"},
		],
		"beats": [],
	}))
	assert_true(parsed.error.is_empty(), parsed.error)
	if parsed.error.is_empty():
		var adapter := ScenarioModule.InputAdapter.new(parsed.scenario.actions, 60)
		assert_float_equal(adapter.step().key_pitch, 1.0, "up is the positive pitch axis")
		assert_float_equal(adapter.step().key_pitch, -1.0, "down is the negative pitch axis")
		assert_float_equal(adapter.step().key_pitch, 2.0, "same-tick key pitches sum")

func test_scenario_rejects_a_malformed_key_pitch_dir() -> void:
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify({
		"name": "bad", "actions": [{"tick": 0, "type": "key_pitch", "dir": "left"}], "beats": []}))
	assert_false(parsed.error.is_empty(), "an unknown pitch direction fails")

func test_scenario_rejects_a_key_pitch_without_a_dir() -> void:
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify({
		"name": "bad", "actions": [{"tick": 0, "type": "key_pitch"}], "beats": []}))
	assert_false(parsed.error.is_empty(), "a key_pitch with no direction fails")

func test_scripted_key_pitch_matches_the_device_look_offer() -> void:
	# The app lane converts the tick's key_pitch axis with the device
	# producer's exact expression, so scripted and held-key pitch agree.
	var input := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "key_pitch", "dir": "up"},
	], 60)
	var axis: float = input.step().key_pitch
	var scripted := InputPlane.ScriptedAdapter.new()
	scripted.look(0.0, axis * InputPlane.PITCH_SPEED / 60.0)
	var scripted_plane := InputPlane.new()
	scripted.offer_tick(scripted_plane)
	var device_plane := InputPlane.new()
	device_plane.offer_look(0.0, 1.0 * InputPlane.PITCH_SPEED * DT)
	_near_float(scripted_plane.take_look().y, device_plane.take_look().y, "one scripted key-pitch tick equals the device offer")
	_near_float(scripted_plane.take_look().y, 0.0, "the scripted pitch is offered for exactly one tick")
