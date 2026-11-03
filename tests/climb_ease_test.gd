extends SimTestCase

func test_climb_easing_and_inverse_match_the_specified_scalar_response() -> void:
	var alpha := 1.0 - exp(-log(20.0) / 9.0)
	for velocity: float in [-1.5, -0.2, 0.0, 0.8, 1.5]:
		for intent: float in [-1.0, -0.1, 0.0, 0.3, 1.0]:
			var expected := velocity + (intent * 1.5 - velocity) * alpha
			var accepted := ClimbEase.step(velocity, intent, 1.5)
			assert_true(absf(accepted - expected) < 1e-14, "independent recurrence")
			assert_true(absf(ClimbEase.intent_for_velocity(velocity, accepted, 1.5) - intent) < 1e-14, "inverse recovers input")
		assert_float_equal(ClimbEase.intent_for_velocity(velocity, 100.0, 1.5), 1.0, "inverse caps upward input")
		assert_float_equal(ClimbEase.intent_for_velocity(velocity, -100.0, 1.5), -1.0, "inverse caps downward input")

func test_ladder_exposes_accepted_velocity_after_variable_zero_input_holds() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var capsule := Resolve.Capsule.new()
	capsule.foot = layout.well(&"C-000-LADDER").landing(14).origin + Vector3.UP * 0.305
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var state := Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, Vector3.FORWARD).state
	for _tick: int in range(24):
		assert_true(state.step(0, false, collision).is_ok(), "mount")
		state.end_tick()
	var expected := 0.0
	var alpha := 1.0 - exp(-log(20.0) / 9.0)
	# Measure free coasting away from the landing capture band.
	for _tick: int in range(80):
		assert_true(state.step(1, false, collision).is_ok(), "reach midshaft")
		state.end_tick()
		expected += (1.5 - expected) * alpha
	assert_true(state.height() > Ladder.LANDING_CAPTURE_REACH, "coast fixture is outside landing capture")
	for held: int in [1, 2, 5, 11]:
		assert_true(state.step(1, false, collision).is_ok(), "accelerate")
		state.end_tick()
		expected += (1.5 - expected) * alpha
		for _tick: int in range(held):
			assert_true(state.step(0, false, collision).is_ok(), "zero-input hold")
			state.end_tick()
			expected += -expected * alpha
		assert_true(absf(state.velocity() - expected) < 1e-14, "velocity follows actual hold length")
