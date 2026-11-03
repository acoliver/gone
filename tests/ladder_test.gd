extends SimTestCase

class ObstructedCollision:
	extends ShipCollision
	var obstruction := AABB()
	func well_slice(id: StringName, capsule: Resolve.Capsule, delta: Vector3) -> ShipCollision.Slice:
		var slice := super.well_slice(id, capsule, delta)
		slice.ids.append(&"test/obstruction")
		slice.colliders.insert(ColliderSet.Aabb.from_parts(obstruction.get_center(), obstruction.size / 2))
		return slice

func test_mount_rejects_embedded_landing_and_sweeps_any_accepted_approach() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var capsule := _capsule(layout, &"C-000-LADDER", 14)
	capsule.foot.y = 0.2
	capsule.head.y = 1.35
	assert_false(Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, Vector3.FORWARD).is_ok(), "embedded standing foot is not a landing pose")
	capsule = _capsule(layout, &"C-000-LADDER", 14)
	capsule.foot.x += 0.2
	capsule.head.x += 0.2
	var before := capsule.foot
	var result := Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, Vector3.FORWARD)
	assert_true(result.is_ok(), "off-center supported approach mounts")
	for _tick_index: int in range(24):
		assert_true(_tick(result.state, collision).is_ok(), "accepted start is swept to axis")
	for tick: int in range(24):
		assert_true(_tick(result.state, collision, 0, tick == 0).is_ok(), "reverse accepted path")
	assert_close(result.state.capsule().foot, before, "dismount reverses accepted approach rather than snapping to another X")

func _capsule(layout: ShipLayout, id: StringName, deck: int) -> Resolve.Capsule:
	var capsule := Resolve.Capsule.new()
	capsule.foot = layout.well(id).landing(deck).origin + Vector3.UP * 0.305
	capsule.head = capsule.foot + Vector3.UP * 1.15
	return capsule

func _tick(state: Ladder.State, collision: ShipCollision, intent: float = 0.0, space: bool = false) -> Ladder.Result:
	var result := state.step(intent, space, collision)
	state.end_tick()
	return result

func _mounted(layout: ShipLayout, collision: ShipCollision, id: StringName, deck: int) -> Ladder.State:
	var mounted := Ladder.try_mount(layout, id, deck, _capsule(layout, id, deck), Vector3.FORWARD)
	assert_true(mounted.is_ok(), "landing mounts")
	if not mounted.is_ok():
		return null
	for tick: int in range(24):
		var result := _tick(mounted.state, collision)
		assert_true(result.is_ok(), "mount sweep %d" % tick)
	assert_int_equal(mounted.state.mode(), Ladder.Mode.CLIMBING, "24th mount tick commits climbing")
	return mounted.state

func test_all_sixty_landings_mount_and_dismount_in_exactly_24_ticks() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for id: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
		for deck: int in range(1, 31):
			var start := _capsule(layout, id, deck)
			var mounted := Ladder.try_mount(layout, id, deck, start, Vector3.FORWARD)
			assert_true(mounted.is_ok(), "mount D%02d %s" % [deck, id])
			if not mounted.is_ok():
				return
			var state := mounted.state
			assert_int_equal(mounted.events[0].kind, Ladder.EventKind.MOUNT, "mount event")
			for tick: int in range(24):
				assert_true(_tick(state, collision, 1, true).is_ok(), "mount ignores climb and its Space")
				assert_int_equal(state.mode(), Ladder.Mode.MOUNTING if tick < 23 else Ladder.Mode.CLIMBING, "one mode per mount tick")
			assert_close(state.capsule().foot, Vector3(start.foot.x, start.foot.y, -4.3), "mount ends on climb axis")
			assert_close(state.capsule().head - state.capsule().foot, start.head - start.foot, "head offset preserved")
			for tick: int in range(24):
				var result := _tick(state, collision, 0, tick == 0)
				assert_true(result.is_ok(), "landing dismount sweep")
				assert_int_equal(state.mode(), Ladder.Mode.DISMOUNTING if tick < 23 else Ladder.Mode.LANDED, "24th dismount tick lands")
			assert_close(state.capsule().foot, start.foot, "returns to supported approach")
			assert_int_equal(state.landing_deck(), deck, "deck commits only at landing")

