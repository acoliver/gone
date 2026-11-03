extends SimTestCase

func test_runtime_exit_is_the_rigidly_transformed_local_path() -> void:
	var game := Game.new(0)
	var frame := ShipLayout.authored().layout.bay_to_world()
	assert_true(frame.basis == Basis(Vector3(0, 0, -1), Vector3.UP, Vector3.RIGHT), "exact cardinal basis")
	var local := Exit.ExitPath.try_new(game.registry.player_pod().placement(), PodGeometry.TRAY_FLOOR_Y).path
	assert_vec3_equal(frame * Vector3(-4.8, 0, 2.9), Vector3(17.9, 0, 12.5), "player pod world pin")
	assert_vec3_equal(frame * Vector3(-0.6, 0, -1.55), Vector3(13.45, 0, 8.3), "rod world pin")
	assert_close(frame * Vector3(6, 0, 0), Vector3(15, 0, 1.7), "bay threshold pin")
	for index: int in range(5):
		assert_vec3_equal(game.exit_path.poses()[index].foot(), frame * local.poses()[index].foot(), "world foot %d" % index)
		assert_vec3_equal(game.exit_path.poses()[index].head(), frame * local.poses()[index].head(), "world head %d" % index)
	for index: int in range(4):
		assert_int_equal(game.exit_path.moves()[index].kind, local.moves()[index].kind, "pivot kind retained")
		assert_vec3_equal(game.exit_path.moves()[index].vector(), frame.basis * local.moves()[index].vector(), "pivot vector rotated once")

func test_runtime_smoke_is_bounded_in_the_bay_frame() -> void:
	var smoke := SmokeSymptoms.new()
	var frame := ShipLayout.authored().layout.bay_to_world()
	for point: Vector3 in [Vector3(-6, 1, 0), Vector3(0, 1, 0), Vector3(5.5, 1, 0)]:
		assert_float_equal(smoke.exposure_at(frame * point), 1.0, "interior full exposure")
	assert_float_equal(smoke.exposure_at(frame * Vector3(5.75, 1, 0)), 0.5, "threshold taper")
	for point: Vector3 in [Vector3(-6.01, 1, 0), Vector3(6, 1, 0), Vector3(0, -0.01, 0), Vector3(0, 3.21, 0), Vector3(0, 1, 4.01), Vector3(0, 6.5, 0)]:
		assert_float_equal(smoke.exposure_at(frame * point), 0.0, "outside volume is clean")

func test_switch_world_pin() -> void:
	assert_vec3_equal(Hallway.SWITCH_PLATE_CENTER, Vector3(16.2, 1.25, 1.45), "hall switch beside bay")

func test_all_pod_and_light_frames_rotate_without_changing_local_fixtures() -> void:
	var game := Game.new(0)
	var frame := game.layout.bay_to_world()
	var pins: Array[Vector3] = [Vector3(12.1, 0, 12.5), Vector3(12.1, 0, 11.1), Vector3(12.1, 0, 9.7), Vector3(12.1, 0, 8.3), Vector3(17.9, 0, 9.7), Vector3(17.9, 0, 11.1), Vector3(17.9, 0, 12.5)]
	for pod: Pods.Pod in game.registry.pods():
		var center := pod.placement().center
		assert_close(frame * Vector3(center.x, 0, center.y), pins[pod.id().index()], "world pod pin")
		assert_close(frame.affine_inverse() * pins[pod.id().index()], Vector3(center.x, 0, center.y), "inverse returns local pod")
	var fixtures := Lighting.fixture_transforms(game.registry)
	for index: int in range(7):
		assert_vec3_equal(Vector3(0, (frame * fixtures[index]).origin.y, 0), Vector3(0, 2.65, 0), "fixture height unchanged")
		assert_vec3_equal((frame * fixtures[index]).basis.x, Vector3(0, 0, -1), "light frame quarter-turn")
	var rig := Player.build(game, null)
	rig.scripted = true
	rig._ready()
	assert_float_in_range(InputPlane.wrap_angle(rig.look_angles().x), -PI / 2 - 1e-4, -PI / 2 + 1e-4, "spawn yaw rotated once")
	rig.free()

func test_resolver_sweep_is_covariant_in_the_moved_bay_and_ends_have_closed_hatches() -> void:
	var game := Game.new(0)
	var frame := game.layout.bay_to_world()
	var local := Resolve.Capsule.new()
	local.foot = Vector3(0, 0.385, 0)
	local.head = local.foot + Vector3.UP * 1.15
	var world := Resolve.Capsule.new()
	world.foot = frame * local.foot
	world.head = frame * local.head
	var expected := Resolve.resolve_motion(local, Vector3(0, 0, 6), ShipCollision.bay_set(game.registry))
	var actual := Resolve.resolve_motion(world, frame.basis * Vector3(0, 0, 6), game.colliders)
	assert_true(expected.is_ok() and actual.is_ok(), "both sweeps accepted")
	assert_close(actual.motion.displacement, frame.basis * expected.motion.displacement, "rotated collision sweep")
	var ids := game.collision.solid_ids(14)
	for x: float in [5.9, 30.1]:
		var probe := ColliderSet.Aabb.try_new(Vector3(x, 1.2, 0), Vector3(0.05, 0.5, 0.3)).box
		var owners: Array[StringName] = []
		for index: int in game.colliders.overlapping(probe):
			owners.append(ids[index])
		var expected_owners := [&"D14-C-000-H-AFT/SWING"] if x < 6 else [&"D14-C-001-H-FORE/BLOCKER", &"D14-C-001-H-FORE/SWING"]
		assert_true(owners == expected_owners, "only the named passage gate and hardware sweep at X=%s: %s" % [x, owners])
