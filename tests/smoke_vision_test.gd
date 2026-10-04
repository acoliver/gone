extends SimTestCase

const SHADER: Shader = preload("res://app/smoke_vision.gdshader")

func test_smoke_vision_is_peripheral_and_hidden_during_wake() -> void:
	var pass_layer := WakePass.build()
	var state := SmokeSymptoms.new()
	assert_true(load("res://app/smoke_vision.gd").get_source_code().contains("rect.mouse_filter = Control.MOUSE_FILTER_IGNORE"), "smoke overlay does not intercept viewport-routed mouse motion")
	var presentation := SmokeVision.build(state, pass_layer)
	assert_true(SHADER != null, "smoke shader loads")
	assert_true(presentation.layer < 100, "symptom pass is below wake pass")
	assert_true(pass_layer.is_active(), "wake pass begins active")
	assert_float_equal(SmokeSymptoms.MAX_DOSE, 1.0, "dose cap is fixed")
	assert_float_equal(SmokeSymptoms.MIN_GAP, 0.2, "cue gap is fixed")
	assert_true(SHADER.code.contains("smoothstep(0.52, 0.95, radius)"), "center region stays outside peripheral treatment")
	assert_true(SHADER.code.contains("color *= 1.0 - radial * 0.12;"), "maximum sustained attenuation is twelve percent")
	assert_true(SHADER.code.contains("color += vec3(0.035) * radial;"), "persistent neutral veil adds at most 0.035 per channel")
	assert_true(SHADER.code.contains("2.0 / viewport_size"), "double-image offset is pixel bounded")
	assert_true(SHADER.code.contains("float blur_pixels = radial * 4.0;"), "pulse cannot exceed four pixel blur")
	assert_true(SHADER.code.contains("float severity = clamp(dose, 0.0, 1.0);"), "every dose stage contributes without a low-dose dead zone")

# Equation pins keep the numerical reference tied to the shader. Windowed QA
# separately checks the compiled shader against synthetic red and black inputs.
func _channel_response(source: Vector3, peripheral: float, dose: float, cough: float, breath: float) -> Vector3:
	var radial := peripheral * clampf(dose, 0.0, 1.0)
	var gray := source.dot(Vector3(0.2126, 0.7152, 0.0722))
	var color := source.lerp(Vector3.ONE * gray, radial * 0.72)
	color *= 1.0 - radial * 0.12
	color += Vector3.ONE * 0.035 * radial
	var haze := peripheral * (cough * 0.26 + breath * 0.14)
	return color.lerp(Vector3(0.32, 0.38, 0.42), haze)

func test_shader_channel_response_on_red_and_black() -> void:
	assert_true(SHADER.code.contains("dot(color, vec3(0.2126, 0.7152, 0.0722))"), "gray uses bounded luminance")
	assert_true(SHADER.code.contains("mix(color, vec3(gray), radial * 0.72)"), "severity removes peripheral red saturation")
	assert_true(SHADER.code.contains("peripheral * (cough_pulse * 0.26 + breath_pulse * 0.14)"), "actual pulses drive haze independently of dose")
	assert_true(SHADER.code.contains("mix(color, vec3(0.32, 0.38, 0.42), haze)"), "muted contrasting haze works on black and red")
	var previous_chroma := 2.0
	var previous_mean := 2.0
	for dose: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
		var red := _channel_response(Vector3(1.0, 0.0, 0.0), 1.0, dose, 0.0, 0.0)
		var chroma := red.x - red.y
		var mean := (red.x + red.y + red.z) / 3.0
		assert_true(chroma < previous_chroma, "red chroma falls at each dose stage")
		assert_true(mean < previous_mean, "vignette dims progressively")
		previous_chroma = chroma
		previous_mean = mean
		assert_vec3_equal(_channel_response(Vector3.ZERO, 1.0, dose, 0.0, 0.0), Vector3.ONE * 0.035 * dose, "persistent veil registers on black at each dose stage")
	var full_red := _channel_response(Vector3(1.0, 0.0, 0.0), 1.0, 1.0, 0.0, 0.0)
	assert_true((full_red.x - full_red.y) / full_red.x <= 0.8, "full-dose red saturation is at most 0.8")
	for source: Vector3 in [Vector3.ZERO, Vector3(1.0, 0.0, 0.0)]:
		var neutral := _channel_response(source, 1.0, 0.0, 0.0, 0.0)
		assert_true(_channel_response(source, 1.0, 0.0, 1.0, 0.0).distance_to(neutral) > 0.1, "unchanged cough blend contrasts with neutral red and black")
		assert_true(_channel_response(source, 1.0, 0.0, 0.0, 0.45).distance_to(neutral) > 0.025, "unchanged breath blend contrasts with neutral red and black")
		for dose: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
			var baseline := _channel_response(source, 1.0, dose, 0.0, 0.0)
			var cough := _channel_response(source, 1.0, dose, 1.0, 0.0)
			var breath := _channel_response(source, 1.0, dose, 0.0, 0.45)
			var haze_color := Vector3(0.32, 0.38, 0.42)
			assert_vec3_equal(cough, baseline.lerp(haze_color, 0.26), "cough retains exact blend strength at every dose")
			assert_vec3_equal(breath, baseline.lerp(haze_color, 0.45 * 0.14), "breath retains exact blend strength at every dose")
			assert_true(breath.distance_to(baseline) < cough.distance_to(baseline), "breath cue is weaker")
			assert_true(cough.max_axis_index() >= 0 and cough.x <= 1.0 and cough.y <= 1.0 and cough.z <= 1.0, "haze does not add uncontrolled gain")