func test_every_deck_is_crossed_up_and_down_in_both_wells_without_height_drift() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
		var collision := ShipCollision.new(layout)
		var state := _mounted(layout, collision, id, 30)
		var start := state.capsule().foot
		var events: Array[int] = []
		for direction: int in [1, -1]:
			for tick: int in range(6380):
				var result := _tick(state, collision, direction)
				assert_true(result.is_ok(), "full-pitch climb sweep")
				if not result.is_ok():
					return
				for event: Ladder.Event in result.events:
					if event.kind == Ladder.EventKind.LANDING:
						events.append(event.deck)
				var expected := -88.0 + (tick + 1) * 0.025 if direction > 0 else 71.5 - (tick + 1) * 0.025
				assert_float_in_range(state.height(), expected - 1e-8, expected + 1e-8, "1.5 m/s scalar height")
				assert_float_in_range(state.capsule().foot.y, expected + 0.305 - 1e-5, expected + 0.305 + 1e-5, "capsule projects scalar height")
			var endpoint := 71.5 if direction > 0 else -88.0
			for _held: int in range(120):
				assert_true(_tick(state, collision, direction).is_ok(), "held endpoint remains mounted")
				assert_float_equal(state.height(), endpoint, "endpoint has no overshoot")
		assert_close(state.capsule().foot, start, "159.5 m out and back has no vector drift")
		var expected_events: Array[int] = []
		for deck: int in range(29, 0, -1):
			expected_events.append(deck)
		for deck: int in range(2, 31):
			expected_events.append(deck)
		assert_true(events == expected_events, "every landing crossed in order exactly once")

func test_midshaft_space_is_dropped_and_requires_a_new_landing_press() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var state := _mounted(layout, collision, &"C-000-LADDER", 14)
	for tick: int in range(220):
		assert_true(_tick(state, collision, 1, tick == 100).is_ok(), "climb through dropped Space")
	assert_int_equal(state.mode(), Ladder.Mode.CLIMBING, "midshaft press is not queued")
	assert_int_equal(state.nearest_landing(), 13, "nearest deck is presentation only")
	assert_int_equal(state.landing_deck(), 14, "no walking deck inferred during climb")
	assert_true(_tick(state, collision, 0, true).is_ok(), "fresh landing Space begins transfer")
	assert_int_equal(state.mode(), Ladder.Mode.DISMOUNTING, "explicit dismount")

func test_tiny_analog_travel_is_swept_in_bounded_signed_batches() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var state := _mounted(layout, collision, &"C-000-LADDER", 14)
	for _tick_index: int in range(10):
		assert_true(_tick(state, collision, 0.01).is_ok(), "tiny input accepted")
	assert_float_equal(state.height(), 0, "unswept travel does not move scalar height")
	assert_float_in_range(state.pending(), 0.0025 - 1e-12, 0.0025 + 1e-12, "small travel retained")
	for _tick_index: int in range(10):
		_tick(state, collision, -0.01)
	assert_float_in_range(state.pending(), -1e-12, 1e-12, "direction reversal cancels signed remainder")
	for _tick_index: int in range(1000):
		assert_true(_tick(state, collision, 0.01).is_ok(), "partial input sweep")
		assert_true(absf(state.pending()) <= 0.005, "remainder bounded by unchanged resolver tolerance")
	assert_float_in_range(state.height() + state.pending(), 0.25 - 1e-10, 0.25 + 1e-10, "no analog travel lost")

func test_partial_input_clamps_exactly_at_both_endpoints() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for deck: int in [1, 30]:
		var state := _mounted(layout, collision, &"C-001-LADDER", deck)
		var inward := -1.0 if deck == 1 else 1.0
		_tick(state, collision, inward * 0.37)
		for _tick_index: int in range(100):
			assert_true(_tick(state, collision, -inward * 0.11).is_ok(), "fractional endpoint sweep")
		assert_float_equal(state.height(), 71.5 if deck == 1 else -88.0, "fractional endpoint is exact")
		assert_float_equal(state.pending(), 0, "no outward remainder at endpoint")

func test_dismount_corrects_nearby_height_then_sweeps_to_supported_landing() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	for direction: float in [-1, 1]:
		var state := _mounted(layout, collision, &"C-000-LADDER", 14)
		for _tick_index: int in range(5):
			_tick(state, collision, direction)
		for tick: int in range(24):
			assert_true(_tick(state, collision, 0, tick == 0).is_ok(), "nearby landing correction")
		assert_int_equal(state.mode(), Ladder.Mode.LANDED, "within 0.15 m can dismount")
		assert_close(state.capsule().foot, _capsule(layout, &"C-000-LADDER", 14).foot, "exact floor restored")
	var state := _mounted(layout, collision, &"C-000-LADDER", 14)
	for _tick_index: int in range(7):
		_tick(state, collision, 1)
	_tick(state, collision, 0, true)
	assert_int_equal(state.mode(), Ladder.Mode.CLIMBING, "outside 0.15 m cannot dismount")

