extends SimTestCase

const HATCH: StringName = &"D14-C-000-H-FORE"

func _context(layout: ShipLayout, id: StringName, face: int = 0) -> Doors.Context:
	var context := Doors.Context.new()
	context.face_id = layout.door(id).face_ids()[face]
	return context

func test_two_faces_share_attempts_six_tick_interpolation_and_release_once() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 0)
	var schedule := HatchResistance.schedule(0, HATCH)
	for attempt: int in range(schedule.weights.size()):
		var result := store.press(HATCH, _context(layout, HATCH, attempt % 2))
		assert_int_equal(result.outcome, Doors.Outcome.STALLED if schedule.weights[attempt] == 0 else Doors.Outcome.MOVED, "one attempt per press on either face")
		var snapshot := store.snapshot(HATCH)
		assert_int_equal(snapshot.attempt, attempt + 1, "shared attempt index")
		assert_float_equal(snapshot.target_angle, schedule.angle_after(attempt + 1), "integer work target")
		for _tick: int in range(5):
			store.tick()
		assert_int_equal(store.snapshot(HATCH).state, Doors.State.CRANKING, "no release before sixth tick")
		store.tick()
	assert_int_equal(store.snapshot(HATCH).state, Doors.State.OPENING, "final interpolation releases")
	assert_float_equal(store.snapshot(HATCH).wheel_angle, 270, "wheel rests at open angle")
	assert_int_equal(store.snapshot(HATCH).releases, 1, "one heavy release")
	for _tick: int in range(47):
		store.tick()
	assert_int_equal(store.snapshot(HATCH).state, Doors.State.OPENING, "passage stays blocked for 47 ticks")
	store.tick()
	assert_int_equal(store.snapshot(HATCH).state, Doors.State.OPEN, "new hatch swings for exactly 48 ticks")
	assert_float_equal(store.snapshot(HATCH).leaf_fraction, 1, "hinge parks at ninety degrees")
	assert_int_equal(store.press(HATCH, _context(layout, HATCH)).outcome, Doors.Outcome.NOT_APPLICABLE, "open hatch never reopens")
	assert_int_equal(store.snapshot(HATCH).releases, 1, "release never repeats")

func test_rapid_presses_retarget_from_displayed_angle_without_losing_work() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 0)
	var context := _context(layout, HATCH)
	for _press: int in range(3):
		store.press(HATCH, context)
	for _tick: int in range(3):
		store.tick()
	assert_float_equal(store.snapshot(HATCH).wheel_angle, 16.875, "halfway through first moving target")
	store.press(HATCH, context)
	assert_float_equal(store.snapshot(HATCH).wheel_angle, 16.875, "retarget starts at displayed angle")
	for _tick: int in range(6):
		store.tick()
	assert_float_equal(store.snapshot(HATCH).wheel_angle, 50.625, "fourth attempt retains all work")

func test_never_opens_bounded_jerk_shudder_and_no_progress() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 42)
	for id: StringName in [&"D13-C-000-H-FORE", &"D14-C-000-LIFT-DOOR", &"D14-S-041-SIDE-003-PORT"]:
		for _press: int in range(100):
			assert_int_equal(store.press(id, _context(layout, id)).outcome, Doors.Outcome.REFUSED, "locked door refuses")
			store.tick()
			assert_true(absf(store.snapshot(id).refusal_offset) <= 4, "jerk stays bounded under repeated presses")
		for _tick: int in range(9):
			store.tick()
		var snapshot := store.snapshot(id)
		assert_int_equal(snapshot.state, Doors.State.CLOSED, "locked forever")
		assert_int_equal(snapshot.work, 0, "no persistent wheel progress")
		assert_float_equal(snapshot.wheel_angle, 0, "no wheel rotation accumulated")
		assert_float_equal(snapshot.refusal_offset, 0, "jerk returns to rest")
		assert_float_equal(snapshot.shudder, 0, "plain leaf returns to rest")
		assert_int_equal(snapshot.releases, 0, "no release event")

