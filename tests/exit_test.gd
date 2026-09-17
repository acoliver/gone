extends SimTestCase
## Port of the exit/mod.rs inline test module.

## Test-scene tray build mirroring the app-side pod cavity: 0.06 m shell
## walls, a 0.1 m base slab, and a 0.012 m plate on top, so the plate
## top (the tray floor the path is authored against) is real geometry,
## not an assumption.
const CAVITY_WALL: float = 0.06
const CAVITY_BASE: float = 0.1
const CAVITY_PLATE: float = 0.012
const TRAY_FLOOR: float = CAVITY_BASE + CAVITY_PLATE

## Test floor slab half-span, well past every pod placement used here.
const FLOOR_SPAN: float = 16.0

## The codebase's position tolerance for transformed expectations.
const POSITION_EPSILON: float = 1e-5

func assert_vec_close(actual: Vector3, expected: Vector3, label: String) -> void:
	var drift: Vector3 = (actual - expected).abs()
	assert_true(drift.x < POSITION_EPSILON and drift.y < POSITION_EPSILON and drift.z < POSITION_EPSILON, "%s: expected %s, got %s" % [label, str(expected), str(actual)])

func placement(yaw: float, center: Vector2) -> Pods.PodPlacement:
	return Pods.PodPlacement.new(center, yaw)

func frozen_player_placement() -> Pods.PodPlacement:
	return Pods.PodRegistry.frozen().player_pod().placement()

func local_to_world(at: Pods.PodPlacement, x: float, y: float, z: float) -> Vector3:
	var sin_yaw: float = sin(at.yaw_radians)
	var cos_yaw: float = cos(at.yaw_radians)
	return Vector3(at.center.x + x * cos_yaw + z * sin_yaw, y, at.center.y - x * sin_yaw + z * cos_yaw)

## The pod-local floor-plan coordinates of a room-frame point (the
## inverse rotation; exact for the axis-aligned test yaws 0 and pi).
func world_planar_local(at: Pods.PodPlacement, world: Vector3) -> Vector2:
	var sin_yaw: float = sin(at.yaw_radians)
	var cos_yaw: float = cos(at.yaw_radians)
	var dx: float = world.x - at.center.x
	var dz: float = world.z - at.center.y
	return Vector2(dx * cos_yaw - dz * sin_yaw, dx * sin_yaw + dz * cos_yaw)

## One axis-aligned test box, pod-local center and size lifted into the
## room frame. The size is a full extent; try_new takes half extents.
## Valid only for yaws that keep boxes axis-aligned (0 and pi here).
func local_box(at: Pods.PodPlacement, center: Vector3, size: Vector3) -> ColliderSet.Aabb:
	return ColliderSet.Aabb.try_new(local_to_world(at, center.x, center.y, center.z), size * 0.5).box

func box_between(corner_min: Vector3, corner_max: Vector3) -> ColliderSet.Aabb:
	return ColliderSet.Aabb.from_min_max(corner_min, corner_max).box

func pod_solids(at: Pods.PodPlacement) -> Array[ColliderSet.Aabb]:
	var wall_mid: float = (CAVITY_BASE + Pods.POD_HEIGHT) / 2.0
	var wall_height: float = Pods.POD_HEIGHT - CAVITY_BASE
	return [
		local_box(at, Vector3(0.0, CAVITY_BASE / 2.0, 0.0), Vector3(Pods.POD_WIDTH, CAVITY_BASE, Pods.POD_LENGTH)),
		local_box(at, Vector3(0.0, TRAY_FLOOR - CAVITY_PLATE / 2.0, 0.0), Vector3(Pods.POD_WIDTH - 2.0 * CAVITY_WALL, CAVITY_PLATE, Pods.POD_LENGTH - 2.0 * CAVITY_WALL)),
		local_box(at, Vector3(-(Pods.POD_WIDTH / 2.0 - CAVITY_WALL / 2.0), wall_mid, -CAVITY_WALL / 2.0), Vector3(CAVITY_WALL, wall_height, Pods.POD_LENGTH - CAVITY_WALL)),
		local_box(at, Vector3(Pods.POD_WIDTH / 2.0 - CAVITY_WALL / 2.0, wall_mid, -CAVITY_WALL / 2.0), Vector3(CAVITY_WALL, wall_height, Pods.POD_LENGTH - CAVITY_WALL)),
		local_box(at, Vector3(0.0, wall_mid, -(Pods.POD_LENGTH - CAVITY_WALL / 2.0)), Vector3(Pods.POD_WIDTH - 2.0 * CAVITY_WALL, wall_height, CAVITY_WALL)),
		local_box(at, Vector3(0.0, Pods.POD_HEIGHT + 0.65, -(Pods.POD_LENGTH - CAVITY_WALL / 2.0)), Vector3(Pods.POD_WIDTH, 1.3, CAVITY_WALL)),
	]

