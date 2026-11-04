extends SimTestCase

class Verifier:
	extends "res://harness/run.gd"
	func _initialize() -> void:
		pass

func _frame(regular: Color, emergency: Color, background: Color = Color(0.48, 0.20, 0.08)) -> Image:
	var image := Image.create(160, 90, false, Image.FORMAT_RGB8)
	image.fill(background)
	image.fill_rect(Rect2i(110, 10, 3, 3), regular)
	image.fill_rect(Rect2i(130, 10, 3, 3), emergency)
	return image

func _entry() -> Dictionary:
	return {"tick": 100, "frame": 100, "lamps": [
		{"id": "regular", "circuit": "white", "pixels": [[110, 10], [111, 10], [112, 10]]},
		{"id": "emergency", "circuit": "emergency", "pixels": [[130, 10], [131, 10], [132, 10]]},
	]}

func _verify(image: Image, entry: Dictionary) -> Verifier:
	var verifier := Verifier.new()
	verifier.scenario = {"beats": [{"name": "rust-close", "light": "white"}]}
	verifier.verify_beat_stats("rust-close", image, entry)
	return verifier

func test_white_lenses_pass_against_a_rust_dominated_frame() -> void:
	var verifier := _verify(_frame(Color(0.9, 0.88, 0.84), Color(0.025, 0.01, 0.005)), _entry())
	assert_int_equal(verifier.failures.size(), 0, "rust is not emergency illumination")
	verifier.free()

func test_red_regular_lenses_fail_even_against_a_neutral_frame() -> void:
	var image := _frame(Color(0.9, 0.1, 0.03), Color.BLACK, Color(0.4, 0.4, 0.4))
	var verifier := _verify(image, _entry())
	assert_true(not verifier.failures.is_empty(), "red regular lenses must fail")
	verifier.free()

func test_failed_handoff_with_white_strips_and_live_emergency_lens_fails() -> void:
	var image := _frame(Color.WHITE, Color(1, 0.28, 0.12), Color(0.4, 0.4, 0.4))
	var verifier := _verify(image, _entry())
	assert_true(not verifier.failures.is_empty(), "white strips cannot conceal an emergency circuit left on")
	verifier.free()

func test_dark_regular_lens_and_absent_lamps_fail() -> void:
	for lamps: Array in [[], [{"id": "dark", "circuit": "white", "pixels": [[110, 10]]}]]:
		var entry := _entry()
		entry.lamps = lamps
		var verifier := _verify(_frame(Color.BLACK, Color.BLACK), entry)
		assert_true(not verifier.failures.is_empty(), "a white beat needs visible white light")
		verifier.free()

func test_scenario_preserves_authored_camera_pullback() -> void:
	var parsed := HarnessScenario.parse(JSON.stringify({"name": "framing", "beats": [{"name": "white", "tick": 100, "light": "white", "camera_back": 3.0}]}))
	assert_true(parsed.error.is_empty(), parsed.error)
	assert_float_equal(parsed.scenario.beats[0].get("camera_back", 0.0), 3.0, "authored framing must reach the capture camera")

func test_scenario_rejects_invalid_camera_pullback() -> void:
	for value: Variant in [-1, "three"]:
		var parsed := HarnessScenario.parse(JSON.stringify({"name": "framing", "beats": [{"name": "white", "tick": 100, "camera_back": value}]}))
		assert_false(parsed.error.is_empty(), "capture pullback must be a finite nonnegative distance")

func test_white_lens_does_not_bypass_nonblack_frame_gate() -> void:
	var verifier := _verify(_frame(Color.WHITE, Color.BLACK, Color.BLACK), _entry())
	assert_true(verifier.failures.any(func(message: String) -> bool: return message.contains("is black")), "whole-frame nonblack requirement remains")
	verifier.free()

func test_missing_lamp_is_an_authoring_error() -> void:
	var entry := _entry()
	entry.erase("lamps")
	var verifier := _verify(_frame(Color.WHITE, Color.BLACK), entry)
	assert_true(verifier.failures.any(func(message: String) -> bool: return message.contains("scenario authoring error")), "missing capture data cannot skip the gate")
	verifier.free()

func test_invalid_lamp_coordinates_fail_without_reading_outside_image() -> void:
	var entry := _entry()
	entry.lamps[0].pixels = [[999, 10]]
	var verifier := _verify(_frame(Color.WHITE, Color.BLACK), entry)
	assert_true(verifier.failures.any(func(message: String) -> bool: return message.contains("outside the measured frame")), "invalid report coordinates fail visibly")
	verifier.free()

func test_malformed_lamp_records_are_rejected() -> void:
	var samples := preload("res://harness/lamp_samples.gd")
	for lamps: Variant in ["bad", [4], [{"id": "a", "circuit": "red", "pixels": [[110, 10]]}], [{"id": "a", "circuit": "white", "pixels": [[1.5, 10]]}]]:
		assert_false(samples.validate(lamps).is_empty(), "malformed lamp data is rejected")

func test_record_projects_lenses_and_respects_opaque_occlusion() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "tests/lamp_scene_checks.gd"], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("ERROR:"), text)

func check_projection() -> void:
	var tree := Engine.get_main_loop() as SceneTree
	var scene := Node3D.new()
	tree.root.add_child(scene)
	var camera := Camera3D.new()
	scene.add_child(camera)
	var lens := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(1, 0.2, 0.1)
	lens.mesh = mesh
	lens.position = Vector3(0, 0, -3)
	lens.set_meta(&"lamp_circuit", "white")
	scene.add_child(lens)
	var sampler := preload("res://harness/lamp_samples.gd").new()
	var size := Vector2i(tree.root.get_visible_rect().size)
	assert_int_equal(sampler.record(scene, camera, size).size(), 1, "visible fixture is projected")
	var blocker := MeshInstance3D.new()
	var wall := BoxMesh.new()
	wall.size = Vector3(1.5, 0.5, 0.1)
	blocker.mesh = wall
	blocker.position = Vector3(0, 0, -2)
	scene.add_child(blocker)
	assert_int_equal(sampler.record(scene, camera, size).size(), 0, "opaque wall hides the lens")
	blocker.position.x = 0.6
	assert_int_equal(sampler.record(scene, camera, size).size(), 1, "exposed lens edge remains measurable when its centre is hidden")
	blocker.layers = 2
	camera.cull_mask = 1
	assert_int_equal(sampler.record(scene, camera, size).size(), 1, "camera-hidden geometry does not occlude")
	lens.hide()
	assert_int_equal(sampler.record(scene, camera, size).size(), 0, "hidden fixture is excluded")
	scene.free()

func test_lamp_pixels_survive_report_roundtrip() -> void:
	var report := HarnessReport.new(5, "lamps", 91, {"app_hash": "a", "scenario_hash": "s", "config_hash": "c"})
	var entry := _entry()
	entry.merge({"file": "beats/white.png", "request_id": 1})
	report.beats["white"] = entry
	var parsed := HarnessReport.parse(report.to_json())
	assert_true(parsed.error.is_empty(), parsed.error)
	var lamps: Array = parsed.report.beats.white.lamps
	assert_int_equal(lamps.size(), 2, "both fixture records survive")
	assert_true(lamps[0].id == "regular" and lamps[1].circuit == "emergency", "fixture identity and circuit survive")
	assert_int_equal(int(lamps[0].pixels[0][0]), 110, "runner receives pinned pixel x")
	assert_int_equal(int(lamps[0].pixels[0][1]), 10, "runner receives pinned pixel y")
