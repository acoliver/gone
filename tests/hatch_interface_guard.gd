extends SceneTree

func _init() -> void:
	var test := preload("res://tests/hatch_seal_test.gd").new()
	test.test_collision_reservations_trimmed_rendering_and_both_sided_seals()
	print("INTERFACE_GUARD ", "PASS" if test.failure.is_empty() else test.failure)
	quit(0 if test.failure.is_empty() else 1)
