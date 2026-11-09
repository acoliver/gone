extends SimTestCase

func test_demo_start_is_opt_in_and_secondary_power_is_ready() -> void:
	assert_true(DemoStart.selected(PackedStringArray()) == "stasis", "default start unchanged")
	assert_true(DemoStart.selected(PackedStringArray(["--start", "quarters"])) == "quarters", "explicit demo option")
	var player := _player()
	assert_int_equal(player.motion.deck(), 16, "demo deck")
	assert_vec3_equal(player.motion.capsule().foot, Vector3(45, -10.695, 0), "corridor spawn")
	assert_true(player.sim_forward().dot(Vector3.BACK) > 0.999, "faces quarters door")
	assert_true(player.game.power_active and player.game.hallway_lit and player.game.wake_state.is_complete(), "secondary power and standing start")
	assert_int_equal(player.game.quarters.state, QuartersMemory.State.UNSEEN, "spawn does not fabricate entry")
	player.free()

func test_saved_scenario_replays_normal_input_and_stays_present_on_reentry() -> void:
	var text := FileAccess.get_file_as_string("res://scenarios/quarters-demo.json")
	var parsed := HarnessScenario.parse(text)
	assert_true(parsed.error == "", "quarters scenario parses")
	var scenario: HarnessScenario = parsed.scenario
	assert_true(scenario.start == "quarters", "scenario opts in")
	var player := _player()
	var route := HarnessRoute.new(player, scenario.max_frames)
	var next := 0
	var raw: Dictionary = JSON.parse_string(text)
	while route.tick < scenario.max_frames - 99:
		var offered: Array = []
		while next < raw.actions.size() and int(raw.actions[next].tick) == route.tick:
			offered.append(raw.actions[next])
			next += 1
		route.step(offered)
		for beat: Dictionary in scenario.beats:
			if int(beat.tick) + 1 == route.tick:
				var expected := QuartersMemory.State.REMEMBERED
				if beat.name == "corridor-door": expected = QuartersMemory.State.UNSEEN
				elif String(beat.name).begins_with("console-"): expected = QuartersMemory.State.PLAYING
				elif String(beat.name).begins_with("present-"): expected = QuartersMemory.State.PRESENT
				assert_int_equal(player.game.quarters.state, expected, "replayed state at " + beat.name)
	assert_int_equal(player.game.quarters.state, QuartersMemory.State.PRESENT, "present survives walking out and in")
	assert_int_equal(player.motion.console_presses, 1, "one accepted ordinary console interaction")
	assert_int_equal(player.game.doors.snapshot(QuartersLayout.DOOR).releases, 1, "one corridor manual release")
	assert_true(player.motion.failure() == "", "furniture paths sweep without motion errors")
	player.free()

func test_harness_start_and_camera_options_are_scoped() -> void:
	var base := {"name": "start-options", "mode": "capture", "content": "gameplay", "beats": []}
	assert_true(HarnessScenario.parse(JSON.stringify(base)).scenario.start == "stasis", "existing scenarios retain stasis")
	base.start = "missing"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error != "", "unknown start fails")
	base.start = "quarters"
	base.mode = "perf"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error != "", "quarters cannot bypass perf lane")
	base.mode = "capture"
	base.beats = [{"name": "view", "tick": 1, "quarters_view": "doorway"}]
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error == "", "approved capture view")
	base.beats[0].quarters_view = "console"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error == "", "desk close capture view")
	base.beats[0].quarters_view = "bed"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error == "", "bed close capture view")
	base.beats[0].quarters_view = "missing"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error != "", "unknown quarters camera rejected")
	base.beats[0].quarters_view = "console"
	base.start = "stasis"
	assert_true(HarnessScenario.parse(JSON.stringify(base)).error != "", "quarters camera cannot alter existing start")

func test_capture_camera_matches_approved_plan() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "tests/quarters_camera_scene_checks.gd"], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, "approved camera scene check: " + text)
	assert_true(text.contains("QUARTERS CAMERA PASS"), "scene check completed all camera assertions")

func _player() -> Player:
	var game := Game.new(114)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	DemoStart.quarters(game, player)
	return player

func test_capture_evidence_survives_report_roundtrip_and_rejects_wrong_roots() -> void:
	var scenario: HarnessScenario = HarnessScenario.parse(FileAccess.get_file_as_string("res://scenarios/quarters-demo.json")).scenario
	var report := HarnessReport.new(5, "quarters-demo", 114)
	for beat: Dictionary in scenario.beats:
		var state := QuartersMemory.State.REMEMBERED
		if beat.name == "corridor-door": state = QuartersMemory.State.UNSEEN
		elif String(beat.name).begins_with("console-"): state = QuartersMemory.State.PLAYING
		elif String(beat.name).begins_with("present-"): state = QuartersMemory.State.PRESENT
		var elapsed := 0
		if beat.name == "console-message": elapsed = 60
		elif beat.name == "console-fault": elapsed = 240
		elif state == QuartersMemory.State.PRESENT: elapsed = 300
		report.beats[beat.name] = {"file": "beats/" + beat.name + ".png", "tick": beat.tick, "frame": 1, "request_id": 1}
		report.add_event({"kind": "quarters", "name": beat.name, "tick": beat.tick, "frame": 1, "evidence": {
			"state": state, "elapsed": elapsed, "door_open": beat.name != "corridor-door", "deck": 16,
			"power_active": true, "remembered_visible": state in [1, 2], "present_visible": state in [0, 3],
			"console_presses": int(state in [2, 3]), "foot": [45, -10.695, 2.3], "camera_eye": [45, -9.35, 1.85],
		}})
	var parsed := HarnessReport.parse(report.to_json())
	assert_true(parsed.error == "", "report roundtrip retains quarters events")
	assert_true(QuartersCapture.verify(parsed.report, scenario).is_empty(), "all state and camera evidence verifies after parsing")
	parsed.report.events.back().evidence.remembered_visible = true
	assert_false(QuartersCapture.verify(parsed.report, scenario).is_empty(), "conflicting state roots fail verification")
