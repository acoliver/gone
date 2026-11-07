extends SimTestCase

const QUERY := preload("res://tests/hatch_render_faces.gd")

func test_power_door_receives_the_same_hall_finish_and_fill_as_side_doors() -> void:
	var game := Game.new(91)
	var room := PowerRoom.build(game)
	var hall := Hallway.build(game)
	var side: MeshInstance3D = hall.side_leaves[&"D14-S-041-SIDE-015-PORT"]
	assert_true(room._door_leaf.material_override == side.material_override, "one shared rusted leaf finish")
	assert_true(room._door_leaf.mesh == side.mesh, "same leaf, border, pull and rivets")
	assert_true((room._door_leaf.layers & Lighting.HALL_FILL_MASK) == (side.layers & Lighting.HALL_FILL_MASK), "hall-facing power steel must receive hallway fill, not only room fill")
	var bound: Array[GeometryInstance3D] = []
	DoorView._collect_bound(room, bound)
	var portal_parts := 0
	for piece: GeometryInstance3D in bound:
		if String(piece.get_meta(&"surface_frame").key).begins_with(String(ShipLayout.POWER_DOOR_ID) + "/"):
			portal_parts += 1
			assert_true(piece.material_override == side.material_override, "power trim, track and leaf share the side-door finish")
			assert_int_equal(piece.layers, 1 | Lighting.HALL_FILL_MASK | Lighting.POWER_FILL_MASK, "power trim and track receive both adjacent fills")
	assert_int_equal(portal_parts, 9, "leaf, six trim pieces, threshold and track")
	room.free()
	hall.free()

func test_every_sliding_label_has_a_layout_location_and_power_room_name() -> void:
	var layout := ShipLayout.authored().layout
	var catalog: GDScript = load("res://app/ship_text.gd")
	assert_true(catalog.has_method("sliding_label"), "catalog needs full sliding-door location labels")
	assert_true(layout.has_method("door_bay_number"), "layout owns station-derived bay numbering")
	if not catalog.has_method("sliding_label") or not layout.has_method("door_bay_number"): return
	var seen := {}
	for id: StringName in _ids(layout):
		var spec := layout.door(id)
		var section := layout.face(spec.face_ids()[0]).destination_section()
		var bay: int = layout.call("door_bay_number", id)
		var key := Vector2i(section, bay)
		assert_false(seen.has(key), "each sliding door has a unique bay within its section")
		seen[key] = true
		var text: ShipText.LabelText = catalog.call("sliding_label", layout, spec)
		assert_true(text.native.begins_with("lometa [16]\nshelani paki [%s]\npama [%s]" % [Naleya.octal(section), Naleya.octal(bay)]), "native location uses existing terms and octal identifiers")
		assert_true(text.perceived_es.begins_with("NIVEL 14\nSECCIÓN %d\nCOMPARTIMENTO %d" % [section, bay]), "all three location quantities")
		if id == ShipLayout.POWER_DOOR_ID:
			assert_true(text.native.ends_with("\nte mu nawa lina"), "existing secondary-power name")
			assert_true(text.perceived_es.ends_with("\nENERGÍA SECUNDARIA"), "short room name")
		var canvas := ShipTextCanvas.new()
		canvas.set_lines(text.native, &"door")
		for quad: PackedVector2Array in canvas.stroke_quads:
			for pixel: Vector2 in quad:
				assert_float_in_range(pixel.x, 0, canvas.texture_size.x, "readable label width")
				assert_float_in_range(pixel.y, 0, canvas.texture_size.y, "all label lines fit")
		canvas.free()
	assert_int_equal(layout.call("door_bay_number", ShipLayout.POWER_DOOR_ID), 7, "fourth port station retains bay seven")
	assert_int_equal(layout.call("door_bay_number", &"D14-S-041-SIDE-015-PORT"), 5, "third port station is bay five")

func _ids(layout: ShipLayout) -> Array[StringName]:
	var ids: Array[StringName] = [ShipLayout.POWER_DOOR_ID]
	for number: int in [40, 41, 42]: ids.append_array(layout.section(ShipLayout.section_id(14, number)).side_door_ids())
	return ids

func _recipe() -> GDScript:
	var path := "res://sim/sliding_door_parts.gd"
	if not ResourceLoader.exists(path):
		assert_true(false, "ordinary doors need one sim-owned pocket recipe")
		return null
	return load(path)

