extends SimTestCase

func test_device_release_near_landing_settles_exactly() -> void:
	_run("settle")

func test_device_space_on_release_dismounts_with_residual_velocity() -> void:
	_run("release")

func test_device_space_after_release_dismounts() -> void:
	_run("delayed")

func test_device_space_while_holding_climb_dismounts() -> void:
	_run("held")

func test_device_endpoint_clamps_and_midshaft_space() -> void:
	_run("bounds")

func _run(mode: String) -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), [
		"--headless", "--fixed-fps", "60", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/ladder_device_checks.gd", "--", mode,
	], output, true)
	var text := "".join(output)
	print(text)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_true(text.contains("DEVICE LADDER PASS " + mode), "device checks completed")
