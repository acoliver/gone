extends SimTestCase
## The dropped rod (issue #58): the prop sits at its authored placement
## beside a non-player pod where the walking capsule can never pass
## through it, reads as plain metal with no emission, an interact press
## in reach while standing picks it up exactly once (the press is only
## consumed when the pickup lands, so the door's channel keeps every
## other press), the carried flag latches, the node leaves the floor,
## and the door opens exactly once with the rod carried.

const DT: float = 1.0 / 60.0
const NEAR: float = 1e-4

func _awake_game() -> Game:
	var game := Game.new()
	game.phase.wake_complete()
	return game

## Press activate in AwakeInPod and drive the four authored segments to
## the waypoint; leaves the mirror in WALK on the sim's Standing phase.
func _stand(motion: PlayerMotion, game: Game, plane: InputPlane) -> void:
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	motion.advance(plane, game, 0.0, DT)
	for _segment: int in range(Exit.EXIT_POSE_COUNT - 1):
		motion.advance(plane, game, 0.0, DT)

## Hold forward through the scripted adapter, re-aiming at the floor-plan
## target every tick, until the capsule sits within stop distance of it.
func _walk_to(motion: PlayerMotion, game: Game, plane: InputPlane,
		adapter: InputPlane.ScriptedAdapter, target: Vector2, stop_distance: float) -> bool:
	for _tick: int in range(1400):
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

func test_rod_sits_beside_a_pod_clear_of_the_walk_and_pods() -> void:
	var game := _awake_game()
	var rod := Rod.build()
	var bar: MeshInstance3D = rod.get_child(0)
	assert_true(rod.visible, "the rod starts on the floor, visible")
	var center := Rod.floor_center()
	assert_vec3_equal(bar.position, Vector3(center.x, Rod.ROD_RADIUS, center.y), "the bar rests its round surface on the floor at the authored center")
	var axis: Vector3 = bar.quaternion * Vector3.UP
	assert_float_in_range(absf(axis.y), 0.0, 1e-4, "the bar's long axis lies in the floor plane")
	assert_float_in_range(absf(axis.length() - 1.0), 0.0, 1e-4, "the axis is a unit direction")
	var half := Rod.ROD_LENGTH / 2.0
	var end_a := center + Vector2(axis.x, axis.z) * half
	var end_b := center - Vector2(axis.x, axis.z) * half
	assert_float_in_range(maxf(end_a.y, end_b.y), 0.0, 1.195, "the whole body stays clear of the aisle's swept walking band (z >= 1.195)")
	assert_float_in_range(maxf(end_a.y, end_b.y), 0.0, 1.8, "the whole body stays clear of the pod row's solids (z >= 1.8)")
	var player_center := game.registry.player_pod().placement().center
	var nearest := Vector2(INF, INF)
	for pod: Pods.Pod in game.registry.pods():
		var pod_center := pod.placement().center
		if center.distance_to(pod_center) < center.distance_to(nearest):
			nearest = pod_center
	assert_float_in_range(center.distance_to(nearest), 0.5, 2.0, "the rod sits beside a pod, not on it and not mid-room")
	assert_true(center.distance_to(player_center) > center.distance_to(nearest), "the nearest pod is not the player's pod")
	var material := bar.material_override as StandardMaterial3D
	assert_true(material != null, "the bar carries a standard material")
	assert_false(material.emission_enabled, "plain metal: no emission, no glow")

func test_pickup_lands_once_only_in_reach_while_standing() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	var lying := PlayerMotion.new()
	var lying_game := _awake_game()
	var lying_plane := InputPlane.new()
	lying_plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(lying.pickup_rod(lying_plane), "an interact while lying does not pick up")
	assert_false(lying.rod_carried, "no carried flag while lying")
	assert_true(lying_plane.take_press(InputPlane.Buttons.INTERACT), "the lying press is left on the channel")
	_stand(motion, game, plane)
	var foot := motion.capsule().foot
	var center := Rod.floor_center()
	assert_float_in_range(Vector2(foot.x - center.x, foot.z - center.y).length(),
		PlayerMotion.ROD_PICKUP_REACH + 0.1, 2.0, "the standing waypoint starts out of the rod's reach")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.pickup_rod(plane), "an interact out of reach does not pick up")
	assert_false(motion.rod_carried, "no carried flag out of reach")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the out-of-reach press is left for the hatch")
	plane.end_frame()
	# Walk the aisle's +X line toward the rod's end of the room.
	for _tick: int in range(60):
		plane.offer_movement(1.0, 0.0)
		motion.advance(plane, game, PI / 2.0, DT)
		plane.end_frame()
	foot = motion.capsule().foot
	assert_float_in_range(Vector2(foot.x - center.x, foot.z - center.y).length(),
		0.0, PlayerMotion.ROD_PICKUP_REACH * 0.9, "the walk arrived in the rod's reach")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.pickup_rod(plane), "one interact in reach picks up the rod")
	assert_true(motion.rod_carried, "the carried flag is set")
	assert_false(plane.take_press(InputPlane.Buttons.INTERACT), "the pickup consumed the press exactly once")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_false(motion.pickup_rod(plane), "a second interact after the pickup is a no-op")
	assert_true(motion.rod_carried, "the carried flag latches")
	assert_true(plane.take_press(InputPlane.Buttons.INTERACT), "the no-op left the press on the channel")
	assert_int_equal(motion.door_openings, 0, "no press at the rod was recorded as a door opening")
	assert_int_equal(game.phase.current(), Phase.Wake.STANDING, "the pickup never touched the phase machine")

