extends HarnessRoute
## Shared real-input journey for guarded tests and windowed captures.

var crossings: Array[int] = []
var digest_lines: PackedStringArray = []

func step(offered: Array = []) -> void:
	super.step(offered)
	for event: Ladder.Event in player.motion.ladder_events:
		digest_lines.append("%d:%s:%d:%d" % [tick, event.well_id, event.kind, event.deck])
		if event.kind == Ladder.EventKind.LANDING:
			crossings.append(event.deck)
			var state := player.motion.locomotion.ladder_state()
			var pose := player.motion.capsule()
			var well := player.game.layout.well(event.well_id)
			assert(absf(state.height() - player.game.layout.floor_y(event.deck)) < 0.02501, "every crossed landing height")
			assert(absf(pose.foot.y - player.game.layout.floor_y(event.deck) - 0.385) < 0.02502, "capsule height at every crossed landing")
			assert(absf(pose.foot.x - well.climb_line().origin.x) < 1e-5 and absf(pose.foot.z - well.climb_line().origin.z) < 1e-5, "every crossed landing stays on climb axis")
	for event: Doors.Event in player.game.doors.events():
		digest_lines.append("%d:%s:%d:%d" % [tick, event.door_id(), event.kind(), event.attempt()])
	assert(player.position.distance_to(player.motion.eye(player.game)) < 1e-5, "real camera rig follows accepted capsule")

func opening() -> void:
	var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	replay_prefix(scenario.actions, int(scenario.beats.back().tick) + 2)
	assert(player.game.power_active and player.motion.rod_carried and player.game.bay_exited, "opening through real input")

func open_hatch(id: StringName, approach: Vector3, destination: Vector3) -> void:
	walk_to(approach)
	look_at(player.game.layout.door(id).frame().origin)
	var count := HatchResistance.schedule(player.game.run_seed, id).weights.size()
	for _attempt: int in range(count):
		press()
		hold(6)
	hold(48)
	assert(player.game.doors.snapshot(id).state == Doors.State.OPEN, "D14 hatch opens with exact seeded attempts")
	walk_to(destination)

func enter_well(index: int) -> void:
	if index == 1:
		walk_to(Vector3(27, 0, 0))
		open_hatch(&"D14-C-001-H-FORE", Vector3(28.2, 0, 0), Vector3(33, 0, 0))
		open_hatch(&"D14-C-001-H-AFT", Vector3(33.9, 0, 0), Vector3(38, 0, 0))
		walk_to(Vector3(33, 0, 0))
	else:
		walk_to(Vector3(8, 0, 0))
		open_hatch(&"D14-C-000-H-AFT", Vector3(7.8, 0, 0), Vector3(3, 0, 0))
		open_hatch(&"D14-C-000-H-FORE", Vector3(2.1, 0, 0), Vector3(-2, 0, 0))
		walk_to(Vector3(3, 0, 0))
	var well := player.game.layout.well(StringName("C-%03d-LADDER" % index))
	walk_to(Vector3(well.landing(14).origin.x, 0, -0.5))
	walk_to(well.landing(14).origin)
	mount()

func mount() -> void:
	var foot := player.motion.capsule().foot
	look_at(foot + Vector3(0, 0, -2))
	press()
	assert(player.motion.locomotion.mode() == Locomotion.Mode.MOUNTING, "fresh Space mounts")
	hold(24)
	assert(player.motion.locomotion.mode() == Locomotion.Mode.CLIMBING, "mount press cannot also dismount")

func climb_to(deck: int, capture_mid: bool = false) -> void:
	crossings.clear()
	var state := player.motion.locomotion.ladder_state()
	var initial := state.nearest_landing()
	var direction := signf(player.game.layout.floor_y(deck) - state.height())
	super.climb_to(deck, capture_mid)
	var expected: Array[int] = []
	for d: int in range(initial - int(direction), deck - int(direction), -int(direction)):
		expected.append(d)
	assert(crossings == expected, "ordered evidence for every landing crossed: %s != %s" % [crossings, expected])
	assert(absf(state.height() - player.game.layout.floor_y(deck)) < 1e-8, "exact destination height")
	if deck in [1, 30]:
		for _tick: int in range(12):
			step([{"type": "climb", "value": direction}])
		assert(absf(state.height() - player.game.layout.floor_y(deck)) < 1e-8, "held outward input never overshoots endpoint")

func dismount(deck: int) -> void:
	press()
	hold(23)
	assert(player.motion.locomotion.mode() == Locomotion.Mode.WALK, "Space commits WALK after swept transfer")
	assert(player.motion.locomotion.deck() == deck, "deck commits only on landing")
	assert(absf(player.motion.capsule().foot.y - player.game.layout.floor_y(deck) - 0.385) < 0.00002, "standing foot at destination landing")

func refusals(index: int, deck: int) -> void:
	var layout := player.game.layout
	var spec := layout.connector(ShipLayout.connector_id(deck, index))
	var center := spec.bounds().get_center()
	walk_to(Vector3(spec.port_opening().origin.x, center.y, -1.2))
	walk_to(Vector3(center.x, center.y, -1.2))
	walk_to(Vector3(center.x, center.y, 0))
	var ids := spec.hatch_ids()
	ids.append(layout.lift(spec.lift_id()).door_id())
	for id: StringName in ids:
		var door := layout.door(id)
		if door.kind() == ShipLayout.DoorKind.HATCH:
			var toward := signf(center.x - door.frame().origin.x)
			walk_to(door.frame().origin + Vector3(toward * 1.7, 0, 0))
		else:
			walk_to(Vector3(center.x, center.y, 0))
		look_at(door.frame().origin)
		var before := player.game.doors.snapshot(id).attempt
		press()
		var after := player.game.doors.snapshot(id)
		assert(after.attempt == before + 1 and after.state == Doors.State.CLOSED and after.work == 0, "real selected endpoint door refuses: %s" % id)
	walk_to(Vector3(center.x, center.y, 0))
	walk_to(Vector3(center.x, center.y, -1.2))
	walk_to(Vector3(spec.port_opening().origin.x, center.y, -1.2))
	walk_to(layout.well(spec.well_id()).landing(deck).origin)

func trip(index: int) -> void:
	enter_well(index)
	climb_to(13)
	dismount(13)
	mount()
	climb_to(1)
	dismount(1)
	refusals(index, 1)
	mount()
	climb_to(15)
	dismount(15)
	mount()
	climb_to(30)
	dismount(30)
	refusals(index, 30)
	mount()
	climb_to(14)
	dismount(14)
	var spec := player.game.layout.connector(ShipLayout.connector_id(14, index))
	walk_to(Vector3(spec.port_opening().origin.x, 0, -0.5))
	walk_to(Vector3(spec.bounds().get_center().x, 0, 0))
	walk_to(Vector3(27 if index == 1 else 8, 0, 0))
