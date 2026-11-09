extends SimTestCase

const CONTACT := 0.002

func test_every_head_is_fed_by_an_exposed_red_drawn_supply_pipe() -> void:
	var layout := ShipLayout.authored().layout
	var bracket := CeilingProps.mesh(&"sprinkler").generate_triangle_mesh()
	for space: ShipLayout.Spec in layout.records():
		if not _built(space): continue
		var spec := layout.ceiling_services(space.id())
		var node := CeilingProps.build(layout, space.id())
		var drawn := node.get_node("SprinklerPipes") as MultiMeshInstance3D
		assert_true(drawn.get_meta(&"role") == &"weathered_red", "supply pipe uses rusted red paint: %s" % space.id())
		assert_true(drawn.material_override == Surfaces.material(&"weathered_red"), "red supply finish comes through Surfaces")
		var run := (drawn.get_meta(&"instance_poses") as Array[Transform3D])[0]
		var size := (run * drawn.multimesh.mesh.get_aabb()).size
		assert_true(absf(size.y - 0.05) <= CONTACT and absf(size.z - 0.05) <= CONTACT, "drawn supply diameter is 50 mm")
		assert_true(spec.bounds.end.y - run.origin.y >= 0.25, "supply clears the wall-top rib heads")
		var into := -1.0 if space is ShipLayout.LiftSpec else 1.0
		var wall := spec.bounds.end.z if into < 0 else spec.bounds.position.z
		assert_true((run.origin.z - wall) * into >= 0.10 - CONTACT, "supply projects into the room, outside wall-top dressing")
		var a := run * Vector3(-0.5, 0, 0)
		var b := run * Vector3(0.5, 0, 0)
		for head: Transform3D in spec.heads:
			var local := head.affine_inverse()
			var hit := bracket.intersect_segment(local * a, local * b)
			assert_false(hit.is_empty(), "drawn supply centreline enters the actual head bracket, not only its AABB: %s" % space.id())
			if hit.is_empty(): continue
			var contact: Vector3 = head * hit.position
			assert_true(contact.distance_to(Geometry3D.get_closest_point_to_segment(contact, a, b)) <= CONTACT, "each head contacts its drawn feed within 2 mm")
		node.free()

func test_supply_is_continuous_to_both_room_corners_and_clipped_to_wall() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not _built(space): continue
		var spec := layout.ceiling_services(space.id())
		var node := CeilingProps.build(layout, space.id())
		var drawn := node.get_node("SprinklerPipes") as MultiMeshInstance3D
		var run := (drawn.get_meta(&"instance_poses") as Array[Transform3D])[0]
		var box := run * drawn.multimesh.mesh.get_aabb()
		var wall_midpoint := ShipLayout.WALL / 2 if spec.spine != null else 0.0
		assert_true(absf(box.position.x - spec.bounds.position.x - wall_midpoint) <= CONTACT, "unbroken supply starts at the wall datum")
		assert_true(absf(box.end.x - spec.bounds.end.x - wall_midpoint) <= CONTACT, "unbroken supply ends at the opposite wall datum")
		assert_true(drawn.multimesh.instance_count >= 1 + spec.heads.size() * 2, "each head hangs from a drawn tee sleeve and drop")
		var clips := node.get_node("PipeClips") as MultiMeshInstance3D
		assert_int_equal(clips.multimesh.instance_count, spec.heads.size(), "clips at each head station, no more than 3 m apart")
		var wall := spec.bounds.end.z if space is ShipLayout.LiftSpec else spec.bounds.position.z
		for index: int in range(clips.multimesh.instance_count):
			var clip := (clips.get_meta(&"instance_poses") as Array[Transform3D])[index] * clips.multimesh.mesh.get_aabb()
			assert_true(minf(absf(clip.position.z - wall), absf(clip.end.z - wall)) <= CONTACT, "drawn clip touches wall within 2 mm")
			assert_true(_gap(clip, box) <= CONTACT, "drawn clip touches supply within 2 mm")
			assert_true(clip.position.y > spec.bounds.position.y + 2.2, "clips stay above walk band")
		for index: int in range(1, drawn.multimesh.instance_count):
			var tee := (drawn.get_meta(&"instance_poses") as Array[Transform3D])[index] * drawn.multimesh.mesh.get_aabb()
			assert_true(_gap(tee, box) <= CONTACT, "every tee joins the continuous supply within 2 mm")
		for pose: Transform3D in spec.pipes + spec.tees + spec.clips:
			for obstacle: AABB in spec.detector_exclusions:
				assert_false((pose * ShipDressing.UNIT).intersects(obstacle), "supply clears doors, labels and other services: %s" % space.id())
		node.free()

func _gap(a: AABB, b: AABB) -> float:
	return (a.position - b.end).max(b.position - a.end).max(Vector3.ZERO).length()

func _built(space: ShipLayout.Spec) -> bool:
	return space is ShipLayout.BaySpec or space is ShipLayout.PowerRoomSpec or space is ShipLayout.LiftSpec or ((space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) and space.is_built())
