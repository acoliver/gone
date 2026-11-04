extends SimTestCase

func test_submitted_fixed_mesh_union_stays_inside_the_same_outline() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var outer := ShipGeometry.hatch_ring_outline(door, ShipGeometry.HATCH_RING_WIDTH)
		var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		var view := DoorView.build(door)
		for side: String in ["ForeSteel", "AftSteel"]:
			var piece: MeshInstance3D = view.get_node("Frame/" + side)
			var vertices: PackedVector3Array = piece.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
			for vertex: Vector3 in vertices:
				var xy := Vector2(vertex.x, vertex.y - center_y)
				var distance := INF
				for edge: int in range(outer.size()): distance = minf(distance, xy.distance_to(Geometry2D.get_closest_point_to_segment(xy, outer[edge], outer[(edge + 1) % outer.size()])))
				assert_true(Geometry2D.is_point_in_polygon(xy, outer) or distance <= 0.002, "submitted fixed geometry cannot widen the ring: %s %s point=%s outside=%.6f" % [id, side, xy, distance])
		view.free()

func test_every_fixed_face_stays_inside_the_single_offset_outline_from_both_sides() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var source := layout.door(id)
		var door := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
		var outer := ShipGeometry.hatch_ring_outline(door, ShipGeometry.HATCH_RING_WIDTH)
		var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		for side: int in [-1, 1]:
			for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door):
				var points := solid.section
				if points.is_empty():
					points = PackedVector2Array([-Vector2(solid.size.x, solid.size.y) / 2, Vector2(solid.size.x, -solid.size.y) / 2, Vector2(solid.size.x, solid.size.y) / 2, Vector2(-solid.size.x, solid.size.y) / 2])
				for point: Vector2 in points:
					var placed := solid.transform * Vector3(point.x, point.y, side * solid.size.z / 2)
					var xy := Vector2(placed.x, placed.y - center_y)
					var distance := INF
					for edge: int in range(outer.size()):
						distance = minf(distance, xy.distance_to(Geometry2D.get_closest_point_to_segment(xy, outer[edge], outer[(edge + 1) % outer.size()])))
					assert_true(Geometry2D.is_point_in_polygon(xy, outer) or distance <= 0.002, "fixed union cannot widen the ring: %s face=%d point=%s outside_m=%.6f" % [solid.id, side, xy, distance])
		var ring_cells := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door):
			if not "/RING/" in String(solid.id): continue
			ring_cells += 1
			for endpoint: int in [2, 3]:
				var p := solid.transform * Vector3(solid.section[endpoint].x, solid.section[endpoint].y, 0)
				var xy := Vector2(p.x, p.y - center_y)
				var nearest := INF
				for expected: Vector2 in outer: nearest = minf(nearest, expected.distance_to(xy))
				assert_true(nearest < 0.000001, "union retains every exact outer ring endpoint")
		assert_int_equal(ring_cells, outer.size(), "complete constant band remains in the fixed union")
