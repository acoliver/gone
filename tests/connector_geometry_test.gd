extends SimTestCase

func test_building_and_freeing_every_hatch_leaves_no_orphans() -> void:
	var layout := ShipLayout.authored().layout
	var initial_orphans := Node.get_orphan_node_ids().size()
	var builds := 0
	for cycle: int in range(2):
		for id: StringName in layout.door_ids():
			var spec := layout.door(id)
			if spec.animation() != ShipLayout.AnimationRecipe.HINGE:
				continue
			var view := DoorView.build(spec)
			for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(spec):
				view.add_child(DoorView.split_surface(solid, spec.frame(), 1, 1))
			view.free()
			builds += 1
			assert_int_equal(Node.get_orphan_node_ids().size(), initial_orphans, "building and freeing %s in cycle %d leaves no orphan nodes" % [id, cycle])
	print("HATCH BUILD/FREE builds=%d orphan_growth=%d" % [builds, Node.get_orphan_node_ids().size() - initial_orphans])

func test_shared_hatch_model_has_no_presenter_dependencies() -> void:
	var source := FileAccess.get_file_as_string("res://app/hatch_model.gd")
	for presenter: String in ["DoorView.", "Hatch.", "Hallway."]:
		assert_false(source.contains(presenter), "shared hatch construction must not depend on " + presenter)

func test_hatch_hardware_shares_resources_without_sharing_room_masks() -> void:
	var layout := ShipLayout.authored().layout
	var first := DoorView.build(layout.door(&"D14-C-001-H-FORE"), 4, 8)
	var remote := DoorView.build(layout.door(&"D01-C-001-H-FORE"), 32, 64)
	var bay := Hatch.build()
	for path: String in ["Frame/ForeSteel", "Frame/AftSteel", "Hinge/Leaf/ForeSteel", "Hinge/Leaf/Wheel"]:
		var a: MeshInstance3D = first.get_node(path).get_child(0) if path.ends_with("Wheel") else first.get_node(path)
		var b: MeshInstance3D = remote.get_node(path).get_child(0) if path.ends_with("Wheel") else remote.get_node(path)
		assert_true(a.mesh == b.mesh and a.material_override == b.material_override, "shared hardware resource " + path)
		assert_int_equal(a.layers, 8 if path.contains("Aft") else 4, "D14 mask remains local")
		assert_int_equal(b.layers, 64 if path.contains("Aft") else 32, "remote mask remains local")
	var panel_parts: Array[String] = ["MountingBox", "Housing", "FacePlate", "Fastener00", "Fastener01", "Fastener10", "Fastener11", "ButtonBezel", "Button", "CardReader", "Indicator", "Toggle"]
	for panel: String in ["ForePanel", "AftPanel"]:
		var first_panel := first.get_node(panel)
		var remote_panel := remote.get_node(panel)
		var bay_panel := bay.view.get_node(panel)
		for owner: Node in [first_panel, remote_panel, bay_panel]:
			assert_int_equal(owner.get_child_count(), panel_parts.size(), "complete panel part inventory")
			for part: String in panel_parts:
				assert_true(owner.has_node(NodePath(part)), "stable panel part name: " + part)
		for a: MeshInstance3D in first_panel.get_children():
			var b := remote_panel.get_node(NodePath(a.name)) as MeshInstance3D
			var c := bay_panel.get_node(NodePath(a.name)) as MeshInstance3D
			assert_true(a.mesh == b.mesh and a.mesh == c.mesh, "all hatch panels share primitives: " + a.name)
			assert_true(a.material_override == b.material_override and a.material_override == c.material_override, "all hatch panels share materials: " + a.name)
			assert_int_equal(a.layers, 4 if panel == "ForePanel" else 8, "panel room mask: " + a.name)
			assert_int_equal(b.layers, 32 if panel == "ForePanel" else 64, "remote panel room mask: " + a.name)
			assert_int_equal(c.layers, 1, "bay panel room mask: " + a.name)
	first.free()
	remote.free()
	bay.free()