func test_slide_direction_is_per_door_layout_data() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in _ids(layout):
		var door := layout.door(id)
		assert_true(door.has_method("slide_sign"), "Round 12: each ordinary door owns its slide sign")
		if not door.has_method("slide_sign"): return
		var direction: int = door.call("slide_sign")
		assert_true(direction in [-1, 1], "one signed local slide axis")
		assert_int_equal(door.data().slide_sign, direction, "direction is serialized layout data")
	var side := layout.door(&"D14-S-041-SIDE-015-PORT")
	assert_true((side.frame().basis * Vector3.RIGHT * int(side.call("slide_sign"))).x < 0, "Round 12: SIDE-015-PORT slides world -X, away from the power-room wall")

func test_drawn_pocket_preserves_exactly_the_existing_wall_colliders() -> void:
	var recipe := _recipe()
	if recipe == null: return
	var layout := ShipLayout.authored().layout
	var total := 0
	for solid: ShipGeometry.SolidSpec in ShipCollision.opening_solids(layout.bay().template(), false, false, layout):
		total += ShipGeometry.collision_boxes(solid).size()
	# #88 adds eleven pod solids; the drawn pockets add no collision.
	assert_int_equal(total, 1024, "drawn cavity only: original solid wall collision stays intact")
	for id: StringName in _ids(layout):
		assert_true(recipe.has_pocket(layout.door(id)) == (id == ShipLayout.POWER_DOOR_ID), "only the opening power door has a pocket")

func test_regular_leaves_are_inside_the_wall_not_proud_mounted() -> void:
	var layout := ShipLayout.authored().layout
	var ids := _ids(layout)
	assert_int_equal(ids.size(), 18, "one power door and seventeen refusing side doors")
	for id: StringName in ids:
		var spec := layout.door(id)
		var solid := ShipGeometry.power_door_leaf() if id == ShipLayout.POWER_DOOR_ID else ShipGeometry.side_door_leaf(spec)
		var bounds := spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
		assert_true(bounds.position.z >= 0 and bounds.end.z <= ShipLayout.WALL, "closed steel lies in the wall: " + String(id))
		assert_float_in_range(bounds.size.z, 0.05, 0.055, "about 50 mm including the shallow raised border")

func test_the_full_slide_ends_inside_a_wall_pocket_with_a_near_jamb_leading_edge() -> void:
	var layout := ShipLayout.authored().layout
	var spec := layout.door(ShipLayout.POWER_DOOR_ID)
	var leaf := ShipGeometry.power_door_leaf()
	var bounds := spec.frame().affine_inverse() * leaf.transform * AABB(-leaf.size / 2, leaf.size)
	bounds.position += spec.frame().basis.inverse() * Vector3(-Doors.POWER_SLIDE, 0, 0)
	assert_true(bounds.position.z >= 0 and bounds.end.z <= ShipLayout.WALL, "open leaf stays between both wall faces")
	assert_float_in_range(bounds.position.x - spec.aperture().x / 2, 0, 0.06, "only the leading edge remains near the jamb")
	var recipe := _recipe()
	if recipe == null: return
	var pocket: AABB = recipe.pocket(spec)
	assert_true(pocket.encloses(bounds), "full open leaf, including its raised border, fits the pocket")

