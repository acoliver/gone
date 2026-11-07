extends SimTestCase

func test_power_room_binds_shell_and_sliding_leaf_without_replacing_console_materials() -> void:
	var game := Game.new(0)
	var room := PowerRoom.build(game)
	assert_true(room.get_node("PowerFloor").material_override == Surfaces.material(&"floor"), "power floor shares architectural material")
	assert_true(room.get_node("PowerWallNorth").get_meta(&"surface_frame").key == &"D14-POWER/PORT", "power wall has layout identity")
	var leaf: GeometryInstance3D = room.get_node("PowerDoorLeaf")
	var material := leaf.material_override
	var local := Vector3(0.2, 0.4, 0.01)
	var before := Surfaces.sample_position(leaf, Surfaces.world_frame(leaf) * local)
	room.set_door_offset(Vector3(0.75, 0, 0))
	assert_true(Surfaces.sample_position(leaf, Surfaces.world_frame(leaf) * local).is_equal_approx(before), "power leaf scan follows offset")
	assert_true(leaf.material_override == material and material == Surfaces.material(&"hatch_leaf"), "slide never allocates a material")
	room.free()

var _bay_frame := ShipLayout.authored().layout.bay_to_world()
## The emergency power room (issue #59): the room's envelope mirrors
## the stasis room's footprint behind the corridor's pierced north
## wall, the power door opens on its ungated press and slides its leaf
## aside, the console census reads exactly one working screen among the
## dead ones, the native and perceived labels change on presses only
## when they act, and the activation hands the hallway and the power
## room and bay from emergency red to dim regular white.

const DT: float = 1.0 / 60.0

func _awake_game() -> Game:
	var game := Game.new(0)
	game.phase.wake_complete()
	return game

func _stand(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	game.advance_doors()
	motion.advance(plane, game, 0.0, DT)
	for _segment: int in range(Exit.EXIT_POSE_COUNT - 1):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)

func _walk_to(motion: PlayerMotion, game: Game, plane: InputPlane,
		adapter: InputPlane.ScriptedAdapter, target: Vector2, stop_distance: float) -> bool:
	for _tick: int in range(4000):
		var foot := motion.capsule().foot
		var to_target := Vector2(target.x - foot.x, target.y - foot.z)
		if to_target.length() <= stop_distance:
			adapter.release()
			adapter.offer_tick(plane)
			game.advance_doors()
			motion.advance(plane, game, 0.0, DT)
			plane.end_frame()
			return true
		adapter.hold(1.0, 0.0)
		adapter.offer_tick(plane)
		game.advance_doors()
		motion.advance(plane, game, atan2(to_target.x, to_target.y), DT)
		plane.end_frame()
	return false

func _probe(set: ColliderSet, lo: Vector3, hi: Vector3) -> int:
	var result: ColliderSet.Result = ColliderSet.Aabb.from_min_max(lo, hi)
	assert_true(result.is_ok(), "the probe box is a valid collider box")
	return set.overlapping(result.box).size()