func test_old_policies_exact_offsets_and_completion_ticks() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 7)
	var bay := _context(layout, ShipLayout.BAY_DOOR_ID)
	assert_int_equal(store.press(ShipLayout.BAY_DOOR_ID, bay).outcome, Doors.Outcome.NOT_APPLICABLE, "rodless press falls through")
	bay.rod_carried = true
	assert_int_equal(store.press(ShipLayout.BAY_DOOR_ID, bay).outcome, Doors.Outcome.RELEASED, "rod releases bay")
	store.press(ShipLayout.POWER_DOOR_ID, _context(layout, ShipLayout.POWER_DOOR_ID))
	for _tick: int in range(6):
		store.tick()
	assert_vec3_equal(store.snapshot(ShipLayout.BAY_DOOR_ID).offset, Vector3(0.085, 0, 0), "old half-retract")
	for _tick: int in range(18):
		store.tick()
	assert_vec3_equal(store.snapshot(ShipLayout.POWER_DOOR_ID).offset, Vector3(-0.575, 0, 0), "old half-slide")
	for _tick: int in range(23):
		store.tick()
	assert_int_equal(store.snapshot(ShipLayout.BAY_DOOR_ID).state, Doors.State.OPENING, "bay closed through tick47")
	assert_int_equal(store.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.OPENING, "power closed through tick47")
	store.tick()
	assert_int_equal(store.snapshot(ShipLayout.BAY_DOOR_ID).state, Doors.State.OPEN, "bay12+36")
	assert_int_equal(store.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.OPEN, "power48")
	assert_vec3_equal(store.snapshot(ShipLayout.BAY_DOOR_ID).offset, Vector3(0.17, 0, -1.2), "old final bay offset")

func test_event_fanout_sequences_ticks_and_snapshot_reconstruction() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 0)
	store.tick()
	store.press(HATCH, _context(layout, HATCH, 1))
	var first := store.events()
	var second := store.events()
	assert_int_equal(first.size(), 1, "one stalled event")
	assert_int_equal(second.size(), 1, "renderer cannot drain audio batch")
	assert_int_equal(first[0].sequence(), 1, "monotonic sequence")
	assert_int_equal(first[0].tick(), 1, "logical tick")
	assert_true(first[0].face_id() == layout.door(HATCH).face_ids()[1], "selected face retained")
	assert_int_equal(first[0].attempt(), 1, "attempt index")
	assert_int_equal(first[0].kind(), Doors.EventKind.CRANK_STALLED, "stalled audio event")
	store.tick()
	assert_int_equal(store.events().size(), 0, "no unbounded event history")
	var view := DoorView.build(layout.door(HATCH))
	view.present(store.snapshot(HATCH))
	assert_float_equal(view.wheel_angle(), store.snapshot(HATCH).wheel_angle + store.snapshot(HATCH).refusal_offset, "view reconstructs from snapshot only")
	view.free()

func test_swing_blockers_reachable_faces_parked_leaf_and_deck_revisions() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 0)
	var collision := ShipCollision.new(layout)
	var spec := layout.door(HATCH)
	var closed := ShipGeometry.door_blockers(spec)
	assert_int_equal(closed.size(), 2, "aperture plus swept envelope reserved before use")
	assert_int_equal(collision.revision(14), 0, "initial revision")
	for attempt: int in range(10):
		store.press(HATCH, _context(layout, HATCH, attempt % 2))
		for _tick: int in range(6):
			store.tick()
	assert_int_equal(collision.revision(14), 0, "crank never rebuilds a deck")
	for _tick: int in range(48):
		var events := store.tick()
		collision.commit(events)
	assert_int_equal(collision.revision(14), 1, "one open completion changes one deck")
	assert_int_equal(collision.revision(13), 0, "other decks unchanged")
	var parked := ShipGeometry.open_door_solids(spec)
	assert_int_equal(parked.size(), 1, "only parked leaf remains")
	var set := ColliderSet.new()
	for solid: ShipGeometry.SolidSpec in parked:
		set.insert(ShipGeometry.box_aabb(solid))
	for direction: float in [-1.0, 1.0]:
		var capsule := Resolve.Capsule.new()
		capsule.foot = spec.frame() * Vector3(0, 0.305, direction * 1.5)
		capsule.head = capsule.foot + Vector3.UP * 1.15
		var delta := spec.frame().basis * Vector3(0, 0, -direction * 3)
		var result := Resolve.resolve_motion(capsule, delta, set)
		assert_true(result.is_ok(), "open passage sweep succeeds")
		assert_close(capsule.foot + result.motion.displacement, capsule.foot + delta, "open aperture admits both directions")