func test_frame_track_label_and_pull_are_light_and_separate() -> void:
	var recipe := _recipe()
	if recipe == null: return
	assert_float_equal(recipe.FRAME_BAND, 0.05, "50 mm visible trim")
	assert_true(recipe.FRAME_PROUD <= 0.015, "trim stays within 15 mm of the wall")
	var layout := ShipLayout.authored().layout
	for id: StringName in _ids(layout):
		var spec := layout.door(id)
		var parts: Array = recipe.leaf_parts(spec)
		var pulls := 0
		var rivets := 0
		for part: HatchParts.Part in parts:
			assert_false("wheel" in String(part.id) or "hinge" in String(part.id) or "dog" in String(part.id) or "hazard" in String(part.id), "ordinary steel has no isolation hardware")
			if "rivet" in String(part.id): rivets += 1
			if "pull" in String(part.id): pulls += 1
		assert_true(rivets > 0 and pulls > 0, "riveted panel and recessed pull exist")
		var pull: Rect2 = recipe.pull_rect(spec)
		var label: Rect2 = recipe.label_rect()
		assert_true(label.position.y - pull.end.y >= 0.03, "level-gaze glyph plate clears pull by at least 30 mm")
		assert_true(label.position.x > -0.34 and label.end.x < 0.55 and label.end.y < spec.aperture().y - 0.11, "all lines stay inside the raised border")
		for side: int in range(2):
			var leaf_pose: Transform3D = recipe.leaf_solid(spec).transform
			var frame: Transform3D = leaf_pose * recipe.label_frame(spec, side)
			var eye: Vector3 = spec.frame() * Vector3(0, 1.605, -1.25 if side == 0 else ShipLayout.WALL + 1.25)
			assert_true(DisplayPerception.attends(eye, -frame.basis.z, frame.origin, frame.basis.x * recipe.LABEL_SIZE.x / 2, frame.basis.y * recipe.LABEL_SIZE.y / 2, frame.basis.z), "standing level gaze reaches the complete label on either face")
		for solid: ShipGeometry.SolidSpec in recipe.fixed_solids(spec):
			assert_true(ShipGeometry.collision_boxes(solid).is_empty(), "trim/flush track do not add colliders")
			var bounds := spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
			if "/TRACK" in String(solid.id): assert_true(bounds.end.y <= 0.000001, "track is flush with floor, never a coaming")

func test_pockets_intersect_no_other_object() -> void:
	var recipe := _recipe()
	if recipe == null: return
	var layout := ShipLayout.authored().layout
	var solids := ShipCollision.opening_solids(layout.bay().template(), false, false, layout)
	for id: StringName in [ShipLayout.POWER_DOOR_ID]:
		var spec := layout.door(id)
		var pocket: AABB = spec.frame() * recipe.cavity(spec)
		print("SLIDING_POCKET id=%s world=%s" % [id, pocket])
		for solid: ShipGeometry.SolidSpec in solids:
			if solid.surface_owner == id or recipe.is_host_wall(spec, solid): continue
			var other := solid.transform * AABB(-solid.size / 2, solid.size)
			var overlap := pocket.intersection(other)
			if overlap.has_volume():
				print("SLIDING_POCKET_STOP id=%s object=%s pocket=%s object_bounds=%s overlap=%s" % [id, solid.id, pocket, other, overlap])
				assert_true(false, "stop: pocket intersects another object; do not move it")
				return

func test_power_pocket_clears_services_and_corridor_dressing() -> void:
	var layout := ShipLayout.authored().layout
	var spec := layout.door(ShipLayout.POWER_DOOR_ID)
	var pocket := spec.frame() * SlidingDoorParts.cavity(spec)
	for space: ShipLayout.SectionSpec in [layout.section(&"D14-S-041")]:
		for service: ShipLayout.ServiceReservation in space.service_reservations():
			assert_false(pocket.intersection(service.bounds).has_volume(), "pocket clears service: " + String(service.id))
		for batch: ShipLayout.DressingBatch in layout.dressing(space.id()).batches:
			for pose: Transform3D in batch.poses:
				assert_false(pocket.intersection(pose * ShipDressing.UNIT).has_volume(), "pocket clears dressing: " + String(batch.family))


func test_power_timing_and_the_seventeen_refusals_do_not_change() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 91)
	var context := Doors.Context.new()
	var spec := layout.door(ShipLayout.POWER_DOOR_ID)
	context.face_id = spec.face_ids()[0]
	store.press(spec.id(), context)
	for tick: int in range(47): store.tick()
	assert_int_equal(store.snapshot(spec.id()).state, Doors.State.OPENING, "passage remains shut until tick 48")
	store.tick()
	assert_int_equal(store.snapshot(spec.id()).state, Doors.State.OPEN, "one ungated press opens after 48 ticks")
	assert_vec3_equal(store.snapshot(spec.id()).offset, Vector3(-1.15, 0, 0), "unchanged stroke and direction")
	for id: StringName in _ids(layout):
		if id == spec.id(): continue
		context.face_id = layout.door(id).face_ids()[0]
		store.press(id, context)
		store.tick()
		assert_int_equal(store.snapshot(id).state, Doors.State.CLOSED, "side leaf never opens: " + String(id))

