extends SimTestCase
const Route := preload("res://harness/route.gd")

func test_all_opening_schedules_replay_through_actual_player() -> void:
	for name: String in ["gameplay-full", "gameplay-keyboard-turn", "rod-pickup", "hallway", "power-room"]:
		var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/%s.json" % name))
		var game := Game.new(0)
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
			assert_int_equal(player.motion.console_presses, 2, "both console presses retained")
		player.rod.free()
		player.free()

func test_fixed_opening_schedule_snapshots() -> void:
	var expected := {
		"gameplay-full": "31a542d425080d8148b18b87e80767a5746461fd7b660a59f024245a8eb9211d",
		"gameplay-keyboard-turn": "b3f83b97da223ee17b547866edf75039d8366493efa5965d80bdbbaa2d3758c9",
		"rod-pickup": "d95d2693a787ee073b842574406e6199d8fa06771c058b222a22f2cdd0fbc372",
		"hallway": "dff9deb9db17bed5f516c81bcd2d60417d60b690f44887983cd7dc9be8952abc",
		"power-room": "cde2a28193324ca608e0f9308c0994a77040c9998d262d1a403364e0f07add74",
	}
	for name: String in expected:
		assert_true(FileAccess.get_sha256("res://scenarios/%s.json" % name) == expected[name], name + " fixed compiled schedule")
