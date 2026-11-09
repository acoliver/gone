extends SimTestCase

func test_authored_layout_is_dense_flat_and_limits_damage_to_one_cluster() -> void:
	var first := BayCeiling.layout()
	assert_true(first == BayCeiling.layout(), "ceiling variant positions are authored and deterministic")
	var counts: Dictionary = {}
	var damaged: Array[Vector2i] = []
	var occupied: Dictionary = {}
	for row: Dictionary in first:
		counts[row.variant] = counts.get(row.variant, 0) + 1
		occupied[row.cell] = true
		if row.variant != &"intact": damaged.append(row.cell)
		var pose: Transform3D = row.pose
		assert_float_in_range(pose.origin.y, 2.98999, 2.99001, "all panel flanges share the captured mechanical seat plane")
		assert_true(pose.basis.is_equal_approx(Basis.IDENTITY), "grid panels stay aligned to the captured frame")
	assert_int_equal(first.size(), 111, "111 perforated panels plus eight fitted utility cassettes fill 119 cells")
	assert_int_equal(counts.get(&"intact", 0), 109, "more than 90 percent of all 120 cells retain normal intact panels")
	assert_int_equal(damaged.size(), 2, "only two adjacent panels carry localized mechanical damage")
	assert_true(damaged.has(Vector2i(3, 9)) and damaged.has(Vector2i(2, 8)), "damage stays beside the one missing tile")
	assert_true(not occupied.has(Vector2i(3, 8)), "one failed panel exposes a localized frame opening")
	assert_true(counts.get(&"intact", 0) + counts.get(&"sag", 0) + counts.get(&"brokenedge", 0) == first.size(), "only the local failure variants are installed")

func test_rendered_ceiling_supports_bounds_and_fixture_clearance() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--path", ProjectSettings.globalize_path("res://"), "-s", "tests/bay_ceiling_scene_checks.gd"], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("ERROR:"), text)
	assert_true(text.contains("CEILING RENDER CONTRACTS passed=4 failed=0"), text)

