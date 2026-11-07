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
	assert_true(controls.has(&"mouse_look") and controls.has(&"mouse_pick") and controls.has(&"escape"), "non-InputMap pointer controls and escape are listed")
	var expected := {
		&"move_forward": "Flecha arriba", &"move_back": "Flecha abajo",
		&"move_left": "Flecha izquierda", &"move_right": "Flecha derecha",
		&"activate": "Espacio", &"interact": "Espacio",
		&"look_left": ", / A", &"look_right": ". / D",
		&"look_up": "W", &"look_down": "S", &"climb_up": "W", &"climb_down": "S",
		&"release_cursor": "Tab", &"help": "F1",
	}
	for action: StringName in expected:
		assert_true(String(controls[action]).ends_with(": " + expected[action]), "Spanish keyboard binding for %s: %s" % [action, controls[action]])
	assert_true(String(controls[&"mouse_pick"]).begins_with("Clic izquierdo:"), "mouse button uses its Spanish name")
	assert_true(String(controls[&"escape"]).begins_with("Esc:"), "escape uses the keyboard legend")
	for line: String in controls.values():
		assert_false(line.contains(" - Physical") or line.contains("Mouse") or line.contains("Button"), "no raw Godot event text: " + line)

func test_help_reads_rebound_inputmap_events() -> void:
	var script := _script()
	if script == null: return
	var original := InputMap.action_get_events(&"activate")
	InputMap.action_erase_events(&"activate")
	var key := InputEventKey.new()
	key.keycode = KEY_UP
	InputMap.action_add_event(&"activate", key)
	var text: String = script.controls()[&"activate"]
	InputMap.action_erase_events(&"activate")
	for event: InputEvent in original: InputMap.action_add_event(&"activate", event)
	assert_true(text.ends_with(": Flecha arriba"), "help displays the actual rebound logical key: " + text)

func test_f1_pauses_until_f1_escape_or_close_button_and_clears_pending_input() -> void:
	if _script() == null: return
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "res://tests/help_panel_integration.gd"], output, true)
	var text := "\n".join(output)
	assert_true(code == 0 and "HELP PASS" in text and "SCRIPT ERROR:" not in text, "help integration: " + text)
