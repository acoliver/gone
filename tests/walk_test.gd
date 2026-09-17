extends SimTestCase
## Port of the walk.rs inline test module.

## Displacement epsilon for free-flight expectations (pure products of
## the frozen constants, exact to a few ulps).
const FLIGHT_EPSILON: float = 1e-5

## Displacement epsilon for resolved stops (the resolver's own house
## tolerance for swept contact expectations).
const STOP_EPSILON: float = 1e-3

## Speed epsilon for the ramp's closed-form expectations.
const SPEED_EPSILON: float = 1e-5

func standing(x: float, foot_y: float, z: float) -> Resolve.Capsule:
	var segment: float = Controller.CAPSULE_STANDING_HEIGHT - 2.0 * Controller.CAPSULE_RADIUS
	var capsule: Resolve.Capsule = Resolve.Capsule.new()
	capsule.foot = Vector3(x, foot_y + Controller.CAPSULE_RADIUS, z)
	capsule.head = Vector3(x, foot_y + Controller.CAPSULE_RADIUS + segment, z)
	return capsule

func started() -> Walk.WalkState:
	return Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), standing(0.0, 0.0, 0.0)).state

func box_between(corner_min: Vector3, corner_max: Vector3) -> ColliderSet.Aabb:
	return ColliderSet.Aabb.from_min_max(corner_min, corner_max).box

func scene(extra: Array) -> ColliderSet:
	var colliders := ColliderSet.new()
	colliders.insert(box_between(Vector3(-10.0, -1.0, -10.0), Vector3(10.0, 0.0, 10.0)))
	for aabb: ColliderSet.Aabb in extra:
		colliders.insert(aabb)
	return colliders

func empty_scene() -> ColliderSet:
	return ColliderSet.new()

func intent(yaw: float, forward: float, strafe: float) -> Walk.MoveIntent:
	return Walk.MoveIntent.try_new(yaw, forward, strafe).intent

func assert_vec_close(actual: Vector3, expected: Vector3, epsilon: float, label: String) -> void:
	var drift: Vector3 = (actual - expected).abs()
	assert_true(drift.x < epsilon and drift.y < epsilon and drift.z < epsilon, "%s: expected %s, walked %s" % [label, str(expected), str(actual)])

func test_speed_at_a_full_stop_is_exactly_the_frozen_initial_product() -> void:
	var state := started()
	assert_float_equal(state.speed(), Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED, "the first step must move at exactly the frozen factor times full speed")

func test_speed_at_one_time_constant_is_the_exponential_approach_value() -> void:
	var state := started()
	var stepped := state.step(intent(0.0, 1.0, 0.0), Controller.STEADYING_TIME_CONSTANT, empty_scene())
	assert_true(stepped.is_ok(), "free step resolves")
	var start_speed: float = Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED
	assert_vec_close(stepped.outcome.displacement, Vector3(0.0, 0.0, start_speed * Controller.STEADYING_TIME_CONSTANT), FLIGHT_EPSILON, "the tick moves at the start speed")
	var expected: float = Controller.SURVIVAL_WALK_SPEED * (1.0 - (1.0 - Controller.STEADY_INITIAL_SPEED_FACTOR) * exp(-1.0))
	assert_true(absf(state.speed() - expected) < SPEED_EPSILON, "speed at one time constant: got %s, expected %s" % [str(state.speed()), str(expected)])

func test_speed_settles_within_epsilon_of_full_speed() -> void:
	var state := started()
	for _tick: int in range(20):
		assert_true(state.step(intent(0.0, 1.0, 0.0), Controller.STEADYING_TIME_CONSTANT, empty_scene()).is_ok(), "free steps resolve")
		state.end_tick()
		assert_true(state.speed() <= Controller.SURVIVAL_WALK_SPEED, "the exponential approach never overshoots full speed")
	assert_true(absf(Controller.SURVIVAL_WALK_SPEED - state.speed()) < 1e-6, "speed after twenty time constants: got %s" % str(state.speed()))

func test_yaw_frames_steer_the_capsule_across_the_world() -> void:
	var dt: float = 0.1
	var speed: float = Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED
	var cases: Array = [
		[0.0, 1.0, 0.0, Vector3(0.0, 0.0, speed * dt), "forward at yaw 0"],
		[PI / 2.0, 1.0, 0.0, Vector3(speed * dt, 0.0, 0.0), "forward at yaw pi/2"],
		[PI / 2.0, 0.0, 1.0, Vector3(0.0, 0.0, -speed * dt), "strafe right at yaw pi/2"],
		[PI / 2.0, -1.0, 0.0, Vector3(-speed * dt, 0.0, 0.0), "back at yaw pi/2"],
	]
	for scenario: Array in cases:
		var yaw: float = scenario[0]
		var forward: float = scenario[1]
		var strafe: float = scenario[2]
		var expected: Vector3 = scenario[3]
		var label: String = scenario[4]
		var state := started()
		var stepped := state.step(intent(yaw, forward, strafe), dt, empty_scene())
		assert_true(stepped.is_ok(), "%s: free step resolves" % label)
		assert_vec_close(stepped.outcome.displacement, expected, FLIGHT_EPSILON, label)
		assert_int_equal(stepped.outcome.contact, Walk.WalkContact.FREE, "%s: free contact" % label)
		assert_true(stepped.outcome.contact_normals.is_empty(), label)
		assert_false(stepped.outcome.grounded, "%s: no floor in the empty scene" % label)

