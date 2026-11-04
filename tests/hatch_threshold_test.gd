extends SimTestCase

func test_floor_bridge_does_not_extend_the_raised_sill_contact_plane() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var bridges := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(door):
			if not "/STEP/" in String(solid.id): continue
			var rear := ShipGeometry.hatch_frame_vertex(door, solid, solid.size / 2)
			assert_true(absf(solid._local_center.z + rear.z - 0.27) < 0.000001, "raised sill retains the compiled route's contact plane")
			bridges += 1
			var bounds: ColliderSet.Aabb = ShipGeometry.collision_boxes(solid)[0]
			assert_true(absf(bounds.max_corner().y - door.frame().origin.y - 0.001) < 0.000001, "floor bridge has its 1 mm joining lap")
			assert_true(bounds.max_corner().y < door.frame().origin.y + Controller.PENETRATION_TOLERANCE, "extended bridge remains below standing capsule clearance")
		assert_int_equal(bridges, 1, "floor continues beneath the setback leaf")

func test_imported_threshold_top_covers_the_full_floor_bridge() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var view := DoorView.build(door)
		var points := PackedVector3Array()
		for side: String in ["ForeSteel", "AftSteel"]:
			var piece: MeshInstance3D = view.get_node("Frame/" + side)
			var arrays := piece.mesh.surface_get_arrays(0)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for index: int in arrays[Mesh.ARRAY_INDEX]: points.append(vertices[index])
		var mesh := TriangleMesh.new()
		assert_true(mesh.create_from_faces(points), "actual threshold triangles")
		var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var far := door.hinge_frame().origin.z + into * ShipLayout.WALL / 2
		for column: int in range(21):
			for depth: int in range(21):
				var x := lerpf(-0.49, 0.49, column / 20.0)
				var z := lerpf(-0.09 if into > 0 else ShipLayout.WALL + 0.09, far, depth / 20.0)
				var hit := mesh.intersect_segment(Vector3(x, 0.12, z), Vector3(x, -0.02, z))
				assert_true(not hit.is_empty(), "coaming top covers the floor below the leaf: %s x=%.3f z=%.3f" % [id, x, z])
				if not hit.is_empty(): assert_true(hit.position.y <= ShipGeometry.SILL_HEIGHT + 0.000001 and hit.position.y >= 0, "no raised walk height or below-floor void: %s x=%.6f z=%.6f hit=%s" % [id, x, z, hit.position])
		view.free()

func test_lower_band_has_no_corner_blocks_and_the_coaming_closes_to_the_floor() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var steps := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_surround_solids(door):
			assert_false("/PIER/" in String(solid.id), "the continuous lower ring needs no rectangular corner overlays")
			if not "/STEP/" in String(solid.id): continue
			steps += 1
			assert_true(solid._local_center.z - solid.size.z / 2 >= -0.098 - 0.000001, "coaming does not project beyond the front reveal")
			assert_true(absf(solid._local_center.y - solid.size.y / 2) < 0.000001, "steel reaches the floor without an underside gap")
			assert_true(absf(solid._local_center.y + solid.size.y / 2 - ShipGeometry.SILL_HEIGHT) < 0.000001, "coaming preserves the authored walk height")
		assert_true(steps > 0, "the low steel coaming remains physical")