func test_hatch_meshes_have_rounded_frame_braces_large_wheel_and_instanced_rivets() -> void:
	var layout := ShipLayout.authored().layout
	var first := DoorView.build(layout.door(&"D14-C-001-H-FORE"))
	var remote := DoorView.build(layout.door(&"D01-C-001-H-FORE"))
	for path: String in ["Frame/ForeSteel", "Frame/AftSteel", "Frame/ForeRivets", "Frame/AftRivets", "Hinge/Leaf/ForeSteel", "Hinge/Leaf/AftSteel", "Hinge/Leaf/ForeRivets", "Hinge/Leaf/AftRivets"]:
		assert_true(first.has_node(NodePath(path)), "rounded steel and rivet assemblies exist: " + path)
		if not first.has_node(NodePath(path)): continue
		var piece := first.get_node(NodePath(path)) as GeometryInstance3D
		var other := remote.get_node(NodePath(path)) as GeometryInstance3D
		if piece is MultiMeshInstance3D:
			assert_true(piece.multimesh.instance_count >= 40, "rivets are batched, not individual mesh nodes")
			assert_true(piece.multimesh == other.multimesh, "all decks share the rivet batch")
		else:
			assert_true(piece.mesh == other.mesh, "all decks share generated geometry")
		assert_true(piece.material_override == other.material_override, "all decks share steel materials")
	for path: String in ["StrapHinges", "Lugs"]:
		var fore: MeshInstance3D = first.get_node("Hinge/Leaf/ForeSteel")
		var aft: MeshInstance3D = first.get_node("Hinge/Leaf/AftSteel")
		# Round 11 shares one real-axis barrel, rather than duplicating face-offset
		# pins. Compare the straps/links here; the attachment test pins barrel axes.
		var fore_bounds := _group_bounds(fore.mesh, path + "/ForeSteel/", path == "StrapHinges")
		var aft_bounds := _group_bounds(aft.mesh, path + "/AftSteel/", path == "StrapHinges")
		assert_float_equal(fore_bounds.position.x, aft_bounds.position.x, "both faces keep the same physical hinge/latch edge: " + path)
		assert_float_equal(fore_bounds.end.x, aft_bounds.end.x, "reverse-face hardware is not moved to the opposite jamb: " + path)
	var leaf_mesh: Mesh = first.get_node("Hinge/Leaf/ForeSteel").mesh
	var plate_bounds := _group_bounds(leaf_mesh, "ForeSteel/plate")
	# Andrew's 2026-11-05 flush-leaf design closes the old 60 mm side recesses.
	assert_float_in_range(plate_bounds.size.x, 1.17999, 1.18001, "flush leaf body survives batching without the obsolete X ribs")
	assert_float_in_range(plate_bounds.size.y, 2.31999, 2.32001, "rounded leaf retains its full tall silhouette")
	var leaf_arrays := leaf_mesh.surface_get_arrays(0)
	var leaf_normals: PackedVector3Array = leaf_arrays[Mesh.ARRAY_NORMAL]
	assert_true(leaf_normals[0].dot(Vector3.FORWARD) > 0.99, "leaf front faces outward, not into the steel")
	var wheel: Node3D = first.get_node("Hinge/Leaf/Wheel")
	var bounds := AABB()
	for child: MeshInstance3D in wheel.get_children(): bounds = bounds.merge(child.transform * child.mesh.get_aabb())
	assert_float_in_range(bounds.size.x, 0.88799, 0.88801, "round7 wheel outside diameter is 0.888m")
	var bay := Hatch.build()
	assert_true(bay.door_piece().get_node("ForeSteel").mesh == first.get_node("Hinge/Leaf/ForeSteel").mesh, "bay and connector hatches use the same shared leaf")
	assert_true(bay.view.get_node("Frame/ForeSteel").mesh == first.get_node("Frame/ForeSteel").mesh, "bay and connector hatches use the same rounded frame")
	bay.free()
	first.free()
	remote.free()

func _group_bounds(mesh: Mesh, prefix: String, straps_only: bool = false) -> AABB:
	var found := false
	var result := AABB()
	var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(mesh)
	for id: StringName in parts:
		if not String(id).begins_with(prefix): continue
		if straps_only and ("/barrel-" in String(id) or "/cap-" in String(id)): continue
		var part: Dictionary = parts[id]
		var bounds: AABB = part.pose * part.bounds
		result = result.merge(bounds) if found else bounds
		found = true
	assert_true(found, "all original hardware groups remain in the submitted buffers: " + prefix)
	return result

func test_all_hatch_bulkheads_share_plated_wall_material_and_mapping() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(26, 0, 0))
	scene.prepare_near(Vector3(10, 0, 0))
	var count := 0
	for node: Node in root.get_children():
		if not node.has_meta(&"solid_id") or "/WALL/" not in String(node.get_meta(&"solid_id")):
			continue
		count += 1
		assert_int_equal(node.get_child_count(), 2, "bulkhead retains independently masked halves")
		for piece: MeshInstance3D in node.get_children():
			assert_true(piece.material_override == RoomGeometry.wall_material(), "hatch bulkhead shares exact plated wall material resource")
			assert_true(piece.has_meta(&"surface_frame"), "hatch bulkhead uses explicit surface-local mapping")
			assert_true(piece.material_override.get_shader_parameter(&"panel_pitch") == Surfaces.PANEL_PITCH, "same wall panel density")
	assert_int_equal(count, 42, "three wall slabs and four pocket corner skins around each of six hatches")
	root.free()

