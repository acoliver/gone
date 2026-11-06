extends SimTestCase

const Exporter := preload("res://tools/export_hatch_parts.gd")
const BASELINE := "res://art-source/hatch/hunyuan/baseline-physical.json"

func _representatives() -> Array[ShipLayout.DoorSpec]:
	var layout := ShipLayout.authored().layout
	return [layout.door(&"D14-C-001-H-FORE"), layout.door(&"D14-C-001-H-AFT")]

func test_fitting_records_are_derived_in_an_identity_portal_frame() -> void:
	var index := 0
	for source: ShipLayout.DoorSpec in _representatives():
		var expected := Exporter.variant(source, index)
		assert_true(expected.has("fit"), "export includes explicit generated-frame fitting records")
		if not expected.has("fit"): return
		for frame: Transform3D in [Transform3D.IDENTITY, Transform3D(Basis(), Vector3(7, -3, 19)), Transform3D(Basis(Vector3.UP, PI / 2), Vector3(-8, 2, 5))]:
			var placed := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), frame, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
			assert_true(Exporter.variant(placed, index) == expected, "translation/quarter-turn cannot alter local export")
		assert_int_equal(expected.fit.schema_version, 1, "explicit fit schema")
		assert_int_equal(expected.fit.ring.inner.size(), 36, "every inner station")
		assert_int_equal(expected.fit.ring.outer.size(), 36, "every outer station")
		assert_int_equal(expected.fit.hinge_stations.size(), 2, "two source-owned hinge stations")
		assert_int_equal(expected.fit.wheel_axes.size(), 2, "both wheel-local frames")
		assert_int_equal(expected.fit.leaf_faces.size(), 2, "independent asymmetric slab faces")
		assert_int_equal(expected.fit.labels.size(), 2, "both independent labels")
		for label: Dictionary in expected.fit.labels:
			assert_true(Vector2(label.size[0], label.size[1]).distance_to(Vector2(0.92, 0.46)) < 0.000001, "unchanged label size")
			assert_float_equal(label.transform.origin[1], PackedFloat32Array([1.86])[0], "unchanged native-float32 label height")
		var ring_cells := 0
		for solid: Dictionary in expected.frame_solids:
			if not "/RING/" in solid.id: continue
			var pose := HatchAsset.pose(solid.transform)
			for pair: Array in [[0, ring_cells], [1, (ring_cells + 1) % 36]]:
				var point := pose * Vector3(solid.section[pair[0]][0], solid.section[pair[0]][1], 0)
				assert_true(point.distance_to(HatchAsset.vector(expected.fit.ring.inner[pair[1]])) < 0.000001, "fit inner loop derives from reservation vertices")
			ring_cells += 1
		assert_int_equal(ring_cells, 36, "all ring reservations exported")
		assert_true(not expected.fit.required_seal_ids.is_empty(), "explicit seal-removal regions")
		index += 1