func test_rod_node_leaves_the_floor_on_pickup() -> void:
	var rod := Rod.build()
	assert_true(rod.visible, "the rod node starts visible")
	rod.pick_up()
	assert_false(rod.visible, "the pickup hides the rod node")
	assert_int_equal(rod.get_child_count(), 1, "hidden, not freed: the bar stays a child")
	rod.pick_up()
	assert_false(rod.visible, "a repeated pickup stays hidden")

func test_pickup_reachable_through_the_scripted_adapter() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	var adapter := InputPlane.ScriptedAdapter.new()
	assert_true(_walk_to(motion, game, plane, adapter, Rod.floor_center(),
		PlayerMotion.ROD_PICKUP_REACH * 0.9), "the scripted adapter walked into the rod's reach")
	assert_true(motion.failure().is_empty(), motion.failure())
	adapter.press(InputPlane.Buttons.INTERACT)
	adapter.offer_tick(plane)
	assert_true(motion.pickup_rod(plane), "a scripted interact press picks up the rod")
	assert_false(motion.pickup_rod(plane), "the scripted pickup is exactly-once too")
	assert_true(motion.rod_carried, "the scripted path sets the carried flag")
	plane.end_frame()

func test_door_opens_with_the_rod_carried() -> void:
	var game := _awake_game()
	var motion := PlayerMotion.new()
	var plane := InputPlane.new()
	_stand(motion, game, plane)
	var adapter := InputPlane.ScriptedAdapter.new()
	var colliders_closed := game.colliders.size()
	var hatch := game.registry.hatch().center
	# Open the door before any pickup; the walking ticks that follow the
	# press carry the opening animation to its end.
	assert_true(_walk_to(motion, game, plane, adapter, hatch,
		PlayerMotion.HATCH_INTERACT_REACH * 0.9), "the walk arrived at the door")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_door(plane, game), "the door opens before the pickup")
	assert_int_equal(motion.door_openings, 1, "one opening before the pickup")
	# Walk back to the rod, pick it up, then return to the open doorway.
	assert_true(_walk_to(motion, game, plane, adapter, Rod.floor_center(),
		PlayerMotion.ROD_PICKUP_REACH * 0.9), "the walk arrived back at the rod")
	assert_int_equal(motion.door_state, PlayerMotion.DoorState.OPEN, "the opening completed during the walk")
	assert_true(game.door_open, "the doorway's colliders opened during the walk")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.pickup_rod(plane), "the pickup lands after the long walk")
	assert_true(motion.rod_carried, "the rod is carried")
	assert_int_equal(motion.door_openings, 1, "the pickup added no opening")
	assert_true(_walk_to(motion, game, plane, adapter, hatch,
		PlayerMotion.HATCH_INTERACT_REACH * 0.9), "the walk arrived at the door with the rod carried")
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(motion.interact_with_door(plane, game), "the press at the open door is still eaten")
	assert_int_equal(motion.door_openings, 1, "the open door never re-opens")
	assert_true(motion.rod_carried, "the door never un-carries the rod")
	assert_int_equal(game.colliders.size(), Hallway.scene_collider_set(game.registry, true).size(), "the open doorway carries the open collider set")
	assert_true(game.colliders.size() != colliders_closed, "the collider set changed when the doorway opened")
	assert_int_equal(motion.state(), PlayerMotion.BodyState.WALK, "the body still owns a standing capsule")
	assert_true(motion.failure().is_empty(), motion.failure())