## The test scene: a room floor slab plus the player pod's cavity solids
## (base, plate, two side walls, head wall, canopy), then any extra
## boxes. Insertion order matters to the resolver's index reports: floor
## 0, base 1, plate 2, side walls 3 and 4, head wall 5, canopy 6, then
## the extras.
func pod_scene(at: Pods.PodPlacement, extra: Array) -> ColliderSet:
	var colliders := ColliderSet.new()
	colliders.insert(box_between(Vector3(-FLOOR_SPAN, -1.0, -FLOOR_SPAN), Vector3(FLOOR_SPAN, 0.0, FLOOR_SPAN)))
	for solid: ColliderSet.Aabb in pod_solids(at):
		colliders.insert(solid)
	for aabb: ColliderSet.Aabb in extra:
		colliders.insert(aabb)
	return colliders

## Drives the full get-up from AwakeInPod to Standing and returns the
## finished controller, the machine, and the per-tick waypoint flags.
func drive_to_standing(path: Exit.ExitPath, world: ColliderSet) -> Array:
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	var start_result := Exit.GetUpController.start(machine, path)
	assert_true(start_result.is_ok(), "the get-up starts from AwakeInPod")
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "start advances to ExitingPod")
	var controller: Exit.GetUpController = start_result.controller
	var waypoints: Array = []
	for expected_index: int in range(1, Exit.EXIT_POSE_COUNT):
		var tick_result := controller.tick(machine, world)
		assert_true(tick_result.is_ok(), "unblocked tick")
		assert_int_equal(tick_result.progress.pose_index, expected_index, "pose order")
		waypoints.append(tick_result.progress.at_waypoint)
		var pose: Exit.ExitPose = path.poses()[expected_index]
		assert_vec_close(controller.capsule().foot, pose.foot(), "pose foot")
		assert_vec_close(controller.capsule().head, pose.head(), "pose head")
	return [controller, machine, waypoints]

func authored_path(at: Pods.PodPlacement) -> Exit.ExitPath:
	var result := Exit.ExitPath.try_new(at, TRAY_FLOOR)
	assert_true(result.is_ok(), "authored floor is valid")
	return result.path

func test_happy_path_visits_every_pose_and_completes_standing_at_the_waypoint() -> void:
	var at: Pods.PodPlacement = frozen_player_placement()
	var path: Exit.ExitPath = authored_path(at)
	var world := pod_scene(at, [])
	var driven: Array = drive_to_standing(path, world)
	var controller: Exit.GetUpController = driven[0]
	var machine: Phase.Machine = driven[1]
	var waypoints: Array = driven[2]
	assert_true(waypoints == [false, false, false, true], "only the last tick completes the waypoint")
	assert_true(machine.in_phase(Phase.Wake.STANDING), "the machine lands in Standing")
	assert_true(machine.locomotion_allowed(), "Standing unlocks locomotion")
	var waypoint: Exit.ExitPose = path.waypoint()
	assert_vec_close(controller.capsule().foot, waypoint.foot(), "waypoint foot")
	assert_vec_close(controller.capsule().head, waypoint.head(), "waypoint head")
	var local_foot: Vector2 = world_planar_local(at, controller.capsule().foot)
	assert_true(absf(local_foot.x) < POSITION_EPSILON, "centered on the pod")
	var expected_standoff: float = Pods.POD_LENGTH / 2.0 + Controller.CAPSULE_RADIUS + 2.0 * Controller.PENETRATION_TOLERANCE
	assert_true(absf(local_foot.y - expected_standoff) < POSITION_EPSILON, "standing past the pod face by the capsule radius")
	assert_true(absf(controller.capsule().foot.y - (Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE)) < 1e-6, "foot sphere one tolerance above the deck")