func test_connector_lights_reach_hatches_floor_ladder_and_lift_inside_falloff() -> void:
	var game := Game.new(0)
	var layout := game.layout
	var root := Node3D.new()
	var scene := ShipScene.build_into(root, game, false)
	scene.prepare_near(Vector3(10, 0, 0))
	scene.prepare_near(Vector3(26, 0, 0))
	for id: StringName in layout.connector_ids():
		var spec := layout.connector(id)
		var connector := root.get_node(NodePath(id)) as ShipConnector if spec.deck_number() == 14 else scene.build_remote(spec) as ShipConnector
		var lights: Array[OmniLight3D] = []
		_collect_lights(connector, lights)
		assert_int_equal(lights.size(), 3, "%s keeps its three-light budget after composition" % id)
		var caged := 0
		for light: OmniLight3D in lights:
			assert_float_equal(light.omni_range, 3.0, "%s keeps its original key ranges" % id)
			if light.get_parent().has_meta(&"hatch_lamp"): caged += 1
			else: assert_close(Surfaces.world_frame(light).origin, spec.landing_key_position(), "remaining key uses the authored landing position")
		assert_int_equal(caged, 2, "%s keeps both hatch keys seated in cages" % id)
		var bounds := spec.bounds()
		var probes: Array[Vector3] = []
		for offset: float in [0.5, 3.0, 5.5]:
			probes.append(Vector3(bounds.position.x + offset, bounds.position.y + 0.02, 0))
		for hatch_id: StringName in spec.hatch_ids():
			var hatch := layout.door(hatch_id)
			var toward_room := 1.0 if hatch.frame().origin.x < bounds.get_center().x else -1.0
			probes.append(hatch.frame().origin + Vector3(toward_room * 0.2, 1.2, 0))
			var panel := hatch.frame() * Vector3(hatch.aperture().x / 2 + 0.38, 1.25, ShipLayout.WALL + 0.08 if toward_room > 0 else -0.08)
			probes.append(panel)
		var landing := layout.well(spec.well_id()).landing(spec.deck_number()).origin
		probes.append(landing + Vector3(0, 1.2, 0))
		probes.append(landing + Vector3(0, 0.02, 0))
		probes.append(layout.door(layout.lift(spec.lift_id()).door_id()).frame().origin + Vector3(0, 1.2, -0.1))
		for probe: Vector3 in probes:
			var best := INF
			for light: OmniLight3D in lights:
				var origin := Surfaces.world_frame(light).origin
				best = minf(best, origin.distance_to(probe) / light.omni_range)
			assert_true(best <= 0.9, "%s room detail lies inside useful light range, not its black cutoff: %s ratio=%f" % [id, probe, best])
		if spec.deck_number() != 14:
			scene.remove_remote(spec, connector)
	root.free()

func test_d14_topology_and_exact_openability() -> void:
	var layout := ShipLayout.authored().layout
	assert_true(layout.deck(14).section_ids() == [&"D14-S-040", &"D14-S-041", &"D14-S-042"], "three ordered sections")
	for fixture: Vector3 in [Vector3(40, -24, 0), Vector3(41, 6, 30), Vector3(42, 36, 60)]:
		var section := layout.section(ShipLayout.section_id(14, int(fixture.x)))
		assert_float_equal(section.bounds().position.x, fixture.y, "independent fore bound")
		assert_float_equal(section.bounds().end.x, fixture.z, "independent aft bound")
		assert_int_equal(section.side_door_ids().size(), 5 if fixture.x == 41 else 6, "exact side leaf count")
		for id: StringName in section.side_door_ids():
			assert_int_equal(layout.door(id).policy(), ShipLayout.Policy.NEVER_OPENS, "side leaf refuses")
	var cranks: Array[StringName] = []
	for id: StringName in layout.door_ids():
		if layout.door(id).policy() == ShipLayout.Policy.CRANK:
			cranks.append(id)
	assert_true(cranks == [&"D14-C-000-H-AFT", &"D14-C-000-H-FORE", &"D14-C-001-H-AFT", &"D14-C-001-H-FORE"], "only four inner hatches crank")