func test_sub_tolerance_endpoint_correction_cannot_advance_through_a_solid() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var blocked := ObstructedCollision.new(layout)
	var state := _mounted(layout, collision, &"C-000-LADDER", 1)
	_tick(state, collision, -1)
	_tick(state, collision, 0.84)
	var before := state.capsule()
	var height := state.height()
	blocked.obstruction = AABB(Vector3(2.5, before.head.y + 0.301, -4.8), Vector3(1, 0.1, 1))
	var result := state.step(0.5, false, blocked)
	assert_false(result.is_ok(), "sub-tolerance endpoint correction is swept and cannot ignore a solid")
	if result.is_ok():
		return
	assert_true(result.error.collider_id == &"test/obstruction", "tiny contact retains collider identity")
	assert_close(state.capsule().foot, before.foot, "tiny blocked endpoint leaves capsule unchanged")
	assert_float_equal(state.height(), height, "tiny blocked endpoint leaves scalar unchanged")

func test_mount_rejects_unknown_well_bad_deck_capsule_facing_and_unsupported_pose() -> void:
	var layout := ShipLayout.authored().layout
	var capsule := _capsule(layout, &"C-000-LADDER", 14)
	var before := capsule.foot
	assert_int_equal(Ladder.try_mount(layout, &"missing", 14, capsule, Vector3.FORWARD).error.kind, Ladder.LadderError.Kind.UNKNOWN_WELL, "typed unknown well")
	assert_int_equal(Ladder.try_mount(layout, &"C-000-LADDER", 0, capsule, Vector3.FORWARD).error.kind, Ladder.LadderError.Kind.INVALID_DECK, "typed bad deck")
	for facing: Vector3 in [Vector3.ZERO, Vector3.BACK, Vector3(NAN, 0, 0)]:
		assert_false(Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, facing).is_ok(), "bad facing rejected")
	assert_close(capsule.foot, before, "mount rejection never edits caller capsule")
	capsule.foot.z = -3.2
	assert_int_equal(Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, Vector3.FORWARD).error.kind, Ladder.LadderError.Kind.NOT_ON_LANDING, "unsupported mount rejected")
	capsule.foot.x = NAN
	assert_int_equal(Ladder.try_mount(layout, &"C-000-LADDER", 14, capsule, Vector3.FORWARD).error.kind, Ladder.LadderError.Kind.NON_FINITE_INPUT, "nonfinite rejected")

func test_rejected_ticks_preserve_capsule_height_pending_clock_and_events() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var state := _mounted(layout, collision, &"C-000-LADDER", 14)
	var before := state.capsule().foot
	for intent: float in [NAN, INF, 1.01, -1.01]:
		var result := state.step(intent, false, collision)
		assert_false(result.is_ok(), "invalid intent rejected")
		assert_true(result.events.is_empty(), "no rejected event")
		assert_close(state.capsule().foot, before, "rejected capsule unchanged")
	for dt: float in [0, -1, NAN, 1.0 / 30.0]:
		assert_int_equal(state.step(1, false, collision, dt).error.kind, Ladder.LadderError.Kind.INVALID_TICK, "fixed 60 Hz required")
	assert_true(state.step(1, false, collision).is_ok(), "valid step remains available")
	before = state.capsule().foot
	assert_int_equal(state.step(1, false, collision).error.kind, Ladder.LadderError.Kind.STEP_ALREADY_TAKEN, "single tick guard")
	assert_close(state.capsule().foot, before, "duplicate tick unchanged")

