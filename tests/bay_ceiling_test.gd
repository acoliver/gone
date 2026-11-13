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
	assert_int_equal(first.size(), 113, "113 perforated panels plus six beam cassettes fill 119 cells")
	assert_int_equal(counts.get(&"intact", 0), 111, "more than 90 percent of all 120 cells retain normal intact panels")
	assert_int_equal(damaged.size(), 2, "only two adjacent panels carry localized mechanical damage")
	assert_true(damaged.has(Vector2i(4, 5)) and damaged.has(Vector2i(3, 4)), "damage stays beside the one missing tile")
	assert_true(not occupied.has(Vector2i(4, 4)), "one failed panel exposes a localized frame opening")
	assert_true(counts.get(&"intact", 0) + counts.get(&"sag", 0) + counts.get(&"brokenedge", 0) == first.size(), "only the local failure variants are installed")

func test_rendered_ceiling_supports_bounds_and_fixture_clearance() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--path", ProjectSettings.globalize_path("res://"), "-s", "tests/bay_ceiling_scene_checks.gd"], output, true)
	var text := "".join(output)
	assert_int_equal(code, 0, text)
	assert_false(text.contains("ERROR:"), text)
	assert_true(text.contains("CEILING RENDER CONTRACTS passed=5 failed=0"), text)

func _check_formed_source_cache_bounds_and_real_bearing_faces() -> void:
	var root := BayCeiling.build()
	var batches := root.get_node("CarrierGrid/PanelSupportLedgersCross")
	var count := 0
	var samples := 0
	var max_gap := 0.0
	var cache_size := BayCeiling.SeatMesh.cache_size()
	assert_int_equal(cache_size,3,"one full span mesh plus the two retained source ends; wall lamps need no ceiling cuts")
	for child: MultiMeshInstance3D in batches.get_children():
		var batch := child.multimesh
		var bounds := batch.mesh.get_aabb()
		assert_true(batch.mesh == BayCeiling.SeatMesh.span(bounds.size.x), "same length reuses exact mesh resource")
		assert_true(batch.mesh.surface_get_material(0)==SeatRailComponent.material(), "unchanged source PBR on every installed cross seat")
		assert_float_in_range(bounds.size.y,0.017999,0.018001,"18mm formed profile, not the former flat strip")
		assert_float_in_range(bounds.size.z,0.041999,0.042001,"42mm rolled envelope preserves 36mm bearing face")
		for index in range(batch.instance_count):
			var pose := batch.get_instance_transform(index)
			assert_true(pose.basis.is_equal_approx(Basis.IDENTITY),"source is never stretched to fit the ceiling")
			assert_float_in_range(pose.origin.y,2.987999,2.988001,"original bearing plane retained")
			for x: float in [-0.4,0.0,0.4]:
				for z: float in [-0.017,0.0,0.017]:
					var underside := _underside(batch.mesh,Vector3(x*bounds.size.x,0,z),-0.01)
					assert_float_in_range(underside,-0.002501,-0.002499,"nine actual sheet rays per installed span preserve 2.5mm top gauge")
					max_gap=maxf(max_gap,absf(underside+0.0025))
					samples += 1
			count += 1
	assert_int_equal(count,129,"all healthy production cross spans use the shared formed source without the old lamp-stem splits")
	assert_int_equal(samples,1161,"nine physical top-skin rays for each of 129 installed spans")
	var again := BayCeiling.build()
	assert_int_equal(BayCeiling.SeatMesh.cache_size(),cache_size,"building another ceiling adds no mesh variants")
	again.free()
	var upper := (root.get_node("CarrierGrid/SupportedCrossRails") as MultiMeshInstance3D).multimesh
	var upper_at_fault := false
	for index in range(upper.instance_count):
		var box := upper.get_instance_transform(index)*upper.mesh.get_aabb()
		if box.has_point(Vector3(-0.6,3.12,-0.6)):
			assert_float_in_range(box.size.y,0.054999,0.055001,"55mm upper carrier remains intact")
			upper_at_fault = true
	assert_true(upper_at_fault,"actual whole upper carrier above source failure")
	preload("res://tools/seat_production_dump.gd").write(root,"res://tmp/verify-stasis-wiring/seat-production/installed-meshes.json")
	print("CEILING_SOURCE spans=%d cache_variants=%d bearing_rays=%d gauge_max_error_m=%s" % [count,cache_size,samples,max_gap])
	root.free()

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
	assert_int_equal(trims.get_child_count(), 6, "only the six real beam apertures need fitted cassettes")
	assert_false(trims.has_node("Cassette_9_5") or trims.has_node("Cassette_9_6"), "wall-mounted lamps leave no phantom ceiling-stem holes")
	for trim: MultiMeshInstance3D in trims.get_children():
		var sheet_area := 0.0
		for index in range(trim.multimesh.instance_count):
			var box := trim.multimesh.get_instance_transform(index) * trim.multimesh.mesh.get_aabb()
			if box.size.y < 0.003: sheet_area += box.size.x * box.size.z
			for obstacle: AABB in obstacles:
				assert_true(not box.grow(-0.000001).intersects(obstacle), "cassette solid clears measured service housing: %s %s vs %s" % [trim.name, box, obstacle])
		assert_float_in_range(sheet_area, 0.4343, 0.4346, "beam cassette fills the cell except the 1.106 by 0.226 m aperture")
	assert_int_equal(BayCeiling.layout().size() + trims.get_child_count(), 119, "only the explicitly failed cell is empty")
	_beam_visibility_and_cassette_bearings(root, fixtures)
	fixtures.free()
	services.free()
	root.free()

