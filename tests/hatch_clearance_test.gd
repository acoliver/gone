extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func _meshes(node: Node, boxes: Array[AABB]) -> void:
	if node is MeshInstance3D and node.mesh != null:
		if node.mesh.has_meta(&"part_ranges"):
			for part: Dictionary in preload("res://tests/hatch_mesh_ranges.gd").parts(node.mesh).values():
				boxes.append(ShipScene._world_frame(node) * part.pose * part.bounds)
		else:
			boxes.append(ShipScene._world_frame(node) * node.mesh.get_aabb())
	if node is MultiMeshInstance3D:
		for pose: Transform3D in node.multimesh.get_meta(&"instance_poses"):
			boxes.append(ShipScene._world_frame(node) * pose * node.multimesh.mesh.get_aabb())
	for child: Node in node.get_children():
		_meshes(child, boxes)

func test_every_leaf_mesh_clears_solids_at_every_degree_of_swing() -> void:
	var layout := ShipLayout.authored().layout
	var solids: Array[ShipGeometry.SolidSpec] = []
	for solid: ShipGeometry.SolidSpec in ShipGeometry.deck_static_solids(layout, 14):
		# Round 11 details use the oriented reservation test below; structural
		# walls and frames retain their original conservative AABB gate.
		if solid.collision_role != &"frame_detail": solids.append(solid)
	var solid_boxes: Array[AABB] = []
	for solid: ShipGeometry.SolidSpec in solids:
		var bounds := ShipGeometry.box_aabb(solid)
		solid_boxes.append(AABB(bounds.min_corner(), bounds.max_corner() - bounds.min_corner()))
	for id: StringName in IDS:
		var spec := layout.door(id)
		assert_int_equal(spec.animation(), ShipLayout.AnimationRecipe.HINGE, "opening hatch uses the shared hinge: " + id)
		if spec.animation() != ShipLayout.AnimationRecipe.HINGE:
			continue
		var view := DoorView.build(spec)
		var hinge: Node3D = view.get_node("Hinge")
		var degrees: Array[float] = []
		for degree: int in range(131):
			degrees.append(float(degree))
		for seed: int in [0, 7, -913]:
			degrees.append(absf(rad_to_deg(spec.swing_radians(seed))))
		for degree: float in degrees:
			hinge.basis = Basis(Vector3.UP, signf(spec.swing_radians()) * deg_to_rad(degree))
			var boxes: Array[AABB] = []
			_meshes(view.label_leaf(), boxes)
			assert_true(boxes.size() > 50, "steel, wheel, hub, latches, straps and individual rivets are sampled")
			for box: AABB in boxes:
				for index: int in range(solids.size()):
					var overlap := box.intersection(solid_boxes[index])
					if overlap.size.x > 0.001 and overlap.size.y > 0.001 and overlap.size.z > 0.001:
						assert_true(false, "%s degree %.3f intersects %s by %s" % [id, degree, solids[index].id, overlap.size])
						view.free()
						return
		view.free()

func test_swept_hardware_is_reserved_and_every_open_leaf_blocks_walkers() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var sweep := ShipGeometry.box_aabb(ShipGeometry.door_blockers(spec)[1])
		var reserved := AABB(sweep.min_corner(), sweep.max_corner() - sweep.min_corner()).grow(0.001)
		var view := DoorView.build(spec)
		for degree: int in range(131):
			view.get_node("Hinge").basis = Basis(Vector3.UP, signf(spec.swing_radians()) * deg_to_rad(degree))
			var boxes: Array[AABB] = []
			_meshes(view.label_leaf(), boxes)
			for box: AABB in boxes:
				assert_true(reserved.encloses(box), "%s reserves hardware sweep at degree %d" % [id, degree])
		for seed: int in [0, 7, -913]:
			var store := Doors.Store.new(layout, seed)
			var context := Doors.Context.new()
			context.face_id = spec.face_ids()[0]
			if id == ShipLayout.BAY_DOOR_ID:
				assert_int_equal(store.press(id, context).outcome, Doors.Outcome.NOT_APPLICABLE, "bay still needs the rod")
				context.rod_carried = true
				store.press(id, context)
			else:
				for attempt: int in range(HatchResistance.schedule(seed, id).weights.size()):
					store.press(id, context)
					for tick: int in range(6): store.tick()
			for tick: int in range(48): store.tick()
			var snapshot := store.snapshot(id)
			assert_int_equal(snapshot.state, Doors.State.OPEN, "shared model completes opening")
			view.present(snapshot)
			var collision := ShipCollision.new(layout, seed)
			collision.open_door(id)
			var ids := collision.solid_ids(14)
			var parked_index := ids.find(StringName("%s/PARKED" % id))
			assert_true(parked_index >= 0, "production collision keeps the open leaf")
			var parked := collision.deck_set(14).boxes()[parked_index]
			var boxes: Array[AABB] = []
			_meshes(view.label_leaf(), boxes)
			for box: AABB in boxes:
				assert_true(AABB(parked.min_corner(), parked.max_corner() - parked.min_corner()).grow(0.001).encloses(box), "parked collider contains every leaf mesh")
			var set := ColliderSet.new()
			set.insert(parked)
			var center := parked.center()
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(parked.min_corner().x - 0.5, 0.385, center.z)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var delta := Vector3(parked.max_corner().x - capsule.foot.x + 0.5, 0, 0)
			var result := Resolve.resolve_motion(capsule, delta, set)
			assert_true(result.is_ok(), "open leaf sweep resolves")
			assert_true(result.motion.displacement.length() < delta.length(), "player cannot walk through %s seed %d" % [id, seed])
		view.free()

func test_seeded_rest_angles_are_distinct_repeatable_and_in_range() -> void:
	var layout := ShipLayout.authored().layout
	for seed: int in [0, 7, 71, -913, 2147483647]:
		var store := Doors.Store.new(layout, seed)
		var repeat := Doors.Store.new(layout, seed)
		var angles: Array[float] = []
		for id: StringName in IDS:
			var angle: Variant = store.snapshot(id).get("open_radians")
			assert_true(angle is float, "snapshot carries seeded rest angle")
			if not angle is float:
				return
			assert_float_in_range(absf(rad_to_deg(angle)), 100.0, 130.0, "not flush against wall")
			assert_float_equal(angle, repeat.snapshot(id).get("open_radians"), "same run reconstructs same rest angle")
			assert_false(absf(angle) in angles, "door ids produce different rest angles")
			angles.append(absf(angle))

func test_console_has_heading_and_inactive_text_before_one_activation_press() -> void:
	var game := Game.new(0)
	var room := PowerRoom.build(game)
	assert_int_equal(game.console_state, Game.ConsoleState.INACTIVE, "arrival is inactive")
	assert_true(room.native_state_text() == "palo" and room.perceived_state_text() == "INACTIVO", "arrival has both text layers")
	assert_true(room.console_display.native_canvas.heading == "te mu nawa lina", "arrival has heading")
	assert_true(game.press_console() and game.power_active, "one press activates")
	room.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(room.native_state_text() == "shenu" and room.perceived_state_text() == "EN FUNCIONAMIENTO", "press changes both text layers")
	assert_false(game.press_console(), "active console consumes no further press")
	room.free()
