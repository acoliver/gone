extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var check := SimTestCase.new()
	var room := Node3D.new()
	var camera := Camera3D.new()
	room.add_child(camera)
	root.add_child(room)
	QuartersCapture.pose(camera, "doorway")
	check.assert_close(camera.global_position, Vector3(45, -9.35, 1.85), "approved doorway eye")
	check.assert_true((-camera.global_basis.z).dot((Vector3(45, -9.75, 7.7) - camera.global_position).normalized()) > 0.99999, "approved doorway aim")
	check.assert_float_equal(camera.fov, 100, "approved horizontal field")
	room.free()
	if not check.failure.is_empty():
		printerr(check.failure)
		quit(1)
		return
	print("QUARTERS CAMERA PASS")
	quit(0)
