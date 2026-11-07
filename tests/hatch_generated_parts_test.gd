extends SimTestCase

func test_whole_latches_and_wheels_replace_primitive_subparts() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var count := 0
	var dogs := 0
	var wheels := 0
	var ribs := 0
	for group: HatchParts.Group in HatchParts.leaf(spec):
		count += group.parts.size()
		if String(group.path).begins_with("Lugs/"):
			assert_int_equal(group.parts.size(), 3, "one whole generated latch per station")
			for index: int in range(group.parts.size()):
				var part := group.parts[index]
				assert_true(String(part.id).ends_with("whole-%d" % index), "whole-object latch ID")
				assert_true(part.size.distance_to(Vector3(.206066697073493, .137948541778924, .063895721073589)) < .000001, "uniform arm-length source scale")
				dogs += 1
		if group.path in [NodePath("Wheel"), NodePath("ReverseWheel")]:
			for part: HatchParts.Part in group.parts:
				if part.shape == &"generated_wheel":
					assert_true(absf(part.radius - .3215) < .000001, "643 mm outside diameter")
					wheels += 1
		if String(group.path).begins_with("Rib/"): ribs += group.parts.size()
	# Six whole dogs replace 36 subparts; two whole wheels replace 22
	# subparts; the two retained nuts and two collider-free ribs add four parts.
	# Andrew 2026-11-06: remove ten duplicate push-side strap/neck/bolt parts,
	# move the barrels/caps to the swing face, and add four working-leaf bolts.
	# Four knuckle/cap cutouts add ten return strips; two moving caps become fixed.
	assert_int_equal(count, 235, "whole-object description with five sealing strips around the fixed hinge hardware")
	assert_int_equal(dogs, 6, "three whole latches on both faces")
	assert_int_equal(wheels, 2, "both wheels use generated geometry")
	assert_int_equal(ribs, 2, "rib split around wheel and label")
	var layout := ShipLayout.authored().layout
	assert_int_equal(ShipCollision.opening_set(layout.bay().template(), false, false, layout).size(), 1013, "no new colliders")

func test_generated_parts_have_frozen_source_provenance() -> void:
	var document := HatchAsset.document()
	assert_true(document.generated_sources.has("parts"), "whole generated hardware and repaired body provenance")
	if not document.generated_sources.has("parts"): return
	var sources: Dictionary = document.generated_sources.parts
	for key: String in ["latch", "wheel", "leaf"]:
		assert_true(sources.has(key), "frozen source " + key)
		if not sources.has(key): continue
		assert_true(FileAccess.get_sha256("res://art-source/hatch/hunyuan/parts/" + sources[key].file) == sources[key].sha256, "frozen source bytes " + key)

func test_whole_latch_stations_follow_the_solved_height_and_shared_inset() -> void:
	var spec := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var heights: Array[float] = [.40, 1.17, 1.496046]
	var center := Vector3((-.03317567414895 + .17289102292454) / 2, (-.03399497871311 + .10395356306582) / 2, -.06389572107359 / 2)
	for group: HatchParts.Group in HatchParts.leaf(spec):
		if not String(group.path).begins_with("Lugs/"): continue
		assert_int_equal(group.parts.size(), 3, "three whole stations")
		if group.parts.size() != 3: continue
		for index: int in range(3):
			var pivot := group.parts[index].transform.origin - center
			assert_true(absf(pivot.x - (1.18 - .193619)) < .000001, "same solved 193.619 mm inset")
			assert_true(absf(pivot.y - heights[index]) < .000001, "highest stop/ring-safe station below label")
			if index == 2:
				assert_true(1.63 - (pivot.y + .10395356306582) >= .03 - .000001, "whole upper latch clears unchanged label by 30 mm")

func test_cut_hub_seats_the_whole_nut_and_covers_actual_spoke_roots() -> void:
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var view := DoorView.build(ShipLayout.authored().layout.door(id))
		_check_cut_hub(view)
		view.free()

func _check_cut_hub(view: DoorView) -> void:
	for path: String in ["Wheel", "ReverseWheel"]:
		var mesh: Mesh = view.label_leaf().get_node(path).get_child(0).mesh
		var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(mesh)
		var points: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		var whole: Dictionary = parts[StringName(path + "/hub")]
		var cap: Dictionary = parts[StringName(path + "/cap")]
		var front := INF
		var spoke_front := INF
		var radius := 0.0
		for index: int in range(int(whole.row.vertex_start), int(whole.row.vertex_start + whole.row.vertex_count)):
			var point := points[index]
			var r := Vector2(point.x, point.y).length()
			front = minf(front, point.z)
			radius = maxf(radius, r)
			if r >= .097014721914355: spoke_front = minf(spoke_front, point.z)
		var nut_back := -INF
		for index: int in range(int(cap.row.vertex_start), int(cap.row.vertex_start + cap.row.vertex_count)):
			nut_back = maxf(nut_back, points[index].z)
		assert_true(absf(radius - .3215) < .000001, "actual submitted wheel diameter remains 643 mm")
		assert_true(absf(front + .021993325053357) < .000001, "one approved planar cut removes the dome")
		assert_true(absf(nut_back - front) < .000001, "whole nut back seats without a floating gap or burial")
		assert_true(spoke_front - front >= .002, "actual generated hub still covers spoke roots by at least 2 mm")

func test_six_generated_spoke_gaps_are_open_geometry() -> void:
	for id: StringName in [&"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var view := DoorView.build(ShipLayout.authored().layout.door(id))
		_check_spoke_gaps(view)
		view.free()

func _check_spoke_gaps(view: DoorView) -> void:
	for path: String in ["Wheel", "ReverseWheel"]:
		var mesh: Mesh = view.label_leaf().get_node(path).get_child(0).mesh
		var arrays := mesh.surface_get_arrays(0)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for sector: int in range(6):
			var angle := deg_to_rad(5 + sector * 60)
			var origin := Vector3(cos(angle) * .22, sin(angle) * .22, -.3)
			var hits := 0
			for index: int in range(0, indices.size(), 3):
				if Geometry3D.ray_intersects_triangle(origin, Vector3.BACK, points[indices[index]], points[indices[index + 1]], points[indices[index + 2]]) != null: hits += 1
			assert_int_equal(hits, 0, "six real open spoke gaps, not painted wedges")