func _beam_visibility_and_cassette_bearings(root: Node3D, fixtures: Node3D) -> void:
	var solids: Array[AABB] = []
	_collect_bounds(root, Transform3D.IDENTITY, solids)
	var visible := 0
	for fixture: Node in fixtures.find_children("CeilingFixture", "Node3D", true, false):
		var parts: Array[AABB] = []
		_collect_bounds(fixture, (fixture.get_parent() as Node3D).transform, parts)
		var body: AABB = parts[0]
		for part: AABB in parts.slice(1): body = body.merge(part)
		assert_float_in_range(body.size.x, 1.0999, 1.1001, "actual beam export is 1.10 m long")
		assert_float_in_range(body.size.z, 0.2199, 0.2201, "actual beam export is 0.22 m wide")
		assert_float_in_range(body.position.y, 3.0999, 3.1001, "fixture bottom retains its slab mount")
		var sight := AABB(Vector3(body.position.x, 2.8, body.position.z), Vector3(body.size.x, body.position.y - 2.8, body.size.z))
		var clear := true
		for solid: AABB in solids:
			if sight.grow(-0.00001).intersects(solid): clear = false
		assert_true(clear, "entire body, grille and lens footprint has an unobstructed upward sightline through the ceiling")
		if clear: visible += 1
	assert_int_equal(visible, 6, "all six generated fixtures remain visible through fitted apertures")
	var ledges: Array[AABB] = []
	for name: String in ["PanelSupportLedgersCross", "PanelSupportLedgersLong"]:
		_collect_bounds(root.get_node("CarrierGrid/" + name), Transform3D.IDENTITY, ledges)
	var contacts := 0
	for trim: MultiMeshInstance3D in root.get_node("ServiceCassettes").get_children():
		var parts := String(trim.name).split("_")
		var center := Vector3(-5.4 + int(parts[1]) * 1.2, 2.988, -3.3 + int(parts[2]) * 0.6)
		var sheets: Array[AABB] = []
		_collect_bounds(trim, Transform3D.IDENTITY, sheets)
		for offset: Vector3 in [Vector3(-0.586, 0, 0), Vector3(0.586, 0, 0), Vector3(0, 0, -0.286), Vector3(0, 0, 0.286)]:
			var point := center + offset
			var seated := false
			var filled := false
			for ledge: AABB in ledges:
				if ledge.grow(0.000001).has_point(point) and absf(ledge.end.y - point.y) < 0.000001: seated = true
			for sheet: AABB in sheets:
				if sheet.grow(0.000001).has_point(point) and absf(sheet.position.y - point.y) < 0.000001: filled = true
			assert_true(seated and filled, "service sheet bears on the shared frame at all four edges")
			contacts += 1
	assert_int_equal(contacts,24,"all six service cassettes retain four healthy edge bearings")
	print("CEILING_BEAM_VISIBILITY fixtures=%d unobstructed_whole_footprints=%d aperture_m=1.106x0.226 clearance_per_side_m=0.003 cassette_edge_contacts=%d" % [visible, visible, contacts])

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
		_collect_bounds(root.get_node("CarrierGrid/" + name), Transform3D.IDENTITY, ledges)
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
	assert_int_equal(contacts, 7667, "17 real mesh bearing samples on each retained side of 113 fitted panels")
	var failure := root.get_node("CarrierGrid/BrokenEdgeFrameRail") as Node3D
	assert_vec3_equal(failure.position,Vector3(-0.6,2.988,-0.6),"#110 actual source failure frame")
	var joined_ends := 0
	for child: MeshInstance3D in failure.get_children():
		var bounds := failure.transform * child.mesh.get_aabb()
		assert_float_in_range(bounds.position.y,2.96999,2.97001,"formed source returns retain 18mm depth")
		assert_float_in_range(bounds.end.y,2.98799,2.98801,"retained bearing top stays at original plane")
		assert_true(bounds.end.x < -1.098 or bounds.position.x > -0.102,"paired tears leave the actual one-metre source missing")
		for ledge: AABB in ledges:
			if ledge.position.z > -0.618 or ledge.end.z < -0.582: continue
			if absf(ledge.position.y-2.985)>0.000001: continue
			if absf(bounds.position.x-ledge.end.x)<0.000001 or absf(bounds.end.x-ledge.position.x)<0.000001: joined_ends += 1
	assert_int_equal(joined_ends,2,"clipped outer ends butt the primary long ledger, with no overlapping caps")
	print("CEILING_CONTACTS samples=%d max_gap_m=%s retained_end_connections=%d" % [contacts,max_gap,joined_ends])
	root.free()

func _underside(mesh: Mesh, point: Vector3, ray_start: float = -1.0) -> float:
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
			var hit: Variant = Geometry3D.segment_intersects_triangle(Vector3(point.x, ray_start, point.z), Vector3(point.x, 4, point.z), a, b, c)
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
