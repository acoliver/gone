extends SimTestCase
## Port of the engine-independent assertions from gone_app wake tests
## (wake_pass.rs mapping tests and wake/tests.rs driver tests): the
## sample-to-shader-param mapping, the pass's closed-from-the-first-frame
## wiring, stage-to-param monotonicity across the authored peeks, timing
## ownership (the sim advances only through the game's tick; presentation
## only reads), start-once, the driven samples matching the authored
## timeline at its boundaries, drift-free sway projection across tick
## batchings, the exactly-once completion handoff, no-input gating through
## the wake, and the read-only bridge boundary.

func _fixture() -> Array:
	var game := Game.new()
	var camera := Camera3D.new()
	camera.rotation = Vector3(0.03, -0.12, 0.0)
	var pass_layer := WakePass.build()
	var driver := WakePresent.build(game, camera, pass_layer)
	return [game, camera, pass_layer, driver]

func _assert_params(pass_layer: WakePass, sample: Wake.WakeSample, label: String) -> void:
	var params := pass_layer.params()
	assert_float_equal(
		float(params["lid_openness"]),
		sample.lid_openness,
		"%s lid openness" % label
	)
	assert_float_equal(float(params["blur"]), sample.blur, "%s blur" % label)
	assert_float_equal(
		float(params["exposure_ramp"]),
		sample.exposure_ramp,
		"%s exposure ramp" % label
	)

func test_sample_maps_to_shader_params_field_for_field() -> void:
	var partial := Wake.WakeSample.new(0.35, 0.85, 0.35, Vector2(0.012, 0.008))
	var closed_params := WakePass.params_from_sample(Wake.WakeSample.closed())
	assert_float_equal(float(closed_params["lid_openness"]), 0.0, "closed lid openness")
	assert_float_equal(float(closed_params["blur"]), 1.0, "closed blur")
	assert_float_equal(float(closed_params["exposure_ramp"]), 0.0, "closed exposure ramp")
	var partial_params := WakePass.params_from_sample(partial)
	assert_float_equal(float(partial_params["lid_openness"]), 0.35, "partial lid openness")
	assert_float_equal(float(partial_params["blur"]), 0.85, "partial blur")
	assert_float_equal(float(partial_params["exposure_ramp"]), 0.35, "partial exposure ramp")
	var neutral_params := WakePass.params_from_sample(Wake.WakeSample.neutral())
	assert_float_equal(float(neutral_params["lid_openness"]), 1.0, "neutral lid openness")
	assert_float_equal(float(neutral_params["blur"]), 0.0, "neutral blur")
	assert_float_equal(float(neutral_params["exposure_ramp"]), 1.0, "neutral exposure ramp")

func test_the_mapping_ignores_the_sway_offset() -> void:
	var still_params := WakePass.params_from_sample(
		Wake.WakeSample.new(0.35, 0.85, 0.35, Vector2(0.012, 0.008))
	)
	var swayed_params := WakePass.params_from_sample(
		Wake.WakeSample.new(0.35, 0.85, 0.35, Vector2(-0.04, 0.05))
	)
	assert_true(
		still_params.hash() == swayed_params.hash(),
		"samples differing only in sway map to identical params"
	)

func test_the_pass_exists_fully_closed_before_readiness() -> void:
	var pass_layer := WakePass.build()
	assert_true(pass_layer.is_active(), "the pass draws from its first frame")
	_assert_params(pass_layer, Wake.WakeSample.closed(), "the pre-start pass")

