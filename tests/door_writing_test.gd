extends SimTestCase

func test_level_hatch_gaze_resolves_decays_and_label_swings_with_leaf() -> void:
	_run("check_hatch")

func test_level_aft_lift_gaze_resolves_and_decays_on_fresh_game() -> void:
	_run("check_lift")

func _run(method: String) -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--windowed", "--resolution", "480x270", "--path", ProjectSettings.globalize_path("res://"), "-s", "tests/door_writing_scene_checks.gd", "--", method], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_false(text.contains("ERROR:"), text)