func test_shader_center_neutrality_for_all_states() -> void:
	for radius: float in [0.0, 0.25, 0.519, 0.52]:
		var peripheral := smoothstep(0.52, 0.95, radius)
		for source: Vector3 in [Vector3.ZERO, Vector3(1.0, 0.0, 0.0), Vector3(0.1, 0.4, 0.7)]:
			for dose: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
				assert_vec3_equal(_channel_response(source, peripheral, dose, 1.0, 0.45), source, "entire protected radius is unchanged even at peak pulses")

func test_sustained_attenuation_and_veil_numeric_bounds() -> void:
	for peripheral: float in [0.0, 0.1, 0.5, 1.0]:
		for dose: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
			var radial := peripheral * dose
			var veil := _channel_response(Vector3.ZERO, peripheral, dose, 0.0, 0.0)
			assert_float_in_range(veil.x, 0.0, 0.04, "persistent RGB addition stays below 0.04")
			assert_vec3_equal(veil, Vector3.ONE * 0.035 * radial, "veil reaches only its dose-scaled 0.035 bound")
			assert_float_equal(veil.x, veil.y, "persistent veil is desaturated")
			assert_float_equal(veil.y, veil.z, "persistent veil has no blue or red tint")
			for gray: float in [0.0, 0.01, 0.2, 0.5, 1.0]:
				var response := _channel_response(Vector3.ONE * gray, peripheral, dose, 0.0, 0.0)
				assert_true(absf(response.x - veil.x - gray * (1.0 - radial * 0.12)) < 0.000001, "attenuation alone never exceeds twelve percent")
				assert_float_in_range(response.x, 0.0, 1.0, "sustained response remains in display range")
	assert_close(_channel_response(Vector3.ONE, 1.0, 1.0, 0.0, 0.0), Vector3.ONE * 0.915, "bright neutral periphery retains 91.5 percent after veil")

func test_black_source_veil_recovers_monotonically_with_dose() -> void:
	var previous := Vector3.ONE
	for dose: float in [1.0, 0.75, 0.5, 0.25, 0.0]:
		var response := _channel_response(Vector3.ZERO, 1.0, dose, 0.0, 0.0)
		assert_true(response.x < previous.x and response.y < previous.y and response.z < previous.z, "each recovery stage removes veil even on black")
		previous = response
	assert_vec3_equal(previous, Vector3.ZERO, "complete recovery returns black exactly")
	for source: Vector3 in [Vector3.ZERO, Vector3.ONE, Vector3(0.1, 0.4, 0.7)]:
		assert_vec3_equal(_channel_response(source, 1.0, 0.0, 0.0, 0.0), source, "zero dose and pulses leave every source unchanged")

func test_black_source_veil_tracks_simulated_hall_recovery() -> void:
	var state := SmokeSymptoms.new()
	for _tick in range(20 * 60):
		state.tick(true, Vector3(0.0, 1.6, 0.0))
	var previous := _channel_response(Vector3.ZERO, 1.0, state.dose(), 0.0, 0.0)
	assert_close(previous, Vector3.ONE * 0.035, "full exposure sets faint maximum veil")
	for _stage in range(4):
		for _tick in range(2 * 60):
			state.tick(true, Vector3(7.0, 1.6, 0.0))
		var response := _channel_response(Vector3.ZERO, 1.0, state.sample().dose, 0.0, 0.0)
		assert_true(response.x < previous.x, "actual hallway dose recovery reduces persistent veil")
		previous = response
	state.tick(true, Vector3(7.0, 1.6, 0.0))
	assert_vec3_equal(_channel_response(Vector3.ZERO, 1.0, state.dose(), 0.0, 0.0), Vector3.ZERO, "eight clean seconds plus rounding tick remove persistent veil")

