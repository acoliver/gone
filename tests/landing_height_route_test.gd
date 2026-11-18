extends SimTestCase
# Issue #142: in the live run (seed 1795037862) every Space press on the D14
# C-001 landing was refused as "off landing" with the foot at y 0.485. Crossing
# the bay hatch right of centre steps the capsule onto the 0.18 m lower jamb
# corner, and walking never stepped back down, so the player floated 0.18 m
# above the deck for the rest of the walk. The earlier route tests crossed every
# hatch on its centre line and placed landing poses at 0.385, the coaming height
# the same missing step-down left behind, so neither height was ever questioned.

const Driver := preload("res://tests/connector_route_driver.gd")
const LIVE_SEED := 1795037862
const STANDING_FOOT := Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
# The lower jamb corner cells of the bay hatch rise to 0.18 m beside the coaming.
const JAMB_CORNER_TOP := 0.18

func _route(seed: int) -> Driver:
	var game := Game.new(seed)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	game.wake_state.mark_ready()
	var route := Driver.new(player, 12000)
	var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	# Real input from the pod through the rod pry to the opened bay hatch.
	route.replay_prefix(scenario.actions, 1290)
	return route

## Cross the opened bay hatch toward its right jamb, as the live run did.
func _off_centre_crossing(route: Driver) -> float:
	route.walk_to(Vector3(15, 0, 3.3))
	var player := route.player
	var target := Vector3(15.4, 0, -0.5)
	var highest := 0.0
	for _tick: int in range(600):
		var foot := player.motion.capsule().foot
		var delta := Vector2(target.x - foot.x, target.z - foot.z)
		if delta.length() <= 0.1:
			break
		var yaw := atan2(delta.x, delta.y)
		route.step([{"type": "look", "yaw_deg": rad_to_deg(InputPlane.wrap_angle(yaw - player.look_angles().x)), "pitch_deg": -rad_to_deg(player.look_angles().y)}, {"type": "move", "forward": 1.0, "strafe": 0.0}])
		highest = maxf(highest, player.motion.capsule().foot.y)
	return highest

func test_off_centre_bay_crossing_still_mounts_d14_c001_and_dismounts_on_d16() -> void:
	for seed: int in [LIVE_SEED, int(JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json")).seed)]:
		var route := _route(seed)
		var player := route.player
		var layout := player.game.layout
		var highest := _off_centre_crossing(route)
		assert_true(highest >= JAMB_CORNER_TOP + STANDING_FOOT - 1e-4, "seed %d: the crossing steps onto the jamb corner as the live run did (highest foot %.4f)" % [seed, highest])
		assert_float_in_range(player.motion.capsule().foot.y, STANDING_FOOT - 1e-5, STANDING_FOOT + 1e-5, "seed %d: past the hatch the foot is back on the corridor deck" % seed)
		route.walk_to(Vector3(27, 0, 0))
		route.open_hatch(&"D14-C-001-H-FORE", Vector3(28.2, 0, 0), Vector3(33, 0, 0))
		route.open_hatch(&"D14-C-001-H-AFT", Vector3(33.9, 0, 0), Vector3(38, 0, 0))
		route.walk_to(Vector3(33, 0, 0))
		var well := layout.well(&"C-001-LADDER")
		route.walk_to(Vector3(well.landing(14).origin.x, 0, -1.1))
		route.walk_to(Vector3(well.landing(14).origin.x, 0, -2.9))
		var foot := player.motion.capsule().foot
		assert_float_in_range(foot.y, STANDING_FOOT - 1e-5, STANDING_FOOT + 1e-5, "seed %d: the landing foot stands on the D14 landing floor" % seed)
		# The live look: straight at the shaft, pitched down at the rungs.
		route.look_at(foot + Vector3(0, 0, -2), -34.5)
		var refusals := player.motion.mount_refusals(layout, player.sim_forward())
		route.press()
		assert_true(player.motion.mounted(), "seed %d: Space mounts C-001 from the D14 landing at %s, refusals %s" % [seed, foot, refusals])
		if not player.motion.mounted():
			player.free()
			continue
		route.hold(24)
		assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.CLIMBING, "seed %d: the transfer reaches the climb line" % seed)
		route.climb_to(16)
		route.press()
		route.hold(23)
		assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.WALK, "seed %d: Space dismounts on D16" % seed)
		assert_int_equal(player.motion.deck(), 16, "seed %d: the dismount commits D16" % seed)
		assert_float_in_range(player.motion.capsule().foot.y - layout.floor_y(16), STANDING_FOOT - 1e-5, STANDING_FOOT + 1e-5, "seed %d: the D16 foot stands on its landing floor" % seed)
		assert_true(player.motion.failure().is_empty(), "seed %d: no motion failures" % seed)
		player.free()
