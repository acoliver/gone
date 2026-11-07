extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func _check_corners(points: PackedVector3Array, outline: PackedVector2Array, center: Vector2, context: String) -> void:
	for point: Vector3 in points:
		var xy := Vector2(point.x, point.y) - center
		# Straight sealing laps remain at the jambs. The four curved corners
		# must stay behind the existing slab contour, not its square AABB.
		for edge: int in range(outline.size()):
			var a := outline[edge]
			var b := outline[(edge + 1) % outline.size()]
			var delta := b - a
			if absf(delta.x) < 1e-6 or absf(delta.y) < 1e-6: continue
			var distance := delta.cross(xy - a) / delta.length()
			assert_true(distance >= -1e-6, "rounded backplate corner %s point=%s outside=%.6f" % [context, xy, -distance])

func test_leaf_backing_and_returns_follow_the_existing_slab_corners() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var door := layout.door(id)
		var groups := HatchParts.leaf(door)
		var plate := groups[0].parts[0]
		var center := Vector2(plate.transform.origin.x + HatchParts.HINGE_OUTSET, plate.transform.origin.y)
		for group: HatchParts.Group in groups:
			if not group.steel: continue
			for part: HatchParts.Part in group.parts:
				var points := PackedVector3Array()
				var contour := part.contour
				if contour.is_empty():
					contour = HatchParts.outline(Vector2(part.size.x, part.size.y), part.radius) if part.shape == &"rounded" else PackedVector2Array([-Vector2(part.size.x, part.size.y) / 2, Vector2(part.size.x, -part.size.y) / 2, Vector2(part.size.x, part.size.y) / 2, Vector2(-part.size.x, part.size.y) / 2])
				for point: Vector2 in contour: points.append(group.transform * part.transform * Vector3(point.x, point.y, 0))
				_check_corners(points, plate.contour, center, "%s/%s" % [id, part.id])

func test_delivered_leaf_backing_and_returns_follow_the_existing_slab_corners() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var door := layout.door(id)
		var plate := HatchParts.leaf(door)[0].parts[0]
		var center := Vector2(plate.transform.origin.x + HatchParts.HINGE_OUTSET, plate.transform.origin.y)
		var view := DoorView.build(door)
		for side: String in ["ForeSteel", "AftSteel"]:
			var piece: MeshInstance3D = view.label_leaf().get_node(side)
			var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(piece.mesh)
			for part_id: StringName in parts:
				var name := String(part_id)
				if not (name.begins_with("BackingLap") or "SealSteel/" in name or name in ["ForeSteel/plate", "AftSteel/plate"]): continue
				var points := PackedVector3Array()
				preload("res://tests/hatch_mesh_ranges.gd").faces(piece, name, points, &"part_ranges", (door.frame() * door.hinge_frame()).affine_inverse())
				_check_corners(points, plate.contour, center, "%s/%s" % [id, part_id])
		view.free()

func test_fixed_rear_lip_follows_the_round_leaf_with_its_existing_sealing_lap() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var source := layout.door(id)
		var door := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
		var inner := ShipGeometry.hatch_ring_outline(door, -HatchParts.SEAL_LAP)
		var opening := ShipGeometry.hatch_ring_outline(door)
		var walk_edge := ShipGeometry.SILL_WALK_WIDTH / 2 + 0.005
		var lower_radius := (door.aperture().x + 0.01) / 2 - walk_edge
		for index: int in range(inner.size() / 2, inner.size()):
			var fraction := clampf((absf(opening[index].x) - walk_edge) / lower_radius, 0, 1)
			inner[index] = Vector2(opening[index].x - signf(opening[index].x) * HatchParts.SEAL_LAP * fraction, opening[index].y)
		var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		var index := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door):
			if not "/LIP/" in String(solid.id): continue
			var point := solid.transform * Vector3(solid.section[0].x, solid.section[0].y, 0)
			assert_true(Vector2(point.x, point.y - center_y).distance_to(inner[index]) <= 1e-6, "fixed aft sealing lip follows the rounded leaf corner with a 20 mm lap: " + solid.id)
			index += 1
		assert_int_equal(index, inner.size(), "all four rounded corners have fixed sealing support")