func test_params_are_monotonic_across_the_authored_stages() -> void:
	var timeline := Wake.WakeTimeline.authored()
	var boundaries := Wake.WakeTimeline.authored_boundaries()
	var stages: Array[Wake.WakeSample] = [
		timeline.sample_at(10),
		timeline.sample_at(boundaries.first_blink_start - 1),
		timeline.sample_at(boundaries.second_blink_start - 1),
		timeline.sample_at(boundaries.complete_tick),
	]
	for index: int in range(stages.size() - 1):
		var from: Wake.WakeSample = stages[index]
		var to: Wake.WakeSample = stages[index + 1]
		assert_true(
			to.lid_openness > from.lid_openness,
			"stage %d opens wider: %.4f then %.4f" % [index, from.lid_openness, to.lid_openness]
		)
		assert_true(
			to.exposure_ramp > from.exposure_ramp,
			"stage %d ramps brighter: %.4f then %.4f" % [index, from.exposure_ramp, to.exposure_ramp]
		)
		assert_true(
			to.blur < from.blur,
			"stage %d resolves sharper: %.4f then %.4f" % [index, from.blur, to.blur]
		)
	assert_float_equal(stages[3].lid_openness, 1.0, "the held stage is fully open")
	assert_float_equal(stages[3].blur, 0.0, "the held stage is fully sharp")

func test_the_sim_advances_only_through_game_ticks() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var pass_layer: WakePass = fixture[2]
	var driver: WakePresent = fixture[3]
	assert_false(game.wake_state.is_started(), "nothing starts before readiness")
	for _frame: int in range(5):
		game.tick()
		driver.present_frame()
	assert_int_equal(game.wake_state.current_tick(), 0, "un-ready ticks consume nothing")
	_assert_params(pass_layer, Wake.WakeSample.closed(), "the un-ready presentation")
	assert_true(game.phase.in_phase(Phase.Wake.WAKING), "the phase holds at the opening")
	driver.begin()
	assert_int_equal(game.wake_state.current_tick(), 0, "the start spends no tick")
	for _frame: int in range(4):
		driver.present_frame()
	assert_int_equal(game.wake_state.current_tick(), 0, "presentation frames never tick the sim")
	for _tick: int in range(3):
		game.tick()
	assert_int_equal(game.wake_state.current_tick(), 3, "only the game's ticks advance the sim")

func test_the_readiness_barrier_starts_once() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var driver: WakePresent = fixture[3]
	assert_int_equal(driver.begin(), Wake.WakeStart.STARTED, "the first begin starts")
	for _repeat: int in range(4):
		assert_int_equal(
			driver.begin(),
			Wake.WakeStart.ALREADY_STARTED,
			"duplicate begins are the machine's own no-op"
		)
	game.tick()
	assert_int_equal(game.wake_state.current_tick(), 1, "no restart, no phantom ticks")

func test_driven_params_match_the_authored_samples_at_boundaries() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var pass_layer: WakePass = fixture[2]
	var driver: WakePresent = fixture[3]
	driver.begin()
	var timeline := Wake.WakeTimeline.authored()
	var boundaries := Wake.WakeTimeline.authored_boundaries()
	var fed := 0
	for boundary: int in [
		boundaries.first_opening_start,
		boundaries.first_blink_start,
		boundaries.second_opening_start,
		boundaries.second_blink_start,
		boundaries.final_opening_start,
	]:
		for _tick: int in range(boundary - fed):
			game.tick()
		fed = boundary
		driver.present_frame()
		_assert_params(
			pass_layer,
			timeline.sample_at(boundary),
			"boundary tick %d" % boundary
		)

func test_sway_projection_is_drift_free_across_tick_batchings() -> void:
	var timeline := Wake.WakeTimeline.authored()
	var boundaries := Wake.WakeTimeline.authored_boundaries()
	var at: int = boundaries.second_opening_start + 7
	var expected: Vector3 = WakePresent.sway_rotation(
		Vector3(0.03, -0.12, 0.0),
		timeline.sample_at(at).sway_offset
	)
	var stepped := _fixture()
	var chunked := _fixture()
	(stepped[3] as WakePresent).begin()
	(chunked[3] as WakePresent).begin()
	for _tick: int in range(at):
		(stepped[0] as Game).tick()
	(stepped[3] as WakePresent).present_frame()
	var driven := 0
	while driven + 3 <= at:
		for _tick: int in range(3):
			(chunked[0] as Game).tick()
		driven += 3
	for _tick: int in range(at - driven):
		(chunked[0] as Game).tick()
	(chunked[3] as WakePresent).present_frame()
	assert_int_equal(
		(chunked[0] as Game).wake_state.current_tick(),
		at,
		"both batchings consumed the same tick count"
	)
	var stepped_camera: Camera3D = stepped[1]
	var chunked_camera: Camera3D = chunked[1]
	assert_vec3_equal(
		stepped_camera.rotation,
		chunked_camera.rotation,
		"sway lands on the same pose bits across batchings"
	)
	assert_vec3_equal(
		stepped_camera.rotation,
		expected,
		"the pose is the pure projection of base plus the authored sway"
	)

