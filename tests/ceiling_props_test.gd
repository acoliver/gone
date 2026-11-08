extends SimTestCase

func test_detector_faces_are_inward_and_visible_from_room_centre() -> void:
	var layout := ShipLayout.authored().layout
	var deck_solids: Dictionary = {}
	for space: ShipLayout.Spec in layout.records():
		if not _built(space): continue
		var spec := layout.ceiling_services(space.id())
		var eye := spec.bounds.get_center()
		# The power room's centre contains the generator; inspect above its crown.
		if space is ShipLayout.PowerRoomSpec: eye.y = spec.bounds.end.y - 0.3
		var to_local := layout.world_to_bay() if space is ShipLayout.BaySpec else Transform3D.IDENTITY
		var deck := space.deck_number()
		if not deck_solids.has(deck):
			var boxes: Array[AABB] = []
			for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(layout, deck):
				for box: AABB in SlidingDoorParts.wall_boxes(layout, solid): boxes.append(solid.transform * box)
			deck_solids[deck] = boxes
		for row: Dictionary in spec.detectors:
			assert_true(row.frame.basis.z.dot(eye - row.frame.origin) > 0, "flame faces room centre: %s" % space.id())
			for offset: Vector2 in [Vector2.ZERO, Vector2(-0.07, -0.07), Vector2(0.07, -0.07), Vector2(-0.07, 0.07), Vector2(0.07, 0.07)]:
				var front: Vector3 = row.frame * Vector3(offset.x, offset.y, CeilingServices.DETECTOR_SIZE.z / 2)
				assert_true(spec.bounds.has_point(front), "detector front is inside %s" % space.id())
				for box: AABB in deck_solids[deck]:
					var obstacle := to_local * box
					assert_true(obstacle.intersects_segment(eye, front) == null, "centre sight to detector clears structure in %s" % space.id())
		for head: Transform3D in spec.heads:
			var front := head * Vector3(0, 0, 0.5)
			assert_true(spec.bounds.has_point(front), "sprinkler projects into room")
			assert_true(head.basis.z.dot(eye - front) > 0, "sprinkler faces room centre")
			for box: AABB in deck_solids[deck]:
				assert_true((to_local * box).intersects_segment(eye, front) == null, "room centre sees sprinkler in %s" % space.id())

func test_fire_service_captures_frame_each_room_detector_and_sprinkler() -> void:
	var capture := FileAccess.get_file_as_string("res://tools/capture_ship_surfaces.gd")
	for name: String in ["bay-detector", "power-detector", "bay-sprinkler", "power-sprinkler", "hall-sprinkler", "duct-flanges"]:
		assert_true(capture.contains('"' + name + '"'), "purpose-framed production capture: %s" % name)

func test_duct_sheet_body_is_planar_with_metric_cross_section() -> void:
	var mesh := CeilingProps.mesh(&"duct")
	var vertices: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var plane_vertices := 0
	for vertex: Vector3 in vertices:
		if is_equal_approx(vertex.y, 0.30 / 0.35 - 0.5) or is_equal_approx(absf(vertex.z), 0.40 / 0.44 / 2): plane_vertices += 1
	assert_true(plane_vertices >= 24, "duct body has flat 0.40 by 0.30 m sheet faces, not generated relief")

func test_every_built_space_has_two_wall_detectors_and_sprinklers() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(layout.has_method(&"ceiling_services"), "layout owns ceiling and fire-safety placements")
	if not layout.has_method(&"ceiling_services"): return
	for space: ShipLayout.Spec in layout.records():
		if not _built(space): continue
		var spec: Variant = layout.call(&"ceiling_services", space.id())
		var detectors: Array = spec.detectors
		assert_int_equal(detectors.size(), 2, "two detectors per built room or section: %s" % space.id())
		assert_true(detectors[0].wall != detectors[1].wall, "different mounting walls")
		for detector: Dictionary in detectors:
			assert_float_equal(detector.frame.origin.y, Vector3(0, spec.bounds.position.y + 2.2, 0).y, "detector height follows room datum")
			for obstacle: AABB in spec.detector_exclusions:
				assert_false(detector.bounds.grow(0.15).intersects(obstacle), "detector keeps 0.15 m from services and doors: %s" % space.id())
		assert_true(spec.heads.size() >= ceili(spec.bounds.size.x / 3.0), "head spacing no greater than 3 m")
		assert_int_equal(spec.pipes.size(), 1, "one continuous wall-top pipe per space")
		for pose: Transform3D in spec.heads + spec.ducts:
			for obstacle: AABB in spec.detector_exclusions:
				assert_false((pose * ShipDressing.UNIT).intersects(obstacle), "overhead props clear doors, ladder mouths and existing wall services: %s" % space.id())
		assert_int_equal(spec.ducts.size(), ceili(spec.bounds.size.x / 0.8) if space is ShipLayout.SectionSpec else 0, "one tiled duct run per hall section")
		var last: float = spec.bounds.position.x
		for duct: Transform3D in spec.ducts:
			var bounds: AABB = duct * ShipDressing.UNIT
			assert_true(absf(bounds.position.x - last) <= 0.002, "duct ends meet")
			assert_true(absf(bounds.end.y - spec.bounds.end.y) <= 0.002, "duct hanger reaches ceiling")
			last = bounds.end.x
		if not spec.ducts.is_empty(): assert_true(absf(last - spec.bounds.end.x) <= 0.002, "run reaches section end wall")