func test_all_crank_faces_are_reachable_outside_reserved_swing_and_clear_ladder_paths() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var spec := layout.door(id)
		var blockers := ShipGeometry.door_blockers(spec)
		var set := ColliderSet.new()
		for solid: ShipGeometry.SolidSpec in blockers:
			set.insert(ShipGeometry.box_aabb(solid))
		for face_id: StringName in spec.face_ids():
			var face := layout.face(face_id)
			var frame := spec.frame() * face.surface_frame()
			var capsule := Resolve.Capsule.new()
			capsule.foot = frame * Vector3(0, 0.305, 1.8)
			capsule.head = capsule.foot + Vector3.UP * 1.15
			assert_true(Resolve.resolve_motion(capsule, frame.basis.z * 0.02, set).is_ok(), "wheel approach starts outside all reserved collision")
			var target := Interactions.Target.new()
			target.id = face_id
			target.policy = Interactions.Selection.FACE_RAY
			target.frame = frame
			target.center = spec.frame().origin
			target.size = spec.aperture()
			var context := Interactions.Context.new()
			context.walking = true
			context.foot = capsule.foot
			context.eye = capsule.foot + Vector3.UP * 1.295
			context.forward = -frame.basis.z
			assert_true(absf(Interactions.hit_distance(target, context, []) - 1.8) < 1e-5, "both faces reachable within 2.2m")
		var connector := layout.connector(spec.owner_id())
		var transfer := layout.well(connector.well_id()).transfer_path(14)
		var capsule := Resolve.Capsule.new()
		capsule.foot = transfer[0] + Vector3.UP * 0.305
		capsule.head = capsule.foot + Vector3.UP * 1.15
		var result := Resolve.resolve_motion(capsule, transfer[1] - transfer[0], set)
		assert_true(result.is_ok(), "swing does not embed ladder approach")
		assert_close(result.motion.displacement, transfer[1] - transfer[0], "swing cannot obstruct ladder transfer")

func test_parked_leaf_blocks_and_opening_keeps_original_blockers() -> void:
	var layout := ShipLayout.authored().layout
	var spec := layout.door(HATCH)
	var collision := ShipCollision.new(layout)
	var before := collision.deck_set(14)
	var store := Doors.Store.new(layout, 0)
	for _press: int in range(10):
		store.press(HATCH, _context(layout, HATCH))
	for _tick: int in range(6):
		collision.commit(store.tick())
	assert_true(collision.deck_set(14) == before, "opening preserves the pre-reserved blockers")
	assert_int_equal(store.press(HATCH, _context(layout, HATCH)).outcome, Doors.Outcome.NOT_APPLICABLE, "extra presses cannot overrun the finite schedule")
	var leaf := ShipGeometry.open_door_solids(spec)[0]
	var set := ColliderSet.new()
	set.insert(ShipGeometry.box_aabb(leaf))
	var capsule := Resolve.Capsule.new()
	capsule.foot = spec.frame() * Vector3(-1.4, 0.305, 0.7)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var delta := spec.frame().basis * Vector3(1.8, 0, 0)
	var result := Resolve.resolve_motion(capsule, delta, set)
	assert_true(result.is_ok(), "parked leaf collision resolves")
	assert_true(result.motion.displacement.length() < delta.length(), "parked leaf cannot be walked through")

func test_stall_keeps_prior_work_and_observers_receive_independent_records() -> void:
	var layout := ShipLayout.authored().layout
	var store := Doors.Store.new(layout, 91)
	var schedule := HatchResistance.schedule(91, HATCH)
	var work := 0
	for index: int in range(schedule.weights.size()):
		store.press(HATCH, _context(layout, HATCH))
		work += schedule.weights[index]
		assert_int_equal(store.snapshot(HATCH).work, work, "stalls retain previous integer work")
		var observer := store.events()
		assert_false(observer[-1] == store.events()[-1], "observers receive independent records")
		var snapshot := store.snapshot(HATCH)
		snapshot.work = -999
		assert_int_equal(store.snapshot(HATCH).work, work, "mutating an observer snapshot cannot change progress")
		for _tick: int in range(6):
			store.tick()