func test_completion_hands_off_exactly_once_at_the_authored_tick() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var camera: Camera3D = fixture[1]
	var pass_layer: WakePass = fixture[2]
	var driver: WakePresent = fixture[3]
	driver.begin()
	var complete: int = Wake.WakeTimeline.authored().complete_tick()
	for _tick: int in range(complete - 1):
		game.tick()
	driver.present_frame()
	assert_true(game.phase.in_phase(Phase.Wake.WAKING), "one tick before completion the wake owns the camera")
	assert_true(pass_layer.is_active(), "the pass draws through the whole wake")
	assert_false(driver.input_allowed(), "input stays gated before completion")
	game.tick()
	driver.present_frame()
	assert_true(game.phase.in_phase(Phase.Wake.AWAKE_IN_POD), "completion hands off to AwakeInPod")
	assert_true(driver.is_complete(), "the driver rests at the neutral hold")
	assert_false(pass_layer.is_active(), "completion deactivates the pass")
	assert_vec3_equal(camera.rotation, Vector3(0.03, -0.12, 0.0), "the completion pose is the neutral base")
	assert_true(driver.input_allowed(), "input unlocks with the phase")
	for _tick: int in range(3):
		game.tick()
		driver.present_frame()
	assert_true(
		game.phase.in_phase(Phase.Wake.AWAKE_IN_POD),
		"the handoff fires exactly once; later frames change nothing"
	)
	assert_false(pass_layer.is_active(), "the pass stays deactivated")
	assert_vec3_equal(camera.rotation, Vector3(0.03, -0.12, 0.0), "the pose holds the neutral base")

func test_no_gameplay_input_through_the_wake_stages() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var driver: WakePresent = fixture[3]
	driver.begin()
	var timeline := Wake.WakeTimeline.authored()
	var boundaries := Wake.WakeTimeline.authored_boundaries()
	var stages := [
		0,
		boundaries.first_opening_start + 21,
		boundaries.first_blink_start,
		boundaries.second_opening_start + 27,
		boundaries.second_blink_start,
		boundaries.final_opening_start + 30,
	]
	var tick := 0
	for stage: int in stages:
		while tick < stage:
			game.tick()
			tick += 1
		driver.present_frame()
		assert_false(
			driver.input_allowed(),
			"input stays gated through stage tick %d" % stage
		)
		assert_true(
			game.phase.in_phase(Phase.Wake.WAKING),
			"the phase machine holds Waking through the whole timeline"
		)
	assert_float_equal(
		timeline.sample_at(tick).lid_openness,
		(game.wake_state.sample()).lid_openness,
		"the read sample is the driven tick's sample"
	)

func test_render_side_writes_never_touch_the_sim() -> void:
	var fixture := _fixture()
	var game: Game = fixture[0]
	var camera: Camera3D = fixture[1]
	var driver: WakePresent = fixture[3]
	driver.begin()
	for _frame: int in range(10):
		camera.rotation = Vector3(0.5, 0.5, 0.5)
		driver.present_frame()
	assert_int_equal(game.wake_state.current_tick(), 0, "no presentation write ticks the sim")
	assert_true(game.phase.in_phase(Phase.Wake.WAKING), "no presentation write moves the phase")
	assert_true(
		game.wake_state.sample().equals(Wake.WakeSample.closed()),
		"the sample holds the closed rest state under render-side writes"
	)