func test_wall_contact_slides_tangentially_and_stops_into_the_face() -> void:
	var wall := box_between(Vector3(-4.0, 0.0, 0.0), Vector3(4.0, 3.2, 0.2))
	var world := scene([wall])
	var state := Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), standing(0.0, 0.0, -1.0)).state
	var stepped := state.step(intent(0.0, 1.0, 1.0), 4.0, world)
	assert_true(stepped.is_ok(), "slide resolves")
	var tangential: float = Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED * 4.0 / sqrt(2.0)
	var into_face: float = 0.7 - Controller.PENETRATION_TOLERANCE
	assert_vec_close(stepped.outcome.displacement, Vector3(tangential, 0.0, into_face), STOP_EPSILON, "wall slide")
	assert_int_equal(stepped.outcome.contact, Walk.WalkContact.SLIDING, "wall slide contact")
	assert_vec3_array_equal(stepped.outcome.contact_normals, [Vector3(0.0, 0.0, -1.0)], "wall normal")
	assert_true(stepped.outcome.grounded, "walking the floor reads grounded")

func test_head_on_contact_stops_into_the_face() -> void:
	var wall := box_between(Vector3(-4.0, 0.0, 0.0), Vector3(4.0, 3.2, 0.2))
	var world := scene([wall])
	var state := Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), standing(0.0, 0.0, -1.0)).state
	var stepped := state.step(intent(0.0, 1.0, 0.0), 4.0, world)
	assert_true(stepped.is_ok(), "head-on resolves")
	var into_face: float = 0.7 - Controller.PENETRATION_TOLERANCE
	assert_vec_close(stepped.outcome.displacement, Vector3(0.0, 0.0, into_face), STOP_EPSILON, "head-on stop")
	assert_int_equal(stepped.outcome.contact, Walk.WalkContact.STOPPED, "head-on contact")
	assert_vec3_array_equal(stepped.outcome.contact_normals, [Vector3(0.0, 0.0, -1.0)], "wall normal")
	assert_true(stepped.outcome.grounded, "the capsule stays grounded on the floor")

func test_intent_is_consumed_exactly_once_per_tick() -> void:
	var state := started()
	assert_true(state.step(intent(0.0, 1.0, 0.0), 0.1, empty_scene()).is_ok(), "first step resolves")
	var foot_after_first: Vector3 = state.capsule().foot
	var head_after_first: Vector3 = state.capsule().head
	var speed_after_first: float = state.speed()
	var second := state.step(intent(0.0, 1.0, 0.0), 0.1, empty_scene())
	assert_true(second.error != null and second.error.equals(Walk.WalkError.step_already_taken()), "a second step in the same tick is a typed error")
	assert_vec3_equal(state.capsule().foot, foot_after_first, "the rejected step moved nothing")
	assert_vec3_equal(state.capsule().head, head_after_first, "the rejected step moved nothing")
	assert_float_equal(state.speed(), speed_after_first, "the rejected step advanced no ramp")
	var text: String = second.error._to_string()
	assert_true(text.find("tick") != -1, "display: %s" % text)
	state.end_tick()
	state.end_tick()
	assert_true(state.step(intent(0.0, 1.0, 0.0), 0.1, empty_scene()).is_ok(), "end_tick opens the next tick, idempotently")

func test_the_ramp_is_temporal_and_not_directional() -> void:
	var turned := started()
	var yaws: Array[float] = [0.0, 0.0, 0.0, PI / 2.0, PI / 2.0, PI]
	for yaw: float in yaws:
		assert_true(turned.step(intent(yaw, 1.0, 0.0), 0.5, empty_scene()).is_ok(), "free step resolves")
		turned.end_tick()
	var straight := started()
	for _tick: int in range(6):
		assert_true(straight.step(intent(0.0, 1.0, 0.0), 0.5, empty_scene()).is_ok(), "free step resolves")
		straight.end_tick()
	assert_float_equal(turned.speed(), straight.speed(), "direction changes must not touch the steadying clock")

func test_start_requires_the_standing_phase() -> void:
	for current: int in [Phase.Wake.WAKING, Phase.Wake.AWAKE_IN_POD, Phase.Wake.EXITING_POD]:
		var result := Walk.WalkState.start(Phase.Machine.new(current), standing(0.0, 0.0, 0.0))
		assert_true(result.error != null and result.error.equals(Walk.WalkError.wrong_phase(Phase.Wake.STANDING, current)), "every earlier phase is a typed rejection naming both phases")
	assert_true(Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), standing(0.0, 0.0, 0.0)).is_ok(), "Standing starts the walk")

