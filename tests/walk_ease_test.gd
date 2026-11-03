extends SimTestCase

func _state() -> Walk.WalkState:
	var pose := Resolve.Capsule.new()
	pose.foot = Vector3(0, 0.3, 0)
	pose.head = Vector3(0, 1.45, 0)
	return Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), pose).state

func _step(state: Walk.WalkState, forward: float, strafe: float = 0, world: ColliderSet = null) -> Vector3:
	var result := state.step(Walk.MoveIntent.try_new(0, forward, strafe).intent, Sim.LOGICAL_TICK_SECS, ColliderSet.new() if world == null else world)
	assert_true(result.is_ok(), "fixed walk tick resolves")
	state.end_tick()
	return result.outcome.displacement / Sim.LOGICAL_TICK_SECS

func _steady(state: Walk.WalkState) -> void:
	for tick: int in range(1500):
		_step(state, 0)

func test_start_reaches_95_percent_in_a_quarter_second() -> void:
	var state := _state()
	_steady(state)
	for tick: int in range(1, 31):
		var velocity := _step(state, 1)
		var expected := 0.9 * (1 - exp(-log(20.0) * tick / 15.0))
		assert_true(absf(velocity.z - expected) < 1e-5, "start tick %d: %.9f expected %.9f" % [tick, velocity.z, expected])

func test_release_decays_to_five_percent_in_a_fifth_second() -> void:
	var state := _state()
	_steady(state)
	for tick: int in range(120):
		_step(state, 1)
	for tick: int in range(1, 31):
		var velocity := _step(state, 0)
		var expected := 0.9 * exp(-log(20.0) * tick / 12.0)
		assert_true(absf(velocity.z - expected) < 2e-5, "stop tick %d: %.9f expected %.9f" % [tick, velocity.z, expected])

func test_direction_change_blends_world_velocity() -> void:
	var state := _state()
	_steady(state)
	for tick: int in range(120):
		_step(state, 1)
	var changed := _step(state, 0, 1)
	var alpha := 1 - exp(-log(20.0) / 15)
	assert_true(absf(changed.x - 0.9 * alpha) < 1e-5, "new direction accelerates")
	assert_true(absf(changed.z - 0.9 * (1 - alpha)) < 2e-5, "old direction decays instead of snapping")

func test_wall_slide_clips_carried_velocity_to_actual_motion() -> void:
	var state := _state()
	_steady(state)
	var world := ColliderSet.new()
	world.insert(ColliderSet.Aabb.from_parts(Vector3(0, 1.5, 0.4), Vector3(10, 1.5, 0.1)))
	for tick: int in range(60):
		var velocity := _step(state, 1, 1, world)
		assert_true(absf(velocity.z) < 1e-5, "wall absorbs normal motion")
	var released := _step(state, 0)
	assert_true(absf(released.z) < 1e-5, "removing wall reveals no stored normal velocity")
	assert_true(released.x > 0, "tangential slide still eases to rest")

func test_support_clips_carried_velocity_and_resume_clears_it() -> void:
	var state := _state()
	_steady(state)
	for tick: int in range(60):
		_step(state, 1)
	var blocked := state.step(Walk.MoveIntent.try_new(0, 1, 0).intent, Sim.LOGICAL_TICK_SECS, ColliderSet.new(), func(_pose: Resolve.Capsule, _delta: Vector3) -> Vector3: return Vector3.ZERO)
	assert_true(blocked.is_ok(), "support block resolves")
	state.end_tick()
	assert_true(_step(state, 0).length() < 1e-5, "unsupported motion cannot accumulate")
	_step(state, 1)
	assert_true(state.resume(state.capsule()).is_ok(), "swept landing resumes")
	assert_true(_step(state, 0).length() < 1e-5, "landing does not restore pre-mount velocity")

func test_smoothing_stays_below_unchanged_steadying_cap() -> void:
	var state := _state()
	for tick: int in range(360):
		var cap := state.speed()
		var velocity := _step(state, 1 if tick % 90 < 45 else -1, 1)
		assert_true(velocity.length() <= cap + 1e-5, "easing cannot exceed recovery cap")
		var expected := 0.9 * (1 - 0.65 * exp(-float(tick + 1) / 60 / 1.2))
		assert_true(absf(state.speed() - expected) < 1e-12, "recovery ramp remains unchanged")

func test_identical_inputs_produce_identical_positions() -> void:
	var first := _state()
	var second := _state()
	for tick: int in range(600):
		var forward := sin(tick * 0.03)
		var strafe := cos(tick * 0.07)
		_step(first, forward, strafe)
		_step(second, forward, strafe)
		assert_vec3_equal(first.capsule().foot, second.capsule().foot, "deterministic position every tick")
