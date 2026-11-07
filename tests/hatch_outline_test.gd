extends SimTestCase

const TOLERANCE: float = 0.001

func _dimension(name: String) -> float:
	var dimensions := (load("res://sim/ship_geometry.gd") as GDScript).get_script_constant_map()
	assert_true(dimensions.has(name), "shared dimension exists: " + name)
	return dimensions.get(name, 0.0)

func _door() -> ShipLayout.DoorSpec:
	return ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")

func _geometry_api() -> bool:
	var geometry := ShipGeometry.new()
	var available := geometry.has_method("hatch_ring_outline") and geometry.has_method("hatch_frame_rivet_stations")
	assert_true(available, "pure hatch outline and rivet station APIs must exist")
	return available

func _outline(door: ShipLayout.DoorSpec, offset: float = 0.0) -> PackedVector2Array:
	return ShipGeometry.new().call("hatch_ring_outline", door, offset)

func _stations(aperture: Vector2) -> Array[Transform3D]:
	return ShipGeometry.new().call("hatch_frame_rivet_stations", aperture)

func _distance(point: Vector2, polygon: PackedVector2Array) -> float:
	var nearest := INF
	for index: int in range(polygon.size()):
		nearest = minf(nearest, point.distance_to(Geometry2D.get_closest_point_to_segment(point, polygon[index], polygon[(index + 1) % polygon.size()])))
	return nearest

func _perimeter(polygon: PackedVector2Array) -> float:
	var length := 0.0
	for index: int in range(polygon.size()):
		length += polygon[index].distance_to(polygon[(index + 1) % polygon.size()])
	return length

func _arc_distance(point: Vector2, polygon: PackedVector2Array) -> float:
	var nearest := INF
	var station := 0.0
	var length := 0.0
	for index: int in range(polygon.size()):
		var a := polygon[index]
		var b := polygon[(index + 1) % polygon.size()]
		var projected := Geometry2D.get_closest_point_to_segment(point, a, b)
		if point.distance_to(projected) < nearest:
			nearest = point.distance_to(projected)
			station = length + a.distance_to(projected)
		length += a.distance_to(b)
	return station

func test_ring_outline_preserves_aperture_top_and_walk_height() -> void:
	if not _geometry_api(): return
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var inner := _outline(door)
		var aperture := door.aperture()
		var original := HatchParts.outline(Vector2(aperture.x + 0.01, aperture.y - ShipGeometry.SILL_HEIGHT), 0.24)
		assert_int_equal(inner.size(), 36, "outline retains eight segments per corner and four straights")
		assert_false(Geometry2D.is_polygon_clockwise(inner), "centered XY outline has positive winding")
		for index: int in range(18):
			assert_true(inner[index].distance_to(original[index]) < 0.000001, "upper aperture remains unchanged: " + String(id))
		var center_y := (aperture.y + ShipGeometry.SILL_HEIGHT) / 2
		var bottom := INF
		for point: Vector2 in inner:
			bottom = minf(bottom, point.y + center_y)
		assert_true(absf(bottom - ShipGeometry.SILL_HEIGHT) < 0.000001, "lower opening stays at the 80mm coaming")
		assert_true(absf(inner[0].x - (aperture.x + 0.01) / 2) < 0.000001, "nominal aperture width stays unchanged")

func test_ring_is_a_constant_width_polygon_offset_everywhere() -> void:
	if not _geometry_api(): return
	var door := _door()
	var width: float = _dimension("HATCH_RING_WIDTH")
	assert_true(width > 0.0, "ring width is a positive shared dimension")
	var inner := _outline(door)
	var outer := _outline(door, width)
	assert_int_equal(outer.size(), inner.size(), "offset preserves cell correspondence")
	for index: int in range(inner.size()):
		var next := (index + 1) % inner.size()
		var edge := (inner[next] - inner[index]).normalized()
		var normal := Vector2(edge.y, -edge.x)
		for step: int in range(17):
			var t := step / 16.0
			var point := outer[index].lerp(outer[next], t)
			assert_true(absf(_distance(point, inner) - width) <= TOLERANCE, "constant width at outer edge %d sample %d" % [index, step])
			var inner_point := inner[index].lerp(inner[next], t)
			assert_true(_distance(inner_point + normal * width, outer) <= TOLERANCE, "normal offset at inner edge %d sample %d" % [index, step])
		assert_true(absf((outer[index] - inner[index]).dot(normal) - width) < 0.000001, "outer edge lies on the parallel offset line")
		assert_true((outer[next] - outer[index]).dot(edge) > 0.0, "offset never reverses an edge")