func test_invalid_tick_seconds_are_rejected_without_consuming_the_tick() -> void:
	var state := started()
	for got: float in [0.0, -0.1, INF]:
		var rejected := state.step(intent(0.0, 1.0, 0.0), got, empty_scene())
		assert_true(rejected.error != null and rejected.error.equals(Walk.WalkError.invalid_tick_seconds(got)), "tick seconds %s rejected" % str(got))
	var nan_rejected := state.step(intent(0.0, 1.0, 0.0), NAN, empty_scene())
	assert_true(nan_rejected.error != null and nan_rejected.error.kind == Walk.WalkError.Kind.INVALID_TICK_SECONDS and is_nan(nan_rejected.error.got), "NaN tick seconds rejected")
	assert_true(state.step(intent(0.0, 1.0, 0.0), 0.1, empty_scene()).is_ok(), "the failed calls must not consume the tick")

func test_non_finite_intent_inputs_are_rejected() -> void:
	var nan_forward := Walk.MoveIntent.try_new(0.0, NAN, 0.0)
	assert_true(nan_forward.error != null and nan_forward.error.kind == Walk.WalkError.Kind.NON_FINITE_INTENT_AXIS and nan_forward.error.axis == Walk.IntentAxis.FORWARD and is_nan(nan_forward.error.got), "NaN forward names the axis")
	var inf_strafe := Walk.MoveIntent.try_new(0.0, 0.0, INF)
	assert_true(inf_strafe.error != null and inf_strafe.error.kind == Walk.WalkError.Kind.NON_FINITE_INTENT_AXIS and inf_strafe.error.axis == Walk.IntentAxis.STRAFE and is_inf(inf_strafe.error.got), "infinite strafe names the axis")
	var nan_yaw := Walk.MoveIntent.try_new(NAN, 0.0, 0.0)
	assert_true(nan_yaw.error != null and nan_yaw.error.kind == Walk.WalkError.Kind.NON_FINITE_INTENT_AXIS and nan_yaw.error.axis == Walk.IntentAxis.YAW and is_nan(nan_yaw.error.got), "NaN yaw names the axis")
	# GDScript floats are f64, so the magnitude needs axes past the f32
	# range to overflow the sum of squares.
	var overflow := Walk.MoveIntent.try_new(0.0, 1e200, 1e200)
	assert_true(overflow.error != null and overflow.error.equals(Walk.WalkError.non_finite_intent_magnitude(INF)), "an unscalable magnitude is rejected")

func test_oversized_intents_clamp_and_sub_unit_intents_keep_magnitude() -> void:
	var diagonal := intent(0.0, 1.0, 1.0)
	assert_true(absf(diagonal.world_direction().length() - Controller.MAX_INPUT_LENGTH) < 1e-6, "a clamped diagonal must resolve to unit length")
	var half := intent(0.0, 0.5, 0.0)
	assert_true(absf(half.world_direction().length() - 0.5) < 1e-6, "a sub-unit intent keeps its magnitude")
	var dt: float = 1.0
	var speed: float = Controller.STEADY_INITIAL_SPEED_FACTOR * Controller.SURVIVAL_WALK_SPEED
	var state := started()
	var stepped := state.step(diagonal, dt, empty_scene())
	assert_true(stepped.is_ok(), "free step resolves")
	assert_true(absf(stepped.outcome.displacement.length() - speed * dt) < FLIGHT_EPSILON, "the clamped diagonal must not outrun a straight line: got %s" % str(stepped.outcome.displacement.length()))

func test_a_resolver_rejection_mutates_nothing_and_consumes_nothing() -> void:
	var world := ColliderSet.new()
	world.insert(box_between(Vector3(-1.0, -1.0, -1.0), Vector3(1.0, 1.0, 1.0)))
	var embedded: Resolve.Capsule = Resolve.Capsule.new()
	embedded.foot = Vector3.ZERO
	embedded.head = Vector3(0.0, 1.15, 0.0)
	var state := Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), embedded).state
	var foot_before: Vector3 = state.capsule().foot
	var head_before: Vector3 = state.capsule().head
	var rejected := state.step(intent(0.0, 1.0, 0.0), 0.1, world)
	assert_true(rejected.error != null and rejected.error.equals(Walk.WalkError.resolver_error(Resolve.ResolveError.start_penetration(0))), "an embedded start surfaces the typed resolver error")
	assert_vec3_equal(state.capsule().foot, foot_before, "the rejected step moved nothing")
	assert_vec3_equal(state.capsule().head, head_before, "the rejected step moved nothing")
	assert_true(state.step(intent(0.0, 1.0, 0.0), 0.1, empty_scene()).is_ok(), "the rejected step must not consume the tick")

func test_a_non_finite_starting_capsule_is_rejected() -> void:
	var bad: Resolve.Capsule = Resolve.Capsule.new()
	bad.foot = Vector3(NAN, Controller.CAPSULE_RADIUS, 0.0)
	bad.head = Vector3(0.0, 1.45, 0.0)
	var result := Walk.WalkState.start(Phase.Machine.new(Phase.Wake.STANDING), bad)
	assert_true(result.error != null and result.error.equals(Walk.WalkError.non_finite_capsule()), "a non-finite starting capsule is rejected")
