extends SimTestCase

func test_every_deck_uses_positive_single_frame_boxes() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door):
			var boxes := ShipGeometry.collision_boxes(solid)
			assert_int_equal(boxes.size(), 1, "one positive inscribed box on remote decks: " + String(solid.id))

func test_frame_collision_has_one_inscribed_box_per_reservation() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var count := 0
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(layout.door(id)):
			var boxes := ShipGeometry.collision_boxes(solid)
			assert_int_equal(boxes.size(), 1, "fixed frame reservation needs one conservative box: " + String(solid.id))
			count += boxes.size()
		assert_true(count <= 120, "fixed frame collider count stays near the unsubdivided model")
	var count := ShipCollision.opening_set(layout.bay().template(), false, false, layout).size()
	print("HATCH_SCENE_COLLIDERS ", count)
	assert_true(count <= 1100, "opening scene returns near the 1013-collider budget")

func test_subdivision_preserves_unchanged_depth_planes_bit_exactly() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(layout.door(id)):
			var expected := ShipGeometry.box_aabb(solid)
			var direction := solid._parent.basis * Basis(solid._local_rotation).z
			var axis := direction.abs().max_axis_index()
			for box: ColliderSet.Aabb in ShipGeometry.collision_boxes(solid):
				assert_true(box.min_corner()[axis] == expected.min_corner()[axis] and box.max_corner()[axis] == expected.max_corner()[axis], "subdivision cannot move an unchanged depth plane by even one ULP: " + String(solid.id))

func test_assembled_deck_frame_colliders_respect_the_ring_outline() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var boxes := collision.deck_set(14).boxes()
	var ids := collision.solid_ids(14)
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var fixed: Dictionary = {}
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door): fixed[solid.id] = true
		var outer := ShipGeometry.hatch_ring_outline(door, ShipGeometry.HATCH_RING_WIDTH)
		var inverse := door.frame().affine_inverse()
		var center_y := (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		var maximum := 0.0
		var checked := 0
		for index: int in range(ids.size()):
			if not fixed.has(StringName(String(ids[index]).get_slice("/CELL/", 0))): continue
			checked += 1
			var box: ColliderSet.Aabb = boxes[index]
			for x: float in [box.min_corner().x, box.max_corner().x]:
				for y: float in [box.min_corner().y, box.max_corner().y]:
					for z: float in [box.min_corner().z, box.max_corner().z]:
						var local := inverse * Vector3(x, y, z)
						var point := Vector2(local.x, local.y - center_y)
						if Geometry2D.is_point_in_polygon(point, outer): continue
						var distance := INF
						for edge: int in range(outer.size()):
							distance = minf(distance, point.distance_to(Geometry2D.get_closest_point_to_segment(point, outer[edge], outer[(edge + 1) % outer.size()])))
						maximum = maxf(maximum, distance)
						assert_true(distance <= 0.002, "assembled clipped frame cannot widen its ring: %s point=%s outside_m=%.6f" % [ids[index], point, distance])
		assert_true(checked >= fixed.size(), "all physical frame reservations reach assembled collision")
		print("COLLISION_OUTLINE %s checked=%d maximum_m=%.6f" % [id, checked, maximum])
