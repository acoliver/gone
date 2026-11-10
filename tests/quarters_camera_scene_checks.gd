extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1536, 864)
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
			var fixture := Node3D.new()
			fixture.position = QuartersLayout.to_world(Vector3(x, 3.05, z))
			CeilingFixture.mount(fixture, QuartersLayout.FLOOR_Y + QuartersLayout.HEIGHT, Lighting.QUARTERS_MASK, CeilingFixture.glass_material(1))
			var bounds := QuartersFurnishings._bounds(fixture)
			for corner: int in range(8): points.append(bounds.get_endpoint(corner))
			fixture.free()
	var viewport := root.get_visible_rect()
	for point: Vector3 in points:
		check.assert_false(camera.is_position_behind(point), "room content in front of wide camera")
		var uv := camera.unproject_position(point) / viewport.size
		check.assert_float_in_range(uv.x, 0.015, 0.985, "whole sofa and ceiling fixtures inside horizontal frame: " + str(uv))
		check.assert_float_in_range(uv.y, 0.015, 0.985, "whole sofa and ceiling fixtures inside vertical frame: " + str(uv))
	QuartersCapture.pose(camera, "bed")
	check.assert_close(camera.global_position, QuartersLayout.to_world(Vector3(2.5, 2.4, 2.25)), "matched bed close eye")
	check.assert_float_equal(camera.fov, 80.0, "bed horizontal field")
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var soft := furnishings.get_node("Placement_bed/bed_soft")
		for mesh: MeshInstance3D in soft.find_children("*", "MeshInstance3D", true, false):
			var bounds := ShipScene._world_frame(mesh) * mesh.get_aabb()
			for corner: int in range(8):
				var point := bounds.get_endpoint(corner)
				check.assert_false(camera.is_position_behind(point), "bed part in front of close camera")
				var uv := camera.unproject_position(point) / viewport.size
				check.assert_float_in_range(uv.x, 0.015, 0.985, "bed part inside horizontal frame: " + str(uv))
				check.assert_float_in_range(uv.y, 0.015, 0.985, "bed part inside vertical frame: " + str(uv))
		furnishings.free()
	var close_items := {"bedside": ["photo_frame"], "table": ["mug_1", "mug_2", "plate_1", "plate_2"], "desk": ["medal_case", "data_tablet_2"]}
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		for view: String in close_items:
			QuartersCapture.pose(camera, view)
			for id: String in close_items[view]:
				var bounds := QuartersFurnishings._bounds(furnishings.get_node("Item_" + id))
				for corner: int in range(8):
					var point := bounds.get_endpoint(corner)
					check.assert_false(camera.is_position_behind(point), "small item in front of close camera")
					var uv := camera.unproject_position(point) / viewport.size
					check.assert_float_in_range(uv.x, 0.015, 0.985, "small item inside horizontal frame: " + id)
					check.assert_float_in_range(uv.y, 0.0613, 0.985, "small item below presentation crop and inside frame: " + id)
		furnishings.free()
	room.free()
	if not check.failure.is_empty():
		printerr(check.failure)
		quit(1)
		return
	print("QUARTERS CAMERA PASS")
	quit(0)
