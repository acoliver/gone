extends SimTestCase

func test_idle_console_shows_only_a_dim_cursor_before_and_after_playback() -> void:
	var game := Game.new(114)
	var room := QuartersRoom.build(game)
	for state: QuartersMemory.State in [QuartersMemory.State.UNSEEN, QuartersMemory.State.REMEMBERED]:
		game.quarters.state = state
		room.process_frame()
		_assert_standby(room)
	game.quarters.press_console()
	for tick: int in range(QuartersMemory.TOTAL_TICKS): game.quarters.tick()
	room.process_frame()
	assert_int_equal(game.quarters.state, QuartersMemory.State.PRESENT, "completed sequence reaches Present")
	_assert_standby(room)
	room.free()

func test_playback_renders_phase_text_without_author_annotations() -> void:
	var game := Game.new(114)
	game.quarters.state = QuartersMemory.State.REMEMBERED
	var room := QuartersRoom.build(game)
	game.quarters.press_console()
	for phase: Array in [[0, "VIDEO DATA CORRUPTED"], [60, QuartersMemory.MESSAGE], [240, QuartersMemory.FAULT]]:
		game.quarters.elapsed = phase[0]
		room.process_frame()
		for label: Label3D in room.screen_labels:
			assert_true(label.text == QuartersRoom._wrapped(phase[1]), "only the phase text is rendered")
			assert_false("PLACEHOLDER" in label.text or "decisions.md" in label.text, "author annotations never appear in world")
			assert_float_equal(label.modulate.a, 1.0, "playback retains full text contrast")
			assert_true(String(label.name) == "ConsoleText", "display node has no development label")
	room.free()

func test_boots_close_view_is_accepted_and_required_in_both_states() -> void:
	var scenario := {"name": "boots-view", "mode": "capture", "content": "gameplay", "start": "quarters", "beats": [{"name": "boots", "tick": 1, "quarters_view": "boots"}]}
	assert_true(HarnessScenario.parse(JSON.stringify(scenario)).error == "", "boots camera accepted for quarters")
	for state: String in ["remembered", "present"]:
		assert_true(QuartersCapture.REQUIRED.has(state + "-boots"), "boots state capture required")

func _assert_standby(room: QuartersRoom) -> void:
	for label: Label3D in room.screen_labels:
		assert_true(label.text == "_", "idle display contains only a cursor")
		assert_float_equal(label.modulate.a, 0.25, "standby cursor is dimmer than playback")
