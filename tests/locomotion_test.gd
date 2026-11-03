extends SimTestCase

func _standing() -> Phase.Machine:
	var phase := Phase.Machine.new()
	phase.wake_complete()
	phase.request_pod_exit(Phase.InputEdge.RISING)
	phase.get_up_complete()
	return phase

func _start(deck: int = 14, id: StringName = &"C-000-LADDER") -> Locomotion:
	var layout := ShipLayout.authored().layout
	var capsule := Resolve.Capsule.new()
	capsule.foot = layout.well(id).landing(deck).origin + Vector3.UP * 0.305
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var walk := Walk.WalkState.start(_standing(), capsule).state
	return Locomotion.start(layout, ShipCollision.new(layout), deck, walk).state

func _input(forward: float = 0, strafe: float = 0) -> Locomotion.Intent:
	var input := Locomotion.Intent.new()
	input.walk = Walk.MoveIntent.try_new(0, forward, strafe).intent
	return input

func _step(state: Locomotion, input: Locomotion.Intent) -> Locomotion.Result:
	var result := state.step(input)
	state.end_tick()
	return result

func _mount(state: Locomotion, id: StringName = &"C-000-LADDER") -> void:
	var input := _input()
	input.space = true
	input.well_id = id
	input.facing = Vector3.FORWARD
	assert_true(_step(state, input).is_ok(), "mount edge accepted")
	assert_int_equal(state.mode(), Locomotion.Mode.MOUNTING, "mount edge consumes only WALK mode")
	for _tick: int in range(24):
		assert_true(_step(state, _input()).is_ok(), "mount transfer")

func test_walking_retains_deck_world_y_and_support_without_a_doorway_seam() -> void:
	for deck: int in [1, 14, 30]:
		var state := _start(deck)
		var y := state.capsule().foot.y
		for _tick: int in range(100):
			assert_true(_step(state, _input(-1)).is_ok(), "supported walk")
		assert_float_equal(state.capsule().foot.y, y, "walking never resets world Y")
		assert_float_in_range(state.capsule().foot.z, -2.995 - 1e-5, -2.995 + 0.0051, "capsule-inset edge stops walking over shaft")
		assert_int_equal(state.deck(), deck, "walk deck remains explicit")
		for _tick: int in range(180):
			assert_true(_step(state, _input(1)).is_ok(), "walk back through open doorway")
		assert_true(state.capsule().foot.z > -1.5, "landing and connector have no support seam")

func test_mount_crosses_support_boundary_and_preserves_walk_ramp() -> void:
	var state := _start()
	for _tick: int in range(60):
		_step(state, _input())
	var speed := state.walk_speed()
	_mount(state)
	assert_int_equal(state.mode(), Locomotion.Mode.CLIMBING, "mounted")
	assert_float_in_range(state.capsule().foot.z, -4.30001, -4.29999, "legal mount crosses open shaft")
	assert_float_equal(state.walk_speed(), speed, "mount does not restart or advance walk ramp")
	for tick: int in range(220):
		assert_true(_step(state, _input(-1, 1)).is_ok(), "legacy forward ascends; strafe has no effect")
	assert_int_equal(state.deck(), 14, "climb does not guess walk deck")
	var input := _input()
	input.space = true
	for tick: int in range(24):
		assert_true(_step(state, input if tick == 0 else _input()).is_ok(), "dismount sweep")
		assert_int_equal(state.deck(), 14 if tick < 23 else 13, "deck commits on last sweep only")
		assert_int_equal(state.mode(), Locomotion.Mode.DISMOUNTING if tick < 23 else Locomotion.Mode.WALK, "mode commits on final tick")
	assert_float_equal(state.walk_speed(), speed, "walk ramp preserved throughout climb")
	assert_float_in_range(state.eye().y, 5.5 + 1.605 - 1e-5, 5.5 + 1.605 + 1e-5, "eye follows standing capsule continuously")
	_step(state, _input())
	assert_true(state.walk_speed() > speed, "walk ramp resumes next tick")

func test_dedicated_climb_and_negative_sim_forward_have_identical_sign_and_no_doubling() -> void:
	var legacy := _start()
	var dedicated := _start()
	_mount(legacy)
	_mount(dedicated)
	var input := _input(-1)
	input.has_climb = true
	input.climb = 1
	for _tick: int in range(100):
		_step(legacy, _input(-1))
		_step(dedicated, input)
	assert_close(dedicated.capsule().foot, legacy.capsule().foot, "dual agreeing channels never multiply speed")
	var q := exp(-log(20.0) / 9)
	var expected := 0.305 + 0.025 * (100 - q * (1 - pow(q, 100)) / (1 - q))
	assert_float_in_range(dedicated.capsule().foot.y, expected - 1e-5, expected + 1e-5, "positive dedicated eases upward")

func test_conflicting_nonfinite_and_duplicate_input_reject_without_mode_or_pose_change() -> void:
	var state := _start()
	_mount(state)
	var before := state.capsule().foot
	var input := _input(-1)
	input.has_climb = true
	input.climb = -1
	assert_int_equal(state.step(input).error.kind, Locomotion.LocomotionError.Kind.INPUT_CONFLICT, "opposed channels reject")
	input.climb = NAN
	assert_false(state.step(input).is_ok(), "nonfinite dedicated input rejects")
	assert_false(state.step(_input(), 1.0 / 30).is_ok(), "non-fixed tick rejects")
	assert_close(state.capsule().foot, before, "rejections unchanged")
	assert_true(state.step(_input()).is_ok(), "valid tick still available")
	assert_int_equal(state.step(_input()).error.kind, Locomotion.LocomotionError.Kind.STEP_ALREADY_TAKEN, "one locomotion mode per tick")

func test_walk_resume_validates_without_mutating_ramp_or_aliased_capsule() -> void:
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(3, 0.305, -2.9)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var walk := Walk.WalkState.start(_standing(), capsule).state
	var empty := ColliderSet.new()
	walk.step(Walk.MoveIntent.try_new(0, 0, 0).intent, Sim.LOGICAL_TICK_SECS, empty)
	walk.end_tick()
	var speed := walk.speed()
	capsule.foot.y = NAN
	assert_false(walk.resume(capsule).is_ok(), "invalid transfer rejected")
	assert_float_equal(walk.speed(), speed, "rejected ramp unchanged")
	capsule.foot = Vector3(3, 71.805, -2.9)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	assert_true(walk.resume(capsule).is_ok(), "swept landing capsule resumes")
	capsule.foot = Vector3.ZERO
	assert_float_in_range(walk.capsule().foot.y, 71.805 - 1e-5, 71.805 + 1e-5, "resume copies accepted capsule")
	assert_float_equal(walk.speed(), speed, "successful resume keeps ramp")