func test_physical_records_change_only_at_the_approved_ring_depth_planes() -> void:
	assert_true(FileAccess.file_exists(BASELINE), "independent pre-migration baseline exists")
	if not FileAccess.file_exists(BASELINE): return
	var baseline: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BASELINE))
	var index := 0
	for source: ShipLayout.DoorSpec in _representatives():
		var actual := Exporter.variant(source, index)
		actual.erase("fit")
		var expected: Dictionary = baseline.variants[index]
		# The driver explicitly changed bead depth, its fixed mount reach and
		# rivet seating. Check those new planes independently before comparing
		# every other byte against the untouched pre-fit physical fixture.
		for si: int in range(actual.frame_solids.size()):
			var row: Dictionary = actual.frame_solids[si]
			var old: Dictionary = expected.frame_solids[si]
			if "/RING/" in row.id or String(row.id).begins_with("HINGE/PLATE-"):
				var ring: bool = "/RING/" in row.id
				var depth := 0.022 if ring else 0.238
				var center := -0.017 if ring else 0.091
				if index == 1: center = 0.2 - center
				assert_true(absf(row.size[2] - depth) < 0.000001, "approved ring/mount depth, no other extent change")
				assert_true(absf(row.transform.origin[2] - center) < 0.000001, "approved ring/mount depth center")
				for vi: int in range(row.vertices.size()):
					assert_true(absf(absf(row.vertices[vi][2]) - depth / 2) < 0.000001, "approved real front/back vertices")
					row.vertices[vi][2] = old.vertices[vi][2]
				row.size[2] = old.size[2]
				row.transform.origin[2] = old.transform.origin[2]
			elif String(row.id).begins_with("KEEPER/"):
				assert_true(absf(row.transform.origin[2] - (-0.048 if index == 0 else 0.248)) < 0.000001, "keeper remains seated on approved bead front")
				row.transform.origin[2] = old.transform.origin[2]
		for ri: int in range(actual.frame_rivets.size()):
			var row: Dictionary = actual.frame_rivets[ri]
			var front_back: Array = [-0.026, -0.008] if index == 0 else [0.208, 0.226]
			assert_true(absf(row.transform.origin[2] - front_back[int(row.side)]) < 0.000001, "rivet seats on approved front/back plane")
			row.transform.origin[2] = expected.frame_rivets[ri].transform.origin[2]
		# Whole-object latches/wheels and the two source ribs have independent
		# dimensional/station pins in hatch_generated_parts_test. Preserve all
		# other fixture bytes, including every keeper and the wheel roots.
		var kept_actual: Array = []
		var kept_expected: Array = []
		for group: Dictionary in actual.groups:
			if String(group.path).begins_with("Rib/"): continue
			if String(group.path).begins_with("Lugs/") or group.path in ["Wheel", "ReverseWheel"]:
				var old: Dictionary = expected.groups[int(group.index)]
				# Fixture decimal parsing leaves float64 tails around 1e-17 m.
				# Both records describe native float32 poses, so compare those
				# Transform3D values exactly, without introducing a tolerance.
				assert_true(HatchAsset.pose(group.transform) == HatchAsset.pose(old.transform), "whole-object replacement preserves group roots")
				continue
			kept_actual.append(group)
		for group: Dictionary in expected.groups:
			if String(group.path).begins_with("Lugs/") or group.path in ["Wheel", "ReverseWheel"]: continue
			kept_expected.append(group)
		actual.groups = kept_actual
		expected.groups = kept_expected
		var serialized: Dictionary = JSON.parse_string(JSON.stringify(actual, "", false, true))
		assert_true(serialized == expected, "all unchanged physical IDs, poses, extents and vertices remain bit identical")
		index += 1

func test_delivered_frame_records_frozen_source_and_build_dependencies() -> void:
	var document := HatchAsset.document()
	assert_true(document.has("generated_sources") and document.has("fit_recipe"), "generated frame has complete provenance")
	if not document.has("generated_sources") or not document.has("fit_recipe"): return
	assert_int_equal(document.generated_sources.schema_version, 1, "generated source schema")
	assert_int_equal(document.fit_recipe.schema_version, 1, "fit recipe schema")
	var root := "res://art-source/hatch/hunyuan/"
	assert_true(document.generated_sources.selected == "C-s410-sv", "driver-selected frame source")
	assert_true(document.generated_sources.source_sha256 == FileAccess.get_sha256(root + "C-s410-sv.glb"), "raw generated source bytes")
	assert_true(document.generated_sources.selection_sha256 == FileAccess.get_sha256(root + "C-s410-sv-selection.json"), "source-index component selections")
	assert_true(document.generated_sources.provenance_sha256 == FileAccess.get_sha256(root + "provenance.json"), "frozen provenance")
	for name: String in document.build_dependencies:
		assert_true(document.build_dependencies[name] == FileAccess.get_sha256("res://tools/blender/" + name), "current fitting/baking dependency: " + name)
	assert_true(document.measurements.normal_method == "cycles_selected_to_active_part_isolated_fitted_source", "normal transfer from matching high-poly parts")
	for name: String in document.nodes:
		var row: Dictionary = document.nodes[name]
		if row.kind == "rivet" or (row.kind == "frame" and ("/RING/" in row.id or String(row.id).begins_with("HINGE/"))):
			assert_true(row.get("generated_source", "") == document.generated_sources.source_sha256, "source-derived frame region: " + name)
