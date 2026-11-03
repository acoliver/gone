extends SimTestCase

func test_native_captured_and_released_clicks_through_real_player() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), [
		"--resolution", "960x540", "--fixed-fps", "60", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/click_device_checks.gd",
	], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_true(text.contains("DEVICE CLICK PASS"), text)
