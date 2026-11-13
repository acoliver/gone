extends SimTestCase

class CapturePlayer:
	extends Player
	var capture_requested := false
	func _set_mouse_capture(captured: bool) -> void:
		capture_requested = captured
		super._set_mouse_capture(captured)

func check_open_close() -> void:
	var script: GDScript = load("res://app/help_panel.gd")
	var tree := Engine.get_main_loop() as SceneTree
	var game := Game.new(91)
	var player := CapturePlayer.new()
	player.game = game
	player.scripted = true
	tree.root.add_child(player)
	var help: Node = script.build(player)
	tree.root.add_child(help)
	var key := InputEventKey.new()
	key.physical_keycode = KEY_F1
	key.pressed = true
	for dismissal: String in ["F1", "Esc", "Close"]:
		player.plane.offer_press(InputPlane.Buttons.INTERACT)
		help._input(key)
		assert_true(tree.paused, "opening help pauses the scene tree")
		assert_false(player.can_process(), "paused player cannot consume a sim tick")
		assert_true(help.can_process(), "popover still receives input while paused")
		assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_VISIBLE, "help releases the cursor")
		assert_int_equal(player.plane.pending_edges(), 0, "pre-pause edges cannot replay")
		var echo := key.duplicate() as InputEventKey
		echo.echo = true
		help._input(echo)
		assert_true(tree.paused, "F1 repeat does not dismiss help")
		Input.action_press("activate")
		Input.action_press("interact")
		match dismissal:
			"F1": help._input(key)
			"Esc":
				var esc := InputEventKey.new()
				esc.physical_keycode = KEY_ESCAPE
				esc.pressed = true
				help._input(esc)
			"Close": help.close_button.pressed.emit()
		assert_false(tree.paused, "dismissal resumes the scene tree")
		assert_true(player.capture_requested, "dismissal requests cursor capture; the headless display has no capture mode")
		assert_int_equal(player.plane.pending_edges(), 0, "dismissal creates no gameplay edges")
		assert_false(Input.is_action_pressed("activate") or Input.is_action_pressed("interact"), "Space used by the modal cannot activate gameplay after dismissal")
	help.free()
	player.free()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
