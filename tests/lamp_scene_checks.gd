extends SceneTree

func _init() -> void:
	_run.call_deferred()

func _run() -> void:
	root.size = Vector2i(480, 270)
	var checks := preload("res://tests/white_lamp_test.gd").new()
	checks.begin_test()
	checks.check_projection()
	if not checks.failure.is_empty(): printerr(checks.failure)
	quit(0 if checks.failure.is_empty() else 1)
