extends SimTestCase

class CountedCollision:
	extends ShipCollision
	var deck_queries := 0
	func deck_set(deck: int) -> ColliderSet:
		deck_queries += 1
		return super.deck_set(deck)

func test_unchanged_well_slice_reuses_assembly_but_not_caller_mutation() -> void:
	var collision := CountedCollision.new(ShipLayout.authored().layout)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(3, 0.305, -4.3)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var first := collision.well_slice(&"C-000-LADDER", capsule, Vector3.UP * 0.025)
	var expected := first.ids.duplicate()
	first.ids.append(&"test/private")
	first.colliders.insert(ColliderSet.Aabb.from_parts(Vector3(3, 1, -4.3), Vector3.ONE))
	collision.deck_queries = 0
	var second := collision.well_slice(&"C-000-LADDER", capsule, Vector3.UP * 0.020)
	assert_int_equal(collision.deck_queries, 0, "same selected decks and revisions reuse the sorted slice assembly")
	assert_true(second.ids == expected, "caller's slice IDs stay private")
	assert_int_equal(second.colliders.size(), expected.size(), "caller cannot add a collider to the cached template")
	collision.open_door(&"D14-C-000-H-AFT")
	var opened := collision.well_slice(&"C-000-LADDER", capsule, Vector3.UP * 0.025)
	assert_true(&"D14-C-000-H-AFT/PARKED" in opened.ids and &"D14-C-000-H-AFT/BLOCKER" not in opened.ids, "opening invalidates the reused slice")

func test_well_slice_includes_adjacent_floor_for_head_and_foot_with_stable_ids() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(3, 4.0, -4.3)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var slice := collision.well_slice(&"C-000-LADDER", capsule, Vector3.UP * 0.1)
	assert_true(&"D13-C-000/LANDING/FLOOR/000" in slice.ids, "head selects adjacent floor before foot crosses it")
	assert_true(&"D14-C-000/LANDING/CEILING/000" not in slice.ids, "nonintersecting vertical slice stays absent")
	capsule.foot.y = 5.81
	capsule.head.y = 6.96
	slice = collision.well_slice(&"C-000-LADDER", capsule, Vector3.DOWN * 0.02)
	assert_true(&"D13-C-000/LANDING/FLOOR/000" in slice.ids, "descending foot includes floor")
	var seen: Dictionary = {}
	for id: StringName in slice.ids:
		assert_false(seen.has(id), "shared solid ids deduplicated")
		seen[id] = true
	var sorted := slice.ids.duplicate()
	sorted.sort()
	assert_true(sorted == slice.ids, "stable collider tie order")
	assert_int_equal(slice.ids.size(), slice.colliders.size(), "slice ids identify resolver contacts")
	assert_int_equal(collision.cached_deck_count(), 1, "only intersected deck lazily constructed")

func test_real_landing_slabs_hit_head_and_foot_but_leave_climb_lane_open() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for id: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
		for deck: int in [1, 14, 30]:
			var floor_y: float = (14 - deck) * 5.5
			var x := layout.well(id).landing(deck).origin.x
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(x, floor_y + 1.5, -2.9)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var slice := collision.well_slice(id, capsule, Vector3.UP)
			var result := Resolve.resolve_motion(capsule, Vector3.UP, slice.colliders)
			assert_true(result.is_ok(), "head sweep valid")
			assert_true(result.motion.displacement.y < 1.0, "landing ceiling catches head")
			capsule.foot.y = floor_y + 0.5
			capsule.head.y = floor_y + 1.65
			slice = collision.well_slice(id, capsule, Vector3.DOWN)
			result = Resolve.resolve_motion(capsule, Vector3.DOWN, slice.colliders)
			assert_true(result.is_ok(), "foot sweep valid")
			assert_true(result.motion.displacement.y > -1.0, "landing floor catches foot")
			capsule.foot = Vector3(x, floor_y + 0.305, -4.3)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			slice = collision.well_slice(id, capsule, Vector3.UP * 0.025)
			result = Resolve.resolve_motion(capsule, Vector3.UP * 0.025, slice.colliders)
			assert_true(result.is_ok(), "shaft cut clears capsule")
			assert_float_in_range(result.motion.displacement.y, 0.025 - 1e-5, 0.025 + 1e-5, "no floor spans climb lane")

