extends SimTestCase
## Port of the engine-independent assertions from the gone_app scene
## tests: placement parity (placement.rs, geometry.rs, placement_truth.rs)
## and collider set completeness (colliders.rs), asserted against the
## same pure data the scene builders spawn.

## The pinned static box count: six shell slabs, one box per pod
## construction solid (6+7+6+7+6+7+6 across the frozen states), and five
## hatch pieces.
const PINNED_BOX_COUNT: int = 56

func assert_vec3_near(actual: Vector3, expected: Vector3, message: String) -> void:
	var drift: Vector3 = (actual - expected).abs()
	assert_true(
		drift.x < 1e-5 and drift.y < 1e-5 and drift.z < 1e-5,
		"%s: expected %s, got %s" % [message, str(expected), str(actual)]
	)

func test_room_shell_bounds_are_the_envelope() -> void:
	var min_corner := Vector3(INF, INF, INF)
	var max_corner := Vector3(-INF, -INF, -INF)
	var shell := Placement.room_shell()
	for placement: Placement.SolidPlacement in shell:
		var half: Vector3 = placement.size / 2.0
		min_corner = min_corner.min(placement.center - half)
		max_corner = max_corner.max(placement.center + half)
	var floor: Placement.SolidPlacement = shell[0]
	var ceiling: Placement.SolidPlacement = shell[1]
	assert_vec3_equal(min_corner, floor.center - floor.size / 2.0, "envelope min is the floor's underside")
	assert_vec3_equal(max_corner, ceiling.center + ceiling.size / 2.0, "envelope max is the ceiling's top")
	assert_vec3_near(
		min_corner,
		Vector3(
			-(Pods.ROOM_LENGTH / 2.0 + Placement.WALL_THICKNESS),
			-Placement.WALL_THICKNESS,
			-(Pods.ROOM_WIDTH / 2.0 + Placement.WALL_THICKNESS)
		),
		"shell tiles the frozen envelope at the min corner"
	)
	assert_vec3_near(
		max_corner,
		Vector3(
			Pods.ROOM_LENGTH / 2.0 + Placement.WALL_THICKNESS,
			Pods.ROOM_CEILING_HEIGHT + Placement.WALL_THICKNESS,
			Pods.ROOM_WIDTH / 2.0 + Placement.WALL_THICKNESS
		),
		"shell tiles the frozen envelope at the max corner"
	)

func test_hatch_door_placement_sits_ajar_in_the_opening() -> void:
	var registry := Pods.PodRegistry.frozen()
	var hatch: Pods.HatchPlacement = registry.hatch()
	var door: Placement.SolidPlacement = Placement.hatch_solids()[4]
	assert_true(door.center.x > Pods.ROOM_LENGTH / 2.0 - 0.5, "the door sits at the short wall")
	assert_true(absf(door.center.y - 1.1) < 1e-5, "the door sits at mid height")
	var free_edge: Vector3 = door.center + door.rotation * Vector3(0.0, 0.0, 0.56)
	assert_true(
		free_edge.x < hatch.center.x - 0.1,
		"the free edge leans into the room, got x %s" % str(free_edge.x)
	)

func test_pod_boxes_stay_in_the_room_and_clear_the_aisle() -> void:
	var registry := Pods.PodRegistry.frozen()
	for pod: Pods.Pod in registry.pods():
		var placement: Pods.PodPlacement = pod.placement()
		var x: float = placement.center.x
		var z: float = placement.center.y
		assert_true(
			absf(x) + Pods.POD_WIDTH / 2.0 <= Pods.ROOM_LENGTH / 2.0 + 1e-5,
			"pod %d inside the long axis" % pod.id().index()
		)
		assert_true(
			absf(z) + Pods.POD_LENGTH / 2.0 <= Pods.ROOM_WIDTH / 2.0 + 1e-5,
			"pod %d inside the short axis" % pod.id().index()
		)
		var aisle_face := absf(z) - Pods.POD_LENGTH / 2.0
		assert_true(
			aisle_face >= Pods.AISLE_HALF_WIDTH + Controller.POD_EXIT_CLEARANCE,
			"pod %d clears the aisle band" % pod.id().index()
		)

func test_hatch_constants_sit_on_the_plus_x_wall() -> void:
	assert_true(Placement.HATCH_DOOR_X < Pods.ROOM_LENGTH / 2.0, "the door is recessed inside the wall")
	var registry := Pods.PodRegistry.frozen()
	var hatch: Pods.HatchPlacement = registry.hatch()
	assert_true(
		absf(hatch.center.x - Pods.ROOM_LENGTH / 2.0) < 1e-6,
		"the registry puts the hatch on the +X wall"
	)
	var frame_front := Placement.HATCH_FRAME_X - Placement.FRAME_DEPTH / 2.0
	assert_true(frame_front < Pods.ROOM_LENGTH / 2.0, "the frame protrudes from the wall face into the room")
	assert_true(Placement.HATCH_DOOR_X > frame_front, "the door sits recessed behind the frame front")
	assert_true(
		absf(Placement.HATCH_FRAME_X + Placement.FRAME_DEPTH / 2.0 - hatch.center.x) < 1e-6,
		"the frame's center plane matches the registry's hatch center"
	)
	assert_int_equal(registry.player_pod().id().index(), 6, "the player pod is id 6")

