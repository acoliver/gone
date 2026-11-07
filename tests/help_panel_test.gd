extends SimTestCase

func _script() -> GDScript:
	var path := "res://app/help_panel.gd"
	assert_true(ResourceLoader.exists(path), "F1 controls help must exist")
	return load(path) if ResourceLoader.exists(path) else null

func test_help_lists_every_inputmap_gameplay_action_and_mouse_binding() -> void:
	var script := _script()
	if script == null: return
	var controls: Dictionary = script.controls()
	for action: StringName in InputMap.get_actions():
		if String(action).begins_with("ui_"): continue
		assert_true(controls.has(action), "actual gameplay action appears: %s" % action)
		for event: InputEvent in InputMap.action_get_events(action):
			assert_true(String(controls[action]).contains(event.as_text()), "actual binding appears: %s" % event.as_text())
	assert_true(controls.has(&"mouse_look") and controls.has(&"mouse_pick") and controls.has(&"escape"), "non-InputMap pointer controls and escape are listed")

func test_f1_pauses_until_f1_escape_or_close_button_and_clears_pending_input() -> void:
	if _script() == null: return
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "res://tests/help_panel_integration.gd"], output, true)
	var text := "\n".join(output)
	assert_true(code == 0 and "HELP PASS" in text and "SCRIPT ERROR:" not in text, "help integration: " + text)