func test_setback_collar_sides_use_the_approach_rooms_light_mask() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]:
		var spec := layout.door(id)
		var view := DoorView.build(spec, 1, 8)
		var approach_mask := 1 if spec.hinge_frame().origin.z > ShipLayout.WALL / 2 else 8
		for part: String in ["FRAME/RIGHT", "FRAME/TOP", "COAMING"]:
			for side: String in ["ForeSteel", "AftSteel"]:
				var piece: MeshInstance3D = view.get_node("Frame/" + side)
				var ranges: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(piece.mesh, &"hatch_reservations")
				var row: Dictionary = ranges[StringName(part)].row
				var normals: PackedVector3Array = piece.mesh.surface_get_arrays(0)[Mesh.ARRAY_NORMAL]
				for index: int in range(int(row.vertex_start), int(row.vertex_start + row.vertex_count)):
					var normal := normals[index]
					var expected := (1 if normal.z < 0 else 8) if absf(normal.z) > 0.5 else approach_mask
					assert_int_equal(piece.layers, expected, "%s %s normal %s belongs to its visible room" % [id, part, normal])
		view.free()

func test_section_41_endcaps_are_replaced_by_owned_portal_solids() -> void:
	var game := Game.new(0)
	for x: float in [6, 30]:
		var probe := ColliderSet.Aabb.try_new(Vector3(x + 0.1, 1.2, 0), Vector3(0.04, 0.4, 0.2)).box
		var owners: Array[StringName] = []
		for solid: ShipGeometry.SolidSpec in ShipCollision.opening_solids(game.registry, false, false, game.layout):
			if ShipGeometry.box_aabb(solid).overlaps(probe):
				owners.append(solid.id)
		assert_true(owners == ([&"D14-C-000-H-AFT/BLOCKER", &"D14-C-000-H-AFT/SWING"] if x == 6 else [&"D14-C-001-H-FORE/BLOCKER", &"D14-C-001-H-FORE/SWING"]), "aperture contains only the named passage gate and hardware sweep, no old endcap: %s" % [owners])

func test_new_geometry_contains_landings_and_no_duplicate_power_wall() -> void:
	var layout := ShipLayout.authored().layout
	var solids := ShipGeometry.deck_static_solids(layout, 14)
	var shared_hits := 0
	var probe := Vector3(31.0, 1.2, -1.6)
	for solid: ShipGeometry.SolidSpec in solids:
		var box := ShipGeometry.box_aabb(solid)
		if AABB(box.min_corner(), box.max_corner() - box.min_corner()).has_point(probe):
			shared_hits += 1
	assert_int_equal(shared_hits, 1, "power south wall has exactly one owner")
	var set := ShipCollision.new(layout).deck_set(14)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(34.5, 0.417, -1.2)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var result := Resolve.resolve_motion(capsule, Vector3(0, 0, -2.1), set)
	assert_true(result.is_ok(), "aft landing approach is valid")
	assert_close(result.motion.displacement, Vector3(0, 0, -2.1), "open port doorway clears unchanged power wall")
	var ids := ShipCollision.new(layout).solid_ids(14)
	assert_true(&"D14-C-001/LANDING/PORT/000" in ids and &"D14-C-000/LANDING/PORT/000" in ids, "both landing side walls exist")

func test_real_scene_has_shared_hatch_details_and_lazy_red_rooms() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	var hatches: Array[DoorView] = []
	for view: DoorView in scene.door_views:
		if game.layout.door(view.door_id()).kind() == ShipLayout.DoorKind.HATCH:
			hatches.append(view)
	assert_int_equal(hatches.size(), 2, "opening contains only its two boundary hatch views")
	for view: DoorView in hatches:
		for path: String in ["Frame", "Hinge/Leaf", "Hinge/Leaf/Wheel", "Hinge/Leaf/ReverseWheel", "ForePanel/Button", "ForePanel/CardReader", "AftPanel/Button", "AftPanel/CardReader"]:
			assert_true(view.has_node(NodePath(path)), "shared hatch detail: " + path)
		var fixed: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(view.get_node("Frame/ForeSteel").mesh, &"hatch_reservations")
		assert_true(fixed.has(&"COAMING"), "coaming is present in the submitted fixed buffer")
		for group: String in ["StrapHinges/ForeSteel/", "Lugs/ForeSteel/"]:
			assert_true(_group_bounds(view.get_node("Hinge/Leaf/ForeSteel").mesh, group).has_volume(), "shared hatch hardware remains rendered: " + group)
	root.free()

