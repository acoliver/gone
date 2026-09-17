extends SimTestCase
## Port of the colliders.rs inline test module.

func unit(x: float, y: float, z: float) -> ColliderSet.Aabb:
	return ColliderSet.Aabb.from_min_max(Vector3(x, y, z), Vector3(x + 1.0, y + 1.0, z + 1.0)).box

func test_inserts_are_indexed_in_order_and_round_trip() -> void:
	var colliders := ColliderSet.new()
	assert_true(colliders.is_empty(), "a new set is empty")
	var first := unit(0.0, 0.0, 0.0)
	var second := unit(5.0, 0.0, 5.0)
	assert_int_equal(colliders.insert(first), 0, "first insert gets index 0")
	assert_int_equal(colliders.insert(second), 1, "second insert gets index 1")
	assert_int_equal(colliders.size(), 2, "set holds two boxes")
	var stored: Array = colliders.boxes()
	assert_int_equal(stored.size(), 2, "boxes read back in insertion order")
	assert_true(stored[0].equals(first), "first box reads back unchanged")
	assert_true(stored[1].equals(second), "second box reads back unchanged")
	assert_vec3_equal(first.center(), Vector3(0.5, 0.5, 0.5), "center")
	assert_vec3_equal(first.half_extents(), Vector3(0.5, 0.5, 0.5), "half extents")
	assert_vec3_equal(first.min_corner(), Vector3.ZERO, "min corner")
	assert_vec3_equal(first.max_corner(), Vector3.ONE, "max corner")

func test_overlap_query_is_inclusive_and_reports_indices() -> void:
	var colliders := ColliderSet.new()
	colliders.insert(unit(0.0, 0.0, 0.0))
	colliders.insert(unit(10.0, 10.0, 10.0))
	var touching := unit(1.0, 0.0, 0.0)
	assert_true(colliders.overlapping(touching) == PackedInt32Array([0]), "face contact counts as overlap")
	var far := unit(50.0, 50.0, 50.0)
	assert_true(colliders.overlapping(far).is_empty(), "separated boxes are skipped")

func test_empty_set_overlaps_nothing() -> void:
	var colliders := ColliderSet.new()
	assert_true(colliders.overlapping(unit(0.0, 0.0, 0.0)).is_empty(), "an empty set answers every query with nothing")

func test_non_finite_geometry_is_rejected() -> void:
	var bad_center := ColliderSet.Aabb.try_new(Vector3(NAN, 0.0, 0.0), Vector3.ONE)
	assert_true(bad_center.error != null and bad_center.error.equals(ColliderSet.ColliderError.non_finite(Vector3(NAN, 0.0, 0.0))), "non-finite center rejected")
	var bad_extent := ColliderSet.Aabb.try_new(Vector3.ZERO, Vector3(1.0, INF, 1.0))
	assert_true(bad_extent.error != null and bad_extent.error.equals(ColliderSet.ColliderError.non_finite(Vector3(1.0, INF, 1.0))), "non-finite half extent rejected")
	var bad_corner := ColliderSet.Aabb.from_min_max(Vector3(NAN, NAN, NAN), Vector3.ONE)
	assert_true(bad_corner.error != null and bad_corner.error.kind == ColliderSet.ColliderError.Kind.NON_FINITE, "non-finite corner rejected")

func test_negative_half_extents_are_rejected() -> void:
	var half := Vector3(-0.1, 1.0, 1.0)
	var rejected := ColliderSet.Aabb.try_new(Vector3.ZERO, half)
	assert_true(rejected.error != null and rejected.error.equals(ColliderSet.ColliderError.negative_half_extent(half)), "negative half extent rejected")
	assert_true(ColliderSet.Aabb.try_new(Vector3.ZERO, Vector3.ZERO).is_ok(), "zero extents stay legal")

func test_inverted_corners_are_rejected_and_ordered_ones_round_trip() -> void:
	var corner_min := Vector3(2.0, 0.0, 0.0)
	var corner_max := Vector3(1.0, 1.0, 1.0)
	var rejected := ColliderSet.Aabb.from_min_max(corner_min, corner_max)
	assert_true(rejected.error != null and rejected.error.equals(ColliderSet.ColliderError.min_above_max(corner_min, corner_max)), "inverted corners rejected")
	var built := unit(1.0, 2.0, 3.0)
	var round := ColliderSet.Aabb.from_min_max(built.min_corner(), built.max_corner())
	assert_true(round.is_ok() and round.box.equals(unit(1.0, 2.0, 3.0)), "ordered corners round trip exactly")
