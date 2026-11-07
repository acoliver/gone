extends SimTestCase

func _player(foot: Vector3, deck: int = 14) -> Player:
	var player := Player.build(Game.new(0), null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	player.game.phase = Phase.Machine.new(Phase.Wake.STANDING)
	var capsule := Resolve.Capsule.new()
	capsule.foot = foot
	capsule.head = foot + Vector3.UP * 1.15
	player.motion.locomotion = Locomotion.start(player.game.layout, player.game.collision, deck, Walk.WalkState.start(player.game.phase, capsule).state).state
	player._look_pitch = 0
	player._look_yaw = 0
	return player

func _ticks(player: Player, count: int) -> void:
	var stepper := GameStep.new(player.game, player)
	for tick: int in range(count):
		stepper.advance()
	assert_true(player.motion.failure().is_empty(), "click motion accepted: " + player.motion.failure())

func _act(player: Player, id: StringName, ticks: int = 240, deck: int = 14) -> void:
	player.adapter.objective(ClickObjective.act(id, deck))
	_ticks(player, ticks)

func test_rod_click_walks_picks_up_once_and_cancels_marker() -> void:
	var player := _player(Vector3(15, 0.305, 8.3))
	player.rod = Rod.build()
	_act(player, &"D14-BAY-ROD")
	assert_true(player.motion.rod_carried, "clicked rod picked up after approach")
	assert_false(player.rod.visible, "presentation hides the carried rod")
	assert_true(player.motion.objectives.current == null, "act completes")
	assert_true(player.motion.capsule().foot.x < 15, "walked toward rod")
	player.rod.free()
	player.free()

func test_opening_actions_share_space_dispatch_and_fire_once() -> void:
	var fixtures := [
		[ShipLayout.BAY_DOOR_ID, Vector3(15, 0.305, 4)],
		[&"D14-HALL-SWITCH", Vector3(19, 0.305, 0)],
		[ShipLayout.POWER_DOOR_ID, Vector3(25, 0.305, 0)],
		[&"D14-POWER-CONSOLE", Vector3(24.5, 0.305, -4.5)],
	]
	for fixture: Array in fixtures:
		var player := _player(fixture[1])
		player.motion.rod_carried = true
		_act(player, fixture[0], 400)
		match fixture[0]:
			ShipLayout.BAY_DOOR_ID:
				assert_true(player.game.door_open, "click pries bay door")
				assert_int_equal(player.game.doors.snapshot(ShipLayout.BAY_DOOR_ID).releases, 1, "one pry")
			&"D14-HALL-SWITCH":
				assert_true(player.game.hallway_lit, "click flips switch")
				assert_int_equal(player.motion.hallway_switch_flips, 1, "one switch press")
			ShipLayout.POWER_DOOR_ID:
				assert_true(player.game.power_door_open, "click opens power door")
			&"D14-POWER-CONSOLE":
				assert_int_equal(player.motion.console_presses, 1, "one console press, no automatic second action")
				assert_true(player.game.power_active, "first click activates power")
				_act(player, fixture[0], 60)
				assert_int_equal(player.motion.console_presses, 1, "active console ignores second click")
				assert_true(player.game.power_active, "active console stays on")
		player.free()

func test_hatch_crank_is_one_attempt_per_click_with_auto_yaw() -> void:
	var layout := ShipLayout.authored().layout
	var door := layout.door(&"D14-C-000-H-FORE")
	var face := door.face_ids()[0]
	var frame := door.frame() * layout.face(face).surface_frame()
	var player := _player(frame * Vector3(0, 0.305, 1.8))
	player._look_yaw = PI / 2
	_act(player, face, 90)
	assert_int_equal(player.game.doors.snapshot(door.id()).attempt, 1, "one crank despite many ticks")
	assert_true(player.sim_forward().dot(-frame.basis.z) > 0.99, "yaw turns toward selected face")
	_act(player, face, 90)
	assert_int_equal(player.game.doors.snapshot(door.id()).attempt, 2, "another click cranks again")
	player.free()

func test_lift_side_and_other_deck_hatches_refuse_once() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-C-000-LIFT-DOOR", &"D14-S-041-SIDE-003-PORT", &"D13-C-000-H-FORE"]:
		var door := layout.door(id)
		var face := door.face_ids()[0]
		var frame := door.frame() * layout.face(face).surface_frame()
		var player := _player(frame * Vector3(0, 0.305, 1), door.deck_number())
		player.adapter.objective(ClickObjective.act(face, door.deck_number()))
		_ticks(player, 1)
		assert_int_equal(player.game.doors.events().size(), 1, "one refusal event for " + id)
		if not player.game.doors.events().is_empty():
			assert_int_equal(player.game.doors.events()[0].kind(), Doors.EventKind.REFUSED, "same refusal as Space")
		_ticks(player, 50)
		assert_true(player.game.doors.events().is_empty(), "no repeated refusal")
		assert_true(player.game.doors.snapshot(id).state != Doors.State.OPEN, "refusal never opens")
		player.free()

func test_other_deck_and_obstructed_clicks_do_not_replace_current_objective() -> void:
	var player := _player(Vector3(18, 0.305, 0))
	player.adapter.objective(ClickObjective.floor_point(Vector3(20, 0, 0), 14))
	_ticks(player, 1)
	_act(player, &"D13-C-000-H-FORE/FORE", 1, 13)
	assert_true(player.motion.objectives.current != null and player.motion.objectives.current.kind == ClickObjective.Kind.FLOOR, "other deck ignored")
	_act(player, &"D14-POWER-CONSOLE", 1)
	assert_true(player.motion.objectives.current != null and player.motion.objectives.current.kind == ClickObjective.Kind.FLOOR, "closed wall/door path ignored")
	player.free()

func test_keys_cancel_even_when_opposing_keys_sum_to_zero() -> void:
	var player := _player(Vector3(18, 0.305, 0))
	player.plane.offer_objective(ClickObjective.floor_point(Vector3(20, 0, 0), 14))
	_ticks(player, 1)
	player.plane.offer_movement(1, 0)
	player.plane.offer_movement(-1, 0)
	_ticks(player, 1)
	assert_true(player.motion.objectives.current == null, "any movement key takes over")
	player.free()

func test_ladder_click_mounts_and_only_level_landing_click_dismounts() -> void:
	var layout := ShipLayout.authored().layout
	var well := layout.well(&"C-000-LADDER")
	var player := _player(well.landing(14).origin + Vector3.UP * 0.305)
	_act(player, well.id(), Ladder.TRANSFER_TICKS + 1)
	assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.CLIMBING, "click mounts ladder")
	_act(player, ShipLayout.POWER_DOOR_ID, 1)
	assert_true(player.motion.mounted(), "door clicks ignored while mounted")
	_act(player, well.id(), 1, 13)
	assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.CLIMBING, "wrong landing ignored")
	_act(player, well.id(), Ladder.TRANSFER_TICKS + 1)
	assert_false(player.motion.mounted(), "level landing click dismounts like Space")
	assert_int_equal(player.motion.deck(), 14, "landing deck committed")
	player.free()

