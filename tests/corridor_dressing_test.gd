extends SimTestCase

const HALL: StringName = &"D14-S-041"
func test_outer_sections_reserve_only_presented_services() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-S-040", &"D14-S-042"]:
		var section := layout.section(id)
		assert_int_equal(section.regular_light_frames().size(), 0, "emergency-only section has no white strips")
		var dressing := layout.dressing(id)
		assert_int_equal(_reservation_count(dressing, "STRIP/"), 0, "absent white strips reserve no volume")
		assert_int_equal(_reservation_count(dressing, "LAMP/"), section.emergency_fixture_frames().size(), "every actual fixture reserves its volume")
		assert_int_equal(_reservation_count(dressing, "SWITCH_REACH"), 0, "no switch means no switch reservation")

func test_service_exclusions_follow_inventory_without_room_identity() -> void:
	var layout := ShipLayout.authored().layout
	var section := layout.section(HALL)
	var original := ShipDressing.build(layout, section)
	section._id = &"TEST-SERVICE-BEARING-SPACE"
	var renamed := ShipDressing.build(layout, section)
	assert_int_equal(_reservation_count(original, "CEILING_DAMAGE/"), 0, "removed hall tray must not suppress attached ceiling dressing")
	for prefix: String in ["SWITCH_REACH", "FILL/", "LAMP/", "STRIP/"]:
		assert_true(_reservation_count(original, prefix) > 0, "authored service exists: %s" % prefix)
		assert_int_equal(_reservation_count(renamed, prefix), _reservation_count(original, prefix), "service inventory survives renaming: %s" % prefix)
	assert_true(_clearance(renamed, &"SWITCH_REACH").is_equal_approx(_clearance(original, &"SWITCH_REACH")), "switch bounds come from the service, not an id")
	var bare := layout.section(&"D14-S-040")
	bare._id = HALL
	var no_switch := ShipDressing.build(layout, bare)
	assert_int_equal(_reservation_count(no_switch, "SWITCH_REACH"), 0, "a familiar id does not invent a switch")
	assert_int_equal(_reservation_count(no_switch, "CEILING_DAMAGE/"), 0, "a familiar id does not invent damage")
	assert_int_equal(_reservation_count(no_switch, "FILL/"), 0, "a familiar id does not invent fills")

func test_typed_service_inventory_is_consumed_and_tracks_authored_changes() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in _spaces(layout):
		var space: ShipLayout.Spec = layout.section(id) if id in layout.deck(14).section_ids() else layout.connector(id)
		var dressing := layout.dressing(id)
		for reservation: ShipLayout.ServiceReservation in space.service_reservations():
			assert_true(reservation.kind in ShipLayout.ServiceKind.values(), "typed service reservation")
			assert_true(_clearance(dressing, reservation.id).is_equal_approx(reservation.bounds), "recipe consumes the authored service bounds")
	var section := layout.section(&"D14-S-040")
	var frame := Transform3D(Basis(), section.bounds().position + Vector3(2, 1.25, 0.1))
	section._services.switch_frames.append(frame)
	var with_switch := layout.dressing(section.id())
	assert_int_equal(_reservation_count(with_switch, "SWITCH_REACH"), 1, "adding a switch requires no recipe identity change")
	assert_vec3_equal(_clearance(with_switch, &"SWITCH_REACH").get_center(), frame.origin, "switch reach follows authored placement")
	section._services.light_role = ShipLayout.ArchitecturalLightRole.HALL_FILL
	var root := CorridorDressing.build(layout, section.id())
	for child: MultiMeshInstance3D in root.get_children():
		assert_int_equal(child.layers, Lighting.space_mask(layout, section.id()) | Lighting.HALL_FILL_MASK, "semantic fill role reaches every architectural batch without hall identity")
	root.free()

