extends SceneTree
## Attention uses global transforms, so run this check after the tree starts.

func _init() -> void:
	_run.call_deferred()

func _run() -> void:
	var checks: SimTestCase = load("res://tests/power_room_test.gd").new()
	checks.begin_test()
	checks.call("_check_status_board_attention")
	if not checks.failure.is_empty():
		printerr(checks.failure)
	quit(0 if checks.failure.is_empty() else 1)
