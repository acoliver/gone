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
	var game := Game.new(0)
	var first := Perception.new(game.writing_memory)
	var second := Perception.new(game.writing_memory)
	_ticks(first, true, 168)
	_ticks(second, true, 21 + 18)
	assert_true(is_equal_approx(second.perceive, 0.5), "another display uses protagonist's completed first reading")
	var fresh_game := Game.new(0)
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

func _attends(eye: Vector3, forward: Vector3) -> bool:
	return Perception.attends(eye, forward, Vector3.ZERO,
		Vector3.RIGHT * 0.46, Vector3.UP * 0.29, Vector3.FORWARD)

func test_attention_accepts_ray_hits_inside_screen() -> void:
	assert_true(_attends(Vector3(0, 0, -2), Vector3.BACK), "center hit")
	assert_true(_attends(Vector3(0.45, 0.28, -2), Vector3.BACK), "hit near screen corner")
	var eye := Vector3(1, 1, -2)
	assert_true(_attends(eye, (Vector3(0.3, 0.2, 0) - eye).normalized()), "oblique ray hits screen")

func test_attention_accepts_ray_hits_inside_twenty_centimetre_margin() -> void:
	for sign_x: float in [-1.0, 1.0]:
		for sign_y: float in [-1.0, 1.0]:
			assert_true(_attends(Vector3(sign_x * 0.65, sign_y * 0.48, -2), Vector3.BACK), "margin includes corners outside physical screen")
	assert_true(_attends(Vector3(0.46 + Perception.ATTENTION_MARGIN, 0, -2), Vector3.BACK), "horizontal margin boundary included")
	assert_true(_attends(Vector3(0, 0.29 + Perception.ATTENTION_MARGIN, -2), Vector3.BACK), "vertical margin boundary included")

func test_attention_rejects_ray_hits_beyond_margin() -> void:
	for sign_axis: float in [-1.0, 1.0]:
		assert_false(_attends(Vector3(sign_axis * 0.661, 0, -2), Vector3.BACK), "beyond horizontal margin")
		assert_false(_attends(Vector3(0, sign_axis * 0.491, -2), Vector3.BACK), "beyond vertical margin")

func test_attention_rejects_away_and_parallel_rays() -> void:
	var eye := Vector3(0, 0, -2)
	assert_false(_attends(eye, Vector3.FORWARD), "intersection behind eye is not attention")
	assert_false(_attends(eye, Vector3.RIGHT), "parallel ray never reaches plane")

func test_attention_requires_screen_center_within_four_metres() -> void:
	assert_true(_attends(Vector3(0, 0, -4), Vector3.BACK), "four metre boundary included")
	assert_false(_attends(Vector3(0, 0, -4.01), Vector3.BACK), "too far")
	var eye := Vector3(0.65, 0.48, -4)
	assert_false(_attends(eye, Vector3.BACK), "range is measured to center, not plane")

func test_attention_requires_screen_front_toward_eye() -> void:
	assert_false(_attends(Vector3(0, 0, 2), Vector3.FORWARD), "behind screen even when ray hits")
	assert_false(_attends(Vector3(2, 0, 0), Vector3.LEFT), "edge-on screen")
	assert_false(_attends(Vector3.ZERO, Vector3.BACK), "eye on screen has no front view")

func test_attention_uses_world_space_screen_axes_and_extents() -> void:
	var basis := Basis.from_euler(Vector3(0.3, PI / 2.0, 0.2))
	var center := Vector3(21.166, 1.3, -7.5)
	var right := basis.x * 0.8
	var up := basis.y * 0.15
	var forward := -basis.z
	var eye := center + basis.z * 2.0 + basis.x * 0.99 + basis.y * 0.34
	assert_true(Perception.attends(eye, forward, center, right, up, basis.z), "rotated screen uses its own size and axes plus world-space margin")
	eye += basis.y * 0.02
	assert_false(Perception.attends(eye, forward, center, right, up, basis.z), "rotated hit beyond top margin misses")