func test_four_open_hatches_allow_both_directions_and_locked_faces_contain() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for id: StringName in [&"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		collision.open_door(id)
	var set := collision.deck_set(14)
	for x: float in [0, 6, 30, 36]:
		for direction: float in [-1, 1]:
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(x - direction * 1.7, 0.417, 0)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var delta := Vector3(direction * 3.4, 0, 0)
			var result := Resolve.resolve_motion(capsule, delta, set)
			assert_true(result.is_ok(), "complete horizontal sweep accepted")
			assert_close(result.motion.displacement, delta, "open hatch traversed from both directions")
	for fixture: Vector3 in [Vector3(-22, 0, 0), Vector3(58, 0, 0), Vector3(39, 0, 0), Vector3(33, 0, 0)]:
		var capsule := Resolve.Capsule.new()
		capsule.foot = fixture + Vector3.UP * 0.417
		capsule.head = capsule.foot + Vector3.UP * 1.15
		var delta := Vector3(-4, 0, 0) if fixture.x < 0 else (Vector3(4, 0, 0) if fixture.x == 58 else Vector3(0, 0, 3))
		var result := Resolve.resolve_motion(capsule, delta, set)
		assert_true(result.is_ok(), "locked-door containment sweep accepted")
		assert_true(result.motion.displacement.length() < delta.length(), "side, lift and boundary doors contain")

func test_prefetch_and_independent_red_light_masks() -> void:
	var root := Node3D.new()
	var game := Game.new(0)
	var scene := ShipScene.build_into(root, game, false)
	for x: float in [18, 25.9]:
		scene.prepare_near(Vector3(x, 0, 0))
		assert_false(root.has_node("D14-C-001"), "no connector construction before final four meters")
	scene.prepare_near(Vector3(26, 0, 0))
	assert_true(root.has_node("D14-C-001") and root.has_node("D14-S-042"), "aft rooms ready before exposure")
	assert_false(root.has_node("D14-C-000"), "fore room is not prebuilt")
	var count := root.get_child_count()
	scene.prepare_near(Vector3(34, 0, 0))
	assert_int_equal(root.get_child_count(), count, "no duplicate rooms or portal owners")
	game.power_active = true
	var lights: Array[OmniLight3D] = []
	_collect_lights(root.get_node("D14-C-001"), lights)
	assert_int_equal(lights.size(), 3, "connector and landing have three steady fixtures")
	for light: OmniLight3D in lights:
		assert_int_equal(light.light_cull_mask, 16, "isolated aft connector mask")
		assert_float_in_range(light.light_energy, Lighting.FIXTURE_ENERGY * Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER - 1e-5, Lighting.FIXTURE_ENERGY * Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER + 1e-5, "red independent of power activation")
		assert_true(light.light_color == Lighting.EMERGENCY_RED, "steady emergency red")
		assert_true(light.omni_range <= 3, "local fixture range")
	scene.prepare_near(Vector3(10, 0, 0))
	assert_true(root.has_node("D14-C-000") and root.has_node("D14-S-040"), "fore rooms prepare at their own threshold")
	var hatches := 0
	for view: DoorView in scene.door_views:
		if game.layout.door(view.door_id()).kind() == ShipLayout.DoorKind.HATCH:
			hatches += 1
	assert_int_equal(hatches, 6, "four crank and two boundary views")
	root.free()

func test_hatch_projects_model_wheel_and_leaf_without_advancing_them() -> void:
	var layout := ShipLayout.authored().layout
	var id: StringName = &"D14-C-001-H-FORE"
	var view := DoorView.build(layout.door(id), 1, 16)
	var store := Doors.Store.new(layout, 0)
	var context := Doors.Context.new()
	context.face_id = layout.door(id).face_ids()[0]
	for _attempt: int in range(HatchResistance.schedule(0, id).weights.size()):
		store.press(id, context)
		for _tick: int in range(6):
			store.tick()
			var snapshot := store.snapshot(id)
			view.present(snapshot)
			assert_float_in_range(view.get_node("Hinge/Leaf/Wheel").rotation.z, deg_to_rad(snapshot.wheel_angle + snapshot.refusal_offset) - 1e-5, deg_to_rad(snapshot.wheel_angle + snapshot.refusal_offset) + 1e-5, "exact model wheel interpolation")
	for _tick: int in range(48):
		store.tick()
		view.present(store.snapshot(id))
	assert_float_in_range(view.get_node("Hinge").rotation.y, layout.door(id).swing_radians() - 1e-5, layout.door(id).swing_radians() + 1e-5, "leaf swings into connector")
	var before := store.snapshot(id).wheel_angle
	view.present(store.snapshot(id))
	assert_float_equal(store.snapshot(id).wheel_angle, before, "presentation never advances model")
	view.free()

func _collect_lights(node: Node, lights: Array[OmniLight3D]) -> void:
	if node is OmniLight3D:
		lights.append(node)
	for child: Node in node.get_children():
		_collect_lights(child, lights)