func _check_ceiling_uses_metric_fitted_panels_and_batched_carriers() -> void:
	assert_vec3_equal(BayCeiling.PANEL_SCALE, Vector3.ONE, "fitted exports use their validated metric dimensions directly")
	var root := BayCeiling.build()
	for variant: StringName in BayCeiling.VARIANTS:
		var panel := root.get_node("Panel_" + String(variant)) as MultiMeshInstance3D
		var heads := root.get_node("MountHeads_" + String(variant)) as MultiMeshInstance3D
		assert_true(panel.multimesh.mesh.get_surface_count() > 0, "body surfaces survive import/merge")
		var body_bounds: AABB = panel.multimesh.mesh.get_aabb()
		assert_float_in_range(body_bounds.size.x, 1.179, 1.181, "fitted source contour spans the measured 1.18 m seat footprint")
		assert_float_in_range(body_bounds.size.z, 0.579, 0.581, "fitted source contour spans the measured 0.58 m seat footprint")
		assert_true(heads.multimesh.mesh.get_surface_count() == 4, "four imported mount-head surfaces survive import/merge")
		for index in range(panel.multimesh.instance_count):
			var pose := panel.multimesh.get_instance_transform(index)
			assert_true(pose.is_equal_approx(heads.multimesh.get_instance_transform(index)), "all four heads follow the actual body instance pose")
			var bounds := pose * body_bounds
			assert_true(bounds.position.y >= 2.85 and bounds.position.y > 2.631425, "actual posed detail clears the unchanged pod sweep")
		for surface in range(panel.multimesh.mesh.get_surface_count()):
			assert_true(panel.multimesh.mesh.surface_get_material(surface) == BayCeilingMaterial.material_for_variant(variant), "body wears its variant material")
	var rails := root.get_node("CarrierGrid/SupportedCrossRails") as MultiMeshInstance3D
	var stations: Dictionary = {}
	for index in range(rails.multimesh.instance_count):
		var z := rails.multimesh.get_instance_transform(index).origin.z
		stations[roundi(z * 100)] = true
	assert_int_equal(stations.size(), 13, "crossrail segments occupy exactly thirteen boundaries")
	assert_true(stations.has(-360) and stations.has(360), "crossrails end at the panel field boundaries")
	var slab := root.get_node("CarrierGrid/RailSlabHangers") as MultiMeshInstance3D
	var long_rails := (root.get_node("CarrierGrid/SupportedLongRails") as MultiMeshInstance3D).multimesh
	assert_true(slab.multimesh.instance_count <= 143 and slab.multimesh.instance_count > 130, "only actual grid crossings receive slab hangers, minus service clearances")
	for index in range(slab.multimesh.instance_count):
		var box := slab.multimesh.get_instance_transform(index) * slab.multimesh.mesh.get_aabb()
		assert_float_in_range(box.end.y, 3.19999, 3.20001, "slab hanger touches the unchanged sealed ceiling")
		assert_float_in_range(box.position.y, 3.14749, 3.14751, "slab hanger touches the actual rail top")
		for rail_batch: MultiMesh in [rails.multimesh, long_rails]:
			var touches := false
			for rail_index in range(rail_batch.instance_count):
				var rail_box := rail_batch.get_instance_transform(rail_index) * rail_batch.mesh.get_aabb()
				if box.grow(0.000001).intersects(rail_box): touches = true; break
			assert_true(touches, "slab hanger touches both retained rails at an actual crossing")
	var intact_heads := root.get_node("MountHeads_intact") as MultiMeshInstance3D
	assert_true(intact_heads.multimesh.mesh.surface_get_material(0) == rails.multimesh.mesh.surface_get_material(0), "mount heads and carriers share ceiling-scoped rough metal")
	root.transform = ShipLayout.authored().layout.bay_to_world()
	for node: Node in root.find_children("*", "MultiMeshInstance3D", true, false):
		var batch := (node as MultiMeshInstance3D).multimesh
		var world_frame := Surfaces.world_frame(node)
		for index in range(batch.instance_count):
			var box := batch.get_instance_transform(index) * batch.mesh.get_aabb()
			assert_true(box.position.x >= -6.0001 and box.end.x <= 6.0001 and box.position.z >= -4 and box.end.z <= 4, "actual render batch stays inside bay walls: " + String(node.name))
			assert_true(batch.custom_aabb.grow(0.0001).encloses(box), "explicit render bounds enclose every instance")
			var world_box := world_frame * batch.get_instance_transform(index) * batch.mesh.get_aabb()
			assert_true((world_frame * batch.custom_aabb).grow(0.0001).encloses(world_box), "actual world-space batch bounds include the bay frame exactly once")
	root.free()
	assert_int_equal(BayCeilingMaterial.cache_size(), 5, "only five panel materials are cached")

func _check_actual_panel_bodies_clear_services_and_light_cells_have_fitted_infill() -> void:
	var game := Game.new(4208)
	var fixtures := Lighting.build(game)
	var services := CeilingProps.build(game.layout, ShipLayout.BAY_ID)
	var obstacles: Array[AABB] = []
	_collect_bounds(fixtures, Transform3D.IDENTITY, obstacles)
	_collect_bounds(services, Transform3D.IDENTITY, obstacles)
	var root := BayCeiling.build()
	for name: String in ["intact", "sag", "brokenedge"]:
		var panels := root.get_node("Panel_" + name) as MultiMeshInstance3D
		for index in range(panels.multimesh.instance_count):
			var box := panels.multimesh.get_instance_transform(index) * panels.multimesh.mesh.get_aabb()
			for obstacle: AABB in obstacles:
				assert_true(not box.grow(-0.00001).intersects(obstacle), "panel body clears a measured fixture/service housing: %s vs %s" % [box, obstacle])
	var trims := root.get_node("ServiceCassettes")
	assert_int_equal(trims.get_child_count(), 8, "six light cassettes and two small hatch-stem edge-cutout cassettes")
	assert_true(trims.has_node("Cassette_9_5") and trims.has_node("Cassette_9_6"), "the stem no longer deletes two whole cells")
	for trim: MultiMeshInstance3D in trims.get_children():
		var sheet_area := 0.0
		for index in range(trim.multimesh.instance_count):
			var box := trim.multimesh.get_instance_transform(index) * trim.multimesh.mesh.get_aabb()
			if box.size.y < 0.003: sheet_area += box.size.x * box.size.z
			for obstacle: AABB in obstacles:
				assert_true(not box.grow(-0.000001).intersects(obstacle), "cassette solid clears measured service housing: %s %s vs %s" % [trim.name, box, obstacle])
		var minimum_area := 0.67 if String(trim.name).begins_with("Cassette_9_") else 0.45
		assert_true(sheet_area > minimum_area, "purpose-built sheet fills cell except its real small service cutout")
	assert_int_equal(BayCeiling.layout().size() + trims.get_child_count(), 119, "only the explicitly failed cell is empty")
	fixtures.free()
	services.free()
	root.free()