func test_continuous_well_walls_and_endpoint_closures_have_no_pitch_gaps() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for id: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
		for deck: int in range(2, 31):
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(layout.well(id).climb_line().origin.x, (14 - deck) * 5.5 + 4.0, -4.3)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			for delta: Vector3 in [Vector3(2, 0, 0), Vector3(-2, 0, 0), Vector3(0, 0, -2)]:
				var slice := collision.well_slice(id, capsule, delta)
				var result := Resolve.resolve_motion(capsule, delta, slice.colliders)
				assert_true(result.is_ok(), "gap-height wall sweep")
				assert_true(result.motion.displacement.length() < 2.0, "full pitch walls prevent sideways escape")
		var solids := ShipGeometry.well_solids(layout.well(id))
		assert_int_equal(solids.size(), 5, "two sides, back, top and bottom closures")
		var ids: Array[StringName] = []
		for solid: ShipGeometry.SolidSpec in solids:
			ids.append(solid.id)
		assert_true(StringName("%s/TOP" % id) in ids and StringName("%s/BOTTOM" % id) in ids, "endpoint closures authored")

func test_well_slices_are_identical_with_cold_or_warm_deck_caches() -> void:
	var layout := ShipLayout.authored().layout
	var cold := ShipCollision.new(layout)
	var warm := ShipCollision.new(layout)
	for deck: int in range(1, 31):
		warm.deck_set(deck)
	for id: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
		for deck: int in range(1, 31):
			var capsule := Resolve.Capsule.new()
			capsule.foot = layout.well(id).climb_line().origin + Vector3.UP * ((14 - deck) * 5.5 + 0.305)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var a := cold.well_slice(id, capsule, Vector3.UP * 0.025)
			var b := warm.well_slice(id, capsule, Vector3.UP * 0.025)
			assert_true(a.ids == b.ids, "presentation-independent lazy partition membership")
			for index: int in range(a.ids.size()):
				assert_true(a.colliders.boxes()[index].equals(b.colliders.boxes()[index]), "cache order cannot alter collision geometry")
	cold.open_door(&"D14-C-000-H-AFT")
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(3, 0.305, -4.3)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var slice := cold.well_slice(&"C-000-LADDER", capsule, Vector3.UP * 0.025)
	assert_false(&"D14-C-000-H-AFT/BLOCKER" in slice.ids, "well query observes latest deck blocker revision")
	assert_true(&"D14-C-000-H-AFT/PARKED" in slice.ids, "well query retains parked leaf")

func test_every_other_deck_hatch_and_lift_contains_walkers() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for deck: int in range(1, 31):
		if deck == 14:
			continue
		var y: float = (14 - deck) * 5.5
		for fixture: Vector2 in [Vector2(0, 1), Vector2(6, -1), Vector2(30, 1), Vector2(36, -1), Vector2(3, 0), Vector2(33, 0)]:
			var capsule := Resolve.Capsule.new()
			capsule.foot = Vector3(fixture.x + fixture.y * 2, y + 0.305, 0)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			var delta := Vector3(-fixture.y * 4, 0, 0) if fixture.y != 0 else Vector3(0, 0, 3)
			var result := Resolve.resolve_motion(capsule, delta, collision.deck_set(deck))
			assert_true(result.is_ok(), "remote closed-door sweep")
			assert_true(result.motion.displacement.length() < delta.length(), "locked hatch/lift contains on every remote deck")

func test_opening_manifest_has_exact_owners_order_and_door_differentials() -> void:
	var layout := ShipLayout.authored().layout
	for flags: Vector2i in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1)]:
		var expected: Array[StringName] = []
		for index: int in range(5):
			expected.append(StringName("D14-BAY/SHELL/%03d" % index))
		if flags.x == 0:
			expected.append(&"D14-BAY-DOOR/BLOCKER")
		var pod_counts := [6, 7, 6, 7, 6, 7, 6]
		for pod: int in range(7):
			for piece: int in range(pod_counts[pod]):
				expected.append(StringName("D14-BAY/POD-%03d/%03d" % [pod, piece]))
		for piece: String in ["FRAME/LEFT", "FRAME/RIGHT", "FRAME/TOP", "COAMING", "FRAME/STOP-LEFT", "FRAME/STOP-RIGHT", "FRAME/STOP-TOP", "FRAME/STOP-BOTTOM"]:
			expected.append(StringName("D14-BAY-DOOR/%s" % piece))
		expected.append_array(_surround_ids("D14-BAY-DOOR", "FORE"))
		# Round 11 adds named presentation reservations, with no added colliders.
		expected.append_array(_fixed_detail_ids("D14-BAY-DOOR"))
		expected.append(&"D14-BAY-DOOR/SWING" if flags.x == 0 else &"D14-BAY-DOOR/PARKED")
		for owner: String in ["D14-S-041/SHELL", "D14-S-041/SIDE-LEAF", "D14-POWER/SHELL", "D14-POWER/CONSOLE"]:
			var count: int = {"D14-S-041/SHELL": 12, "D14-S-041/SIDE-LEAF": 5, "D14-POWER/SHELL": 5, "D14-POWER/CONSOLE": 6}[owner]
			for index: int in range(count):
				expected.append(StringName("%s/%03d" % [owner, index]))
		expected.append(&"D14-POWER/GENERATOR")
		if flags.y == 0:
			expected.append(&"D14-POWER-DOOR/LEAF")
		expected.append_array(_extension_ids())
		var solids := ShipCollision.opening_solids(layout.bay().template(), bool(flags.x), bool(flags.y), layout)
		assert_int_equal(solids.size(), expected.size(), "exact D14 solid manifest")
		var set := ShipCollision.opening_set(layout.bay().template(), bool(flags.x), bool(flags.y), layout)
		var offset := 0
		for index: int in range(expected.size()):
			assert_true(solids[index].id == expected[index], "ordered owner and piece %d" % index)
			for box: ColliderSet.Aabb in ShipGeometry.collision_boxes(solids[index]):
				assert_true(box.equals(set.boxes()[offset]), "manifest covers ordered collider %d" % offset)
				offset += 1
		assert_int_equal(offset, set.size(), "manifest covers every subdivided collider exactly once")

