extends SimTestCase

const Driver := preload("res://tests/connector_route_driver.gd")
const HATCH: StringName = &"D16-C-001-H-AFT"

func test_d16_corridor_lighting_follows_secondary_power() -> void:
	var game := Game.new(0)
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, game)
	scene.build_remote(game.layout.connector(&"D16-C-001"))
	assert_true(scene.d16_section != null, "aft landing prepares corridor presentation")
	assert_float_equal(scene.d16_lighting.red_level(), 0, "unlit hallway circuit")
	game.light_hallway()
	for tick: int in range(30): scene.tick_rooms()
	assert_float_equal(scene.d16_lighting.red_level(), 1, "same switched emergency circuit")
	game.press_console()
	for tick: int in range(30): scene.tick_rooms()
	assert_float_equal(scene.d16_lighting.red_level(), 0, "secondary power removes emergency red")
	assert_float_equal(scene.d16_lighting.white_level(), 1, "regular white strips under secondary power")
	root.free()

func test_d16_authored_route_and_only_off_d14_crank() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(layout.deck(16).section_ids() == [&"D16-S-042"], "#114 builds only D16 section 42")
	var section := layout.section(&"D16-S-042")
	assert_vec3_equal(section.bounds().position, Vector3(36, -11, -1.5), "D16 section start")
	assert_close(section.bounds().end, Vector3(60, -7.8, 1.5), "D16 section end")
	assert_int_equal(section.side_door_ids().size(), 6, "same three paired stations")
	assert_int_equal(section.regular_light_frames().size(), 4, "secondary-power strip stations")
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.deck_number() != 14 and door.kind() == ShipLayout.DoorKind.HATCH:
			assert_int_equal(door.policy(), ShipLayout.Policy.CRANK if id == HATCH else ShipLayout.Policy.NEVER_OPENS, "#114 only opens the quarters route hatch")

func test_stasis_to_d16_aft_landing_crank_and_corridor_through_player() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	var game := Game.new(int(source.seed))
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := Driver.new(player, 15000)
	route.opening()
	route.enter_well(1)
	route.climb_to(16)
	route.dismount(16)
	route.walk_to(Vector3(34.5, -11, -1.2))
	route.walk_to(Vector3(33, -11, -1.2))
	route.walk_to(Vector3(33, -11, 0))
	route.open_hatch(HATCH, Vector3(33.9, -11, 0), Vector3(38, -11, 0))
	route.walk_to(Vector3(45, -11, 0))
	assert_int_equal(player.motion.deck(), 16, "D16 owns walking")
	assert_true(player.motion.capsule().foot.x > 44.8, "walks from stasis to quarters station")
	assert_true(game.doors.snapshot(HATCH).attempt > 0, "real crank input")
	assert_true(player.motion.failure().is_empty(), "route has no motion failures")
	player.free()

func test_door_selection_is_deck_aware_in_both_directions() -> void:
	var game := Game.new(0)
	var interactions := Interactions.new(game.layout)
	for deck: int in [14, 16]:
		var context := Interactions.Context.new()
		context.walking = true
		context.deck = deck
		context.foot = Vector3(45, game.layout.floor_y(deck) + 0.305, 0)
		context.eye = context.foot + Vector3.UP * 1.35
		context.forward = Vector3.BACK
		var targets: Array[Interactions.Target] = []
		for other: int in [14, 16]:
			targets.append(interactions.target_for(StringName("D%02d-S-042-SIDE-009-STARBOARD/HALL" % other), other, context.foot))
		var hits := Interactions.eligible(targets, context, [])
		assert_int_equal(hits.size(), 1, "other-deck face never selected")
		if not hits.is_empty(): assert_int_equal(hits[0].deck, deck, "current-deck face selected")