func _check_actual_ledger_surfaces_have_one_owner_at_every_junction() -> void:
	var root := BayCeiling.build()
	var ledges: Array[Dictionary] = []
	for name: String in ["PanelSupportLedgersCross", "PanelSupportLedgersLong", "BrokenEdgeFrameRail"]:
		_ledger_meshes(root.get_node("CarrierGrid/" + name), Transform3D.IDENTITY, name, ledges)
	var straight_junctions := 0
	var bowed_junctions := 0
	for first in range(ledges.size()):
		for second in range(first + 1, ledges.size()):
			var a: Dictionary = ledges[first]
			var b: Dictionary = ledges[second]
			var a_box: AABB = a.bounds
			var b_box: AABB = b.bounds
			if minf(a_box.end.x, b_box.end.x) - maxf(a_box.position.x, b_box.position.x) <= 0.000001: continue
			if minf(a_box.end.z, b_box.end.z) - maxf(a_box.position.z, b_box.position.z) <= 0.000001: continue
			if not _coplanar_horizontal_overlap(a.faces, b.faces): continue
			if a.name == "BrokenEdgeFrameRail" or b.name == "BrokenEdgeFrameRail": bowed_junctions += 1
			else: straight_junctions += 1
	print("CEILING_JUNCTIONS straight_positive_area=%d bowed_positive_area=%d coplanar_tolerance_m=0.000001" % [straight_junctions, bowed_junctions])
	assert_int_equal(straight_junctions, 0, "actual straight ledger triangles have one owner at T-grid junctions")
	assert_int_equal(bowed_junctions, 0, "actual bowed ledger triangles have one owner at both retained end junctions")
	root.free()

func _ledger_meshes(node: Node, parent_pose: Transform3D, label: String, result: Array[Dictionary]) -> void:
	var pose := parent_pose
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D: _ledger_faces((node as MeshInstance3D).mesh, pose, label, result)
	if node is MultiMeshInstance3D:
		var batch := (node as MultiMeshInstance3D).multimesh
		for index in range(batch.instance_count): _ledger_faces(batch.mesh, pose * batch.get_instance_transform(index), label, result)
	for child: Node in node.get_children(): _ledger_meshes(child, pose, label, result)

func _ledger_faces(mesh: Mesh, pose: Transform3D, label: String, result: Array[Dictionary]) -> void:
	var faces: Array[Dictionary] = []
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var count := vertices.size() if indices.is_empty() else indices.size()
		for index in range(0, count, 3):
			var a := pose * vertices[index if indices.is_empty() else indices[index]]
			var b := pose * vertices[index + 1 if indices.is_empty() else indices[index + 1]]
			var c := pose * vertices[index + 2 if indices.is_empty() else indices[index + 2]]
			if maxf(a.y, maxf(b.y, c.y)) - minf(a.y, minf(b.y, c.y)) > 0.000001: continue
			var polygon := PackedVector2Array([Vector2(a.x, a.z), Vector2(b.x, b.z), Vector2(c.x, c.z)])
			if _polygon_area(polygon) <= 0.00000001: continue
			faces.append({"y": (a.y + b.y + c.y) / 3, "polygon": polygon})
	result.append({"name": label, "bounds": pose * mesh.get_aabb(), "faces": faces})

func _coplanar_horizontal_overlap(first: Array, second: Array) -> bool:
	for a: Dictionary in first:
		for b: Dictionary in second:
			if absf(a.y - b.y) > 0.000001: continue
			for polygon: PackedVector2Array in Geometry2D.intersect_polygons(a.polygon, b.polygon):
				if _polygon_area(polygon) > 0.00000001: return true
	return false

func _polygon_area(polygon: PackedVector2Array) -> float:
	var twice_area := 0.0
	for index in range(1, polygon.size() - 1):
		twice_area += (polygon[index] - polygon[0]).cross(polygon[index + 1] - polygon[0])
	return absf(twice_area) / 2

