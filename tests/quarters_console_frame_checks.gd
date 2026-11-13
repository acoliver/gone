extends SceneTree

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	root.size = Vector2i(1536, 864)
	var scene := Node3D.new()
	root.add_child(scene)
	var camera := Camera3D.new()
	scene.add_child(camera)
	QuartersCapture.pose(camera, "console")
	var check := SimTestCase.new()
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		scene.add_child(furnishings)
		var console := furnishings.get_node("Placement_console/console")
		for part: MeshInstance3D in console.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(part.mesh.get_surface_count()):
				for vertex: Vector3 in part.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
					var point := part.global_transform * vertex
					check.assert_false(camera.is_position_behind(point), "console stays in front of close camera")
					var pixel := camera.unproject_position(point)
					check.assert_true(pixel.x >= 2 and pixel.x <= 1534 and pixel.y >= 2 and pixel.y <= 862, "%s/%s stays inside full camera frame: %s" % [state, part.name, pixel])
		furnishings.free()
	scene.free()
	if not check.failure.is_empty():
		printerr(check.failure)
		quit(1)
		return
	print("CONSOLE FRAME PASS")
	quit(0)