func test_adjacent_generated_floor_geometry_has_unique_ownership_and_complete_coverage() -> void:
	var layout := ShipLayout.authored().layout
	for door_id: StringName in layout.door_ids():
		var door := layout.door(door_id)
		if door.kind() != ShipLayout.DoorKind.HATCH: continue
		var spaces := door.spaces()
		var connector_id := spaces[0] if "-C-" in String(spaces[0]) else spaces[1]
		var section_id := spaces[1] if connector_id == spaces[0] else spaces[0]
		var connector := layout.connector(connector_id)
		var section := layout.section(section_id)
		if not connector.is_built() or not section.is_built(): continue
		var owners: Array[ShipLayout.DressingSpec] = [layout.dressing(section_id), layout.dressing(connector_id)]
		var first_trays := _floor_boxes(owners[0], false)
		var second_trays := _floor_boxes(owners[1], false)
		for a: AABB in first_trays:
			for b: AABB in second_trays:
				assert_false(_xz_overlap(a, b), "opaque faces have one threshold owner: %s" % door_id)
		for index: int in range(2):
			var other_trays := second_trays if index == 0 else first_trays
			for bar: AABB in _floor_boxes(owners[index], true):
				for tray: AABB in other_trays:
					assert_false(_xz_overlap(bar, tray), "grate cannot enter its neighbor's floor patch: %s" % door_id)
	var trays: Array[AABB] = []
	var expected: Array[AABB] = []
	# Include every owner on the deck: the opposite end of a connector can
	# belong to a third room's bridge rather than either member of a pair.
	for id: StringName in layout.deck(14).section_ids() + layout.deck(14).connector_ids():
		var solids := ShipGeometry.section_solids(layout, layout.section(id)) if id in layout.deck(14).section_ids() else ShipGeometry.connector_solids(layout, layout.connector(id))
		var box := ShipGeometry.box_aabb(solids[0])
		expected.append(AABB(box.min_corner(), box.max_corner() - box.min_corner()))
		trays.append_array(_floor_boxes(layout.dressing(id), false))
	# Partition at every generated and structural edge, so even a narrow gap
	# or overlap occupies a complete checked cell rather than evading a grid.
	var xs: Array[float] = []
	var zs: Array[float] = []
	for box: AABB in expected + trays:
		xs.append_array([box.position.x, box.end.x])
		zs.append_array([box.position.z, box.end.z])
	xs.sort()
	zs.sort()
	for xi: int in range(xs.size() - 1):
		if xs[xi + 1] - xs[xi] < 0.0001: continue
		for zi: int in range(zs.size() - 1):
			if zs[zi + 1] - zs[zi] < 0.0001: continue
			var point := Vector2((xs[xi] + xs[xi + 1]) / 2, (zs[zi] + zs[zi + 1]) / 2)
			var supported := _xz_count(expected, point) > 0
			assert_int_equal(_xz_count(trays, point), 1 if supported else 0, "complete unique generated tray coverage at %s" % point)

func _reservation_count(spec: ShipLayout.DressingSpec, prefix: String) -> int:
	var count := 0
	for clearance: ShipLayout.DressingClearance in spec.clearances:
		if String(clearance.id).begins_with(prefix): count += 1
	return count

func _floor_boxes(spec: ShipLayout.DressingSpec, bars: bool) -> Array[AABB]:
	var boxes: Array[AABB] = []
	for batch: ShipLayout.DressingBatch in spec.batches:
		if (bars and String(batch.family).begins_with("Grate")) or (not bars and batch.family == &"SubfloorTray"):
			for pose: Transform3D in batch.poses: boxes.append(pose * ShipDressing.UNIT)
	return boxes

func _xz_overlap(a: AABB, b: AABB) -> bool:
	return minf(a.end.x, b.end.x) - maxf(a.position.x, b.position.x) > 0.0001 and minf(a.end.z, b.end.z) - maxf(a.position.z, b.position.z) > 0.0001

func _xz_count(boxes: Array[AABB], point: Vector2) -> int:
	var count := 0
	for box: AABB in boxes:
		if point.x > box.position.x and point.x < box.end.x and point.y > box.position.z and point.y < box.end.z: count += 1
	return count

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
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), bounds, section.opening_ids(), section.side_door_ids(), section.circuit(), true, section._services)
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
	records[records.find(section)] = ShipLayout.SectionSpec.new(section.id(), 14, section.number(), bounds, section.opening_ids(), section.side_door_ids(), section.circuit(), true, section._services)
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
	for id: StringName in [HALL, &"D14-C-001", &"D14-S-040", &"D01-C-000", &"D30-C-001"]:
		var node: Node3D = script.build(layout, id)
		var spec: Variant = layout.call(&"dressing", id)
		assert_int_equal(node.get_child_count(), spec.batches.size(), "one MultiMesh per family")
		var mask := Lighting.space_mask(layout, id) | (Lighting.HALL_FILL_MASK if _reservation_count(spec, "FILL/") > 0 else 0)
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
	var scene := ShipScene.build_into(root, game)
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
	var scene := ShipScene.build_into(root, game)
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