func test_waypoint_room_position_is_the_placement_transform_not_a_hard_code() -> void:
	var standing_y: float = Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
	var waypoint_z: float = Pods.POD_LENGTH / 2.0 + Controller.CAPSULE_RADIUS + 2.0 * Controller.PENETRATION_TOLERANCE
	var row_a: Pods.PodPlacement = placement(0.0, Vector2(-3.0, -2.9))
	var path_a := Exit.ExitPath.try_new(row_a, TRAY_FLOOR)
	assert_true(path_a.is_ok(), "authored floor is valid")
	# Godot's Vector2/Vector3 hold 32-bit components, so the exact-arithmetic
	# expectation must pass through the same f32 containers the production
	# transform uses (the Rust original was f32 end to end).
	var sin_yaw: float = sin(0.0)
	var cos_yaw: float = cos(0.0)
	var center := Vector2(-3.0, -2.9)
	var local := Vector3(0.0, standing_y, waypoint_z)
	var expected := Vector3(
		center.x + local.x * cos_yaw + local.z * sin_yaw,
		local.y,
		center.y - local.x * sin_yaw + local.z * cos_yaw
	)
	assert_vec3_equal(path_a.path.waypoint().foot(), expected, "identity yaw transforms exactly")
	var player: Pods.PodPlacement = frozen_player_placement()
	var path_b := Exit.ExitPath.try_new(player, TRAY_FLOOR)
	assert_true(path_b.is_ok(), "authored floor is valid")
	assert_vec_close(path_b.path.waypoint().foot(), local_to_world(player, 0.0, standing_y, waypoint_z), "yaw-pi waypoint")
	var separation: float = (path_a.path.waypoint().foot() - path_b.path.waypoint().foot()).length()
	assert_true(separation > 1.0, "the waypoint follows the placement")

func test_start_rejects_every_phase_except_awake_in_pod() -> void:
	var path: Exit.ExitPath = authored_path(frozen_player_placement())
	for current: int in [Phase.Wake.WAKING, Phase.Wake.EXITING_POD, Phase.Wake.STANDING]:
		var machine := Phase.Machine.new(current)
		var result := Exit.GetUpController.start(machine, path)
		assert_true(result.error != null and result.error.equals(Exit.ExitError.wrong_phase(Phase.Wake.AWAKE_IN_POD, current)), "only AwakeInPod starts the get-up")
		assert_true(machine.in_phase(current), "the phase is unchanged")
		var text: String = result.error._to_string()
		assert_true(text.find("phase") != -1, "display: %s" % text)
		assert_true(text.find(Phase.phase_name(current)) != -1, "display: %s" % text)

func test_ticking_a_spent_controller_is_rejected_even_after_a_machine_reset() -> void:
	var at: Pods.PodPlacement = frozen_player_placement()
	var path: Exit.ExitPath = authored_path(at)
	var world := pod_scene(at, [])
	var driven: Array = drive_to_standing(path, world)
	var controller: Exit.GetUpController = driven[0]
	var reset := Phase.Machine.new(Phase.Wake.EXITING_POD)
	var spent := controller.tick(reset, world)
	assert_true(spent.error != null and spent.error.equals(Exit.ExitError.get_up_already_complete()), "a spent controller refuses every further tick")
	assert_true(spent.error._to_string() == "the get-up already reached the waypoint", "display names the spent get-up")

func test_a_blocked_aperture_stops_the_get_up_with_a_typed_error() -> void:
	var at: Pods.PodPlacement = frozen_player_placement()
	var path: Exit.ExitPath = authored_path(at)
	var wall_mid: float = (CAVITY_BASE + Pods.POD_HEIGHT) / 2.0
	# A jamb filling the +x half of the exit mouth strip: the clear
	# passage drops to 0.45 m, under the 0.60 m capsule diameter.
	var jamb := local_box(at, Vector3(0.25, wall_mid, Pods.POD_LENGTH / 2.0 - CAVITY_WALL / 2.0), Vector3(0.5, Pods.POD_HEIGHT - CAVITY_BASE, CAVITY_WALL))
	var world := pod_scene(at, [jamb])
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	var controller := Exit.GetUpController.start(machine, path).controller
	assert_true(controller.tick(machine, world).is_ok(), "the sit-up pivot clears the tray")
	var blocked := controller.tick(machine, world)
	assert_true(blocked.error != null and blocked.error.kind == Exit.ExitError.Kind.PATH_BLOCKED, "expected a blocked path")
	assert_int_equal(blocked.error.pose_index, 2, "the walk to the aperture line is blocked")
	assert_true(blocked.error.shortfall > Exit.POSE_TOLERANCE, "a real block, %s m" % str(blocked.error.shortfall))
	assert_true(blocked.error.shortfall > 0.05, "stopped before the mouth: %s m" % str(blocked.error.shortfall))
	var local_foot: Vector2 = world_planar_local(at, controller.capsule().foot)
	assert_true(absf(local_foot.x) < POSITION_EPSILON, "still centered")
	assert_true(local_foot.y + Controller.CAPSULE_RADIUS < Pods.POD_LENGTH / 2.0 - CAVITY_WALL, "foot sphere short of the mouth line, local z %s" % str(local_foot.y))
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "the machine never advanced")
	var retry := controller.tick(machine, world)
	assert_true(retry.error != null and retry.error.kind == Exit.ExitError.Kind.PATH_BLOCKED, "the retry fails the same way")

