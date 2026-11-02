extends SimTestCase

func _target(id: StringName = &"fixture") -> Interactions.Target:
	var target := Interactions.Target.new()
	target.id = id
	target.policy = Interactions.Selection.FACE_RAY
	target.frame = Transform3D.IDENTITY
	target.size = Vector2(1.2, 2.4)
	target.center = Vector3(0, 1.2, 0)
	return target

func _context() -> Interactions.Context:
	var context := Interactions.Context.new()
	context.walking = true
	context.deck = 14
	context.foot = Vector3(0, 0.305, 2)
	context.eye = Vector3(0, 1.6, 2)
	context.forward = Vector3.FORWARD
	return context

func test_face_requires_walk_deck_reach_band_front_and_facing() -> void:
	var target := _target()
	var context := _context()
	assert_float_equal(Interactions.hit_distance(target, context, []), 2.0, "ray hits the face")
	context.walking = false
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "mounted/lying cannot select")
	context = _context()
	context.deck = 13
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "wrong deck cannot select")
	context = _context()
	context.foot.z = 2.21
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "outside reach")
	context = _context()
	context.eye.y = 2.61
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "outside vertical band")
	context = _context()
	context.forward = Vector3.BACK
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "looking away")
	context.eye.z = -2
	context.foot.z = -2
	assert_float_equal(Interactions.hit_distance(target, context, []), -1.0, "back of face rejected")

func test_face_rectangle_margin_and_static_occlusion() -> void:
	var context := _context()
	context.foot.x = 0.79
	context.eye.x = 0.79
	assert_float_equal(Interactions.hit_distance(_target(), context, []), 2.0, "twenty centimeter margin")
	context.eye.x = 0.81
	assert_float_equal(Interactions.hit_distance(_target(), context, []), -1.0, "outside face rectangle")
	context = _context()
	var solids: Array[AABB] = [AABB(Vector3(-1, 0, 0.8), Vector3(2, 3, 0.2))]
	assert_float_equal(Interactions.hit_distance(_target(), context, solids), -1.0, "wall occludes the hit")

func test_equal_hits_sort_by_id() -> void:
	var targets: Array[Interactions.Target] = [_target(&"z"), _target(&"a")]
	var eligible := Interactions.eligible(targets, _context(), [])
	assert_true(eligible[0].id == &"a", "stable id breaks the tie")

func test_one_actionable_edge_and_rodless_switch_fallthrough() -> void:
	var game := Game.new(0)
	game.phase.wake_complete()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	game.advance_doors()
	motion.advance(plane, game, 0, Sim.LOGICAL_TICK_SECS)
	for _segment: int in range(4):
		game.advance_doors()
		motion.advance(plane, game, 0, Sim.LOGICAL_TICK_SECS)
	var context := _context()
	context.game = game
	context.motion = motion
	context.foot = game.layout.anchor(&"D14-HALL-SWITCH").origin
	context.eye = context.foot + Vector3.UP * 1.6
	var coordinator := Interactions.new(game.layout)
	plane.offer_press(InputPlane.Buttons.INTERACT)
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == &"D14-HALL-SWITCH", "rodless bay door falls through")
	assert_true(game.hallway_lit, "switch acts")
	assert_int_equal(plane.pending_edges(), 1, "exactly one actionable edge consumed")
	plane.end_frame()
	assert_int_equal(plane.pending_edges(), 0, "extra edges expire")

func test_fixture_cranks_through_selection_from_both_faces_and_drops_ineligible_edges() -> void:
	var game := Game.new(0)
	var motion := PlayerMotion.new()
	var coordinator := Interactions.new(game.layout)
	var plane := InputPlane.new()
	var door := game.layout.door(&"D14-C-000-H-FORE")
	for attempt: int in range(10):
		var face_id := door.face_ids()[attempt % 2]
		var frame := door.frame() * game.layout.face(face_id).surface_frame()
		var context := _fixture_context(game, motion, frame)
		context.forward = frame.basis.z
		plane.offer_press(InputPlane.Buttons.INTERACT)
		assert_true(coordinator.process(plane, context) == &"", "looking away is ineligible")
		plane.end_frame()
		context.forward = -frame.basis.z
		assert_true(coordinator.process(plane, context) == &"", "ineligible edge was dropped, not queued")
		plane.offer_press(InputPlane.Buttons.INTERACT)
		assert_true(coordinator.process(plane, context) == face_id, "new door needs no Player branch")
		assert_int_equal(game.doors.snapshot(door.id()).attempt, attempt + 1, "one selected press advances one attempt")
		plane.end_frame()
		for _tick: int in range(6):
			game.advance_doors()
	assert_int_equal(game.doors.snapshot(door.id()).state, Doors.State.OPENING, "fixture releases after seeded attempts")

func _fixture_context(game: Game, motion: PlayerMotion, frame: Transform3D) -> Interactions.Context:
	var context := Interactions.Context.new()
	context.game = game
	context.motion = motion
	context.walking = true
	context.foot = frame * Vector3(0, 0.305, 1.8)
	context.eye = context.foot + Vector3.UP * 1.295
	context.forward = -frame.basis.z
	return context

func test_existing_plain_side_door_refuses_without_self_occlusion() -> void:
	var game := Game.new(0)
	var coordinator := Interactions.new(game.layout, ShipCollision.opening_sight_solids(game.registry, game.layout))
	var door := game.layout.door(&"D14-S-041-SIDE-003-PORT")
	var frame := door.frame() * game.layout.face(door.face_ids()[0]).surface_frame()
	var context := _fixture_context(game, PlayerMotion.new(), frame)
	context.foot = frame * Vector3(0, 0.305, 1.0)
	context.eye = context.foot + Vector3.UP * 1.295
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == door.face_ids()[0], "visible side leaf receives the press")
	assert_int_equal(game.doors.events()[-1].kind(), Doors.EventKind.REFUSED, "plain-door thud event")
	game.advance_doors()
	assert_true(game.doors.snapshot(door.id()).shudder > 0, "plain leaf shudders")
	assert_float_equal(game.doors.snapshot(door.id()).wheel_angle, 0, "plain leaf has no wheel")
