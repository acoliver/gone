extends SimTestCase

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
		for index: int in range(4):
			expected.append(StringName("D14-BAY/FRAME/%03d" % index))
		if flags.x == 0:
			expected.append(&"D14-BAY-DOOR/LEAF")
		for owner: String in ["D14-S-041/SHELL", "D14-S-041/SIDE-LEAF", "D14-POWER/SHELL", "D14-POWER/CONSOLE"]:
			var count: int = {"D14-S-041/SHELL": 10, "D14-S-041/SIDE-LEAF": 5, "D14-POWER/SHELL": 5, "D14-POWER/CONSOLE": 6}[owner]
			for index: int in range(count):
				expected.append(StringName("%s/%03d" % [owner, index]))
		expected.append(&"D14-POWER/GENERATOR")
		if flags.y == 0:
			expected.append(&"D14-POWER-DOOR/LEAF")
		var solids := ShipCollision.opening_solids(layout.bay().template(), bool(flags.x), bool(flags.y), layout)
		assert_int_equal(solids.size(), expected.size(), "exact S03 solid manifest")
		var set := ShipCollision.opening_set(layout.bay().template(), bool(flags.x), bool(flags.y), layout)
		for index: int in range(expected.size()):
			assert_true(solids[index].id == expected[index], "ordered owner and piece %d" % index)
			assert_true(ShipGeometry.box_aabb(solids[index]).equals(set.boxes()[index]), "manifest covers collider %d" % index)

func test_opening_counts_and_every_box_keep_original_insertion_order() -> void:
	var registry := Pods.PodRegistry.frozen()
	for flags: Vector2i in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(1, 1)]:
		var pure := ShipCollision.opening_set(registry, bool(flags.x), bool(flags.y))
		var adapter := PowerRoom.scene_collider_set(registry, bool(flags.x), bool(flags.y))
		var expected := 84 if flags.x == 0 else (82 if flags.y == 0 else 81)
		assert_int_equal(pure.size(), expected, "full scene count")
		for index: int in range(pure.size()):
			assert_true(pure.boxes()[index].equals(adapter.boxes()[index]), "same ordered collider")
	var closed := ShipCollision.opening_set(registry, false, false)
	assert_vec3_equal(closed.boxes()[0].center(), Vector3(15, -0.1, 7.7), "first bay floor")
	assert_vec3_equal(closed.boxes()[5].center(), Vector3(15, 1.2, 1.6), "pierce replaces east wall at same index")
	assert_vec3_equal(closed.boxes()[8].center(), Vector3(11.03, 0.45, 12.5), "closed bay blocker index")
	assert_vec3_equal(closed.boxes()[83].center(), Vector3(27, 1.1, -1.47), "last power leaf")

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
