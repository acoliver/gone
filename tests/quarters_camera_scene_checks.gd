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
	QuartersCapture.pose(camera, "wide")
	check.assert_float_in_range(camera.global_position.y - QuartersLayout.FLOOR_Y, 2.19, 2.21, "wide camera is at the requested 2.2 m height")
	var points: Array[Vector3] = []
	for state: StringName in [&"as_built", &"aged"]:
		var furnishings := QuartersFurnishings.build(state)
		var sofa := QuartersFurnishings._bounds(furnishings.get_node("Placement_sofa"))
		for corner: int in range(8): points.append(sofa.get_endpoint(corner))
		furnishings.free()
	for x: float in [2.0, 6.0]:
		for z: float in [1.5, 4.5]:
			for edge: float in [-0.65, 0.65]:
				points.append(QuartersLayout.to_world(Vector3(x + edge, 3.2, z)))
	var viewport := root.get_visible_rect()
	for point: Vector3 in points:
		check.assert_false(camera.is_position_behind(point), "room content in front of wide camera")
		var uv := camera.unproject_position(point) / viewport.size
		check.assert_float_in_range(uv.x, 0.015, 0.985, "whole sofa and ceiling fixtures inside horizontal frame: " + str(uv))
		check.assert_float_in_range(uv.y, 0.015, 0.985, "whole sofa and ceiling fixtures inside vertical frame: " + str(uv))
	room.free()
	if not check.failure.is_empty():
		printerr(check.failure)
		quit(1)
		return
	print("QUARTERS CAMERA PASS")
	quit(0)
