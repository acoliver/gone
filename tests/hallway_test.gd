extends SimTestCase
## The hallway behind the door (the #59 prerequisite milestone): the
## corridor's envelope derives from the room's authored constants (twice
## the room's length, the aisle's width, the room's ceiling), the
## doorway pierces the east wall's exact envelope with the hatch's
## aperture, the collider sets extend the walk sim's with the door shut
## and the doorway cleared when open, the hall's surfaces wear the
## stasis room's shared material instances, the red fixtures hold zero
## until the beside-door switch's exactly-once flip, settle to the
## stasis bay's levels, and hold their lit level steady without
## blinking, the closed side doors collide, and the subtree carries no
## smoke.

const DT: float = 1.0 / 60.0

func _awake_game() -> Game:
	var game := Game.new()
	game.phase.wake_complete()
	return game

func _stand(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	for _segment: int in range(Exit.EXIT_POSE_COUNT - 1):
		motion.advance(plane, game, 0.0, DT)

func _walk_to(motion: PlayerMotion, game: Game, plane: InputPlane,
		adapter: InputPlane.ScriptedAdapter, target: Vector2, stop_distance: float) -> bool:
	for _tick: int in range(4000):
		var foot := motion.capsule().foot
		var to_target := Vector2(target.x - foot.x, target.y - foot.z)
		if to_target.length() <= stop_distance:
			adapter.release()
			adapter.offer_tick(plane)
			motion.advance(plane, game, 0.0, DT)
			plane.end_frame()
			return true
		adapter.hold(1.0, 0.0)
		adapter.offer_tick(plane)
		motion.advance(plane, game, atan2(to_target.x, to_target.y), DT)
		plane.end_frame()
	return false

func _probe(set: ColliderSet, lo: Vector3, hi: Vector3) -> int:
	var result: ColliderSet.Result = ColliderSet.Aabb.from_min_max(lo, hi)
	assert_true(result.is_ok(), "the probe box is a valid collider box")
	return set.overlapping(result.box).size()

func test_envelope_derives_from_the_room_constants() -> void:
	assert_float_in_range(Hallway.HALL_LENGTH, Pods.ROOM_LENGTH * 2.0 - 1e-4, Pods.ROOM_LENGTH * 2.0 + 1e-4, "the corridor runs twice the stasis room's length")
	assert_float_in_range(Hallway.HALL_WIDTH, Pods.AISLE_HALF_WIDTH * 2.0 - 1e-4, Pods.AISLE_HALF_WIDTH * 2.0 + 1e-4, "the corridor carries the pod bay's aisle width through the doorway")
	assert_float_in_range(Hallway.HALL_CEILING_HEIGHT, Pods.ROOM_CEILING_HEIGHT - 1e-4, Pods.ROOM_CEILING_HEIGHT + 1e-4, "the ceiling matches the room's height language")
	assert_float_in_range(Hallway.HALL_START_X, Pods.ROOM_LENGTH / 2.0 - 1e-4, Pods.ROOM_LENGTH / 2.0 + 1e-4, "the corridor starts at the room's east wall face")
	assert_float_in_range(Hallway.HALL_END_X, Hallway.HALL_START_X + 24.0 - 1e-4, Hallway.HALL_START_X + 24.0 + 1e-4, "the corridor's far wall sits at its authored end")
	var solids := Hallway.hallway_solids()
	assert_int_equal(solids.size(), 7, "the hall shell holds floor, ceiling, the pierced north wall's three pieces, the south wall, and the far wall")
	assert_vec3_equal(solids[0].center, Vector3(18.1, -0.1, 0.0), "the hall floor slab's center is pinned")
	assert_vec3_equal(solids[0].size, Vector3(24.2, 0.2, 3.4), "the hall floor slab tucks under the room's wall band")
	assert_vec3_equal(solids[1].center, Vector3(18.1, 3.3, 0.0), "the hall ceiling slab's center is pinned")
	assert_vec3_equal(solids[6].center, Vector3(30.1, 1.6, 0.0), "the far wall's center is pinned")
	assert_vec3_equal(solids[2].center, Vector3(16.25, 1.6, -1.6), "the north wall's west pierce piece centers on its band")
	assert_vec3_equal(solids[3].center, Vector3(28.85, 1.6, -1.6), "the north wall's east pierce piece centers on its band")
	assert_vec3_equal(solids[4].center, Vector3(27.0, 2.7, -1.6), "the north wall's lintel sits over the power aperture")
	assert_vec3_equal(solids[5].center, Vector3(18.1, 1.6, 1.6), "the south side wall's center is pinned")

func test_doorway_pierces_the_east_walls_envelope() -> void:
	var pierce := Hallway.doorway_wall_solids()
	assert_int_equal(pierce.size(), 3, "the pierce holds two side pieces and a lintel")
	var east_wall := Placement.room_shell()[Hallway.ROOM_SHELL_EAST_WALL_INDEX]
	assert_float_in_range(east_wall.center.x, Hallway.HALL_START_X + 0.1 - 1e-4, Hallway.HALL_START_X + 0.1 + 1e-4, "the pierce replaces the east wall's own band")
	var pierce_volume := 0.0
	for piece: Placement.SolidPlacement in pierce:
		pierce_volume += piece.size.x * piece.size.y * piece.size.z
	var wall_volume := east_wall.size.x * east_wall.size.y * east_wall.size.z
	var aperture_volume := Placement.WALL_THICKNESS * Hallway.DOORWAY_HEIGHT * Hallway.DOORWAY_WIDTH
	assert_float_in_range(pierce_volume + aperture_volume, wall_volume - 1e-4, wall_volume + 1e-4, "the pierce pieces tile the wall's envelope minus exactly the aperture")
	assert_float_in_range(Hallway.DOORWAY_WIDTH, Placement.HATCH_WIDTH - 1e-4, Placement.HATCH_WIDTH + 1e-4, "the aperture is the hatch's width")
	assert_float_in_range(Hallway.DOORWAY_HEIGHT, Placement.HATCH_HEIGHT - 1e-4, Placement.HATCH_HEIGHT + 1e-4, "the aperture is the hatch's height")
	assert_vec3_equal(Hallway.doorway_block().center, Vector3(6.1, 1.2, 0.0), "the closed block fills the aperture's center")
	assert_vec3_equal(Hallway.doorway_block().size, Vector3(0.2, 2.4, 1.2), "the closed block fills the aperture exactly")

func test_collider_sets_extend_the_walk_sim_open_and_shut() -> void:
	var registry := Pods.PodRegistry.frozen()
	var closed := Hallway.scene_collider_set(registry, false)
	var open := Hallway.scene_collider_set(registry, true)
	assert_int_equal(closed.size(), 72, "the closed set's box count is pinned")
	assert_int_equal(open.size(), 70, "the open set drops the doorway block and the slid-aside slab")
	var game := _awake_game()
	assert_int_equal(game.colliders.size(), PowerRoom.scene_collider_set(registry, false, false).size(), "the game boots on the closed set — the power room extends it from boot")
	# The aperture is solid while shut and clear when open: the walk
	# sim's doorway crossing rides exactly on this difference.
	var aperture_hits_shut := _probe(closed, Vector3(6.0, 0.4, -0.3), Vector3(6.2, 2.0, 0.3))
	var aperture_hits_open := _probe(open, Vector3(6.0, 0.4, -0.3), Vector3(6.2, 2.0, 0.3))
	assert_true(aperture_hits_shut >= 1, "the shut doorway collides inside the aperture")
	assert_int_equal(aperture_hits_open, 0, "the open doorway is clear through the aperture")
	# The hall's own surfaces and every closed side door collide in both
	# sets — they never move.
	assert_true(_probe(open, Vector3(29.9, 1.0, -0.2), Vector3(30.3, 2.2, 0.2)) >= 1, "the far wall collides")
	assert_true(_probe(open, Vector3(14.5, 0.5, 1.42), Vector3(15.5, 1.9, 1.52)) >= 1, "a south side door collides")
	assert_true(_probe(open, Vector3(20.5, 0.5, -1.52), Vector3(21.5, 1.9, -1.42)) >= 1, "a north side door collides")
	assert_true(_probe(open, Vector3(6.1, -0.19, 0.0), Vector3(30.0, -0.01, 0.5)) >= 1, "the hall floor collides")
	assert_true(_probe(open, Vector3(6.1, 3.21, 0.0), Vector3(30.0, 3.39, 0.5)) >= 1, "the hall ceiling collides")
	assert_true(_probe(open, Vector3(10.0, 0.4, 1.5), Vector3(11.0, 2.0, 1.7)) >= 1, "the south hall wall collides")
	assert_true(_probe(open, Vector3(26.4, 1.0, -1.7), Vector3(26.6, 2.0, -1.5)) >= 1, "the north wall's west pierce piece collides beside the power aperture")
	assert_true(_probe(open, Vector3(27.5, 2.5, -1.7), Vector3(27.6, 3.1, -1.5)) >= 1, "the power aperture's lintel collides above the doorway")
	assert_int_equal(Hallway.side_door_solids().size(), 6, "six side doors: the power room's leaf is the PowerRoom module's own")

func test_surfaces_wear_the_stasis_rooms_material_instances() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	var floor_piece: MeshInstance3D = hallway.get_node("HallFloor")
	var ceiling_piece: MeshInstance3D = hallway.get_node("HallCeiling")
	var wall_piece: MeshInstance3D = hallway.get_node("HallWallNorthWest")
	var doorway_wall: MeshInstance3D = hallway.get_node("DoorwayWall").get_child(0)
	assert_true(floor_piece.material_override == RoomGeometry.floor_material(), "the hall floor wears the stasis floor material instance")
	assert_true(ceiling_piece.material_override == RoomGeometry.ceiling_material(), "the hall ceiling wears the stasis ceiling material instance")
	assert_true(wall_piece.material_override == RoomGeometry.wall_material(), "the hall walls wear the stasis wall material instance")
	assert_true(doorway_wall.material_override == RoomGeometry.wall_material(), "the pierced east wall wears the stasis wall material instance")

func test_switch_plate_sits_beside_the_doorway() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	var switch_group: Node3D = hallway.get_node("HallSwitch")
	assert_vec3_equal(switch_group.position, Hallway.SWITCH_PLATE_CENTER, "the switch plate sits at its authored center")
	var pierce_face_x: float = Hallway.HALL_START_X + Hallway.WALL
	assert_float_in_range(Hallway.SWITCH_PLATE_CENTER.x,
		pierce_face_x + Hallway.SWITCH_PLATE_SIZE.x / 2.0 - 1e-4,
		pierce_face_x + Hallway.SWITCH_PLATE_SIZE.x / 2.0 + 1e-4,
		"the plate mounts proud of the pierced wall's hall face")
	assert_float_in_range(Hallway.SWITCH_PLATE_CENTER.y, 1.25 - 1e-4, 1.25 + 1e-4, "the plate centers at working height")
	assert_float_in_range(Hallway.SWITCH_PLATE_CENTER.z, 0.85 - 1e-4, 0.85 + 1e-4, "the plate sits on the latch side of the aperture, next to the door")
	var latch_side: float = absf(Hallway.SWITCH_PLATE_CENTER.z)
	assert_float_in_range(latch_side,
		Hallway.DOORWAY_WIDTH / 2.0 + Hallway.SWITCH_PLATE_SIZE.z / 2.0,
		Pods.ROOM_WIDTH / 2.0 - Hallway.SWITCH_PLATE_SIZE.z / 2.0,
		"the plate sits clear of the aperture, inside the wall piece")
	var plate: MeshInstance3D = switch_group.get_node("Plate")
	var dome: MeshInstance3D = switch_group.get_node("Dome")
	assert_true(plate != null and dome != null, "the switch carries a plate and a domed button")
	assert_float_in_range(dome.position.x,
		Hallway.SWITCH_PLATE_SIZE.x / 2.0 + Hallway.SWITCH_DOME_RADIUS * 0.55 - 1e-4,
		Hallway.SWITCH_PLATE_SIZE.x / 2.0 + Hallway.SWITCH_DOME_RADIUS * 0.55 + 1e-4,
		"the dome stands proud of the plate into the hall")
	var dome_material := dome.material_override as StandardMaterial3D
	assert_true(dome_material != null, "the dome carries a standard material")
	assert_true(dome_material.albedo_color == Hallway.SWITCH_DOME_COLOR, "the dome reads the fuel-stop red")
	assert_false(dome_material.emission_enabled, "the dome does not glow before the flip: the dark hides it")
	assert_float_in_range(Hallway.switch_act_center().x, Hallway.SWITCH_PLATE_CENTER.x - 1e-4, Hallway.SWITCH_PLATE_CENTER.x + 1e-4, "the act volume centers under the plate")
	assert_float_in_range(Hallway.switch_act_center().z, Hallway.SWITCH_PLATE_CENTER.z - 1e-4, Hallway.SWITCH_PLATE_CENTER.z + 1e-4, "the act volume centers under the plate")
	var hatch := Vector2(game.registry.hatch().center.x, game.registry.hatch().center.y)
	var act := Vector2(Hallway.switch_act_center().x, Hallway.switch_act_center().z)
	assert_float_in_range(hatch.distance_to(act), 0.0, PlayerMotion.HATCH_INTERACT_REACH,
		"the beside-door plate sits inside the doorway's press overlap")

func test_hallway_holds_no_smoke() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	var stack: Array[Node] = [hallway]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		assert_false(node is GPUParticles3D, "no smoke anywhere in the hallway subtree")
		assert_false(node is WorldEnvironment, "the hallway adds no environment of its own")
		for child in node.get_children():
			stack.append(child)

func test_fixtures_hold_zero_until_the_switch_flips() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	var lights := hallway.lights()
	assert_int_equal(Hallway.FIXTURE_STATIONS_X.size(), 4, "a fixture pair stands at every berth station, the power door's included")
	assert_float_in_range(Hallway.FIXTURE_STATIONS_X[3], Hallway.POWER_DOOR_X - 1e-4, Hallway.POWER_DOOR_X + 1e-4, "the power-door station carries its pair")
	assert_int_equal(Hallway.fixture_transforms().size(), 8, "the fixture group holds four station pairs")
	assert_int_equal(lights.size(), 8, "every station pair's fixtures light the corridor")
	assert_int_equal(hallway.lenses().size(), 8, "every light carries its lens")
	for light: OmniLight3D in lights:
		assert_float_in_range(light.light_energy, -1e-4, 1e-4, "every hall fixture starts dark")
		assert_true(light.light_color == Lighting.EMERGENCY_RED, "the hall fixtures hold the stasis bay's emergency red")
		assert_float_in_range(light.omni_range, Lighting.FIXTURE_RANGE - 1e-4, Lighting.FIXTURE_RANGE + 1e-4, "the hall fixtures hold the stasis bay's range")
	assert_true(hallway.lens_material().emission == Color(0.0, 0.0, 0.0), "the lenses hold no emission before the flip")
	assert_true(hallway.is_settled(), "the dark hallway starts settled")
	assert_false(game.hallway_lit, "the sim starts the hallway unlit")
	game.light_hallway()
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		hallway.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(hallway.is_settled(), "the flip settles on the fixture clock")
	assert_float_in_range(hallway.level(), 0.999, 1.001, "the fade lands at full level")
	for light: OmniLight3D in lights:
		assert_float_in_range(light.light_energy, Lighting.FIXTURE_ENERGY - 1e-3, Lighting.FIXTURE_ENERGY + 1e-3, "the fixtures hold the stasis bay's lit energy")
	assert_float_in_range(hallway.lens_material().emission.r, Lighting.FIXTURE_EMISSIVE - 1e-3, Lighting.FIXTURE_EMISSIVE + 1e-3, "the lenses hold the stasis bay's lit emission")
	# The regular strips wait for the secondary power: the switch's red
	# flip must never touch them.
	assert_int_equal(Hallway.REGULAR_STATIONS_X.size(), 4, "a regular strip stands at every fixture station")
	assert_int_equal(hallway.white_lights().size(), 4, "every station's strip lights the corridor")
	assert_int_equal(hallway.white_lenses().size(), 4, "every strip carries its lens")
	for light: OmniLight3D in hallway.white_lights():
		assert_float_in_range(light.light_energy, -1e-4, 1e-4, "the regular strips hold dark through the red flip")
	assert_float_in_range(hallway.white_level(), -1e-4, 1e-4, "the strips' fade holds zero")
	assert_float_in_range(hallway.white_lens_material().emission.r, -1e-4, 1e-4, "the strip lenses hold no emission before activation")

## Andrew's steadiness doctrine: the button lights the hall's red
## fixtures at their steady level — blinking belongs to the automatic
## fire circuit, and this hall has no fire. After the settle, many
## frames hold the energies and the lens emission exactly constant.
func test_lit_fixtures_hold_their_level_steady() -> void:
	var game := _awake_game()
	var hallway := Hallway.build(game)
	game.light_hallway()
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		hallway.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(hallway.is_settled(), "the flip settles on the fixture clock")
	var steady_emission := Color(Lighting.FIXTURE_EMISSIVE, 0.0, 0.0)
	for _frame: int in range(300):
		hallway.process_frame(Sim.LOGICAL_TICK_SECS)
		for light: OmniLight3D in hallway.lights():
			assert_float_in_range(light.light_energy, Lighting.FIXTURE_ENERGY - 1e-6, Lighting.FIXTURE_ENERGY + 1e-6, "a settled fixture never blinks: the energy holds steady")
		assert_true(hallway.lens_material().emission == steady_emission, "a settled lens never blinks: the emission holds steady")
	assert_true(hallway.is_settled(), "the steady hall stays settled")

## The press channel at the beside-door overlap: the closed door without
## the rod consumes nothing, so the switch standing beside it receives
## the press the door could not use — and once flipped, later fully
## refused presses stay on the channel.
func test_presses_fall_through_to_the_beside_door_switch() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	var adapter := InputPlane.ScriptedAdapter.new()
	assert_true(_walk_to(motion, game, plane, adapter, Vector2(5.4, 0.5), 0.2), "the walk arrived at the beside-door overlap")
	var hatch := Vector2(game.registry.hatch().center.x, game.registry.hatch().center.y)
	var act := Vector2(Hallway.switch_act_center().x, Hallway.switch_act_center().z)
	var foot := motion.capsule().foot
	assert_float_in_range(hatch.distance_to(Vector2(foot.x, foot.z)), 0.0, PlayerMotion.HATCH_INTERACT_REACH, "the overlap stand holds the door in reach")
	assert_float_in_range(act.distance_to(Vector2(foot.x, foot.z)), 0.0, PlayerMotion.SWITCH_ACT_REACH, "the overlap stand holds the switch in reach")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.pickup_rod(plane), "the rod is nowhere near the stand")
	assert_false(motion.interact_with_door(plane, game), "the closed door without the rod consumes no press")
	assert_int_equal(motion.door_openings, 0, "the door never started")
	assert_int_equal(motion.door_state, PlayerMotion.DoorState.CLOSED, "the door stays shut")
	assert_true(motion.flip_hallway_switch(plane, game), "the refused press reaches the beside-door switch")
	assert_true(game.hallway_lit, "the fall-through press lit the hall")
	assert_int_equal(motion.hallway_switch_flips, 1, "the fall-through flipped exactly once")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.pickup_rod(plane), "still no rod in reach")
	assert_false(motion.interact_with_door(plane, game), "the door still refuses without the rod")
	assert_false(motion.flip_hallway_switch(plane, game), "the once-only switch never flips twice")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the fully refused press stays on the channel")
	assert_true(motion.failure().is_empty(), motion.failure())

