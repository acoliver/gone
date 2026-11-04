extends SimTestCase

func _player(game: Game) -> Player:
	var player := Player.build(game, null)
	player.scripted = true
	player._ready()
	return player

func test_one_step_and_capture_pause_freeze_all_logic() -> void:
	var game := Game.new(0)
	var player := _player(game)
	var step := GameStep.new(game, player)
	var lighting := Lighting.build(game)
	var hallway := Hallway.build(game)
	step.fixtures.assign([lighting, hallway])
	game.light_hallway()
	var press := Doors.Context.new()
	press.face_id = game.layout.door(ShipLayout.POWER_DOOR_ID).face_ids()[0]
	game.doors.press(ShipLayout.POWER_DOOR_ID, press)
	game.wake_state.mark_ready()
	step.advance()
	assert_int_equal(game.wake_state.current_tick(), 1, "one call consumes one wake tick")
	assert_int_equal(step.logical_tick, 1, "one logical tick")
	var before := player.position
	var fade_before := hallway.level()
	var fills := hallway.find_children("EmergencyFill*", "OmniLight3D", true, false)
	assert_int_equal(fills.size(), 4, "four hall fills follow the logical clock")
	var fill_before: float = fills[0].light_energy if not fills.is_empty() else -1.0
	var door_before := game.doors.snapshot(ShipLayout.POWER_DOOR_ID).offset
	assert_true(fade_before > 0 and fade_before < 1, "a fade is running before capture")
	for _frame: int in range(30):
		step.advance(true)
	assert_int_equal(step.logical_tick, 1, "capture freezes the logical clock")
	assert_int_equal(game.wake_state.current_tick(), 1, "capture freezes wake")
	assert_vec3_equal(player.position, before, "capture freezes movement")
	assert_float_equal(lighting.level(), 1.0, "capture holds fixture state")
	assert_float_equal(hallway.level(), fade_before, "capture freezes a running fade")
	for fill: OmniLight3D in fills:
		assert_float_equal(fill.light_energy, fill_before, "capture freezes the warm fill with the keys")
	assert_vec3_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).offset, door_before, "capture freezes a running door")
	player.free()
	lighting.free()
	hallway.free()

func test_wake_completion_does_not_require_a_presented_frame() -> void:
	var game := Game.new(0)
	var step := GameStep.new(game)
	game.wake_state.mark_ready()
	for _tick: int in range(281):
		step.advance()
	assert_int_equal(game.phase.current(), Phase.Wake.WAKING, "wake stays gated through tick 281")
	step.advance()
	assert_int_equal(game.phase.current(), Phase.Wake.AWAKE_IN_POD, "logical tick 282 completes the phase")
	for _tick: int in range(8):
		step.advance()
	assert_int_equal(game.phase.current(), Phase.Wake.AWAKE_IN_POD, "completion happens once")

func test_unhandled_edge_expires_and_previous_eye_samples_smoke() -> void:
	var game := Game.new(0)
	var player := _player(game)
	var step := GameStep.new(game, player)
	step.smoke = SmokeSymptoms.new(game.layout)
	player.plane.offer_press(InputPlane.Buttons.INTERACT)
	var previous := player.motion.eye(game)
	step.advance()
	assert_int_equal(player.plane.pending_edges(), 0, "unused edge expires")
	assert_vec3_equal(step.sampled_eye, previous, "smoke samples the previous accepted eye")
	player.free()