func test_fire_props_have_shared_surface_roles_and_no_colliders() -> void:
	var script: GDScript = load("res://app/ceiling_props.gd") if FileAccess.file_exists("res://app/ceiling_props.gd") else null
	assert_true(script != null, "ceiling prop presenter exists")
	if script == null: return
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_ID, ShipLayout.POWER_ID, &"D14-S-041"]:
		var node: Node3D = script.call(&"build", layout, id)
		assert_true(node.find_children("*", "CollisionObject3D", true, false).is_empty(), "out-of-walk-band props add no collision")
		assert_true(node.find_children("*", "Light3D", true, false).is_empty(), "flame has no light source")
		for piece: MultiMeshInstance3D in node.get_children():
			assert_true(piece.has_meta(&"surface_frame"), "every finish comes through Surfaces")
			assert_true(piece.material_override == Surfaces.material(piece.get_meta(&"role")), "finite shared surface role")
		node.free()

func test_imported_generated_meshes_stay_in_instance_budgets() -> void:
	var script: GDScript = load("res://app/ceiling_props.gd") if FileAccess.file_exists("res://app/ceiling_props.gd") else null
	assert_true(script != null, "generated mesh provider exists")
	if script == null: return
	for shape: String in ["detector", "sprinkler", "duct", "module"]:
		var mesh: Mesh = script.call(&"mesh", StringName(shape))
		var triangles := mesh.get_faces().size() / 3
		assert_true(triangles > 0 and triangles <= {"detector": 3000, "sprinkler": 3000, "duct": 2000, "module": 1500}[shape], "instance budget: %s = %d" % [shape, triangles])
		assert_int_equal(mesh.get_surface_count(), 1, "one draw per repeated mesh family")

func test_light_cassettes_follow_every_existing_strip_and_use_glass_role() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_ID, ShipLayout.POWER_ID, &"D14-S-041"]:
		var spec := layout.ceiling_services(id)
		assert_int_equal(spec.modules.size(), 8 if id == &"D14-S-041" else 12, "two cassettes per existing regular strip")
		for pose: Transform3D in spec.modules:
			assert_vec3_equal(pose.basis.get_scale(), CeilingServices.MODULE_SIZE, "metric cassette size remains layout-owned")
	var glass := Surfaces.light_glass_material()
	assert_true(glass.get_meta(&"surface_role") == &"light_glass", "one surface factory supplies light glass")
	for role: StringName in [&"weathered_red", &"corroded_brass"]:
		var finish := Surfaces.material(role)
		assert_false(finish.shader.code.contains("EMISSION"), "fire-safety finishes have no emission")

func test_tipped_hall_tray_stub_is_removed() -> void:
	assert_int_equal(ShipLayout.authored().layout.section(&"D14-S-041").ceiling_trays().size(), 1, "keep attached long tray only")

func test_each_service_mount_touches_structure_and_stays_above_walk_band() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(layout.has_method(&"ceiling_services"), "service mount recipe exists")
	if not layout.has_method(&"ceiling_services"): return
	var attachment: SimTestCase = load("res://tests/dressing_attachment_test.gd").new()
	for space: ShipLayout.Spec in layout.records():
		if not _built(space): continue
		var spec: Variant = layout.call(&"ceiling_services", space.id())
		var structure: Array[AABB] = []
		var b: AABB = spec.bounds
		var to_local := layout.world_to_bay() if space is ShipLayout.BaySpec else Transform3D.IDENTITY
		for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(layout, space.deck_number()):
			if solid.material_role == &"door": continue
			for box: AABB in SlidingDoorParts.wall_boxes(layout, solid): structure.append(to_local * solid.transform * box)
		var pieces: Dictionary = {}
		for index: int in range(spec.detectors.size()): pieces["detector/%d" % index] = spec.detectors[index].bounds
		var poses: Array[Transform3D] = spec.heads + spec.pipes + spec.clips + spec.ducts
		for index: int in range(poses.size()):
			var box: AABB = poses[index] * ShipDressing.UNIT
			assert_true(box.position.y > b.position.y + 2.2, "overhead services stay outside walking envelope")
			pieces["overhead/%d" % index] = box
		attachment.begin_test()
		attachment.call(&"_check_graph", structure, pieces)
		assert_true(attachment.failure == "", "%s: %s" % [space.id(), attachment.failure])

func _built(space: ShipLayout.Spec) -> bool:
	return space is ShipLayout.BaySpec or space is ShipLayout.PowerRoomSpec or space is ShipLayout.LiftSpec or ((space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) and space.is_built())
