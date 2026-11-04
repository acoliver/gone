extends SimTestCase

const HALL: StringName = &"D14-S-041"
func test_grate_retains_the_complete_shared_wall_threshold_footprint() -> void:
	if not _available(): return
	var layout := ShipLayout.authored().layout
	var spec: Variant = layout.call(&"dressing", HALL)
	var floor_mesh := ShipGeometry.hallway_solids(layout)[0]
	var box := ShipGeometry.box_aabb(floor_mesh)
	assert_float_equal(spec.grate_footprint.position.x, box.min_corner().x, "grate starts at structural floor edge")
	assert_float_equal(spec.grate_footprint.end.x, box.max_corner().x, "grate reaches the shared aft wall band")
	assert_float_equal(spec.grate_footprint.position.z, box.min_corner().z, "power threshold remains covered")
	assert_float_equal(spec.grate_footprint.end.z, box.max_corner().z, "bay threshold remains covered")


func _available() -> bool:
	var layout := ShipLayout.authored().layout
	assert_true(layout.has_method(&"dressing"), "ShipLayout must own a pure DressingSpec per corridor space")
	return layout.has_method(&"dressing")

func test_layout_owns_stations_and_moved_opening_exclusions() -> void:
	if not _available(): return
	var original := ShipLayout.authored().layout
	var before: Variant = original.call(&"dressing", HALL)
	assert_float_equal(before.rib_pitch, 2.0, "approved rib rhythm")
	assert_float_equal(before.rib_stations[0], 7.0, "station derives from section start")
	var records := original.records()
	var section := original.section(HALL)
	var bounds := section.bounds()
	bounds.position.x -= 1
	bounds.size.x += 1
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), bounds, section.opening_ids(), section.side_door_ids(), section.circuit(), true)
	var door := original.door(&"D14-S-041-SIDE-003-PORT")
	var frame := door.frame()
	frame.origin.x += 0.75
	records[records.find(door)] = ShipLayout.DoorSpec.new(door.id(), 14, door.kind(), door.policy(), frame, door.aperture(), door.spaces(), door.face_ids(), door.owner_id(), door.animation(), door.has_wheel())
	var result := ShipLayout.try_new(records)
	assert_true(result.is_ok(), "moved authored inputs remain valid")
	var after: Variant = result.layout.call(&"dressing", HALL)
	assert_float_equal(after.rib_stations[0], 6.0, "station moves with section")
	var old_exclusion: AABB = _clearance(before, StringName("%s/OPENING" % door.id()))
	var new_exclusion: AABB = _clearance(after, StringName("%s/OPENING" % door.id()))
	assert_vec3_equal(new_exclusion.position - old_exclusion.position, Vector3(0.75, 0, 0), "opening exclusion follows DoorSpec, not station index")

func test_every_space_pose_stays_out_of_every_reserved_envelope() -> void:
	if not _available(): return
	var layout := ShipLayout.authored().layout
	for id: StringName in _spaces(layout):
		var spec: Variant = layout.call(&"dressing", id)
		assert_true(not spec.batches.is_empty(), "built corridor has dressing: %s" % id)
		for batch: Variant in spec.batches:
			for pose: Transform3D in batch.poses:
				var bounds: AABB = pose * AABB(Vector3.ONE * -0.5, Vector3.ONE)
				for clearance: Variant in spec.clearances:
					assert_false(_overlap(bounds, clearance.bounds), "%s/%s intrudes into %s" % [id, batch.family, clearance.id])
				assert_true(spec.bounds.grow(0.25).encloses(bounds), "room-local batch extent: %s/%s" % [id, batch.family])