func test_collider_set_carries_the_pinned_box_count() -> void:
	var registry := Pods.PodRegistry.frozen()
	var set := Placement.scene_collider_set(registry)
	assert_int_equal(set.size(), PINNED_BOX_COUNT, "the pinned static box count")
	var rebuilt := Placement.scene_collider_set(registry)
	assert_int_equal(rebuilt.size(), PINNED_BOX_COUNT, "the rebuild derives the same count")
	for index: int in range(set.boxes().size()):
		assert_true(
			set.boxes()[index].equals(rebuilt.boxes()[index]),
			"box %d is identical across builds" % index
		)
	var expected := Placement.room_shell().size()
	for pod: Pods.Pod in registry.pods():
		expected += PodBody.pod_solids(pod.state()).size()
	expected += Placement.hatch_solids().size()
	assert_int_equal(set.size(), expected, "one collider box per construction solid")

func test_named_boxes_derive_from_their_placements() -> void:
	var registry := Pods.PodRegistry.frozen()
	var boxes := Placement.scene_collider_set(registry).boxes()
	var floor_box: ColliderSet.Aabb = boxes[0]
	assert_vec3_near(floor_box.min_corner(), Vector3(-6.2, -0.2, -4.2), "floor min")
	assert_vec3_near(floor_box.max_corner(), Vector3(6.2, 0.0, 4.2), "floor max")
	var before_player := 0
	for pod: Pods.Pod in registry.pods():
		if Pods.is_player(pod.state()):
			break
		before_player += PodBody.pod_solids(pod.state()).size()
	var base: ColliderSet.Aabb = boxes[Placement.room_shell().size() + before_player]
	assert_vec3_near(base.center(), Vector3(-4.8, 0.05, 2.9), "player base center")
	assert_vec3_near(
		base.half_extents(),
		Vector3(Pods.POD_WIDTH / 2.0, 0.05, Pods.POD_LENGTH / 2.0),
		"player base half extents"
	)
	var first_post: ColliderSet.Aabb = boxes[PINNED_BOX_COUNT - Placement.hatch_solids().size()]
	assert_vec3_near(
		first_post.center(),
		Vector3(
			Placement.HATCH_FRAME_X,
			(Placement.HATCH_HEIGHT + Placement.FRAME_POST_WIDTH) / 2.0,
			-(Placement.HATCH_WIDTH + Placement.FRAME_POST_WIDTH) / 2.0
		),
		"hatch -Z post center"
	)
	assert_vec3_near(
		first_post.half_extents(),
		Vector3(Placement.FRAME_DEPTH / 2.0, 1.28, 0.08),
		"hatch -Z post half extents"
	)

func test_exit_aperture_mouth_stays_clear_of_every_collider() -> void:
	var registry := Pods.PodRegistry.frozen()
	var set := Placement.scene_collider_set(registry)
	var player: Pods.PodPlacement = registry.player_pod().placement()
	var sin_yaw := sin(player.yaw_radians)
	var cos_yaw := cos(player.yaw_radians)
	var to_world := func(local: Vector3) -> Vector3:
		return Vector3(
			player.center.x + local.x * cos_yaw + local.z * sin_yaw,
			local.y,
			player.center.y - local.x * sin_yaw + local.z * cos_yaw
		)
	var mouth_start := Pods.POD_LENGTH / 2.0 - PodBody.CAVITY_WALL + 0.01
	var near: Vector3 = to_world.call(Vector3(-Pods.POD_WIDTH / 2.0, PodBody.TRAY_FLOOR_Y, mouth_start))
	var far: Vector3 = to_world.call(Vector3(Pods.POD_WIDTH / 2.0, 1.9, Pods.POD_LENGTH / 2.0))
	var strip: ColliderSet.Result = ColliderSet.Aabb.from_min_max(near.min(far), near.max(far))
	assert_true(strip.is_ok(), "the mouth strip is a valid box")
	var overlappers: PackedInt32Array = set.overlapping(strip.box)
	assert_true(
		overlappers.is_empty(),
		"nothing may stand in the exit mouth: boxes %s" % str(overlappers)
	)

func test_shared_exit_path_is_the_scene_construction() -> void:
	var shared := PlacementTruth.player_exit_path()
	var built := Exit.ExitPath.try_new(
		Pods.PodRegistry.frozen().player_pod().placement(),
		PodBody.TRAY_FLOOR_Y
	)
	assert_true(built.is_ok(), "the frozen player pod authors a valid exit path")
	assert_int_equal(shared.poses().size(), Exit.EXIT_POSE_COUNT, "the path holds its key poses")
	for index: int in range(shared.poses().size()):
		assert_vec3_equal(shared.poses()[index].foot(), built.path.poses()[index].foot(), "pose foot parity")
		assert_vec3_equal(shared.poses()[index].head(), built.path.poses()[index].head(), "pose head parity")
		assert_float_equal(
			shared.poses()[index].tolerance(),
			built.path.poses()[index].tolerance(),
			"pose tolerance parity"
		)
	var foot: Vector3 = shared.waypoint().foot()
	assert_true(
		absf(foot.y - (Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE)) < 1e-6,
		"the waypoint foot rests on the room floor, got %s" % str(foot)
	)
	var expected_eye_y := foot.y - Controller.CAPSULE_RADIUS + PlacementTruth.STANDING_EYE_HEIGHT
	assert_true(
		absf(expected_eye_y - (Controller.PENETRATION_TOLERANCE + PlacementTruth.STANDING_EYE_HEIGHT)) < 1e-6,
		"the standing eye height derives from the waypoint foot"
	)
