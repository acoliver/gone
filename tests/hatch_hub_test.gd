extends SimTestCase

func test_imported_hub_has_a_front_boss_collar_and_hex_nut() -> void:
	var door := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var view := DoorView.build(door)
	for path: String in ["Wheel", "ReverseWheel"]:
		var mesh: Mesh = view.label_leaf().get_node(path).get_child(0).mesh
		var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(mesh)
		var arrays := mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var hub: Dictionary = parts[StringName(path + "/hub")]
		var radii: Dictionary = {}
		for index: int in range(int(hub.row.vertex_start), int(hub.row.vertex_start + hub.row.vertex_count)):
			var point: Vector3 = vertices[index]
			if point.z < -0.004:
				radii[roundi(Vector2(point.x, point.y).length() * 10000)] = true
		assert_true(radii.size() >= 3, "three machined radial steps project ahead of the spokes")
		var cap: Dictionary = parts[StringName(path + "/cap")]
		var corners: Dictionary = {}
		var front: float = cap.bounds.end.y
		for index: int in range(int(cap.row.vertex_start), int(cap.row.vertex_start + cap.row.vertex_count)):
			var point: Vector3 = cap.pose.affine_inverse() * vertices[index]
			if absf(point.y - front) < 0.000001:
				corners[roundi(atan2(point.z, point.x) * 10000)] = true
		assert_int_equal(corners.size(), 6, "front retention nut has six flat sides")
	view.free()

func test_wheel_hub_front_occludes_the_spoke_roots() -> void:
	var door := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	for group: HatchParts.Group in HatchParts.leaf(door):
		if String(group.path) not in ["Wheel", "ReverseWheel"]: continue
		var hub_front := INF
		var spoke_front := INF
		for part: HatchParts.Part in group.parts:
			var bounds: AABB = part.transform * AABB(-part.size / 2, part.size)
			if String(part.id).ends_with("/hub"): hub_front = bounds.position.z
			if "/spoke-" in String(part.id): spoke_front = minf(spoke_front, bounds.position.z)
		assert_true(hub_front < spoke_front - 0.002, "hub's machined front shoulder covers vertical spoke roots by at least 2mm")

func test_retention_nut_has_real_chamfer_and_stands_proud_of_boss_shoulder() -> void:
	var view := DoorView.build(ShipLayout.authored().layout.door(&"D14-C-001-H-FORE"))
	for path: String in ["Wheel", "ReverseWheel"]:
		var mesh: Mesh = view.label_leaf().get_node(path).get_child(0).mesh
		var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(mesh)
		var vertices: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		var cap: Dictionary = parts[StringName(path + "/cap")]
		var hub: Dictionary = parts[StringName(path + "/hub")]
		var stations: Dictionary = {}
		var nut_front := INF
		for index: int in range(int(cap.row.vertex_start), int(cap.row.vertex_start + cap.row.vertex_count)):
			var point: Vector3 = vertices[index]
			nut_front = minf(nut_front, point.z)
			stations[roundi(point.z * 1000000)] = true
		assert_true(stations.size() >= 4, "nut has two real chamfers and an axial flat, not an extruded hex cap")
		var shoulder_front := INF
		for index: int in range(int(hub.row.vertex_start), int(hub.row.vertex_start + hub.row.vertex_count)):
			var point: Vector3 = vertices[index]
			if Vector2(point.x, point.y).length() >= 0.085:
				shoulder_front = minf(shoulder_front, point.z)
		print("HATCH_NUT_RELIEF %s stations=%d proud_m=%.6f" % [path, stations.size(), shoulder_front - nut_front])
		assert_true(shoulder_front - nut_front >= 0.008, "nut stands at least 8mm ahead of the surrounding boss shoulder")
	view.free()