func test_resolver_rejections_surface_as_the_typed_resolver_error() -> void:
	var at: Pods.PodPlacement = frozen_player_placement()
	var path: Exit.ExitPath = authored_path(at)
	# A slab around the lying capsule's middle, embedding it far past the
	# penetration tolerance on every axis.
	var block := local_box(at, Vector3(0.0, TRAY_FLOOR + Controller.CAPSULE_RADIUS, 0.0), Vector3(0.2, 0.2, 0.4))
	var world := pod_scene(at, [block])
	var machine := Phase.Machine.new(Phase.Wake.AWAKE_IN_POD)
	var controller := Exit.GetUpController.start(machine, path).controller
	var rejected := controller.tick(machine, world)
	assert_true(rejected.error != null and rejected.error.equals(Exit.ExitError.resolver_error(Resolve.ResolveError.start_penetration(7))), "the resolver's own rejection wraps, naming the collider index")
	var text: String = rejected.error._to_string()
	assert_true(text.find("resolver") != -1, "display: %s" % text)
	assert_true(text.find("embedded") != -1, "display: %s" % text)
	assert_true(machine.in_phase(Phase.Wake.EXITING_POD), "the machine stays in ExitingPod")

func test_authored_moves_match_the_pose_table_and_mouth_poses_stay_centered() -> void:
	var at: Pods.PodPlacement = frozen_player_placement()
	var path: Exit.ExitPath = authored_path(at)
	for index: int in range(Exit.EXIT_POSE_COUNT - 1):
		var expected: Exit.SegmentMove = Exit.segment_move(path.poses()[index], path.poses()[index + 1])
		assert_true(path.moves()[index].equals(expected), "segment %d" % index)
	assert_int_equal(path.moves()[0].kind, Exit.SegmentMove.Kind.PIVOT_ABOUT_FOOT, "the sit-up is the authored pivot")
	for index: int in range(1, Exit.EXIT_POSE_COUNT - 1):
		assert_int_equal(path.moves()[index].kind, Exit.SegmentMove.Kind.RIGID, "everything else is rigid")
	# Every pose from the aperture line on is centered: the mouth is
	# always crossed on the pod's lateral axis.
	for index: int in range(2, Exit.EXIT_POSE_COUNT):
		assert_true(absf(path.poses()[index].foot().x - at.center.x) < POSITION_EPSILON, "centered foot at the mouth")
		assert_true(absf(path.poses()[index].head().x - at.center.x) < POSITION_EPSILON, "centered head at the mouth")
	assert_true(Exit.EXIT_MOUTH_WIDTH >= 2.0 * Controller.CAPSULE_RADIUS + 2.0 * 0.149, "the frozen mouth width covers the capsule with the frozen clearance per side")

func test_path_construction_validates_its_inputs() -> void:
	var player: Pods.PodPlacement = frozen_player_placement()
	var nan_placement := Exit.ExitPath.try_new(Pods.PodPlacement.new(Vector2(NAN, 0.0), 0.0), TRAY_FLOOR)
	assert_true(nan_placement.error != null and nan_placement.error.equals(Exit.ExitPathError.non_finite_placement()), "a non-finite placement is rejected")
	var nan_floor := Exit.ExitPath.try_new(player, NAN)
	assert_true(nan_floor.error != null and nan_floor.error.equals(Exit.ExitPathError.non_finite_tray_floor()), "a non-finite floor is rejected")
	var below := Exit.ExitPath.try_new(player, -0.5)
	assert_true(below.error != null and below.error.equals(Exit.ExitPathError.tray_floor_below_room(-0.5)), "a floor below the room floor is rejected")
	var max_floor: float = Pods.POD_HEIGHT - 2.0 * Controller.CAPSULE_RADIUS
	var too_high := Exit.ExitPath.try_new(player, max_floor + 0.01)
	assert_true(too_high.error != null and too_high.error.equals(Exit.ExitPathError.tray_floor_too_high(max_floor, max_floor + 0.01)), "a floor too high for the lying capsule is rejected")
	assert_true(Exit.ExitPath.try_new(player, TRAY_FLOOR).is_ok(), "the authored tray floor is inside both bounds")
	assert_true(Exit.ExitPath.try_new(player, 0.0).is_ok(), "the room floor boundary is accepted")
	assert_true(Exit.ExitPath.try_new(player, max_floor).is_ok(), "the ceiling boundary is accepted")
