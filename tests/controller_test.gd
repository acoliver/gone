extends SimTestCase
## The controller module is a frozen specification: constants only. The
## values must stay exactly as frozen in controller.rs.

func test_frozen_constants_match_the_specification() -> void:
	assert_float_equal(Controller.CAPSULE_RADIUS, 0.30, "capsule radius")
	assert_float_equal(Controller.CAPSULE_STANDING_HEIGHT, 1.75, "standing height")
	assert_float_equal(Controller.STEP_UP_HEIGHT, 0.25, "step-up height")
	assert_int_equal(Controller.SWEEP_ITERATION_BOUND, 8, "sweep iteration bound")
	assert_float_equal(Controller.PENETRATION_TOLERANCE, 0.005, "penetration tolerance")
	assert_float_equal(Controller.POD_EXIT_CLEARANCE, 0.15, "pod exit clearance")
	assert_float_equal(Controller.SURVIVAL_WALK_SPEED, 0.9, "survival walk speed")
	assert_float_equal(Controller.STEADY_INITIAL_SPEED_FACTOR, 0.35, "initial speed factor")
	assert_float_equal(Controller.STEADYING_TIME_CONSTANT, 1.2, "steadying time constant")
	assert_float_equal(Controller.MAX_INPUT_LENGTH, 1.0, "max input length")