func test_room_envelope_mirrors_the_stasis_room() -> void:
	assert_float_in_range(PowerRoom.ROOM_START_X, 21.0 - 1e-4, 21.0 + 1e-4, "the room's west wall sits a full room-length east of the power door")
	assert_float_in_range(PowerRoom.ROOM_END_X, 33.0 - 1e-4, 33.0 + 1e-4, "the room's east wall sits a full room-length east of the power door")
	assert_float_in_range(PowerRoom.ROOM_END_X - PowerRoom.ROOM_START_X, Pods.ROOM_LENGTH - 1e-4, Pods.ROOM_LENGTH + 1e-4, "the room carries the stasis room's length")
	assert_float_in_range(PowerRoom.ROOM_START_Z - PowerRoom.ROOM_END_Z, Pods.ROOM_WIDTH - 1e-4, Pods.ROOM_WIDTH + 1e-4, "the room carries the stasis room's width")
	assert_float_in_range(PowerRoom.ROOM_START_Z, -(Hallway.HALL_WIDTH / 2.0 + Placement.WALL_THICKNESS) - 1e-4, -(Hallway.HALL_WIDTH / 2.0 + Placement.WALL_THICKNESS) + 1e-4, "the corridor's north wall band is the room's south wall")
	assert_float_in_range(PowerRoom.ROOM_CEILING, Pods.ROOM_CEILING_HEIGHT - 1e-4, Pods.ROOM_CEILING_HEIGHT + 1e-4, "the room carries the stasis room's ceiling")
	var solids := PowerRoom.room_solids()
	assert_int_equal(solids.size(), 5, "the room shell holds floor, ceiling, both side walls and far wall; hall owns the shared south wall")
	assert_vec3_equal(solids[0].center, Vector3(27.0, -0.1, -5.8), "the room floor slab's center is pinned")
	assert_vec3_equal(solids[0].size, Vector3(12.4, 0.2, 8.4), "the room floor slab tucks under the wall bands")
	assert_vec3_equal(solids[4].center, Vector3(27.0, 1.6, -9.8), "the far wall's center is pinned")
	assert_vec3_equal(Hallway.power_doorway_wall_solids()[1].center, Vector3(30.35, 1.6, -1.6), "the south gap band centers east of the corridor's pierce")
	assert_vec3_equal(Hallway.power_doorway_wall_solids()[1].size, Vector3(5.7, 3.2, 0.2), "the south gap band closes the corner the corridor leaves open")

func test_the_south_face_tiles_the_band_minus_the_aperture() -> void:
	var pierce := Hallway.power_doorway_wall_solids()
	assert_int_equal(pierce.size(), 3, "the corridor's north band carries two side pieces and a lintel")
	var volume := 0.0
	for piece: Placement.SolidPlacement in pierce:
		volume += piece.size.x * piece.size.y * piece.size.z
	var band_length: float = (PowerRoom.ROOM_END_X + Placement.WALL_THICKNESS) - Hallway.HALL_START_X
	var band_volume: float = band_length * Hallway.HALL_CEILING_HEIGHT * Placement.WALL_THICKNESS
	var aperture: float = Hallway.SIDE_DOOR_WIDTH * Hallway.SIDE_DOOR_HEIGHT * Placement.WALL_THICKNESS
	assert_float_in_range(volume + aperture, band_volume - 1e-4, band_volume + 1e-4, "the pierce pieces plus the gap band tile the south face's envelope minus exactly the power aperture")

func test_power_door_leaf_mounts_proud_of_the_corridor() -> void:
	var leaf := PowerRoom.door_leaf()
	assert_vec3_equal(leaf.center, Vector3(27.0, 1.1, -1.47), "the closed leaf centers in the power aperture")
	assert_vec3_equal(leaf.size, Vector3(1.0, 2.2, 0.06), "the leaf carries the side doors' dimensions")
	assert_float_in_range(PowerRoom.door_act_center().x, 27.0 - 1e-4, 27.0 + 1e-4, "the power door's act volume centers under the aperture")
	assert_float_in_range(PowerRoom.door_act_center().z, -0.9 - 1e-4, -0.9 + 1e-4, "the act volume stands on the corridor side")

func test_console_census_reads_exactly_one_working_screen() -> void:
	var stations := PowerRoom.console_stations()
	assert_int_equal(stations.size(), 6, "six console stations line the room's walls")
	var working := 0
	for station: PowerRoom.ConsoleStation in stations:
		if station.health == PowerRoom.CONSOLE_HEALTHS["active"]:
			working += 1
	assert_int_equal(working, 1, "exactly one console works — the rest read dead")
	assert_int_equal(stations[1].health, PowerRoom.CONSOLE_HEALTHS["active"], "the working console is the west wall's deep station")
	# Every station's panel faces into the room, off its own wall.
	assert_vec3_equal(PowerRoom.console_act_center(), Vector3(22.05, 0.0, -7.5), "the working console's act volume is pinned in front of its screen")
	assert_true(PowerRoom.console_labels(Game.ConsoleState.INACTIVE) == {
		"native": "te mu nawa lina palo",
		"perceived_es": "SISTEMA DE ENERGÍA SECUNDARIO INACTIVO",
	}, "the machine-check form of both inactive labels is pinned")
	assert_true(PowerRoom.console_labels(Game.ConsoleState.ACTIVE) == {
		"native": "te mu nawa lina shenu",
		"perceived_es": "SISTEMA DE ENERGÍA SECUNDARIO EN FUNCIONAMIENTO",
	}, "the machine-check form of both active labels is pinned")
	assert_true(PowerRoom.console_state_name(Game.ConsoleState.INACTIVE) == "inactive", "the inactive state's name is pinned")
	assert_true(PowerRoom.console_state_name(Game.ConsoleState.ACTIVE) == "active", "the active state's name is pinned")

