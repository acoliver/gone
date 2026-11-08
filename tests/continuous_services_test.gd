extends SimTestCase

const CONTACT := 0.002

func test_all_six_drawn_pipe_and_conduit_runs_reach_bulkhead_centres() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var roots: Array[Node3D] = [CorridorDressing.build(layout, space.id()), CeilingProps.build(layout, space.id())]
		var runs := _all_runs(roots)
		assert_int_equal(runs.size(), 6, "six unbroken service lines: %s" % space.id())
		for run: AABB in runs:
			assert_true(absf(run.position.x - space.bounds().position.x - ShipLayout.WALL / 2) <= CONTACT, "all services reach fore bulkhead centre: %s" % space.id())
			assert_true(absf(run.end.x - space.bounds().end.x - ShipLayout.WALL / 2) <= CONTACT, "all services reach aft bulkhead centre: %s" % space.id())
		for root: Node3D in roots: root.free()

func test_all_service_lines_match_across_every_bulkhead() -> void:
	var layout := ShipLayout.authored().layout
	var joins := 0
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.kind() != ShipLayout.DoorKind.HATCH or not layout.connector(door.owner_id()).is_built(): continue
		var sides: Array = []
		for space_id: StringName in door.spaces():
			var runs: Array[AABB] = []
			var services := layout.ceiling_services(space_id)
			for pose: Transform3D in services.spine.pipes + services.pipes:
				runs.append(pose * ShipDressing.UNIT)
			for pose: Transform3D in services.spine.side_conduits:
				runs.append(pose * ShipDressing.UNIT)
			sides.append(runs)
		assert_int_equal(sides[0].size(), 6, "all six lines on near face")
		assert_int_equal(sides[1].size(), 6, "all six lines on far face")
		if sides[0].size() != 6 or sides[1].size() != 6: return
		for index: int in range(6):
			var a: AABB = sides[0][index]
			var b: AABB = sides[1][index]
			assert_close(Vector3(a.end.x, a.get_center().y, a.get_center().z), Vector3(b.position.x, b.get_center().y, b.get_center().z), "all six lines join: %s/%d" % [id, index])
			assert_true(absf(a.size.y - b.size.y) <= CONTACT and absf(a.size.z - b.size.z) <= CONTACT, "service diameters match")
		joins += 1
	assert_int_equal(joins, 120, "every built bulkhead joins all six services")

func test_penetration_collars_have_visible_shoulders_and_bolt_rings() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var spine := layout.ceiling_services(space.id()).spine
		var fittings: Variant = spine.get("fittings")
		assert_true(fittings != null, "each pipe and duct has a drawn bolted wall fitting")
		if fittings == null: return
		assert_int_equal(fittings.size(), 14, "six pipe collars and one duct frame on each wall")
		for fitting: Dictionary in fittings:
			var box: AABB = fitting.body * ShipDressing.UNIT
			assert_true(box.size.x >= 0.025 - CONTACT and box.size.x <= 0.040 + CONTACT, "25 to 40 mm proud of the wall")
			assert_true(fitting.bolts.size() >= 4, "visible bolt ring on every fitting")
			if fitting.kind == &"pipe":
				assert_true(box.size.y >= fitting.diameter * 1.6 - CONTACT and box.size.y <= fitting.diameter * 1.8 + CONTACT, "pipe collar shoulder is 1.6 to 1.8 times pipe diameter")
			for bolt: Transform3D in fitting.bolts:
				assert_true((bolt * ShipDressing.UNIT).grow(CONTACT).intersects(box), "bolt ring attaches to fitting")
		var node := CeilingProps.build(layout, space.id())
		var drawn: Array[Transform3D] = []
		for family: String in ["OverheadPipes", "SideConduits", "PipeBrackets"]:
			drawn.append_array(node.get_node(family).get_meta(&"instance_poses"))
		for fitting: Dictionary in fittings:
			if fitting.kind == &"pipe": assert_true(fitting.body in drawn, "pipe collar is drawn, not metadata only")
			for bolt: Transform3D in fitting.bolts: assert_true(bolt in drawn, "every bolt is drawn")
		for pose: Transform3D in spine.duct_collars: assert_true(pose in drawn, "duct frame is drawn")
		assert_true(node.get_node("PipeBrackets").get_meta(&"role") == &"collar_steel", "contrasting worn steel wall fittings")
		assert_true(Surfaces.material(&"collar_steel").get_shader_parameter("colour_gain").x < 0.5, "collars contrast with wall steel without changing lights")
		node.free()