func test_wake_and_get_up_drop_objectives_without_buffering() -> void:
	var player := Player.build(Game.new(0), null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	player.adapter.objective(ClickObjective.floor_point(Vector3(15, 0, 8), 14))
	_ticks(player, 1)
	assert_true(player.motion.objectives.current == null, "wake drops objective")
	assert_int_equal(player.motion.state(), PlayerMotion.BodyState.LYING, "click does not start get-up")
	player.game.phase.wake_complete()
	player.adapter.press(InputPlane.Buttons.ACTIVATE)
	_ticks(player, 1)
	player.adapter.objective(ClickObjective.act(&"D14-BAY-ROD", 14))
	_ticks(player, 1)
	assert_true(player.motion.objectives.current == null, "get-up drops objective")
	player.free()

func test_scenario_objectives_validate_and_offer_one_tick() -> void:
	for action: Dictionary in [
		{"tick": 0, "type": "objective", "kind": "floor", "deck": 14, "point": [18, 0, 0]},
		{"tick": 0, "type": "objective", "kind": "act", "deck": 14, "target": "D14-BAY-ROD"},
	]:
		var parsed := HarnessScenario.parse(JSON.stringify({"name": "click", "actions": [action]}))
		assert_true(parsed.error.is_empty(), "valid objective parses")
		var adapter := HarnessScenario.InputAdapter.new(parsed.scenario.actions)
		assert_true(adapter.step().objective != null, "typed objective on due tick")
		assert_true(adapter.step().objective == null, "no repeat")
	for bad: Dictionary in [
		{"kind": "floor", "deck": 14, "point": [0, 0]},
		{"kind": "floor", "deck": 14, "point": [0, "bad", 0]},
		{"kind": "act", "deck": 14, "target": ""},
		{"kind": "act", "deck": 14.5, "target": "D14-BAY-ROD"},
		{"kind": "act", "deck": 31, "target": "D14-BAY-ROD"},
	]:
		bad.merge({"tick": 0, "type": "objective"})
		assert_false(HarnessScenario.parse(JSON.stringify({"name": "bad", "actions": [bad]})).error.is_empty(), "malformed objective rejected")

func test_blocked_floor_objective_slides_then_stops_without_repeating() -> void:
	var player := _player(Vector3(18, 0.305, 0))
	# The old proud leaf stopped this slide early. Aim just beyond the now
	# flat wall so the unchanged blocked-progress gate expires within 600 ticks.
	player.adapter.objective(ClickObjective.floor_point(Vector3(22, 0, 2), 14))
	_ticks(player, 600)
	assert_true(player.motion.objectives.current == null, "wall-blocked floor objective expires")
	assert_true(player.motion.capsule().foot.x > 20.0, "resolver slides along the wall past the flush side door: %s" % player.motion.capsule().foot)
	assert_true(player.motion.capsule().foot.z < 1.5, "no tunnelling through wall")
	var stopped := player.motion.capsule().foot
	_ticks(player, 60)
	assert_close(player.motion.capsule().foot, stopped, "expired objective stays stopped")
	player.free()

func test_click_route_uses_only_objectives_after_get_up_and_replays_deterministically() -> void:
	var parsed := HarnessScenario.parse(FileAccess.get_file_as_string("res://scenarios/click-route.json"))
	assert_true(parsed.error.is_empty(), "click route parses")
	var scenario: HarnessScenario = parsed.scenario
	for action: Dictionary in scenario.actions:
		assert_true(action.type in ["objective", "look"] or (action.type == "press" and action.button == "activate"), "standing route has no movement or direct interact actions")
	var recorded: Array = []
	for run: int in range(2):
		var player := Player.build(Game.new(scenario.seed), null)
		player.scripted = true
		player.adapter = InputPlane.ScriptedAdapter.new()
		player._ready()
		player.game.wake_state.mark_ready()
		var input := HarnessScenario.InputAdapter.new(scenario.actions)
		var stepper := GameStep.new(player.game, player)
		for tick: int in range(int(scenario.beats.back().tick) + 3):
			var offered := input.step()
			for edge: Dictionary in offered.edges:
				player.adapter.press(InputPlane.Buttons.ACTIVATE)
			player.adapter.look(deg_to_rad(offered.look_deg.x), deg_to_rad(offered.look_deg.y))
			if offered.objective != null:
				player.adapter.objective(offered.objective)
			stepper.advance()
			var pose := [player.motion.eye(player.game), player.look_angles(), player.motion.rod_carried, player.game.console_state]
			if run == 0:
				recorded.append(pose)
			else:
				assert_true(recorded[tick] == pose, "same objective input has identical accepted pose/state at tick %d" % tick)
		assert_true(player.motion.rod_carried and player.game.door_open and player.game.hallway_lit and player.game.power_door_open and player.game.power_active, "click route completes opening")
		assert_int_equal(player.motion.console_presses, 1, "exactly one console click")
		player.free()

func test_picker_resolves_layout_targets_and_stops_at_shared_solids() -> void:
	var fixtures := [
		[&"D14-BAY-ROD", Vector3(15, 0.305, 8.3), Vector3(13.45, 0.04, 8.3)],
		[ShipLayout.BAY_DOOR_ID, Vector3(15, 0.305, 4), Vector3(15, 1.2, 1.7)],
		[&"D14-HALL-SWITCH", Vector3(18, 0.305, 0), Vector3(16.2, 1.25, 1.45)],
		[ShipLayout.POWER_DOOR_ID, Vector3(25, 0.305, 0), Vector3(27, 1.2, -1.5)],
		[&"D14-POWER-CONSOLE", Vector3(24.5, 0.305, -4.5), Vector3(22.05, 1.1, -7.5)],
		[&"C-000-LADDER", Vector3(3, 0.305, -2.9), Vector3(3, 1.2, -4.3)],
	]
	for fixture: Array in fixtures:
		var player := _player(fixture[1])
		var origin := player.motion.eye(player.game)
		var objective := ClickPicker.pick(origin, (Vector3(fixture[2]) - origin).normalized(), player.game, player.motion, player.interactions)
		assert_true(objective != null and objective.kind == ClickObjective.Kind.ACT and objective.target_id == fixture[0], "ray selects " + String(fixture[0]))
		player.free()
	var layout := ShipLayout.authored().layout
	for id: StringName in [&"D14-C-000-H-FORE", &"D14-S-041-SIDE-003-PORT", &"D14-C-000-LIFT-DOOR"]:
		var door := layout.door(id)
		var face := door.face_ids()[0]
		var frame := door.frame() * layout.face(face).surface_frame()
		var rig := _player(frame * Vector3(0, 0.305, 1.8))
		var ray := (frame * Vector3(0, 1.2, 0) - rig.motion.eye(rig.game)).normalized()
		var selected := ClickPicker.pick(rig.motion.eye(rig.game), ray, rig.game, rig.motion, rig.interactions)
		assert_true(selected != null and selected.target_id == face, "face ray picks " + String(id))
		rig.free()
	var player := _player(Vector3(18, 0.305, 0))
	var origin := player.motion.eye(player.game)
	var objective := ClickPicker.pick(origin, (Vector3(18, 0, 4) - origin).normalized(), player.game, player.motion, player.interactions)
	assert_true(objective == null, "wall blocks hidden floor")
	objective = ClickPicker.pick(origin, Vector3.UP, player.game, player.motion, player.interactions)
	assert_true(objective == null, "ceiling is not a floor objective")
	player.free()

func test_ladder_picker_only_accepts_the_level_landing_doorway() -> void:
	var layout := ShipLayout.authored().layout
	var well := layout.well(&"C-000-LADDER")
	var player := _player(well.landing(14).origin + Vector3.UP * 0.305)
	_act(player, well.id(), Ladder.TRANSFER_TICKS + 1)
	var origin := player.motion.eye(player.game)
	var objective := ClickPicker.pick(origin, Vector3.BACK, player.game, player.motion, player.interactions)
	assert_true(objective != null and objective.target_id == well.id() and objective.deck == 14, "level doorway offers dismount")
	assert_true(ClickPicker.pick(origin, Vector3.FORWARD, player.game, player.motion, player.interactions) == null, "click on ladder while mounted ignored")
	player.adapter.climb(1)
	_ticks(player, 1)
	for tick: int in range(40):
		player.adapter.climb(1)
		_ticks(player, 1)
	origin = player.motion.eye(player.game)
	assert_true(ClickPicker.pick(origin, Vector3.BACK, player.game, player.motion, player.interactions) == null, "midshaft doorway click ignored")
	player.free()

func test_scripted_near_switch_click_cannot_act_through_bay_wall() -> void:
	var player := _player(Vector3(16.2, 0.305, 2.2))
	_act(player, &"D14-HALL-SWITCH", 1)
	assert_false(player.game.hallway_lit, "bay wall blocks nearby scripted switch click")
	assert_int_equal(player.motion.hallway_switch_flips, 0, "blocked click performs no action")
	assert_true(player.motion.objectives.current == null, "zero-distance approach is refused at admission")
	player.free()

func test_scripted_near_switch_click_succeeds_without_wall() -> void:
	var player := _player(Vector3(16.2, 0.305, 0.7))
	_act(player, &"D14-HALL-SWITCH", 1)
	assert_true(player.game.hallway_lit, "unobstructed nearby scripted switch click succeeds")
	assert_int_equal(player.motion.hallway_switch_flips, 1, "one nearby switch action")
	assert_true(player.motion.objectives.current == null, "nearby action completes without walking")
	player.free()

func test_active_click_rechecks_visibility_before_attempt() -> void:
	var player := _player(Vector3(16.2, 0.305, 2.2))
	# An admitted objective must still be checked against the accepted current pose.
	player.motion.objectives.set_objective(ClickObjective.act(&"D14-HALL-SWITCH", 14))
	_ticks(player, 1)
	assert_false(player.game.hallway_lit, "active objective cannot attempt through a wall")
	assert_int_equal(player.motion.hallway_switch_flips, 0, "no action after visibility is lost")
	player.free()

func test_space_legacy_switch_proximity_still_falls_through_rodless_bay_door() -> void:
	var player := _player(Vector3(16.2, 0.305, 2.2))
	player.adapter.press(InputPlane.Buttons.INTERACT)
	_ticks(player, 1)
	assert_true(player.game.hallway_lit, "Space retains legacy proximity through switch fallthrough")
	assert_int_equal(player.motion.hallway_switch_flips, 1, "rodless bay door does not consume Space")
	assert_false(player.game.door_open, "bay door still requires rod")
	player.free()

func test_space_and_click_ladder_selection_parity_for_both_wells() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.well_ids():
		for deck: int in [1, 13, 14, 15, 30]:
			for offset: float in [-0.3, 0.0, 0.3]:
				var well := layout.well(id)
				var player := _player(well.landing(deck).origin + Vector3(offset, 0.305, 0), deck)
				var eye := player.motion.eye(player.game)
				var direction := (well.climb_line().origin + Vector3(0, layout.floor_y(deck) + 1.2, 0) - eye).normalized()
				var space := player.motion.mount_target(layout, direction)
				var click := ClickPicker.pick(eye, direction, player.game, player.motion, player.interactions)
				assert_true(space == id, "Space selects well %s D%d offset %s" % [id, deck, offset])
				assert_true(click != null and click.target_id == space and click.deck == deck, "click and Space select the same ladder")
				player.free()

func test_ladder_dismount_picker_follows_layout_doorway_frame() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.well_ids():
		var well := layout.well(id)
		var player := _player(well.landing(14).origin + Vector3.UP * 0.305)
		_act(player, id, Ladder.TRANSFER_TICKS + 1)
		var connector_id := ShipLayout.connector_id(14, 0 if id == &"C-000-LADDER" else 1)
		var connector := player.game.layout.connector(connector_id)
		var frame := player.game.layout.ladder_doorway_frame(id, 14)
		assert_true(frame == connector.port_opening(), "doorway frame is the connector's layout opening")
		# Moving the authored doorway must move the pick rectangle, not leave a world-Z copy.
		connector._port_opening.origin += Vector3(2, 0, -0.5)
		frame = player.game.layout.ladder_doorway_frame(id, 14)
		assert_true(frame == connector.port_opening(), "doorway frame follows layout placement")
		var eye := player.motion.eye(player.game)
		var direction := (frame * Vector3(0, 1.2, 0) - eye).normalized()
		var click := ClickPicker.pick(eye, direction, player.game, player.motion, player.interactions)
		assert_true(click != null and click.target_id == id, "dismount picks layout-derived doorway")
		player.free()

func test_ladder_targets_share_one_factory() -> void:
	var player := _player(Vector3(3, 0.305, -2.9))
	for id: StringName in player.game.layout.well_ids():
		for deck: int in [1, 14, 30]:
			var shared := Interactions.ladder_target(player.game.layout, id, deck)
			var click := player.interactions.target_for(id, deck, Vector3.ZERO)
			var doorway := player.game.layout.ladder_doorway_frame(id, deck)
			assert_true(shared.id == id and shared.kind == Interactions.Kind.LADDER and shared.deck == deck, "shared ladder identity")
			assert_true(shared.frame.basis == doorway.basis and shared.center.y == doorway.origin.y, "ladder interaction follows layout frame")
			assert_true(click.frame == shared.frame and click.center == shared.center and click.size == shared.size, "click consumes shared ladder geometry")
			var exit := Interactions.ladder_target(player.game.layout, id, deck, true)
			assert_true(exit.frame.origin == doorway.origin and exit.frame.basis.z == -doorway.basis.z, "dismount targets opposite side of layout doorway")
	player.free()

func test_requested_dispatch_rechecks_visibility_at_accepted_pose() -> void:
	var player := _player(Vector3(16.2, 0.305, 2.2))
	player.plane.offer_press(InputPlane.Buttons.INTERACT)
	var selected := player.interactions.process(player.plane, Interactions.context_for(player.game, player.motion), &"D14-HALL-SWITCH")
	assert_true(selected == &"", "requested click dispatch is refused behind bay wall")
	assert_false(player.game.hallway_lit, "queued action cannot bypass final visibility check")
	assert_int_equal(player.motion.hallway_switch_flips, 0, "no through-wall action at dispatch")
	player.free()