func test_every_portal_and_hall_lamp_has_an_explicit_clearance() -> void:
	if not _available(): return
	var layout := ShipLayout.authored().layout
	for id: StringName in _spaces(layout):
		var spec: Variant = layout.call(&"dressing", id)
		var names: Array[StringName] = []
		for clearance: Variant in spec.clearances: names.append(clearance.id)
		assert_true(&"WALK" in names, "walking envelope always present")
		for door_id: StringName in layout.door_ids():
			var door := layout.door(door_id)
			if id not in door.spaces(): continue
			assert_true(StringName("%s/OPENING" % door_id) in names, "every portal excluded: %s/%s" % [id, door_id])
			if door.has_wheel(): assert_true(StringName("%s/SWING" % door_id) in names, "complete swept and parked reservation")
			for face_id: StringName in door.face_ids():
				if layout.face(face_id).source_space() == id: assert_true(StringName("%s/LABEL" % face_id) in names, "label approach excluded on every face")
		if "-C-" in String(id): assert_true(&"TRANSFER" in names and &"CLIMB" in names, "every connector protects its ladder")
	var hall := Hallway.build(Game.new(0))
	var dressing: Variant = layout.call(&"dressing", HALL)
	for light: Node in hall.find_children("*", "OmniLight3D", true, false):
		var point := Surfaces.world_frame(light).origin
		var emitter := AABB(point - Vector3.ONE * 0.10, Vector3.ONE * 0.20)
		for batch: Variant in dressing.batches:
			for pose: Transform3D in batch.poses:
				assert_false(_overlap(pose * AABB(Vector3.ONE * -0.5, Vector3.ONE), emitter), "hall station/fill emitter stays uncovered at %s" % point)
	hall.free()

func test_batch_count_depends_on_families_not_corridor_length() -> void:
	if not _available(): return
	var layout := ShipLayout.authored().layout
	var original: Variant = layout.call(&"dressing", HALL)
	var section := layout.section(HALL)
	var records := layout.records()
	var bounds := section.bounds()
	bounds.size.x *= 4
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), bounds, section.opening_ids(), section.side_door_ids(), section.circuit(), true)
	var longer := ShipLayout.try_new(records)
	assert_true(longer.is_ok(), "extended section valid")
	var extended: Variant = longer.layout.call(&"dressing", HALL)
	assert_true(extended.batches.size() <= 18, "fixed family budget, not one node per station")
	assert_true(extended.batches.size() <= original.batches.size() + 1, "length does not create batch families")
	assert_true(_pose_count(extended) > _pose_count(original) * 2, "long section actually adds geometry")

func test_presenter_uses_owned_masked_batches_only() -> void:
	if not _available(): return
	var script: GDScript = load("res://app/corridor_dressing.gd")
	var layout := ShipLayout.authored().layout
	for id: StringName in [HALL, &"D14-S-040", &"D01-C-000", &"D30-C-001"]:
		var node: Node3D = script.build(layout, id)
		var spec: Variant = layout.call(&"dressing", id)
		assert_int_equal(node.get_child_count(), spec.batches.size(), "one MultiMesh per family")
		var mask := Lighting.space_mask(layout, id) | (Lighting.HALL_FILL_MASK if id == HALL else 0)
		for child: Node in node.get_children():
			assert_true(child is MultiMeshInstance3D, "dressing adds only batched geometry")
			assert_int_equal(child.layers, mask, "room light mask")
			assert_int_equal(child.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "dressing never shadows emergency emitters")
			assert_true(child.material_override == Surfaces.material(child.get_meta(&"role")), "finite role material sharing")
			assert_true(child.get_meta(&"instance_poses") is Array, "headless pose truth retained")
		node.free()

func test_visible_grate_has_real_holes_exact_bar_tops_and_recessed_tray() -> void:
	if not _available(): return
	var layout := ShipLayout.authored().layout
	for id: StringName in _spaces(layout):
		var spec: Variant = layout.call(&"dressing", id)
		var floor_y: float = spec.bounds.position.y
		assert_float_equal(spec.grate_depth, 0.20, "opaque tray recess")
		var families: Dictionary = {}
		for batch: Variant in spec.batches:
			families[batch.family] = batch
			if String(batch.family).begins_with("Grate"):
				for pose: Transform3D in batch.poses:
					var bounds: AABB = pose * AABB(Vector3.ONE * -0.5, Vector3.ONE)
					assert_float_equal(bounds.end.y, floor_y, "every grate bar/support top at layout floor")
			if batch.family == &"SubfloorTray":
				for pose: Transform3D in batch.poses:
					var bounds: AABB = pose * AABB(Vector3.ONE * -0.5, Vector3.ONE)
					assert_float_equal(bounds.end.y, Vector3(0, floor_y - spec.grate_depth, 0).y, "tray below open bars at Vector3 precision")
		assert_true(families.has(&"GrateCrossBars") and families.has(&"GrateLongBars") and families.has(&"GrateCarriers") and families.has(&"SubfloorTray"), "three grate families plus opaque tray")
		var bars: Array = families[&"GrateCrossBars"].poses
		assert_true(bars.size() > 2, "repeated real transverse bars")
		assert_true(bars[0].basis.x.length() < 0.12, "bars leave open holes between stations")

