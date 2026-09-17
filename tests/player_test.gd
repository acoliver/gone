extends SimTestCase
## Ported engine-independent assertions from gone_app player/motion_tests.rs
## and player/tests.rs: the get-up mirror walks the authored path one
## segment per tick to Standing, the walk's first steps follow the frozen
## steadying ramp in the look frame, scripted input matches device input,
## presses before their phase are dropped not buffered, hatch refusals
## only land in reach while standing, and the plane's channels are
## consumed exactly once per tick.

const DT: float = 1.0 / 60.0
const NEAR: float = 1e-4

func _awake_game() -> Game:
	var game := Game.new()
	game.phase.wake_complete()
	return game

## Press activate in AwakeInPod and drive the four authored segments to
## the waypoint; leaves the mirror in WALK on the sim's Standing phase.
func _stand(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	for _segment: int in range(Exit.EXIT_POSE_COUNT - 1):
		motion.advance(plane, game, 0.0, DT)

func _near_vec3(actual: Vector3, expected: Vector3, message: String) -> void:
	var drift := (actual - expected).abs()
	if not (drift.x < NEAR and drift.y < NEAR and drift.z < NEAR):
		_fail("%s: expected %s, got %s" % [message, str(expected), str(actual)])

func _near_float(actual: float, expected: float, message: String) -> void:
	if absf(actual - expected) >= NEAR:
		_fail("%s: expected %s, got %s" % [message, str(expected), str(actual)])

func test_get_up_walks_authored_path_per_tick() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	var poses := game.exit_path.poses()
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	assert_int_equal(motion.state(), PlayerMotion.BodyState.GET_UP, "press starts the get-up")
	assert_int_equal(game.phase.current(), Phase.Wake.EXITING_POD, "machine advanced to ExitingPod")
	_near_vec3(motion.capsule().foot, poses[0].foot(), "start pose foot")
	_near_vec3(motion.capsule().head, poses[0].head(), "start pose head")
	for index: int in range(1, Exit.EXIT_POSE_COUNT - 1):
		motion.advance(plane, game, 0.0, DT)
		_near_vec3(motion.capsule().foot, poses[index].foot(), "pose %d foot" % index)
		_near_vec3(motion.capsule().head, poses[index].head(), "pose %d head" % index)
		_near_vec3(motion.eye(game), poses[index].head(), "get-up eye rides the head at pose %d" % index)
	motion.advance(plane, game, 0.0, DT)
	_near_vec3(motion.capsule().foot, poses[Exit.EXIT_POSE_COUNT - 1].foot(), "waypoint foot")
	assert_true(motion.failure().is_empty(), motion.failure())
	assert_int_equal(motion.state(), PlayerMotion.BodyState.WALK, "waypoint hands the walk the capsule")
	assert_int_equal(game.phase.current(), Phase.Wake.STANDING, "machine reached Standing")
	var waypoint := game.exit_path.waypoint()
	var standing := PlayerMotion.standing_eye(motion.capsule())
	_near_float(standing.y, waypoint.foot().y - Controller.CAPSULE_RADIUS + PlacementTruth.STANDING_EYE_HEIGHT, "standing eye height")
	_near_vec3(standing, motion.eye(game), "standing eye over the waypoint foot")

func test_get_up_start_rejected_outside_awake_in_pod() -> void:
	var game := Game.new()
	var result := Exit.GetUpController.start(game.phase, game.exit_path)
	assert_false(result.is_ok(), "start in Waking is rejected")
	assert_int_equal(result.error.kind, Exit.ExitError.Kind.WRONG_PHASE, "typed rejection")
	assert_int_equal(result.error.expected, Phase.Wake.AWAKE_IN_POD, "expected AwakeInPod")
	assert_int_equal(result.error.current, Phase.Wake.WAKING, "found Waking")
	assert_int_equal(game.phase.current(), Phase.Wake.WAKING, "the machine is unchanged")

func test_walk_start_rejected_before_standing() -> void:
	var game := _awake_game()
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(0.0, Controller.CAPSULE_RADIUS, 0.0)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var result := Walk.WalkState.start(game.phase, capsule)
	assert_false(result.is_ok(), "walk start in AwakeInPod is rejected")
	assert_int_equal(result.error.kind, Walk.WalkError.Kind.WRONG_PHASE, "typed rejection")
	assert_int_equal(result.error.expected, Phase.Wake.STANDING, "expected Standing")

func test_first_walk_steps_follow_frozen_ramp_in_look_frame() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	assert_float_equal(motion.walk_speed(), Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED, "first step at the frozen initial product")
	var yaw := 1.234
	var before := motion.capsule().foot
	plane.offer_movement(1.0, 0.0)
	motion.advance(plane, game, yaw, DT)
	var first := motion.capsule().foot - before
	var expected_first := Vector3(sin(yaw), 0.0, cos(yaw)) * (Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED * DT)
	_near_vec3(first, expected_first, "first tick moves along the look forward axis at the initial speed")
	var before2 := motion.capsule().foot
	plane.offer_movement(0.0, 1.0)
	motion.advance(plane, game, yaw, DT)
	var second := motion.capsule().foot - before2
	var ramped := Controller.SURVIVAL_WALK_SPEED * (1.0 - (1.0 - Controller.STEADY_INITIAL_SPEED_FACTOR) * exp(-DT / Controller.STEADYING_TIME_CONSTANT))
	var expected_second := Vector3(cos(yaw), 0.0, -sin(yaw)) * (ramped * DT)
	_near_vec3(second, expected_second, "second tick moves along the look right axis at the ramped speed")
	_near_float(motion.walk_speed(), Controller.SURVIVAL_WALK_SPEED * (1.0 - (1.0 - Controller.STEADY_INITIAL_SPEED_FACTOR) * exp(-(2.0 * DT) / Controller.STEADYING_TIME_CONSTANT)), "steadying clock advances per consumed tick")
	assert_true(motion.failure().is_empty(), motion.failure())

func test_scripted_adapter_matches_device_offers() -> void:
	var device_game := _awake_game()
	var device_motion := PlayerMotion.new()
	var device_plane := InputPlane.new()
	_stand(device_motion, device_game, device_plane)
	var scripted_game := _awake_game()
	var scripted_motion := PlayerMotion.new()
	var scripted_plane := InputPlane.new()
	_stand(scripted_motion, scripted_game, scripted_plane)
	var adapter := InputPlane.ScriptedAdapter.new()
	adapter.hold(1.0, 0.0)
	for _tick: int in range(30):
		device_plane.offer_movement(1.0, 0.0)
		device_motion.advance(device_plane, device_game, 0.0, DT)
		device_plane.end_frame()
		adapter.offer_tick(scripted_plane)
		scripted_motion.advance(scripted_plane, scripted_game, 0.0, DT)
		scripted_plane.end_frame()
	_near_vec3(scripted_motion.capsule().foot, device_motion.capsule().foot, "scripted and device capsules agree")
	_near_vec3(scripted_motion.capsule().head, device_motion.capsule().head, "scripted and device heads agree")
	var waypoint := device_game.exit_path.waypoint().foot()
	assert_float_in_range((scripted_motion.capsule().foot - waypoint).length(), 0.01, 12.0, "the walk actually moved")
	assert_true(scripted_motion.failure().is_empty(), scripted_motion.failure())

func test_movement_before_standing_moves_nothing() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	for _tick: int in range(5):
		plane.offer_movement(1.0, 0.0)
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_int_equal(motion.state(), PlayerMotion.BodyState.LYING, "no controller while lying")
	assert_true(motion.capsule() == null, "no capsule while lying")
	assert_true(motion.failure().is_empty(), "dropped intent is not a failure")
	_near_vec3(motion.eye(game), game.exit_path.poses()[0].head(), "the lying eye stays at the spawn")

func test_press_in_waking_is_dropped_not_buffered() -> void:
	var game := Game.new()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	plane.end_frame()
	assert_int_equal(motion.state(), PlayerMotion.BodyState.LYING, "the press did not start a get-up in Waking")
	game.phase.wake_complete()
	motion.advance(plane, game, 0.0, DT)
	assert_int_equal(motion.state(), PlayerMotion.BodyState.LYING, "the earlier press was dropped, not buffered")
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	assert_int_equal(motion.state(), PlayerMotion.BodyState.GET_UP, "a fresh press in AwakeInPod starts the get-up")

func test_refusal_only_in_reach_and_standing() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	var colliders_before := game.colliders.size()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.interact_with_hatch(plane, game), "interact while lying is not a refusal")
	assert_int_equal(motion.refusals, 0, "no refusal recorded while lying")
	_stand(motion, game, plane)
	var hatch := game.registry.hatch().center
	var foot := motion.capsule().foot
	assert_float_in_range(Vector2(foot.x - hatch.x, foot.z - hatch.y).length(), PlayerMotion.HATCH_INTERACT_REACH + 1.0, 30.0, "the waypoint starts out of reach")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.interact_with_hatch(plane, game), "interact out of reach is not a refusal")
	assert_int_equal(motion.refusals, 0, "no refusal recorded out of reach")
	# Walk the aisle to the hatch, re-aiming at the door as the sway of the
	# ramp settles; the swept resolver carries the capsule the whole way.
	var adapter := InputPlane.ScriptedAdapter.new()
	for tick: int in range(1400):
		foot = motion.capsule().foot
		var to_hatch := Vector2(hatch.x - foot.x, hatch.y - foot.z)
		if to_hatch.length() <= PlayerMotion.HATCH_INTERACT_REACH * 0.9:
			adapter.release()
			adapter.offer_tick(plane)
			motion.advance(plane, game, 0.0, DT)
			plane.end_frame()
			break
		adapter.hold(1.0, 0.0)
		adapter.offer_tick(plane)
		motion.advance(plane, game, atan2(to_hatch.x, to_hatch.y), DT)
		plane.end_frame()
	assert_true(motion.failure().is_empty(), motion.failure())
	assert_float_in_range(Vector2(motion.capsule().foot.x - hatch.x, motion.capsule().foot.z - hatch.y).length(), 0.0, PlayerMotion.HATCH_INTERACT_REACH, "the walk arrived at the door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(plane, game), "interact at the door is refused")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_hatch(plane, game), "a second interact is refused again")
	assert_int_equal(motion.refusals, 2, "every in-reach interact refused")
	assert_int_equal(motion.refusal_events.size(), 2, "one recorded event per refusal")
	assert_int_equal(game.colliders.size(), colliders_before, "the door never opens: the collider set is unchanged")
	assert_int_equal(motion.state(), PlayerMotion.BodyState.WALK, "the body still owns a standing capsule")
	assert_int_equal(game.phase.current(), Phase.Wake.STANDING, "the phase machine never left Standing")

func test_input_channels_consumed_exactly_once() -> void:
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	assert_true(plane.take_press(InputPlane.Buttons.ACTIVATE), "a queued press is consumed")
	assert_false(plane.take_press(InputPlane.Buttons.ACTIVATE), "the press is consumed exactly once")
	plane.offer_look(0.1, 0.05)
	var taken := plane.take_look()
	_near_vec3(Vector3(taken.x, taken.y, 0.0), Vector3(0.1, 0.05, 0.0), "the look delta is taken once")
	var again := plane.take_look()
	_near_vec3(Vector3(again.x, again.y, 0.0), Vector3.ZERO, "a second take drains nothing")
	var adapter := InputPlane.ScriptedAdapter.new()
	adapter.press(InputPlane.Buttons.INTERACT)
	assert_true(adapter.has_pending_edges(), "the adapter queues the edge")
	adapter.offer_tick(plane)
	assert_false(adapter.has_pending_edges(), "the tick drained the queue")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the drained edge reached the plane")
	adapter.offer_tick(plane)
	assert_false(plane.take_press(InputPlane.Buttons.INTERACT), "the edge was offered for exactly one tick")
	adapter.hold(1.0, 0.0)
	adapter.offer_tick(plane)
	var movement := plane.take_movement()
	_near_vec3(Vector3(movement.x, movement.y, 0.0), Vector3(1.0, 0.0, 0.0), "held movement is offered each tick")
	_near_vec3(Vector3(plane.take_movement().x, plane.take_movement().y, 0.0), Vector3.ZERO, "movement is taken exactly once per tick")

func test_look_integration_clamps_pitch_and_wraps_yaw() -> void:
	var up := InputPlane.integrate_look(0.0, 0.0, Vector2(0.0, 10.0))
	_near_float(up.y, InputPlane.PITCH_LIMIT, "pitch clamps at the vertical stop")
	var over := InputPlane.integrate_look(3.1, 0.0, Vector2(0.2, 0.0))
	_near_float(over.x, 3.1 + 0.2 - TAU, "yaw wraps into (-PI, PI]")
	var plane := InputPlane.new()
	plane.offer_look_pixels(Vector2(10.0, -5.0))
	var pixels := plane.take_look()
	_near_float(pixels.x, -10.0 * InputPlane.LOOK_SENSITIVITY, "mouse right decreases yaw")
	_near_float(pixels.y, 5.0 * InputPlane.LOOK_SENSITIVITY, "mouse up increases pitch")

func test_standing_and_get_up_eyes() -> void:
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(1.0, Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE, 2.0)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var standing := PlayerMotion.standing_eye(capsule)
	_near_vec3(standing, Vector3(1.0, capsule.foot.y - Controller.CAPSULE_RADIUS + PlacementTruth.STANDING_EYE_HEIGHT, 2.0), "standing eye sits above the ground contact")
	_near_vec3(PlayerMotion.get_up_eye(capsule), capsule.head, "get-up eye rides the head sphere")