func test_generator_hull_guards_the_room_center() -> void:
	var hull := PowerRoom.generator_solid()
	assert_vec3_equal(hull.center, Vector3(27.0, 1.3, -5.7), "the generator's hull centers on the room")
	assert_vec3_equal(hull.size, Vector3(1.6, 2.6, 1.6), "the hull is the column's conservative square")

func test_collider_sets_extend_the_hallways_both_doors() -> void:
	var registry := Pods.PodRegistry.frozen()
	var shut := PowerRoom.scene_collider_set(registry, false, false)
	var hall_open := PowerRoom.scene_collider_set(registry, true, false)
	var both_open := PowerRoom.scene_collider_set(registry, true, true)
	# Removing drawn fillers retains their existing collision reservations.
	assert_int_equal(shut.size(), 1013, "unchanged wall, frame and stop collision reservations")
	assert_int_equal(hall_open.size(), 1012, "opening the stasis doorway replaces its block and swing reservation with the parked leaf")
	assert_int_equal(both_open.size(), 1011, "opening the power door drops its leaf")
	var game := _awake_game()
	assert_int_equal(game.colliders.size(), shut.size(), "the game boots on the shut set")
	# The power aperture is solid while shut and clear once the leaf
	# slides aside, riding the same difference the walk sim crosses on.
	assert_true(_probe(shut, Vector3(26.6, 0.4, -1.5), Vector3(27.4, 2.0, -1.44)) >= 1, "the shut leaf collides inside the power aperture")
	assert_int_equal(_probe(both_open, Vector3(26.6, 0.4, -1.5), Vector3(27.4, 2.0, -1.44)), 0, "the open power doorway is clear through the aperture")
	# The room's own furniture collides in every set.
	assert_true(_probe(both_open, Vector3(26.9, 1.0, -5.9), Vector3(27.1, 2.0, -5.5)) >= 1, "the generator's hull collides")
	assert_true(_probe(both_open, Vector3(21.05, 0.5, -7.6), Vector3(21.5, 1.7, -7.4)) >= 1, "the working console's hull collides")
	assert_true(_probe(both_open, Vector3(24.3, 0.5, -9.6), Vector3(24.7, 1.7, -9.4)) >= 1, "a far-wall console's hull collides")
	assert_true(_probe(both_open, Vector3(21.1, -0.19, -9.0), Vector3(32.9, -0.01, -2.0)) >= 1, "the room floor collides")
	assert_true(_probe(both_open, Vector3(21.1, 3.21, -9.0), Vector3(32.9, 3.39, -2.0)) >= 1, "the room ceiling collides")
	assert_true(_probe(both_open, Vector3(20.9, 0.4, -9.5), Vector3(21.1, 2.0, -2.0)) >= 1, "the west wall collides")
	assert_true(_probe(both_open, Vector3(32.9, 0.4, -9.5), Vector3(33.1, 2.0, -2.0)) >= 1, "the east wall collides")
	assert_true(_probe(both_open, Vector3(24.0, 0.4, -9.9), Vector3(30.0, 2.0, -9.7)) >= 1, "the far wall collides")
	assert_true(_probe(both_open, Vector3(30.3, 0.4, -1.7), Vector3(33.1, 2.0, -1.5)) >= 1, "the south gap band collides")

