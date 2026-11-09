extends SimTestCase
# New pod #88: regenerated ordinary-input routes retain exact schedule/digest checks.
const Route := preload("res://harness/route.gd")

func test_all_opening_schedules_replay_through_actual_player() -> void:
	for name: String in ["gameplay-full", "gameplay-keyboard-turn", "rod-pickup", "hallway", "power-room"]:
		var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/%s.json" % name))
		var game := Game.new(int(scenario.seed))
		var player := Player.build(game, null)
		player.scripted = true
		player.rod = Rod.build()
		player.adapter = InputPlane.ScriptedAdapter.new()
		player._ready()
		game.wake_state.mark_ready()
		var route := Route.new(player, int(scenario.max_frames))
		route.replay_prefix(scenario.actions, int(scenario.beats.back().tick) + 2)
		assert_true(player.motion.failure().is_empty(), name + " motion accepted")
		assert_true(player.motion.rod_carried and game.door_open, name + " deliberate pickup and pry")
		assert_int_equal(game.doors.snapshot(ShipLayout.BAY_DOOR_ID).releases, 1, name + " exactly one bay opening")
		if name in ["hallway", "power-room"]:
			assert_true(game.bay_exited and game.hallway_lit, name + " physical crossing and switch")
			assert_int_equal(player.motion.hallway_switch_flips, 1, "one switch flip")
		if name == "power-room":
			assert_true(game.power_door_open and game.power_active, "power room route completes")
			assert_int_equal(player.motion.console_presses, 1, "one console activation retained")
		player.rod.free()
		player.free()

func test_fixed_opening_schedule_snapshots() -> void:
	# Pin capture framing separately so every original input, beat tick, check
	# and budget byte still matches the existing snapshots.
	var expected := {
		"gameplay-full": "00b5248ac8bccc8d3111280fa965f3f11574ef752f9b75cb60eff3d54a3c0779",
		"gameplay-keyboard-turn": "2eb82357723558ec38d1da61af31c766ff5dcce9f6d96d18f1acebf469866970",
		"rod-pickup": "6ad6d75c76ec032165114dc035b09346e6629de0d7108ad4e8230418f93e50df",
		"hallway": "52ac14ded190d348566825248fbf5c8d84a0d7b760df6a46a36f5e346cebb849",
		"power-room": "fccfcd702eeef0d15dd2cd6534ad6ab146f6d516843797e41d3b7b78b8b81170",
		"connector-route": "12cbdd957741adc8644b595945afeb5ca9d8998b5f7e8e6abf9d948b85341a9a",
		"click-route": "2f6927124bd407bb087c870bcb4462b2a65dd81987f04035e6904d190f48c069",
	}
	for name: String in expected:
		var source := FileAccess.get_file_as_string("res://scenarios/%s.json" % name)
		if name in ["power-room", "connector-route", "click-route"]:
			var scenario: HarnessScenario = HarnessScenario.parse(source).scenario
			var captures := {"power-active": {"camera_pitch_up": 30.0}}
			if name != "click-route": captures["hall-white"] = {"camera_back": 2.0, "camera_pitch_up": 15.0}
			for label: String in captures:
				var beat: Dictionary = scenario.beats.filter(func(value: Dictionary) -> bool: return value.name == label)[0]
				for key: String in captures[label]:
					var value: float = captures[label][key]
					assert_float_equal(float(beat.get(key, -1.0)), value, name + " pins the fixture view " + key)
					var field := "\t\t\t\"%s\": %.1f,\n" % [key, value]
					assert_int_equal(source.count(field), 1, name + " permits only the declared capture framing")
					source = source.replace(field, "")
		assert_true(source.sha256_text() == expected[name], name + " fixed compiled schedule")