func test_added_services_clear_hatch_frames_and_complete_swings_without_lowering_runs() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var spine := layout.ceiling_services(space.id()).spine
		for pose: Transform3D in spine.side_conduits + spine.service_collars + spine.bolts:
			var box := pose * ShipDressing.UNIT
			assert_true(box.position.y >= space.bounds().end.y - 0.658 - CONTACT, "side fittings stay above the former side-conduit bottom")
			for door_id: StringName in layout.door_ids():
				var door := layout.door(door_id)
				if space.id() not in door.spaces() or door.kind() != ShipLayout.DoorKind.HATCH: continue
				for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(door):
					assert_false(box.intersects(solid.transform * AABB(-solid.size / 2, solid.size)), "new fittings clear the hatch frame")
				for degree: int in range(131):
					var hinge := door.hinge_frame()
					hinge.basis = Basis(Vector3.UP, signf(door.swing_radians()) * deg_to_rad(degree))
					assert_false(box.intersects(door.frame() * hinge * ShipGeometry.hatch_leaf_bounds(door)), "new fittings clear the complete hatch swing")

func _all_runs(roots: Array[Node3D]) -> Array[AABB]:
	var runs: Array[AABB] = []
	for family: String in ["OverheadPipes", "SprinklerPipes", "SideConduits"]:
		for box: AABB in _boxes(roots, family):
			if box.size.x > 1: runs.append(box)
	return runs

func test_spine_runs_reach_both_bulkheads_in_every_built_space() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var roots: Array[Node3D] = [CorridorDressing.build(layout, space.id()), CeilingProps.build(layout, space.id())]
		var pipes := _boxes(roots, "OverheadPipes")
		var runs: Array[AABB] = []
		for box: AABB in pipes:
			if box.size.x > 1: runs.append(box)
		assert_int_equal(runs.size(), 3, "three unbroken overhead lines: %s" % space.id())
		var b: AABB = space.bounds()
		for run: AABB in runs:
			assert_true(absf(run.position.x - b.position.x - ShipLayout.WALL / 2) <= CONTACT, "pipe starts at the fore bulkhead centre: %s" % space.id())
			assert_true(absf(run.end.x - b.end.x - ShipLayout.WALL / 2) <= CONTACT, "pipe ends at the aft bulkhead centre: %s" % space.id())
		var ducts := _boxes(roots, "CeilingDucts")
		assert_true(not ducts.is_empty(), "hatch bays carry the same duct: %s" % space.id())
		var last := b.position.x + ShipLayout.WALL / 2
		for duct: AABB in ducts:
			assert_true(absf(duct.position.x - last) <= CONTACT, "duct tiles have no gaps: %s" % space.id())
			assert_true(absf(duct.end.y - b.end.y) <= CONTACT, "duct remains ceiling-mounted")
			last = duct.end.x
		assert_true(absf(last - b.end.x - ShipLayout.WALL / 2) <= CONTACT, "duct ends inside the end wall: %s" % space.id())
		for root: Node3D in roots:
			assert_true(root.find_children("*", "CollisionObject3D", true, false).is_empty(), "services introduce zero prop colliders")
			root.free()