func test_surround_cells_are_convex_nonzero_and_join_without_sawteeth() -> void:
	var door := _door()
	var rings: Dictionary = {}
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(door):
		if solid.section.is_empty(): continue
		assert_int_equal(solid.section.size(), 4, "each annular cell is a convex quad")
		assert_true(solid.size.x > 0 and solid.size.y > 0 and solid.size.z > 0, "cell extrusion has positive dimensions")
		var points := PackedVector2Array()
		var portal := door.frame().affine_inverse() * solid.transform
		for point: Vector2 in solid.section:
			var placed := portal * Vector3(point.x, point.y, 0)
			points.append(Vector2(placed.x, placed.y))
		for index: int in range(4):
			var a := solid.section[index]
			var b := solid.section[(index + 1) % 4]
			var c := solid.section[(index + 2) % 4]
			assert_true((b - a).cross(c - b) < -0.000000001, "cell is strictly convex, consistently wound and nondegenerate: " + String(solid.id))
		var family := String(solid.id).get_slice("/", 3)
		if not rings.has(family): rings[family] = []
		rings[family].append(points)
		var mesh := HatchModel.solid_mesh(solid)
		var arrays := mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for triangle: int in range(0, indices.size(), 3):
			var a := vertices[indices[triangle]]
			var b := vertices[indices[triangle + 1]]
			var c := vertices[indices[triangle + 2]]
			assert_true((b - a).cross(c - a).length() > 0.000000001, "no collapsed rendered triangle: " + String(solid.id))
	assert_int_equal(rings.size(), 3, "ring, lip and throat are all checked")
	for family: String in rings:
		var cells: Array = rings[family]
		for index: int in range(cells.size()):
			var next: PackedVector2Array = cells[(index + 1) % cells.size()]
			var cell: PackedVector2Array = cells[index]
			assert_true(cell[1].distance_to(next[0]) < 0.000001 and cell[2].distance_to(next[3]) < 0.000001, "neighboring %s cells share both endpoints" % family)

func test_ring_cells_use_public_outline_and_do_not_raise_walk_band() -> void:
	if not _geometry_api(): return
	var layout := ShipLayout.authored().layout
	var width: float = _dimension("HATCH_RING_WIDTH")
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var inner := _outline(door)
		var outer := _outline(door, width)
		var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		var index := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(door):
			if solid.section.is_empty(): continue
			var center := solid._local_center
			if "/RING/" in String(solid.id):
				var expected := PackedVector2Array([inner[index], inner[(index + 1) % inner.size()], outer[(index + 1) % inner.size()], outer[index]])
				for vertex: int in range(4):
					var actual := center + Vector3(solid.section[vertex].x, solid.section[vertex].y, 0)
					assert_true(Vector2(actual.x, actual.y - center_y).distance_to(expected[vertex]) < 0.000001, "ring cell follows shared centered outline: " + String(solid.id))
				index += 1
			if center.y < center_y and absf(center.x) - solid.size.x / 2 < ShipGeometry.SILL_WALK_WIDTH / 2:
				assert_true(center.y + solid.size.y / 2 <= ShipGeometry.SILL_HEIGHT + 0.000001, "lower ring/lip/throat collision stays below the walk band: " + String(solid.id))
		assert_int_equal(index, inner.size(), "every ring edge is a physical cell")

func test_frame_rivets_have_uniform_closed_arc_pitch_and_centered_inset() -> void:
	if not _geometry_api(): return
	var door := _door()
	var width: float = _dimension("HATCH_RING_WIDTH")
	var centerline := _outline(door, width / 2)
	var inner := _outline(door)
	var outer := _outline(door, width)
	var perimeter := _perimeter(centerline)
	var stations := _stations(door.aperture())
	assert_true(stations.size() > 40, "rivet row covers the closed surround")
	assert_true(stations == _stations(door.aperture()), "station data is deterministic")
	var pitch := perimeter / stations.size()
	assert_true(absf(pitch - 0.13) < 0.002, "one closed-loop pitch stays close to the authored 130mm target")
	var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
	for index: int in range(stations.size()):
		var pose := stations[index]
		var point := Vector2(pose.origin.x, pose.origin.y - center_y)
		var next_pose := stations[(index + 1) % stations.size()]
		var next := Vector2(next_pose.origin.x, next_pose.origin.y - center_y)
		var gap := fposmod(_arc_distance(next, centerline) - _arc_distance(point, centerline), perimeter)
		assert_true(absf(gap - pitch) < 0.00001, "uniform arc pitch includes the closing seam: station %d" % index)
		assert_true(_distance(point, centerline) < 0.000001, "rivet station lies on the frame centerline")
		assert_true(absf(_distance(point, inner) - width / 2) < TOLERANCE and absf(_distance(point, outer) - width / 2) < TOLERANCE, "equal inset to both frame edges")
		assert_float_equal(pose.origin.z, 0.0, "pure station has zero portal-local depth")
		assert_true(pose.basis.get_scale().distance_to(Vector3.ONE) < 0.000001, "rivets have no size variation")
		assert_true((pose.basis * Vector3.UP).distance_to(Vector3.BACK) < 0.000001, "cylinder axis faces portal depth")

func test_frame_rivet_mesh_consumes_shared_station_data_and_dimensions() -> void:
	if not _geometry_api(): return
	var aperture := _door().aperture()
	var stations := _stations(aperture)
	var batch := HatchModel.rivets(&"frame", aperture)
	var poses: Array[Transform3D] = batch.get_meta(&"instance_poses")
	assert_true(poses == stations, "presentation uses the pure physical station transforms without resampling")
	assert_int_equal(batch.instance_count, stations.size(), "one mesh instance per station")
	assert_true(absf(batch.mesh.top_radius - _dimension("HATCH_RIVET_RADIUS")) < 0.00000001, "shared rivet head radius")
	assert_true(absf(batch.mesh.bottom_radius - _dimension("HATCH_RIVET_RADIUS")) < 0.00000001, "uniform cylinder radius")
	assert_true(absf(batch.mesh.height - _dimension("HATCH_RIVET_DEPTH")) < 0.00000001, "shared rivet head depth")