func _check_actual_panel_undersides_rest_on_continuous_ledge_faces() -> void:
	var root := BayCeiling.build()
	var ledges: Array[AABB] = []
	for name: String in ["PanelSupportLedgersCross", "PanelSupportLedgersLong"]:
		var batch := (root.get_node("CarrierGrid/" + name) as MultiMeshInstance3D).multimesh
		for index in range(batch.instance_count):
			ledges.append(batch.get_instance_transform(index) * batch.mesh.get_aabb())
	var measured: Dictionary = {}
	for variant: StringName in [&"intact", &"sag", &"brokenedge"]:
		var body := (root.get_node("Panel_" + String(variant)) as MultiMeshInstance3D).multimesh.mesh
		var points: Array[Vector3] = []
		for edge in range(4):
			if variant == &"brokenedge" and edge == 2: continue
			for index in range(17):
				var along := lerpf(-0.95, 0.95, index / 16.0)
				var point := Vector3(-0.586 if edge == 0 else 0.586, 0, along * 0.28) if edge < 2 else Vector3(along * 0.58, 0, -0.286 if edge == 2 else 0.286)
				point.y = _underside(body, point)
				assert_float_in_range(point.y, -0.00201, -0.00199, "actual triangle at bearing strip is flat flange, not inset face")
				points.append(point)
		measured[variant] = points
	var contacts := 0
	var max_gap := 0.0
	for row: Dictionary in BayCeiling.layout():
		for local: Vector3 in measured[row.variant]:
			var point: Vector3 = row.pose * local
			var nearest := INF
			for ledge: AABB in ledges:
				if point.x < ledge.position.x or point.x > ledge.end.x or point.z < ledge.position.z or point.z > ledge.end.z: continue
				nearest = minf(nearest, absf(point.y - ledge.end.y))
			assert_true(nearest < 0.00001, "exported flange ray rests on actual ledge face at %s, gap=%s" % [point, nearest])
			max_gap = maxf(max_gap, nearest)
			contacts += 1
	assert_int_equal(contacts, 7531, "17 real mesh bearing samples on each retained side of 111 panels")
	var bent := (root.get_node("CarrierGrid/BrokenEdgeFrameRail") as MeshInstance3D).mesh
	assert_float_in_range(_underside(bent, Vector3(-1.8, 0, 1.8)), 2.94699, 2.94701, "failure lip bows 38 mm at center")
	for x: float in [-2.38, -1.22]:
		assert_float_in_range(_underside(bent, Vector3(x, 0, 1.8)), 2.98499, 2.98501, "failure lip retained ends stay flat at the original seat plane")
	var bounds := bent.get_aabb()
	var joined_ends := 0
	for ledge: AABB in ledges:
		if ledge.position.z > bounds.position.z or ledge.end.z < bounds.end.z: continue
		if absf(ledge.position.y - 2.985) > 0.000001 or absf(ledge.end.y - 2.988) > 0.000001: continue
		if absf(bounds.position.x - ledge.end.x) < 0.000001: joined_ends += 1
		if absf(bounds.end.x - ledge.position.x) < 0.000001: joined_ends += 1
	assert_int_equal(joined_ends, 2, "both flat bowed end caps butt against retained long-ledger vertical faces")
	print("CEILING_CONTACTS samples=%d max_gap_m=%s bowed_end_connections=%d" % [contacts, max_gap, joined_ends])
	root.free()

func _underside(mesh: Mesh, point: Vector3) -> float:
	var lowest := INF
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var count := vertices.size() if indices.is_empty() else indices.size()
		for index in range(0, count, 3):
			var a := vertices[index if indices.is_empty() else indices[index]]
			var b := vertices[index + 1 if indices.is_empty() else indices[index + 1]]
			var c := vertices[index + 2 if indices.is_empty() else indices[index + 2]]
			var hit: Variant = Geometry3D.segment_intersects_triangle(Vector3(point.x, -1, point.z), Vector3(point.x, 4, point.z), a, b, c)
			if hit != null: lowest = minf(lowest, hit.y)
	return lowest


func _collect_bounds(node: Node, parent_pose: Transform3D, result: Array[AABB]) -> void:
	var pose := parent_pose
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D: result.append(pose * (node as MeshInstance3D).mesh.get_aabb())
	if node is MultiMeshInstance3D:
		var batch := (node as MultiMeshInstance3D).multimesh
		for index in range(batch.instance_count): result.append(pose * batch.get_instance_transform(index) * batch.mesh.get_aabb())
	for child: Node in node.get_children(): _collect_bounds(child, pose, result)