func test_generator_reaches_ceiling_with_unchanged_bands_and_light() -> void:
	var room := PowerRoom.build(Game.new(91))
	var generator: Node3D = room.get_node("Generator")
	var column: MeshInstance3D = generator.get_node("Column")
	var bounds := Surfaces.world_frame(column) * column.mesh.get_aabb()
	assert_float_equal(bounds.position.y, 0, "generator still meets the floor")
	assert_vec3_equal(Vector3(0, bounds.end.y, 0), Vector3(0, PowerRoom.ROOM_CEILING, 0), "generator body reaches the ceiling")
	assert_true(generator.has_node("CeilingCollar"), "generator has a visible ceiling attachment")
	if generator.has_node("CeilingCollar"):
		var collar: MeshInstance3D = generator.get_node("CeilingCollar")
		var mount := Surfaces.world_frame(collar) * collar.mesh.get_aabb()
		assert_vec3_equal(Vector3(0, mount.end.y, 0), Vector3(0, PowerRoom.ROOM_CEILING, 0), "collar meets the ceiling")
		assert_true(mount.intersects(bounds), "collar engages the column")
		assert_true(mount.size.x > bounds.size.x and mount.size.z > bounds.size.z, "mount is visible beyond the column")
	var bands: Array[MeshInstance3D] = []
	for child: Node in generator.get_children():
		if child is MeshInstance3D and child.mesh is TorusMesh: bands.append(child)
	assert_int_equal(bands.size(), 3, "all three glowing bands remain")
	for index: int in range(bands.size()):
		assert_vec3_equal(bands[index].position, Vector3(0, [0.7, 1.5, 2.3][index], 0), "band positions unchanged")
		assert_vec3_equal(Vector3(bands[index].mesh.inner_radius, bands[index].mesh.outer_radius, 0), Vector3(0.66, 0.84, 0), "band inner and outer radii unchanged")
		assert_true(bands[index].material_override == room._generator_ring_material, "bands keep their switched glow")
	assert_vec3_equal(generator.get_node("Glow").position, Vector3(0, 1.9, 0), "body growth must not move the generator light")
	room.free()

func test_extreme_runs_terminate_inside_the_actual_ship_end_walls() -> void:
	var layout := ShipLayout.authored().layout
	var ends := 0
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.kind() != ShipLayout.DoorKind.HATCH or layout.connector(door.owner_id()).is_built(): continue
		for space_id: StringName in door.spaces():
			if space_id not in layout.deck(14).section_ids(): continue
			var section := layout.section(space_id)
			var spine: Variant = layout.ceiling_services(space_id).get("spine")
			assert_true(spine != null, "outer section has terminating spine services")
			if spine == null: return
			var fore := door.frame().origin.x == section.bounds().position.x
			var runs: Array[Transform3D] = spine.pipes + spine.side_conduits + layout.ceiling_services(space_id).pipes
			runs.append(spine.ducts[0] if fore else spine.ducts[-1])
			for pose: Transform3D in runs:
				var box: AABB = pose * ShipDressing.UNIT
				var point := box.get_center()
				point.x = box.position.x if fore else box.end.x
				var inside := false
				for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(door):
					for wall: AABB in SlidingDoorParts.wall_boxes(layout, solid):
						if (solid.transform * wall).has_point(point): inside = true
				assert_true(inside, "extreme run ends inside the actual end-wall lintel: %s" % id)
			ends += 1
	assert_int_equal(ends, 2, "both ends of the authored ship terminate in bulkheads")

func test_side_rooms_and_lifts_do_not_gain_spine_runs() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.BaySpec or space is ShipLayout.PowerRoomSpec or space is ShipLayout.LiftSpec): continue
		assert_true(layout.ceiling_services(space.id()).get("spine") == null, "spine stays out of side rooms and lifts")