func test_obstructed_mount_climb_and_dismount_are_typed_atomic_errors() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ObstructedCollision.new(layout)
	var start := _capsule(layout, &"C-000-LADDER", 14)
	var state := Ladder.try_mount(layout, &"C-000-LADDER", 14, start, Vector3.FORWARD).state
	collision.obstruction = AABB(Vector3(2.5, 0, -3.25), Vector3(1, 2.5, 0.02))
	var result := state.step(0, false, collision)
	assert_false(result.is_ok(), "real solid blocks mount")
	assert_int_equal(result.error.kind, Ladder.LadderError.Kind.PATH_BLOCKED, "path error")
	assert_true(result.error.collider_id == &"test/obstruction", "offending collider id retained")
	assert_close(state.capsule().foot, start.foot, "failed mount tick is atomic")
	var clean := ShipCollision.new(layout)
	state = _mounted(layout, clean, &"C-000-LADDER", 14)
	var before := state.capsule().foot
	collision.obstruction = AABB(Vector3(2.5, before.y + 1.15 + 0.31, -4.8), Vector3(1, 0.1, 1))
	result = state.step(1, false, collision)
	assert_false(result.is_ok(), "head collision stops climb")
	assert_true(result.error.collider_id == &"test/obstruction", "head collision id")
	assert_close(state.capsule().foot, before, "climb error atomic")
	collision.obstruction = AABB(Vector3(2.5, before.y - 0.32, -4.8), Vector3(1, 0.01, 1))
	assert_false(state.step(-1, false, collision).is_ok(), "foot collision stops descent")
	assert_close(state.capsule().foot, before, "foot error atomic")
	collision.obstruction = AABB(Vector3(2.5, 0, -3.95), Vector3(1, 2.5, 0.02))
	result = state.step(0, true, collision)
	assert_false(result.is_ok(), "dismount never ignores solids")
	assert_int_equal(state.mode(), Ladder.Mode.CLIMBING, "blocked dismount does not change mode")

func test_replay_digest_includes_every_transition_and_capsule() -> void:
	var expected := "62c0f9ccf0dd7580177415c2c0ac1e9d0736dd23c97969fa4d395fa25b406bc6"
	assert_true(_digest() == expected, "pinned capsule and transition digest")
	assert_true(_digest() == expected, "second execution has identical fixed input replay")

func test_exact_transition_events_and_final_landing_tick() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var mounted := Ladder.try_mount(layout, &"C-000-LADDER", 14, _capsule(layout, &"C-000-LADDER", 14), Vector3.FORWARD)
	var events: Array[String] = ["0:%d:14" % mounted.events[0].kind]
	for tick: int in range(1, 269):
		var result := _tick(mounted.state, collision, 1 if tick > 24 and tick <= 244 else 0, tick == 245)
		assert_true(result.is_ok(), "transition schedule tick")
		for event: Ladder.Event in result.events:
			assert_true(event.well_id == &"C-000-LADDER", "events retain well identity")
			events.append("%d:%d:%d" % [tick, event.kind, event.deck])
	assert_true(events == ["0:0:14", "24:1:14", "244:2:13", "245:3:13", "268:4:13"], "mount, climb, crossing, dismount and WALK commit occur once on exact ticks")

func test_capsule_reads_are_copies_and_rejections_preserve_pending_travel() -> void:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var state := _mounted(layout, collision, &"C-000-LADDER", 14)
	_tick(state, collision, 0.1)
	var pending := state.pending()
	var before := state.capsule().foot
	var read := state.capsule()
	read.foot = Vector3.ZERO
	assert_close(state.capsule().foot, before, "capsule snapshot is not writable state")
	assert_false(state.step(INF, true, collision).is_ok(), "invalid input cannot consume remainder or Space")
	assert_float_equal(state.pending(), pending, "pending unchanged on rejected tick")
	assert_float_equal(state.height(), 0, "height unchanged on rejected tick")
	assert_int_equal(state.mode(), Ladder.Mode.CLIMBING, "mode unchanged on rejected tick")
	assert_true(state.step(0.2, false, collision).is_ok(), "valid input still sweeps accumulated travel")
	assert_float_in_range(state.height(), 0.0075 - 1e-10, 0.0075 + 1e-10, "pending consumed once")

func _digest() -> String:
	var layout := ShipLayout.authored().layout
	var collision := ShipCollision.new(layout)
	var state := _mounted(layout, collision, &"C-001-LADDER", 14)
	var trace := PackedStringArray()
	for tick: int in range(244):
		var result := _tick(state, collision, 1 if tick < 220 else 0, tick == 220)
		trace.append("%d|%d|%.12f|%s" % [tick, state.mode(), state.height(), state.capsule().foot])
		for event: Ladder.Event in result.events:
			trace.append("%d:%s:%d" % [event.kind, event.well_id, event.deck])
	return "\n".join(trace).sha256_text()