func test_shader_screen_framing_and_displacement_invariants() -> void:
	assert_true(SHADER.code.contains("vec2 uv = SCREEN_UV;"), "effect uses rendered screen coordinates")
	assert_true(SHADER.code.contains("(uv - vec2(0.5)) * vec2(viewport_size.x / viewport_size.y, 1.0)"), "radial framing remains aspect corrected")
	assert_true(SHADER.code.contains("normalize(centered + vec2(0.00001)) * radial * (2.0 / viewport_size)"), "ghost remains radial and bounded to two pixels")
	assert_true(SHADER.code.contains("mix(center.rgb, ghost.rgb, radial * 0.08)"), "ghost contribution stays bounded")
	assert_true(SHADER.code.contains("texture(screen_texture, uv + vec2(px.x, 0.0)).rgb, radial * 0.18"), "four-pixel blur stays peripheral")
	for viewport: Vector2 in [Vector2(480.0, 270.0), Vector2(1152.0, 648.0), Vector2(2304.0, 1296.0)]:
		for uv: Vector2 in [Vector2(0.5, 0.5), Vector2(0.5, 0.0), Vector2(0.0, 0.5), Vector2(1.0, 1.0)]:
			var centered := (uv - Vector2.ONE * 0.5) * Vector2(viewport.x / viewport.y, 1.0)
			var peripheral := smoothstep(0.52, 0.95, centered.length())
			if uv.x == 0.5:
				assert_float_equal(peripheral, 0.0, "center and vertical midpoint edge remain protected in all capture sizes")
			else:
				assert_true(peripheral > 0.9, "horizontal periphery keeps its rendered framing in all capture sizes")
			var offset := centered.normalized() * peripheral * (Vector2.ONE * 2.0 / viewport)
			assert_true(absf(offset.x * viewport.x) <= 2.0 and absf(offset.y * viewport.y) <= 2.0, "displacement remains pixel bounded at every capture size")

func test_actual_scheduler_pulses_have_smooth_attack_and_decay() -> void:
	var state := SmokeSymptoms.new()
	var bay := Vector3(0.0, 1.6, 0.0)
	var cough_start := -1
	var breath_start := -1
	var cough_onset := -1
	var previous_cough := 0.0
	var previous_breath := 0.0
	var cough_peak := 0.0
	var breath_peak := 0.0
	for tick: int in range(1, 181):
		state.tick(true, bay)
		for event: SmokeSymptoms.Event in state.drain_events():
			if event.kind == SmokeSymptoms.COUGH:
				cough_onset = tick
		var sample := state.sample()
		assert_float_equal(state.sample().cough_pulse, sample.cough_pulse, "sampling does not advance cough")
		assert_float_equal(state.sample().breath_pulse, sample.breath_pulse, "sampling does not advance breath")
		assert_true(absf(sample.cough_pulse - previous_cough) <= 0.25, "cough has no one-frame peak flash")
		assert_true(absf(sample.breath_pulse - previous_breath) <= 0.06, "breath ramps smoothly")
		if sample.cough_pulse > 0.0 and cough_start < 0:
			cough_start = tick
			assert_true(sample.cough_pulse < 0.1, "cough starts near zero")
		if sample.breath_pulse > 0.0 and breath_start < 0:
			breath_start = tick
			assert_true(sample.breath_pulse < 0.02, "breath starts near zero")
		if cough_start >= 0:
			var age := tick - cough_start + 1
			if age <= 6:
				assert_true(sample.cough_pulse >= previous_cough, "six-tick cough attack is monotonic")
			elif age <= 36:
				assert_true(sample.cough_pulse <= previous_cough, "thirty-tick cough decay is monotonic")
			if age == 6:
				assert_float_equal(sample.cough_pulse, 1.0, "cough peaks after 0.1 seconds")
			if age >= 36:
				assert_float_equal(sample.cough_pulse, 0.0, "cough ends after its 0.5 second decay")
		if breath_start >= 0 and tick < 100:
			var age := tick - breath_start + 1
			if age <= 12:
				assert_true(sample.breath_pulse >= previous_breath, "breath attack is monotonic")
			elif age <= 48:
				assert_true(sample.breath_pulse <= previous_breath, "breath decay is monotonic")
			if age == 12:
				assert_float_equal(sample.breath_pulse, 0.45, "breath peaks lower after 0.2 seconds")
			if age >= 48:
				assert_float_equal(sample.breath_pulse, 0.0, "breath fully decays")
		cough_peak = maxf(cough_peak, sample.cough_pulse)
		breath_peak = maxf(breath_peak, sample.breath_pulse)
		previous_cough = sample.cough_pulse
		previous_breath = sample.breath_pulse
	assert_float_equal(cough_peak, 1.0, "scheduler cough reaches its peak")
	assert_float_equal(breath_peak, 0.45, "scheduler breath reaches its weaker peak")
	assert_int_equal(cough_start - cough_onset, roundi(SmokeSymptoms.COUGH_ACTIVE_OFFSET * 60.0), "visual attack starts at the existing active cough offset")