func test_regular_mouths_preserve_the_neighbouring_rounded_hatch_wall() -> void:
	var layout := ShipLayout.authored().layout
	var count := 0
	for solid: ShipGeometry.SolidSpec in ShipGeometry.hallway_solids(layout):
		if solid.hatch_profile == null: continue
		var original := TriangleMesh.new()
		var drawn := TriangleMesh.new()
		assert_true(original.create_from_faces(HatchModel.solid_mesh(solid).get_faces()), "existing rounded wall has triangles")
		assert_true(drawn.create_from_faces(SlidingDoorModel.wall_mesh(layout, solid).get_faces()), "regular-door cuts retain wall triangles")
		var relative := solid.transform.affine_inverse() * solid.hatch_profile.frame()
		for side: int in [-1, 1]:
			for x_index: int in range(52):
				for y_index: int in range(73):
					var point := Vector3(lerpf(-1.31, 1.31, x_index / 51.0), lerpf(0.003, 3.10, y_index / 72.0), 0)
					var start := relative * (point + Vector3(0, 0, side * 2.0))
					var end := relative * (point - Vector3(0, 0, side * 2.0))
					assert_true(original.intersect_segment(start, end).is_empty() == drawn.intersect_segment(start, end).is_empty(), "regular mouths never square or fill the hatch opening")
		count += 1
	assert_int_equal(count, 3, "all three rounded bay-wall pieces preserve their original silhouette")

func test_real_wall_and_leaf_meshes_seal_pocket_and_closed_mouth_from_both_sides() -> void:
	var recipe := _recipe()
	if recipe == null: return
	var model_path := "res://app/sliding_door_model.gd"
	if not ResourceLoader.exists(model_path):
		assert_true(false, "production factory must read the pocket recipe")
		return
	var model: GDScript = load(model_path)
	var layout := ShipLayout.authored().layout
	var solids := ShipCollision.opening_solids(layout.bay().template(), false, false, layout)
	for id: StringName in _ids(layout):
		var spec := layout.door(id)
		var root := Node3D.new()
		var leaf: MeshInstance3D = model.leaf(spec)
		root.add_child(leaf)
		root.add_child(model.frame(spec))
		for solid: ShipGeometry.SolidSpec in solids:
			if not recipe.is_host_wall(spec, solid) and solid.material_role != &"floor": continue
			# The flush threshold seals against the production floor, not a raised sill.
			root.add_child(HatchModel.mesh_piece(model.wall_mesh(layout, solid), solid.transform, 1, Surfaces.material(&"wall")))
		for opened: bool in [false, true] if id == ShipLayout.POWER_DOOR_ID else [false]:
			leaf.position = (spec.frame() * Vector3(0, spec.aperture().y / 2, ShipLayout.WALL / 2)) + Vector3(-Doors.POWER_SLIDE if opened else 0.0, 0, 0)
			for side: float in [-1.0, 1.0]:
				for eye_x: float in [-0.7, 0, 0.7]:
					var local_eye := Vector3(eye_x, 1.65, ShipLayout.WALL / 2 + side * 2)
					var eye := spec.frame() * local_eye
					var faces := PackedVector3Array()
					QUERY.collect(root, eye, 1, faces)
					var mesh := TriangleMesh.new()
					assert_true(mesh.create_from_faces(faces), "production pocket has facing triangles")
					var misses := 0
					var tested := 0
					for x_index: int in range(126):
						var x := lerpf(-0.649, 1.799, x_index / 125.0)
						if opened and absf(x) < spec.aperture().x / 2: continue
						for y_index: int in range(111):
							var xy := Vector2(x, lerpf(0.001, 2.219, y_index / 110.0))
							var target := Vector3(xy.x, xy.y, 0 if side < 0 else ShipLayout.WALL)
							var direction := target - local_eye
							var exit_z := ShipLayout.WALL + 0.001 if side < 0 else -0.001
							var end := local_eye + direction * ((exit_z - local_eye.z) / direction.z)
							tested += 1
							if mesh.intersect_segment(eye, spec.frame() * end).is_empty():
								misses += 1
					print("SLIDING_SEAL id=%s open=%s side=%s eye_x=%s rays=%d misses=%d" % [id, opened, side, eye_x, tested, misses])
					assert_int_equal(misses, 0, "zero see-through at closed steel and pocket/jamb")
		root.free()
