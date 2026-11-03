extends SceneTree
## Positional players need an initialized tree, unlike the runner's _init tests.

func _init() -> void:
	_run.call_deferred()

func _run() -> void:
	var checks: SimTestCase = load("res://tests/door_audio_test.gd").new()
	checks.begin_test()
	checks.call(OS.get_cmdline_user_args()[0])
	if not checks.failure.is_empty():
		printerr(checks.failure)
	quit(0 if checks.failure.is_empty() else 1)