func test_structural_floor_keeps_original_recipe_but_is_hidden() -> void:
	if not _available(): return
	var game := Game.new(0)
	var hall := Hallway.build(game)
	var floor_mesh: MeshInstance3D = hall.get_node("HallFloor")
	var solid := ShipGeometry.hallway_solids(game.layout)[0]
	assert_false(floor_mesh.visible, "flat structural floor hidden under grate")
	assert_true(floor_mesh.transform.is_equal_approx(solid.transform), "original floor transform retained")
	assert_true(floor_mesh.mesh.get_aabb().size.is_equal_approx(solid.size), "original structural dimensions retained")
	assert_true(hall.has_node("CorridorDressing/GrateCrossBars"), "visible replacement exists")
	hall.free()

func test_all_ordered_collision_boxes_are_identical_before_after_build_and_free() -> void:
	if not _available(): return
	var game := Game.new(0)
	var before: Dictionary = {}
	for deck: int in range(1, 31): before[deck] = game.collision.deck_set(deck).boxes()
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(8, 0.305, 0))
	scene.prepare_near(Vector3(27, 0.305, 0))
	scene.stream.focus(&"C-000-LADDER", 1)
	for frame: int in range(5): scene.stream.build_next()
	root.free()
	for deck: int in range(1, 31):
		var after := game.collision.deck_set(deck).boxes()
		assert_int_equal(after.size(), before[deck].size(), "complete collider inventory unchanged")
		for index: int in range(after.size()): assert_true(after[index].equals(before[deck][index]), "ordered box equality D%02d index %d" % [deck, index])

func test_stream_eviction_frees_batches_and_reload_restores_identical_poses() -> void:
	if not _available(): return
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.stream.focus(&"C-000-LADDER", 1)
	for frame: int in range(5): scene.stream.build_next()
	var room: Node3D = scene.stream.room(&"D01-C-000")
	var dressing: Node3D = room.get_node("CorridorDressing")
	var poses: Array = dressing.get_child(0).get_meta(&"instance_poses").duplicate()
	var references: Array[WeakRef] = []
	for batch: Node in dressing.get_children(): references.append(weakref(batch))
	scene.stream.focus(&"C-000-LADDER", 30)
	for reference: WeakRef in references: assert_true(reference.get_ref() == null, "batch freed with its room")
	for frame: int in range(5): scene.stream.build_next()
	scene.stream.focus(&"C-000-LADDER", 1)
	for frame: int in range(5): scene.stream.build_next()
	var rebuilt: Node3D = scene.stream.room(&"D01-C-000").get_node("CorridorDressing")
	assert_true(rebuilt.get_child(0).get_meta(&"instance_poses") == poses, "deterministic reload")
	root.free()

func _spaces(layout: ShipLayout) -> Array[StringName]:
	var ids := layout.deck(14).section_ids()
	ids.append_array(layout.connector_ids())
	return ids

func _clearance(spec: Variant, id: StringName) -> AABB:
	for clearance: Variant in spec.clearances:
		if clearance.id == id: return clearance.bounds
	assert_true(false, "missing clearance: %s" % id)
	return AABB()

func _pose_count(spec: Variant) -> int:
	var count := 0
	for batch: Variant in spec.batches: count += batch.poses.size()
	return count

func _overlap(a: AABB, b: AABB) -> bool:
	var amount := a.end.min(b.end) - a.position.max(b.position)
	return amount.x > 0.0001 and amount.y > 0.0001 and amount.z > 0.0001
