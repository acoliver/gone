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
			assert_int_equal(player.motion.console_presses, 1, "one console activation retained")
		player.rod.free()
		player.free()

func test_fixed_opening_schedule_snapshots() -> void:
	# Slice 3 v2 compilers re-plan walks around the new parked hardware.
	# Driver accepted shifted arrival ticks, conditional on all seven native
	# lanes passing with unchanged beat names, order, checks and budgets.
	# SHA-256 before -> after (clean 436071a -> regenerated):
	# hallway: de483f1247c8f5119582b551a3f7ae4ca1c915d6fb85a0b4a726d7a27b71e1fb
	#       -> 4fd9fd7f7f14af18b6ba67ea74cd221d744793761779cd0b6801065e9563d6be
	# power-room: aae6c93908cf41bc70177305d466b98fa24d7b530de4b33a70f7a68ec1984cad
	#          -> f81a883793a6420f26daf83ba15fcddbb1daae55650f2d643554dd12ac800ba3
	# connector-route: 7ef725c65420e8bf33660016cdc593a44346ab9eed511af042f1b83d5cf24529
	#               -> fdc1e44858f5e4761d58c2baadaa6e8a02411eb8e9a952994128fedd70e852d5
	# Changed beat ticks before -> after; all unlisted ticks are unchanged:
	# hallway: hall-dark 1781->1778, hall-lit 2214->2211, hall-corridor 2466->2463.
	# power-room (also connector-route): hall-lit 1577->1580,
	# power-door-opened 2366->2369, console-inactive 3003->3006,
	# power-active 3057->3060, hall-white 3660->3663.
	# Remaining connector-route: fore-inner-closed 4943->4946,
	# fore-inner-mid-crank 4980->4983, fore-inner-open 5380->5383,
	# fore-outer-closed 5443->5446, fore-outer-mid-crank 5473->5476,
	# fore-outer-open 5537->5540, d14-label-native 7851->7854,
	# d14-label-partial 7971->7974, d14-label-resolved 8141->8144,
	# x30-closed 8144->8147, x30-mid-crank 8174->8177, x30-open 8556->8559,
	# aft-connector 8559->8562, x36-closed 8623->8626,
	# x36-mid-crank 8646->8649, x36-open 8710->8713,
	# section42-refusal 9065->9068, mid-shaft 11185->11188,
	# d01-connector-native 13031->13034, d01-connector-partial 13070->13073,
	# d01-connector-resolved 13240->13243, d30-connector-native 20590->20593,
	# d30-connector-partial 20629->20632, d30-connector-resolved 20799->20802,
	# back-d14 25157->25160; connector route_ticks 25162->25165.
	var expected := {
		"gameplay-full": "31a542d425080d8148b18b87e80767a5746461fd7b660a59f024245a8eb9211d",
		"gameplay-keyboard-turn": "b3f83b97da223ee17b547866edf75039d8366493efa5965d80bdbbaa2d3758c9",
		"rod-pickup": "d95d2693a787ee073b842574406e6199d8fa06771c058b222a22f2cdd0fbc372",
		"hallway": "4fd9fd7f7f14af18b6ba67ea74cd221d744793761779cd0b6801065e9563d6be",
		"power-room": "f81a883793a6420f26daf83ba15fcddbb1daae55650f2d643554dd12ac800ba3",
		"connector-route": "fdc1e44858f5e4761d58c2baadaa6e8a02411eb8e9a952994128fedd70e852d5",
	}
	for name: String in expected:
		assert_true(FileAccess.get_sha256("res://scenarios/%s.json" % name) == expected[name], name + " fixed compiled schedule")
