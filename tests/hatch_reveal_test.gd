extends SimTestCase

func test_throat_visible_depth_is_at_most_eighty_millimetres() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(layout.door(id)):
			if "/THROAT/" in String(solid.id):
				assert_true(solid.size.z <= 0.08 + 0.000001, "visible sleeve is shallow, with sealing returns owned by the collar")

func test_imported_rear_seating_lip_and_throat_keep_continuous_depth_runs() -> void:
	var packed: PackedScene = load(HatchAsset.SOURCE)
	var root := packed.instantiate()
	var meshes: Dictionary = {}
	_collect(root, meshes)
	var document: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(HatchAsset.MANIFEST))
	for variant: Dictionary in document.variants:
		var door := ShipLayout.authored().layout.door(StringName(variant.door_id))
		var seating := ShipGeometry.hatch_seating_outline(door)
		var ring: Dictionary = {}
		var runs: Dictionary = {}
		for solid: Dictionary in variant.frame_solids:
			if "/RING/" in solid.id: ring[int(String(solid.id).get_slice("/", 3))] = solid
		for solid: Dictionary in variant.frame_solids:
			if not ("/LIP/" in solid.id or "/THROAT/" in solid.id): continue
			var station := int(String(solid.id).get_slice("/", 3))
			var ring_pose := HatchAsset.pose(ring[station].transform)
			var pose := HatchAsset.pose(solid.transform)
			for endpoint: int in [0, 1]:
				var expected := ring_pose * Vector3(ring[station].section[endpoint][0], ring[station].section[endpoint][1], 0)
				# The rear lip deliberately laps the rounded upper leaf. The
				# lower seat keeps its walk height; the throat stays on the ring.
				var corner := (station + endpoint) % seating.size()
				if "/LIP/" in solid.id:
					expected.x = seating[corner].x
					expected.y = seating[corner].y + (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
				var actual := pose * Vector3(solid.section[endpoint][0], solid.section[endpoint][1], 0)
				assert_true(Vector2(actual.x, actual.y).distance_to(Vector2(expected.x, expected.y)) < 0.000001, "rear lip meets its rounded seat; throat stays on the ring")
			var wall_normals: Array[Vector3] = []
			var wall_points: Array[Vector3] = []
			for name: String in document.nodes:
				var row: Dictionary = document.nodes[name]
				if row.kind != "frame" or int(row.variant) != int(variant.index) or row.id != solid.id: continue
				var arrays: Array = meshes[name].surface_get_arrays(0)
				var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
				var a := Vector2(solid.section[0][0], solid.section[0][1])
				var b := Vector2(solid.section[1][0], solid.section[1][1])
				for index: int in range(points.size()):
					var point := points[index]
					if Geometry2D.get_closest_point_to_segment(Vector2(point.x, point.y), a, b).distance_to(Vector2(point.x, point.y)) > 0.000001: continue
					if absf(normals[index].z) > 0.01: continue
					wall_normals.append(normals[index])
					wall_points.append(point)
			assert_true(wall_points.size() >= 4, "actual imported inner reveal wall exists")
			for normal: Vector3 in wall_normals:
				assert_true(normal.dot(wall_normals[0]) > 0.999999, "actual reveal wall has no repeated rolled bands or discontinuous normals")
			var depths: Dictionary = {}
			for point: Vector3 in wall_points: depths[roundi(point.z * 1000000)] = true
			assert_int_equal(depths.size(), 2, "actual imported reveal has only its front and rear stations, no polygonal depth steps")
			var low := INF
			var high := -INF
			for point: Vector3 in wall_points:
				var depth := (pose * point).z
				low = minf(low, depth)
				high = maxf(high, depth)
			if not runs.has(station): runs[station] = []
			runs[station].append(Vector2(low, high))
		for station: int in runs:
			var ring_solid: Dictionary = ring[station]
			var ring_pose := HatchAsset.pose(ring_solid.transform)
			var end_a := (ring_pose * Vector3(0, 0, -ring_solid.size[2] / 2)).z
			var end_b := (ring_pose * Vector3(0, 0, ring_solid.size[2] / 2)).z
			runs[station].append(Vector2(minf(end_a, end_b), maxf(end_a, end_b)))
			for a: int in range(runs[station].size()):
				for b: int in range(a + 1, runs[station].size()):
					var first: Vector2 = runs[station][a]
					var second: Vector2 = runs[station][b]
					assert_true(minf(first.y, second.y) - maxf(first.x, second.x) <= 0.000001, "actual inner walls never overlap coplanar faces along their depth runs")
	root.free()

func _collect(node: Node, meshes: Dictionary) -> void:
	if node is MeshInstance3D: meshes[String(node.name)] = node.mesh
	for child: Node in node.get_children(): _collect(child, meshes)