func test_switch_flips_exactly_once_from_a_full_crossing() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	# The rod's pickup is its own lane; carrying it here walks the door's
	# open and the beside-door flip end to end.
	motion.rod_carried = true
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.flip_hallway_switch(plane, game), "a press while standing at the pod cannot flip the beside-door switch")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the out-of-reach press is left on the channel")
	plane.end_frame()
	var adapter := InputPlane.ScriptedAdapter.new()
	var hatch := game.registry.hatch().center
	assert_true(_walk_to(motion, game, plane, adapter, hatch,
		PlayerMotion.HATCH_INTERACT_REACH * 0.9), "the walk arrived at the door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_door(plane, game), "the rod-carried press at the door starts the open")
	assert_int_equal(motion.door_openings, 1, "one press, one opening")
	assert_true(_walk_to(motion, game, plane, adapter,
		Vector2(Hallway.HALL_START_X + 1.2, 0.2), 0.3),
		"the walk crossed the threshold into the hall")
	var foot := motion.capsule().foot
	assert_float_in_range(foot.x, Hallway.HALL_START_X + Hallway.WALL, Hallway.HALL_END_X, "the capsule crossed into the hallway through the open doorway")
	assert_int_equal(motion.door_state, PlayerMotion.DoorState.OPEN, "the crossing found the door open")
	var act := Vector2(Hallway.switch_act_center().x, Hallway.switch_act_center().z)
	assert_float_in_range(act.distance_to(Vector2(foot.x, foot.z)), 0.0, PlayerMotion.SWITCH_ACT_REACH, "the crossing stand holds the beside-door switch in reach")
	# The open door owns no press: the dispatch order delivers this press
	# to the switch beside it.
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.pickup_rod(plane), "the carried rod consumes no press")
	assert_false(motion.interact_with_door(plane, game), "the open door leaves the press on the channel")
	assert_true(motion.flip_hallway_switch(plane, game), "the press beside the open door lights the hall")
	assert_true(game.hallway_lit, "the flip lit the hallway")
	assert_int_equal(motion.hallway_switch_flips, 1, "the switch flips exactly once")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.flip_hallway_switch(plane, game), "a second press never flips again")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the once-only switch leaves the second press on the channel")
	assert_int_equal(motion.door_openings, 1, "the open door never re-opens")
	assert_true(motion.failure().is_empty(), motion.failure())
