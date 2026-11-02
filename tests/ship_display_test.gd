extends SimTestCase

const Writing = preload("res://app/naleya.gd")

func test_console_builds_native_strokes_for_both_states_and_none_for_standby() -> void:
	var game := Game.new()
	var room := PowerRoom.build(game)
	var display := room.console_display
	var quad: MeshInstance3D = display.get_node("TextSurface")
	assert_true(display.native_canvas.stroke_quads.is_empty(), "standby has no native strokes")
	assert_true(display.native_canvas.heading.is_empty() and display.perceived_canvas.heading.is_empty(), "standby has no heading")
	assert_false(quad.visible, "standby text quad hidden")
	for word: String in ["palo", "shenu"]:
		game.press_console()
		room.process_frame(Sim.LOGICAL_TICK_SECS)
		assert_true(display.native_canvas.heading == "te mu nawa lina", "native heading")
		assert_true(display.native_canvas.state_word == word, "native state")
		assert_true(display.perceived_canvas.heading == "SISTEMA DE ENERGÍA SECUNDARIO", "perceived heading")
		assert_true(display.perceived_canvas.state_word == ("INACTIVO" if word == "palo" else "EN FUNCIONAMIENTO"), "perceived state")
		var expected := Writing.expand_strokes(Writing.layout("te mu nawa lina", 150).strokes).size() \
			+ Writing.expand_strokes(Writing.layout(word, 150).strokes).size()
		assert_int_equal(display.native_canvas.stroke_quads.size(), expected, "all native segments become drawable quads")
		for stroke: PackedVector2Array in display.native_canvas.stroke_quads:
			assert_int_equal(Geometry2D.triangulate_polygon(stroke).size(), 6, "drawable native stroke")
			for pixel: Vector2 in stroke:
				assert_float_in_range(pixel.x, 0.0, 1024.0, "native ink inside screen width")
				assert_float_in_range(pixel.y, 0.0, 640.0, "native ink inside screen height")
		assert_true(quad.visible, "working text quad visible")
		assert_true(display.perceived_canvas.stroke_quads.is_empty(), "Spanish never generates native strokes")
	room.free()

func test_physical_only_switch_forces_shader_perception_to_zero() -> void:
	_run_scene_check("_check_physical_only_switch")

func _check_physical_only_switch() -> void:
	var game := Game.new()
	var room := PowerRoom.build(game)
	game.press_console()
	room.process_frame(Sim.LOGICAL_TICK_SECS)
	var display := room.console_display
	var tree := Engine.get_main_loop() as SceneTree
	tree.root.add_child(room)
	var eye := display.global_position + display.global_basis.z * 2.0
	var forward := -display.global_basis.z
	for _tick: int in range(168):
		display.tick_attention(eye, forward)
	var control := DisplayPerception.new(DisplayPerception.Memory.new())
	for _tick: int in range(168):
		control.tick(true)
	var strokes := display.native_canvas.stroke_quads.duplicate()
	display.physical_only = true
	assert_true(display.perception_amount() == 0.0, "physical-only presentation is native")
	var surface: MeshInstance3D = display.get_node("TextSurface")
	assert_true(surface.material_override.get_shader_parameter("perceive") == 0.0, "physical switch reaches shader")
	for _tick: int in range(DisplayPerception.DECAY + 10):
		display.tick_attention(eye, forward)
		control.tick(true)
	assert_true(control.perceive == 1.0, "attending control remains resolved")
	assert_true(display.perception.perceive == control.perceive, "physical-only mode leaves attending model resolved beyond decay")
	assert_true(surface.material_override.get_shader_parameter("perceive") == 0.0, "physical presentation stays native while attending")
	display.physical_only = false
	assert_true(display.perception_amount() == 1.0, "disabling physical-only reveals resolved model immediately")
	assert_true(surface.material_override.get_shader_parameter("perceive") == 1.0, "resolved presentation reaches shader")
	assert_true(display.native_canvas.stroke_quads == strokes, "perception never rewrites the physical glyphs")
	game.press_console()
	room.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(display.perception_amount() == 0.0, "console state change resets perception immediately")
	assert_true(surface.material_override.get_shader_parameter("perceive") == 0.0, "text reset reaches shader")
	room.free()

func test_steady_attention_ticks_do_not_upload_unchanged_shader_amount() -> void:
	_run_scene_check("_check_steady_attention_shader_amount")

func _check_steady_attention_shader_amount() -> void:
	var display := ShipDisplay.build(DisplayPerception.Memory.new())
	display.set_messages("secondary_power.heading", "secondary_power.inactive")
	var tree := Engine.get_main_loop() as SceneTree
	tree.root.add_child(display)
	var eye := display.global_position + display.global_basis.z * 2.0
	var forward := -display.global_basis.z
	var surface: MeshInstance3D = display.get_node("TextSurface")
	var material := surface.material_override as ShaderMaterial
	# A sentinel at the material boundary detects any redundant parameter write.
	material.set_shader_parameter("perceive", 0.25)
	for _tick: int in range(10):
		display.tick_attention(eye, -forward)
	assert_true(material.get_shader_parameter("perceive") == 0.25, "unattended zero does not upload")
	for _tick: int in range(DisplayPerception.FIRST_HOLD):
		display.tick_attention(eye, forward)
	assert_true(material.get_shader_parameter("perceive") == 0.25, "unchanged hold does not upload")
	display.tick_attention(eye, forward)
	assert_true(is_equal_approx(material.get_shader_parameter("perceive"), 1.0 / DisplayPerception.FIRST_RAMP), "changed ramp amount uploads in the same tick")
	for _tick: int in range(DisplayPerception.FIRST_RAMP - 1):
		display.tick_attention(eye, forward)
	assert_true(material.get_shader_parameter("perceive") == 1.0, "completed ramp reaches material")
	material.set_shader_parameter("perceive", 0.25)
	for _tick: int in range(10):
		display.tick_attention(eye, forward)
	assert_true(material.get_shader_parameter("perceive") == 0.25, "resolved steady state does not upload")
	display.physical_only = true
	assert_true(material.get_shader_parameter("perceive") == 0.0, "physical-only toggle uploads immediately")
	material.set_shader_parameter("perceive", 0.25)
	for _tick: int in range(DisplayPerception.DECAY + 10):
		display.tick_attention(eye, forward)
	assert_true(material.get_shader_parameter("perceive") == 0.25, "unchanged physical-only amount does not upload")
	display.physical_only = false
	assert_true(material.get_shader_parameter("perceive") == 1.0, "resolved presentation returns without a tick")
	display.set_messages("secondary_power.heading", "secondary_power.active")
	assert_true(material.get_shader_parameter("perceive") == 0.0, "text reset uploads without a tick")
	display.free()

func _run_scene_check(method: String) -> void:
	var output: Array = []
	var exit_code := OS.execute(OS.get_executable_path(), [
		"--headless", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/ship_display_scene_checks.gd", "--", method,
	], output, true)
	var text := "".join(output)
	assert_int_equal(exit_code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_false(text.contains("ERROR:"), text)
