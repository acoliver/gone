extends SimTestCase

func test_fnv_utf8_signed_seed_and_xorshift_vectors() -> void:
	assert_int_equal(HatchResistance.hash_bytes(""), 2166136261, "FNV offset basis")
	assert_int_equal(HatchResistance.seed_for(0, &"D14-C-000-H-FORE"), 4245312885, "seed fixture")
	assert_int_equal(HatchResistance.seed_for(-42, &"D14-C-001-H-AFT"), 3597329358, "signed decimal seed")
	var stream := HatchResistance.Stream.new(4245312885)
	for expected: int in [1127316039, 3813417755, 2193711372, 1928755708, 83706904]:
		assert_int_equal(stream.next(), expected, "xorshift 13/17/5 fixture")
	var zero := HatchResistance.Stream.new(0)
	assert_int_equal(zero.state, 0x6d2b79f5, "zero state replaced at construction")

func test_exact_schedule_and_integer_work_angles() -> void:
	var schedule := HatchResistance.schedule(0, &"D14-C-000-H-FORE")
	assert_true(schedule.weights == [0, 0, 4, 2, 5, 3, 5, 5, 4, 4], "exact stalled/moving slots")
	assert_int_equal(schedule.total_weight, 32, "integer work sum")
	assert_float_equal(schedule.angle_after(1), 0, "first press stalls")
	assert_float_equal(schedule.angle_after(3), 33.75, "third press moves by weighted share")
	assert_float_equal(schedule.angle_after(10), 270, "last press reaches release angle")

func test_corpus_category_bounds_stalls_and_seed_id_independence() -> void:
	var normal := 0
	for seed: int in range(10000):
		var schedule := HatchResistance.schedule(seed - 5000, StringName("fixture-%d" % seed))
		var n := schedule.weights.size()
		assert_true(n >= 5 and n <= 16, "attempt bounds")
		if n <= 10:
			normal += 1
		var stalls := schedule.weights.count(0)
		assert_true(stalls == 1 or stalls == 2, "one or two stalled slots")
		assert_true(schedule.weights[-1] > 0, "last attempt always moves")
		assert_float_equal(schedule.angle_after(n), 270, "every schedule opens exactly at N")
	assert_int_equal(normal, 8524, "fixed corpus category count, not a probabilistic assertion")
	var a := HatchResistance.schedule(12, &"a")
	assert_false(a.weights == HatchResistance.schedule(13, &"a").weights, "run seed separates schedules")
	assert_false(a.weights == HatchResistance.schedule(12, &"b").weights, "door id separates schedules")
	assert_true(a.weights == HatchResistance.schedule(12, &"a").weights, "render order cannot consume schedule state")