func test_opening_counts_and_every_box_keep_original_insertion_order() -> void:
	var registry := Pods.PodRegistry.frozen()
	for flags: Vector2i in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1)]:
		var pure := ShipCollision.opening_set(registry, bool(flags.x), bool(flags.y))
		var adapter := PowerRoom.scene_collider_set(registry, bool(flags.x), bool(flags.y))
		# Four corner infills on each of the seven D14 hinged hatches.
		var expected := 1013 if flags.x == 0 else (1012 if flags.y == 0 else 1011)
		assert_int_equal(pure.size(), expected, "full scene count")
		for index: int in range(pure.size()):
			assert_true(pure.boxes()[index].equals(adapter.boxes()[index]), "same ordered collider")
	var closed := ShipCollision.opening_set(registry, false, false)
	assert_vec3_equal(closed.boxes()[0].center(), Vector3(15, -0.1, 7.7), "first bay floor")
	assert_vec3_equal(closed.boxes()[5].center(), Vector3(15, 1.2, 1.6), "pierce replaces east wall at same index")
	assert_vec3_equal(closed.boxes()[8].center(), Vector3(11.03, 0.45, 12.5), "closed bay blocker index")
	assert_vec3_equal(closed.boxes()[198].center(), Vector3(27, 1.1, -1.47), "power leaf follows the bay frame and four new wall-pocket corner skins")

func test_approved_layout_cache_and_blocker_revisions_are_deck_local() -> void:
	var collision := ShipCollision.new(ShipLayout.authored().layout)
	assert_int_equal(collision.cached_deck_count(), 0, "lazy construction")
	var remote := collision.deck_set(13)
	var before := collision.deck_set(14)
	assert_int_equal(collision.cached_deck_count(), 2, "only requested decks built")
	assert_true(collision.deck_set(14) == before, "cached assembled set reused")
	var before_ids := collision.solid_ids(14)
	assert_true(&"D14-C-000-H-AFT/BLOCKER" in before_ids, "closed aperture present")
	collision.open_door(&"D14-C-000-H-AFT")
	assert_int_equal(collision.revision(14), 1, "one deck revision")
	assert_int_equal(collision.revision(13), 0, "remote revision unchanged")
	var after := collision.deck_set(14)
	assert_false(after == before, "changed deck assembled once")
	assert_true(collision.deck_set(14) == after, "new assembled set reused")
	assert_true(collision.deck_set(13) == remote, "remote cache untouched")
	assert_false(&"D14-C-000-H-AFT/BLOCKER" in collision.solid_ids(14), "open aperture removed")
	assert_true(&"D14-C-000-H-FORE/BLOCKER" in collision.solid_ids(14), "other hatch remains closed")
	collision.open_door(&"D14-C-000-H-AFT")
	assert_int_equal(collision.revision(14), 1, "duplicate completion does not rebuild")

func test_approved_solids_have_unique_ordered_ids_and_no_scene_dependency() -> void:
	var collision := ShipCollision.new(ShipLayout.authored().layout)
	for deck: int in [1, 14, 30]:
		var ids := collision.solid_ids(deck)
		var seen: Dictionary = {}
		for id: StringName in ids:
			assert_false(seen.has(id), "solid owner and piece unique")
			seen[id] = true
		var sorted := ids.duplicate()
		sorted.sort_custom(func(a: StringName, b: StringName) -> bool: return String(a) < String(b))
		assert_true(ids == sorted, "stable owner and local piece order")
		assert_int_equal(ids.size(), collision.deck_set(deck).size(), "manifest covers every collider")
	var ids := collision.solid_ids(14)
	ids.clear()
	assert_false(collision.solid_ids(14).is_empty(), "manifest read is a copy")

