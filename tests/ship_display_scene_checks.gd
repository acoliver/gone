extends SceneTree
## Attention uses global transforms, so run these checks after the tree starts.

func _init() -> void:
	_run.call_deferred()

func _run() -> void:
	var checks: SimTestCase = load("res://tests/ship_display_test.gd").new()
	checks.begin_test()
	checks.call(OS.get_cmdline_user_args()[0])
	if not checks.failure.is_empty():
		printerr(checks.failure)
	quit(0 if checks.failure.is_empty() else 1)
