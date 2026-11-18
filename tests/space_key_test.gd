extends SimTestCase

# Issue #142: Andrew pressed the physical Space key on the D14 C-001 landing
# and nothing mounted. The checks drive real InputEventKey presses through the
# production main scene from frame time, at the matched live look and two
# others, with 40, 80 and 150 ms holds. Every press must mount and print one
# SPACE line. A key that reaches the player's _input without an interact edge
# must also print one, so a key the game never sees (no line) can be told
# apart from one it saw but did not act on.
func test_space_key_events_mount_and_every_press_reports() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), [
		"--headless", "--fixed-fps", "60", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/space_key_checks.gd",
	], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_true(text.contains("SPACE KEY PASS cases=10"), text)
	var reports: PackedStringArray = []
	for line: String in text.split("\n"):
		if line.begins_with("SPACE state="):
			reports.append(line)
	assert_int_equal(reports.size(), 10, "one SPACE line per press:\n" + "\n".join(reports))
	var mounts := 0
	for line: String in reports:
		if line.ends_with("result=mount C-001-LADDER"):
			mounts += 1
	assert_int_equal(mounts, 9, "every key press mounts:\n" + "\n".join(reports))
	var last := reports[reports.size() - 1] if not reports.is_empty() else ""
	assert_true(last == "SPACE state=walking deck=14 foot=(34.500, 0.385, -2.950) yaw=-20.0 pitch=-48.0 result=no edge", "a key without an interact edge reports: " + last)
