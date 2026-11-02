extends SimTestCase

const Perception = preload("res://app/display_perception.gd")

func _ticks(model: RefCounted, attend: bool, count: int) -> void:
	for _tick: int in range(count):
		model.tick(attend)

func test_first_resolution_holds_72_ticks_and_ramps_96() -> void:
	var session := Perception.Memory.new()
	var model := Perception.new(session)
	_ticks(model, true, 72)
	assert_true(model.perceive == 0.0, "first HOLD is 1.2 seconds")
	_ticks(model, true, 48)
	assert_true(is_equal_approx(model.perceive, 0.5), "half of first RAMP")
	assert_false(session.has_resolved, "partial reading is not a completed resolution")
	_ticks(model, true, 47)
	assert_true(model.perceive < 1.0, "first RAMP lasts all 96 ticks")
	model.tick(true)
	assert_true(model.perceive == 1.0 and session.has_resolved, "first resolution completes")
	_ticks(model, true, 100)
	assert_true(model.perceive == 1.0, "attending holds the Spanish")

func test_look_away_decays_and_return_uses_fast_timings() -> void:
	var model := Perception.new(Perception.Memory.new())
	_ticks(model, true, 168)
	_ticks(model, false, 10)
	assert_true(is_equal_approx(model.perceive, 11.0 / 21.0), "linear look-away decay")
	_ticks(model, false, 11)
	assert_true(model.perceive == 0.0, "native restored in 21 ticks")
	_ticks(model, true, 21)
	assert_true(model.perceive == 0.0, "later HOLD is 0.35 seconds")
	_ticks(model, true, 18)
	assert_true(is_equal_approx(model.perceive, 0.5), "half of later 36-tick RAMP")
	_ticks(model, true, 18)
	assert_true(model.perceive == 1.0, "later reading resolves")

func test_text_change_resets_immediately_then_resolves_fast() -> void:
	var model := Perception.new(Perception.Memory.new())
	_ticks(model, true, 168)
	model.text_changed()
	assert_true(model.perceive == 0.0, "a changed message is initially native")
	_ticks(model, true, 21)
	assert_true(model.perceive == 0.0, "changed message HOLD")
	_ticks(model, true, 36)
	assert_true(model.perceive == 1.0, "changed message RAMP")

func test_text_change_during_first_reading_restarts_slow_timing_until_completed() -> void:
	var memory := Perception.Memory.new()
	var model := Perception.new(memory)
	_ticks(model, true, 120)
	assert_true(is_equal_approx(model.perceive, 0.5), "first reading is halfway resolved")
	model.text_changed()
	assert_true(model.perceive == 0.0, "replacement immediately restores native writing")
	assert_false(memory.has_resolved, "replacement cannot consume the first resolution")
	_ticks(model, true, 57)
	assert_true(model.perceive == 0.0, "later timing cannot skip the first resolution")
	_ticks(model, true, 15)
	assert_true(model.perceive == 0.0, "replacement restarts the full 72-tick first hold")
	_ticks(model, true, 48)
	assert_true(is_equal_approx(model.perceive, 0.5), "replacement uses the 96-tick first ramp")
	_ticks(model, true, 47)
	assert_false(memory.has_resolved, "first resolution needs the entire ramp")
	model.tick(true)
	assert_true(model.perceive == 1.0 and memory.has_resolved, "replacement completes the first resolution")
	model.text_changed()
	assert_true(model.perceive == 0.0, "next replacement resets immediately")
	_ticks(model, true, 21)
	assert_true(model.perceive == 0.0, "completed memory selects the later hold")
	_ticks(model, true, 35)
	assert_true(model.perceive > 0.0 and model.perceive < 1.0, "later ramp still needs its last tick")
	model.tick(true)
	assert_true(model.perceive == 1.0, "next replacement completes in the later 57 ticks")

func test_first_resolution_memory_is_shared_across_displays_and_new_game_is_fresh() -> void:
	var game := Game.new()
	var first := Perception.new(game.writing_memory)
	var second := Perception.new(game.writing_memory)
	_ticks(first, true, 168)
	_ticks(second, true, 21 + 18)
	assert_true(is_equal_approx(second.perceive, 0.5), "another display uses protagonist's completed first reading")
	var fresh_game := Game.new()
	assert_false(fresh_game.writing_memory.has_resolved, "new game has independent memory")

func test_interrupted_first_attempt_does_not_consume_first_resolution() -> void:
	var memory := Perception.Memory.new()
	var model := Perception.new(memory)
	_ticks(model, true, 120)
	_ticks(model, false, 21)
	assert_false(memory.has_resolved, "unresolved text leaves first reading available")
	_ticks(model, true, 72)
	assert_true(model.perceive == 0.0, "interrupted first reading still holds slowly")

func test_tick_trace_is_deterministic_and_bounded() -> void:
	var a := Perception.new(Perception.Memory.new())
	var b := Perception.new(Perception.Memory.new())
	for tick: int in range(1200):
		if tick % 193 == 0:
			a.text_changed()
			b.text_changed()
		var attend := tick % 251 < 207
		a.tick(attend)
		b.tick(attend)
		assert_true(a.perceive == b.perceive, "identical tick trace")
		assert_float_in_range(a.perceive, 0.0, 1.0, "bounded perception")

func test_attention_requires_range_front_face_and_camera_cone() -> void:
	var center := Vector3.ZERO
	var front := Vector3.FORWARD
	var eye := Vector3(0, 0, -2)
	assert_true(Perception.attends(eye, Vector3.BACK, center, front), "in range and facing")
	assert_true(Perception.attends(Vector3(0, 0, -4), Vector3.BACK, center, front), "four metre boundary included")
	assert_false(Perception.attends(Vector3(0, 0, -4.01), Vector3.BACK, center, front), "too far")
	assert_false(Perception.attends(Vector3(0, 0, 2), Vector3.FORWARD, center, front), "behind screen")
	assert_false(Perception.attends(Vector3(2, 0, 0), Vector3.LEFT, center, front), "edge-on screen")
	assert_true(Perception.attends(eye, Vector3.BACK.rotated(Vector3.UP, deg_to_rad(13.99)), center, front), "inside cone")
	assert_false(Perception.attends(eye, Vector3.BACK.rotated(Vector3.UP, deg_to_rad(14.01)), center, front), "outside 14 degree cone")
	assert_false(Perception.attends(eye, Vector3.FORWARD, center, front), "looking away")
	assert_false(Perception.attends(center, Vector3.BACK, center, front), "eye on screen has no front view")