func test_game_console_state_machine_activates_the_power() -> void:
	var game := _awake_game()
	assert_int_equal(game.console_state, Game.ConsoleState.INACTIVE, "the console starts labeled inactive")
	assert_false(game.power_active, "the secondary power starts down")
	assert_false(game.power_door_open, "the power doorway starts shut")
	assert_true(game.press_console(), "one press activates")
	assert_int_equal(game.console_state, Game.ConsoleState.ACTIVE, "the console shows shenu / EN FUNCIONAMIENTO")
	assert_true(game.power_active, "the activation lights the secondary power")
	assert_false(game.press_console(), "a third press never lands")
	assert_int_equal(game.console_state, Game.ConsoleState.ACTIVE, "the active console holds its state")

func test_power_door_opens_on_an_ungated_press() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	assert_false(motion.rod_carried, "this lane never touches the rod")
	var adapter := InputPlane.ScriptedAdapter.new()
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(4.3, 0.0)), 0.3), "the walk reached the stasis door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(Interactions.new(game.layout).process_id(ShipLayout.POWER_DOOR_ID, plane, game, motion), "the shut stasis door is not the power door")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the refused press stays on the channel")
	plane.end_frame()
	# The rod gate: the door test lanes carry the rod by pickup; here
	# the press is simply refused — the power door itself stays the
	# target. Walk it open through the hall on the rodless route.
	# (The stasis door needs the rod; carrying it here is the unit
	# shortcut, exactly like the hallway milestone's crossing test.)
	motion.rod_carried = true
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.BAY_DOOR_ID, plane, game, motion), "the rod-carried press opens the stasis door")
	for _tick: int in range(60):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(5.6, 0.15)), 0.15), "the walk aligned to the aperture axis")
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(7.3, 0.15)), 0.2), "the walk crossed the threshold")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -0.3), 0.3), "the walk reached the power door")
	motion.rod_carried = false
	var foot := motion.capsule().foot
	var reach := Vector2(PowerRoom.door_act_center().x - foot.x, PowerRoom.door_act_center().z - foot.z)
	assert_float_in_range(reach.length(), 0.0, Interactions.POWER_DOOR_REACH, "the stand holds the power door in reach")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.POWER_DOOR_ID, plane, game, motion), "the ungated press starts the power door")
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).releases, 1, "one press, one opening")
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.OPENING, "the leaf slides")
	for _tick: int in range(Doors.SWING_TICKS - 24):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.OPENING, "the slide runs on the tick clock")
	assert_vec3_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).offset, Vector3(-Doors.POWER_SLIDE * 0.5, 0.0, 0.0), "the leaf is half-slid at half its ticks")
	for _tick: int in range(24):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_int_equal(game.doors.snapshot(ShipLayout.POWER_DOOR_ID).state, Doors.State.OPEN, "the slide completed on the tick clock")
	assert_true(game.power_door_open, "the power doorway opened with the collider rebuild")
	assert_int_equal(game.colliders.size(), PowerRoom.scene_collider_set(game.registry, game.door_open, true).size(), "the opened set drops the leaf")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(Interactions.new(game.layout).process_id(ShipLayout.POWER_DOOR_ID, plane, game, motion), "the open power door eats no press")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the open door leaves the press on the channel")
	assert_true(motion.failure().is_empty(), motion.failure())