func test_remote_connectors_stay_sealed_at_endpoint_decks() -> void:
	var collision := ShipCollision.new(ShipLayout.authored().layout)
	for fixture: Vector2 in [Vector2(1, 71.5), Vector2(30, -88)]:
		var set := collision.deck_set(int(fixture.x))
		var y := fixture.y
		for x: float in [0.0, 6.0, 30.0, 36.0]:
			var query := ColliderSet.Aabb.try_new(Vector3(x + 0.1, y + 1.2, 0), Vector3(0.05, 0.5, 0.3)).box
			assert_true(set.overlapping(query).size() > 0, "remote hatch blocks passage")

func _extension_ids() -> Array[StringName]:
	var ids: Array[StringName] = []
	for section: String in ["D14-S-040", "D14-S-042"]:
		for surface: String in ["FLOOR/000", "CEILING/000", "PORT/000", "STARBOARD/000"]:
			ids.append(StringName("%s/%s" % [section, surface]))
		for station: int in [3, 9, 15]:
			for side: String in ["PORT", "STARBOARD"]:
				ids.append(StringName("%s-SIDE-%03d-%s/LEAF" % [section, station, side]))
	for connector: String in ["D14-C-000", "D14-C-001"]:
		for surface: String in ["FLOOR/000", "CEILING/000", "PORT/000", "PORT/001", "PORT/002", "STARBOARD/000", "STARBOARD/001", "STARBOARD/002", "LANDING/FLOOR/000", "LANDING/CEILING/000", "LANDING/PORT/000", "LANDING/STARBOARD/000", "LANDING/BACK/000"]:
			ids.append(StringName("%s/%s" % [connector, surface]))
		for surface: String in ["SIDE--1/000", "SIDE-1/000", "BACK/000", "FLOOR/000", "CEILING/000"]:
			ids.append(StringName("%s-LIFT/%s" % [connector, surface]))
	var hatches: Array[String] = ["D14-C-000-H-AFT", "D14-C-000-H-FORE", "D14-C-001-H-AFT", "D14-C-001-H-FORE", "D14-C-002-H-FORE", "D14-C-M001-H-AFT"]
	for hatch: String in hatches:
		for surface: String in ["WALL/000", "WALL/001", "WALL/002", "WALL/POCKET/000", "WALL/POCKET/001", "WALL/POCKET/002", "WALL/POCKET/003", "FRAME/LEFT", "FRAME/RIGHT", "FRAME/TOP", "COAMING", "FRAME/STOP-LEFT", "FRAME/STOP-RIGHT", "FRAME/STOP-TOP", "FRAME/STOP-BOTTOM"]:
			ids.append(StringName("%s/%s" % [hatch, surface]))
		ids.append_array(_surround_ids(hatch, "FORE" if hatch.ends_with("FORE") else "AFT"))
		ids.append_array(_fixed_detail_ids(hatch))
	for door: String in ["D14-C-000-H-AFT", "D14-C-000-H-FORE", "D14-C-000-LIFT-DOOR", "D14-C-001-H-AFT", "D14-C-001-H-FORE", "D14-C-001-LIFT-DOOR", "D14-C-002-H-FORE", "D14-C-M001-H-AFT"]:
		ids.append(StringName("%s/BLOCKER" % door))
		if not "LIFT" in door:
			ids.append(StringName("%s/SWING" % door))
	return ids

func _fixed_detail_ids(hatch: String) -> Array[StringName]:
	var ids: Array[StringName] = []
	# Andrew's 2026-11-06 full-height hinge leaves use separate upper bridges.
	# Name both new reservations in order; they add no collision boxes.
	for piece: String in ["HINGE/PLATE-0", "HINGE/BRIDGE-0", "HINGE/KNUCKLE-0", "HINGE/PLATE-1", "HINGE/BRIDGE-1", "HINGE/KNUCKLE-1", "KEEPER/0", "KEEPER/1", "KEEPER/2"]:
		ids.append(StringName("%s/%s" % [hatch, piece]))
	return ids

func _surround_ids(hatch: String, side: String) -> Array[StringName]:
	var ids: Array[StringName] = []
	for ring: String in ["RING", "LIP", "THROAT"]:
		for cell: int in range(36): ids.append(StringName("%s/SURROUND/%s/%s/%03d" % [hatch, side, ring, cell]))
	ids.append(StringName("%s/SURROUND/%s/STEP/000" % [hatch, side]))
	return ids
