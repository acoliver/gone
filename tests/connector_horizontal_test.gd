extends SimTestCase
const Route := preload("res://harness/route.gd")

func test_first_space_at_x30_cranks_facing_hatch_not_closed_power_door() -> void:
	var game := Game.new(0)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := Route.new(player, 10000)
	var opening: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/hallway.json"))
	route.replay_prefix(opening.actions, int(opening.beats.back().tick) + 2)
	assert_true(game.bay_exited and game.hallway_lit, "real input reaches lit section 41")
	var hatch := game.layout.door(&"D14-C-001-H-FORE")
	route.walk_to(Vector3(28.05, 0, 0), 0.02)
	assert_float_in_range(player.motion.capsule().foot.x, 28.03, 28.07, "real player at overlapping interaction reaches")
	route.look_at(hatch.frame().origin)
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.CLOSED, "power door starts closed")
	route.press()
	assert_int_equal(game.doors.snapshot(hatch.id()).attempt, 1, "first Space cranks the hatch in view")
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.CLOSED, "unfaced power door stays closed")
	route.hold(6)
	route.look_at(game.layout.door(ShipLayout.POWER_DOOR_ID).frame().origin)
	route.press()
	route.hold(48)
	assert_true(game.power_door_open, "Space facing the power door still opens it")
	assert_int_equal(game.doors.snapshot(hatch.id()).attempt, 1, "power-door press does not crank the hatch again")
	player.free()

func test_real_player_cranks_both_directions_and_locked_doors_refuse() -> void:
	var game := Game.new(0)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := Route.new(player, 18000)
	var opening: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	route.replay_prefix(opening.actions, int(opening.beats.back().tick) + 2)
	assert_true(game.bay_exited and game.hallway_lit and game.power_active and game.power_door_open, "opening through real input remains intact")
	for n: int in [1, 0]:
		var connector := game.layout.connector(ShipLayout.connector_id(14, n))
		var outward := 1.0 if n == 1 else -1.0
		var ids := connector.hatch_ids()
		if n == 0:
			ids.reverse()
		for id: StringName in ids:
			var door := game.layout.door(id)
			var position := door.frame().origin
			route.walk_to(position - Vector3(outward * 1.85, 0, 0))
			route.look_at(position)
			var schedule := HatchResistance.schedule(game.run_seed, id)
			for _attempt: int in range(schedule.weights.size()):
				route.press()
				route.hold(6)
			assert_int_equal(game.doors.snapshot(id).attempt, schedule.weights.size(), "one selected Space edge per attempt")
			route.hold(48)
			assert_int_equal(game.doors.snapshot(id).state, Doors.State.OPEN, "hatch completes swing")
			route.walk_to(position + Vector3(outward * 1.85, 0, 0))
			assert_true((player.motion.capsule().foot.x - position.x) * outward > 1.7, "real player crosses the aperture")
		var section := game.layout.section(ShipLayout.section_id(14, 42 if n == 1 else 40))
		var side_id := section.side_door_ids()[0]
		var side := game.layout.door(side_id)
		route.walk_to(Vector3(side.frame().origin.x, 0, 0))
		route.look_at(side.frame().origin)
		route.press()
		assert_int_equal(game.doors.events().back().kind(), Doors.EventKind.REFUSED, "side door refusal event")
		assert_int_equal(game.doors.snapshot(side_id).attempt, 1, "side door refuses through input")
		var boundary_id: StringName = &"D14-C-002-H-FORE" if n == 1 else &"D14-C-M001-H-AFT"
		var boundary := game.layout.door(boundary_id)
		route.walk_to(boundary.frame().origin - Vector3(outward * 1.85, 0, 0))
		route.look_at(boundary.frame().origin)
		route.press()
		assert_int_equal(game.doors.events().back().kind(), Doors.EventKind.REFUSED, "boundary refusal event")
		assert_int_equal(game.doors.snapshot(boundary_id).attempt, 1, "far boundary refuses")
		assert_int_equal(game.doors.snapshot(boundary_id).work, 0, "far boundary never gains work")
		# Return through the open portals before approaching the lift face.
		for id: StringName in [ids[1], ids[0]]:
			route.walk_to(game.layout.door(id).frame().origin + Vector3(outward * 1.85, 0, 0))
			route.walk_to(game.layout.door(id).frame().origin - Vector3(outward * 1.85, 0, 0))
			if id == ids[1]:
				var lift := game.layout.door(game.layout.lift(connector.lift_id()).door_id())
				route.walk_to(Vector3(lift.frame().origin.x, 0, 0))
				route.look_at(lift.frame().origin)
				route.press()
				assert_int_equal(game.doors.events().back().kind(), Doors.EventKind.REFUSED, "lift refusal event")
				assert_int_equal(game.doors.snapshot(lift.id()).attempt, 1, "lift refuses through input")
				# The landing remains supported up to its visible shaft edge.
				var landing := game.layout.well(connector.well_id()).landing(14).origin
				route.walk_to(Vector3(landing.x, 0, 0))
				route.walk_to(landing)
				route.step([{"type": "look", "yaw_deg": -rad_to_deg(player.look_angles().x), "pitch_deg": 0.0}, {"type": "move", "forward": -1.0, "strafe": 0.0}])
				for _tick: int in range(90):
					route.step([{"type": "move", "forward": -1.0, "strafe": 0.0}])
				assert_true(player.motion.capsule().foot.z >= -3.3 + Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE - 1e-5, "WALK cannot float over the shaft")
				route.walk_to(Vector3(landing.x, 0, 0))
	assert_true(player.motion.failure().is_empty(), "complete accepted horizontal journey")
	for id: StringName in game.layout.door_ids():
		if game.layout.door(id).policy() == ShipLayout.Policy.NEVER_OPENS:
			assert_int_equal(game.doors.snapshot(id).state, Doors.State.CLOSED, "all locked doors remain closed")
	player.free()