func test_each_bulkhead_joins_matching_runs_and_has_two_face_collars() -> void:
	var layout := ShipLayout.authored().layout
	var joins := 0
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.kind() != ShipLayout.DoorKind.HATCH: continue
		var spaces := door.spaces()
		# The two outer D14 hatches terminate the authored ship rather than
		# creating service runs inside their unbuilt connector placeholders.
		if not layout.connector(door.owner_id()).is_built(): continue
		var left: Variant = layout.ceiling_services(spaces[0]).get("spine")
		var right: Variant = layout.ceiling_services(spaces[1]).get("spine")
		assert_true(left != null and right != null, "both bulkhead faces own spine services: %s" % id)
		if left == null or right == null: return
		for index: int in range(3):
			var a: AABB = left.pipes[index] * ShipDressing.UNIT
			var b: AABB = right.pipes[index] * ShipDressing.UNIT
			assert_close(Vector3(a.end.x, a.get_center().y, a.get_center().z), Vector3(b.position.x, b.get_center().y, b.get_center().z), "same pipe passes through both sides: %s" % id)
			assert_true(absf(a.size.y - b.size.y) <= CONTACT and absf(a.size.z - b.size.z) <= CONTACT, "pipe cross-section continues")
			for pair: Array in [[left, index * 2 + 1, door.frame().origin.x], [right, index * 2, door.frame().origin.x + ShipLayout.WALL]]:
				var collar: AABB = pair[0].pipe_collars[pair[1]] * ShipDressing.UNIT
				assert_true(absf((collar.end.x if pair[0] == left else collar.position.x) - pair[2]) <= CONTACT, "collar seats on the bulkhead face")
				assert_true(collar.intersects(a) or collar.intersects(b), "collar engages the pipe")
		var a: AABB = left.ducts[-1] * ShipDressing.UNIT
		var b: AABB = right.ducts[0] * ShipDressing.UNIT
		assert_close(Vector3(a.end.x, a.get_center().y, a.get_center().z), Vector3(b.position.x, b.get_center().y, b.get_center().z), "same duct passes through both sides: %s" % id)
		assert_true(absf(a.size.y - b.size.y) <= CONTACT and absf(a.size.z - b.size.z) <= CONTACT, "duct cross-section continues")
		for pair: Array in [[left, 4, door.frame().origin.x], [right, 0, door.frame().origin.x + ShipLayout.WALL]]:
			for index: int in range(4):
				var collar: AABB = pair[0].duct_collars[pair[1] + index] * ShipDressing.UNIT
				assert_true(absf((collar.end.x if pair[0] == left else collar.position.x) - pair[2]) <= CONTACT, "duct collar seats on the bulkhead face")
				assert_true(collar.grow(CONTACT).intersects(a) or collar.grow(CONTACT).intersects(b), "duct collar engages the continuous run")
		for spine: Variant in [left, right]:
			assert_int_equal(spine.duct_collars.size(), 8, "four-sided duct collar at both walls")
			for pose: Transform3D in spine.duct_collars:
				assert_true(pose.origin.y >= a.position.y, "collar never hangs below the duct")
		joins += 1
	assert_int_equal(joins, 120, "four bulkhead joins on each of thirty decks")

func test_spine_services_clear_hatch_openings_sweeps_and_existing_services() -> void:
	var layout := ShipLayout.authored().layout
	for space: ShipLayout.Spec in layout.records():
		if not (space is ShipLayout.SectionSpec or space is ShipLayout.ConnectorSpec) or not space.is_built(): continue
		var services := layout.ceiling_services(space.id())
		var spine: Variant = services.get("spine")
		assert_true(spine != null, "spine recipe exists")
		if spine == null: return
		for pose: Transform3D in spine.pipes + spine.pipe_collars + spine.brackets + spine.ducts + spine.duct_collars:
			var box: AABB = pose * ShipDressing.UNIT
			assert_true(box.position.y >= space.bounds().end.y - 0.365, "no service hangs below the existing overhead pipes")
			for obstacle: AABB in services.detector_exclusions:
				assert_false(box.intersects(obstacle), "spine clears existing door services: %s" % space.id())
			for sprinkler: Transform3D in services.pipes + services.tees + services.clips + services.heads:
				assert_false(box.intersects(sprinkler * ShipDressing.UNIT), "sprinkler supply remains separate")
			for door_id: StringName in layout.door_ids():
				var door := layout.door(door_id)
				if space.id() not in door.spaces() or door.kind() != ShipLayout.DoorKind.HATCH: continue
				for degree: int in range(131):
					var hinge := door.hinge_frame()
					hinge.basis = Basis(Vector3.UP, signf(door.swing_radians()) * deg_to_rad(degree))
					assert_false(box.intersects(door.frame() * hinge * ShipGeometry.hatch_leaf_bounds(door)), "spine clears the complete hatch swing")
		var previous := -INF
		for index: int in range(spine.brackets.size() / 3):
			var x: float = spine.brackets[index].origin.x
			if index > 0: assert_true(absf(x - previous - 2.0) <= CONTACT, "supports retain two-metre pitch")
			assert_true(absf(fposmod(x, 2.0) - 1.0) <= CONTACT, "same support phase in every space")
			previous = x

func _boxes(roots: Array[Node3D], family: String) -> Array[AABB]:
	var result: Array[AABB] = []
	for root: Node3D in roots:
		if not root.has_node(family): continue
		var piece: MultiMeshInstance3D = root.get_node(family)
		for pose: Transform3D in piece.get_meta(&"instance_poses"):
			result.append(pose * piece.multimesh.mesh.get_aabb())
	return result