func test_console_presses_consume_only_when_they_act() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	# Fresh body: a press before standing at the console owns nothing.
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(Interactions.new(game.layout).process_id(&"D14-POWER-CONSOLE", plane, game, motion), "an out-of-reach press consumes nothing")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the refused press stays on the channel")
	plane.end_frame()
	var adapter := InputPlane.ScriptedAdapter.new()
	motion.rod_carried = true
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(4.3, 0.0)), 0.3), "the walk reached the stasis door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.BAY_DOOR_ID, plane, game, motion), "the door press landed")
	for _tick: int in range(60):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	# Align to the aperture axis before crossing, exactly like the lane
	# generator: the door jamb grazes any diagonal crossing.
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(5.6, 0.15)), 0.15), "the walk aligned to the aperture axis")
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(7.3, 0.15)), 0.2), "the walk crossed the threshold")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -0.5), 0.3), "the walk reached the power door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.POWER_DOOR_ID, plane, game, motion), "the power door press landed")
	for _tick: int in range(60):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_true(game.power_door_open, "the power doorway opened before the room walk")
	# Align to the power aperture's axis before crossing: the hall stand
	# can sit west of centerline and the jamb catches a diagonal entry.
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -0.8), 0.1), "the walk aligned to the power aperture axis")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -3.0), 0.3), "the walk crossed into the power room")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(22.4, -7.5), 0.2), "the walk reached the working console")
	var foot := motion.capsule().foot
	var reach := Vector2(PowerRoom.console_act_center().x - foot.x, PowerRoom.console_act_center().z - foot.z)
	assert_float_in_range(reach.length(), 0.0, Interactions.CONSOLE_ACT_REACH, "the stand holds the working console in reach")
	# A stand at a dead console owns no press: the far wall's busted one.
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(&"D14-POWER-CONSOLE", plane, game, motion), "the first press activates")
	assert_int_equal(game.console_state, Game.ConsoleState.ACTIVE, "the console reads shenu / EN FUNCIONAMIENTO")
	assert_true(game.power_active, "the secondary power lit")
	assert_int_equal(motion.console_presses, 1, "one activation press consumed, exactly")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(Interactions.new(game.layout).process_id(&"D14-POWER-CONSOLE", plane, game, motion), "a press at the active console owns nothing")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the surplus press stays on the channel")
	assert_true(motion.failure().is_empty(), motion.failure())

func test_activation_hands_both_rooms_to_regular_white() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	var room := PowerRoom.build(game)
	var stasis := Lighting.build(game)
	assert_float_in_range(stasis.level(), 0.999, 1.001, "the stasis bay's red circuit starts lit")
	assert_float_in_range(room.level(), -1e-4, 1e-4, "the power room's red fixtures start dark")
	assert_float_in_range(room.white_level(), -1e-4, 1e-4, "the power room's white strips start dead")
	assert_float_in_range(room.generator_lit(), -1e-4, 1e-4, "the generator starts dark")
	game.light_hallway()
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		hallway.process_frame(Sim.LOGICAL_TICK_SECS)
		room.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_float_in_range(hallway.level(), 0.999, 1.001, "the corridor's red settles after the flip")
	assert_float_in_range(room.level(), 0.999, 1.001, "the power room's red settles with the corridor")
	# The activation walk: both presses at the state machine.
	assert_true(game.press_console(), "the activation press lands")
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		hallway.process_frame(Sim.LOGICAL_TICK_SECS)
		room.process_frame(Sim.LOGICAL_TICK_SECS)
		stasis.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_float_in_range(hallway.level(), -1e-4, 1e-4, "the corridor's red hands off after activation")
	assert_float_in_range(hallway.white_level(), 0.999, 1.001, "the corridor's regular strips settle white")
	assert_float_in_range(room.level(), -1e-4, 1e-4, "the power room's red hands off after activation")
	assert_float_in_range(room.white_level(), 0.999, 1.001, "the power room's regular strips settle white")
	assert_float_in_range(room.generator_lit(), 0.999, 1.001, "the generator's glow settles lit")
	assert_float_in_range(stasis.level(), -1e-4, 1e-4, "the stasis bay's red hands off after activation")
	assert_float_in_range(stasis.white_level(), 0.999, 1.001, "the stasis bay settles to regular white")
	assert_true(room.native_state_text() == "shenu", "the screen renders the native active label")
	assert_true(room.perceived_state_text() == "EN FUNCIONAMIENTO", "the perception layer carries the active label")
	assert_true(room.rendered_console_state() == "active", "the room renders the active state")

func test_label_is_present_on_arrival() -> void:
	var game := _awake_game()
	var room := PowerRoom.build(game)
	assert_true(room.native_state_text() == "palo", "the arrival screen renders palo")
	assert_true(room.perceived_state_text() == "INACTIVO", "arrival perception layer carries INACTIVO")
	assert_true(room.rendered_console_state() == "inactive", "arrival state is inactive")
	room.free()

