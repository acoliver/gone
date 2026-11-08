extends SceneTree

class Driver:
	extends Node
	var step: GameStep
	func _physics_process(_dt: float) -> void: step.advance()

func _initialize() -> void: _run.call_deferred()

func _run() -> void:
	var checks := preload("res://tests/help_panel_checks.gd").new()
	checks.check_open_close()
	if not checks.failure.is_empty():
		printerr(checks.failure)
		quit(1)
		return
	var player := Player.build(Game.new(91), null)
	player.scripted = true
	root.add_child(player)
	var driver := Driver.new()
	driver.step = GameStep.new(player.game, player)
	root.add_child(driver)
	var help := HelpPanel.build(player)
	root.add_child(help)
	await physics_frame
	var f1 := InputEventKey.new()
	f1.physical_keycode = KEY_F1
	f1.pressed = true
	root.push_input(f1)
	await process_frame
	if not paused:
		printerr("F1 did not reach the modal through the input pipeline")
		quit(1)
		return
	var tick := driver.step.logical_tick
	for frame: int in range(5): await physics_frame
	if driver.step.logical_tick != tick:
		printerr("help advanced simulation while paused")
		quit(1)
		return
	var escape := InputEventKey.new()
	escape.physical_keycode = KEY_ESCAPE
	escape.pressed = true
	root.push_input(escape)
	await process_frame
	if paused:
		printerr("Esc did not dismiss the modal through the input pipeline")
		quit(1)
		return
	for frame: int in range(5): await physics_frame
	if driver.step.logical_tick <= tick:
		printerr("closing help did not resume simulation")
		quit(1)
		return
	help.free()
	driver.free()
	player.free()
	print("HELP PASS: F1, Esc, Close, cursor, pending input and real fixed-tick pause/resume")
	quit(0)