func test_surfaces_wear_the_stasis_rooms_material_instances() -> void:
	var game := _awake_game()
	var room := PowerRoom.build(game)
	var floor_piece: MeshInstance3D = room.get_node("PowerFloor")
	var ceiling_piece: MeshInstance3D = room.get_node("PowerCeiling")
	var wall_piece: MeshInstance3D = room.get_node("PowerWallWest")
	assert_true(floor_piece.material_override == RoomGeometry.floor_material(), "the power room floor wears the stasis floor material instance")
	assert_true(ceiling_piece.material_override == RoomGeometry.ceiling_material(), "the power room ceiling wears the stasis ceiling material instance")
	assert_true(wall_piece.material_override == RoomGeometry.wall_material(), "the power room walls wear the stasis wall material instance")

func test_power_room_carries_no_smoke() -> void:
	var game := _awake_game()
	var room := PowerRoom.build(game)
	var stack: Array[Node] = [room]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		assert_false(node is GPUParticles3D, "no smoke anywhere in the power room subtree")
		assert_false(node is WorldEnvironment, "the power room adds no environment of its own")
		for child in node.get_children():
			stack.append(child)

## The activation from the standing start end to end: this test walks
## the whole authored route (door, corridor, power door, console) with
## the same press discipline the lane replays, and the state machine
## lands with the colliders rebuilt and the power on.
func test_full_route_lights_the_power() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	var adapter := InputPlane.ScriptedAdapter.new()
	motion.rod_carried = true
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(4.3, 0.0)), 0.3), "the walk reached the stasis door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.BAY_DOOR_ID, plane, game, motion), "the door press landed")
	for _tick: int in range(60):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	# Align to the aperture axis before crossing, exactly like the lane
	# generator: the door jamb grazes any diagonal crossing.
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(5.6, 0.15)), 0.15), "the walk aligned to the aperture axis")
	assert_true(_walk_to(motion, game, plane, adapter, _bay(Vector2(7.3, 0.15)), 0.2), "the walk crossed the threshold")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -0.5), 0.3), "the walk reached the power door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(ShipLayout.POWER_DOOR_ID, plane, game, motion), "the power door press landed")
	for _tick: int in range(60):
		game.advance_doors()
		motion.advance(plane, game, 0.0, DT)
		plane.end_frame()
	assert_true(game.power_door_open, "the power doorway opened before the room walk")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -0.8), 0.1), "the walk aligned to the power aperture axis")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(27.0, -3.0), 0.3), "the walk crossed the power aperture")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(24.5, -4.5), 0.3), "the walk crossed to the room's center line west of the generator")
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(22.4, -7.5), 0.2), "the walk reached the working console")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(Interactions.new(game.layout).process_id(&"D14-POWER-CONSOLE", plane, game, motion), "the activation press landed")
	assert_true(game.power_active, "the secondary power is on")
	assert_true(game.door_open and game.power_door_open, "both doorways stand open")
	assert_int_equal(game.colliders.size(), PowerRoom.scene_collider_set(game.registry, true, true).size(), "the rebuilt set carries both open doorways")
	assert_true(motion.failure().is_empty(), motion.failure())

func test_rendered_power_shell_uses_pure_collision_recipe() -> void:
	var room := PowerRoom.build(Game.new(0))
	var names := ["PowerFloor", "PowerCeiling", "PowerWallWest", "PowerWallEast", "PowerWallNorth"]
	var solids := ShipGeometry.power_room_solids()
	for index: int in range(solids.size()):
		var mesh: MeshInstance3D = room.get_node(NodePath(names[index]))
		assert_vec3_equal(mesh.position, solids[index].center, "rendered power center is collider input")
		assert_vec3_equal((mesh.mesh as BoxMesh).size, solids[index].size, "rendered power size is collider input")
	room.free()

func _bay(local: Vector2) -> Vector2:
	var point := _bay_frame * Vector3(local.x, 0, local.y)
	return Vector2(point.x, point.z)
