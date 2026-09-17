extends SimTestCase
## Port of the resolve.rs inline test module.

const TOL: float = Controller.PENETRATION_TOLERANCE
const RADIUS: float = Controller.CAPSULE_RADIUS

func standing(x: float, foot_y: float, z: float) -> Resolve.Capsule:
	var segment: float = Controller.CAPSULE_STANDING_HEIGHT - 2.0 * Controller.CAPSULE_RADIUS
	var capsule: Resolve.Capsule = Resolve.Capsule.new()
	capsule.foot = Vector3(x, foot_y + Controller.CAPSULE_RADIUS, z)
	capsule.head = Vector3(x, foot_y + Controller.CAPSULE_RADIUS + segment, z)
	return capsule

func box_between(corner_min: Vector3, corner_max: Vector3) -> ColliderSet.Aabb:
	return ColliderSet.Aabb.from_min_max(corner_min, corner_max).box

func scene(extra: Array) -> ColliderSet:
	var colliders := ColliderSet.new()
	colliders.insert(box_between(Vector3(-10.0, -1.0, -10.0), Vector3(10.0, 0.0, 10.0)))
	for aabb: ColliderSet.Aabb in extra:
		colliders.insert(aabb)
	return colliders

func test_head_on_motion_stops_at_the_wall() -> void:
	var world := scene([box_between(Vector3(2.0, 0.0, -4.0), Vector3(2.2, 3.2, 4.0))])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(5.0, 0.0, 0.0), world)
	assert_true(result.is_ok(), "head-on stop resolves")
	var expected: float = 2.0 - RADIUS - TOL
	assert_close(result.motion.displacement, Vector3(expected, 0.0, 0.0), "head-on")
	assert_true(result.motion.grounded, "standing on the floor")
	assert_vec3_array_equal(result.motion.contact_normals, [Vector3(-1.0, 0.0, 0.0)], "wall normal")

func test_diagonal_motion_slides_along_a_face_around_a_corner() -> void:
	var world := scene([box_between(Vector3(-10.0, 0.0, 2.0), Vector3(10.0, 3.2, 2.2))])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(10.0, 0.0, 3.0), world)
	assert_true(result.is_ok(), "corner slide resolves")
	assert_close(result.motion.displacement, Vector3(10.0, 0.0, 1.695), "corner slide")
	var gap: float = 2.0 - (result.motion.displacement.z + RADIUS)
	assert_float_in_range(gap, 0.0, TOL + 1e-6, "normal-axis gap must sit inside the tolerance band")
	assert_vec3_array_equal(result.motion.contact_normals, [Vector3(0.0, 0.0, -1.0)], "wall normal")

func test_a_corner_wedge_reports_both_face_normals() -> void:
	var wall_x := box_between(Vector3(2.0, 0.0, -10.0), Vector3(2.2, 3.2, 10.0))
	var wall_z := box_between(Vector3(-10.0, 0.0, 2.0), Vector3(10.0, 3.2, 2.2))
	var world := scene([wall_x, wall_z])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(5.0, 0.0, 5.0), world)
	assert_true(result.is_ok(), "wedge resolves within the production bound")
	var x_gap: float = 2.0 - (result.motion.displacement.x + RADIUS)
	var z_gap: float = 2.0 - (result.motion.displacement.z + RADIUS)
	assert_float_in_range(x_gap, 0.0, TOL + 1e-6, "wedge x gap must sit inside the tolerance band")
	assert_float_in_range(z_gap, 0.0, TOL + 1e-6, "wedge z gap must sit inside the tolerance band")
	assert_vec3_array_equal(result.motion.contact_normals, [Vector3(0.0, 0.0, -1.0), Vector3(-1.0, 0.0, 0.0)], "both face normals in first-hit order")

func test_step_up_onto_a_0p2_ledge_carries_the_capsule() -> void:
	var world := scene([box_between(Vector3(3.0, 0.0, -4.0), Vector3(6.0, 0.2, 4.0))])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(3.5, 0.0, 0.0), world)
	assert_true(result.is_ok(), "0.2 step resolves")
	assert_close(result.motion.displacement, Vector3(3.5, 0.2 + TOL, 0.0), "0.2 step")
	assert_true(result.motion.grounded, "standing on the ledge top")
	assert_true(result.motion.contact_normals.is_empty(), "a stepped-over ledge is not a contact")

func test_step_up_onto_a_0p4_ledge_is_refused() -> void:
	var world := scene([box_between(Vector3(3.0, 0.0, -4.0), Vector3(6.0, 0.4, 4.0))])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(5.0, 0.0, 0.0), world)
	assert_true(result.is_ok(), "0.4 refusal resolves")
	var expected: float = 3.0 - RADIUS - TOL
	assert_close(result.motion.displacement, Vector3(expected, 0.0, 0.0), "0.4 refusal")
	assert_true(result.motion.grounded, "still standing on the floor")
	assert_vec3_array_equal(result.motion.contact_normals, [Vector3(-1.0, 0.0, 0.0)], "wall normal")
	assert_true(Controller.STEP_UP_HEIGHT < 0.4, "the refusal must come from the frozen budget, not the geometry")

func test_thin_walls_do_not_tunnel_under_oversized_displacement() -> void:
	var world := scene([box_between(Vector3(5.0, 0.0, -4.0), Vector3(5.1, 3.2, 4.0))])
	var result := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3(50.0, 0.0, 0.0), world)
	assert_true(result.is_ok(), "thin wall resolves")
	var expected: float = 5.0 - RADIUS - TOL
	assert_close(result.motion.displacement, Vector3(expected, 0.0, 0.0), "thin wall")
	var face: float = result.motion.displacement.x + RADIUS
	assert_true(face < 5.0, "capsule face %s must stay short of the wall" % str(face))

func test_exceeding_the_iteration_bound_is_a_hard_error() -> void:
	var world := ColliderSet.new()
	world.insert(box_between(Vector3(2.0, 0.0, -10.0), Vector3(2.2, 3.2, 10.0)))
	world.insert(box_between(Vector3(-10.0, 0.0, 2.0), Vector3(10.0, 3.2, 2.2)))
	var capsule := standing(0.0, 0.0, 0.0)
	var displacement := Vector3(5.0, 0.0, 5.0)
	var bounded: Resolve.Result = Resolve.sweep_with_bound(capsule, displacement, world, 1)
	assert_true(bounded.error != null and bounded.error.equals(Resolve.ResolveError.sweep_bound_exceeded(1)), "one blocking iteration cannot settle a two-face wedge")
	assert_true(bounded.error != null and bounded.error._to_string().find("bound") != -1, "error message names the bound")
	var settled: Resolve.Result = Resolve.sweep_with_bound(capsule, displacement, world, Controller.SWEEP_ITERATION_BOUND)
	assert_true(settled.is_ok(), "production bound settles the wedge")
	assert_true(settled.motion.displacement.x > 0.0 and settled.motion.displacement.z > 0.0, "wedge motion made progress")
	var zero_bound: Resolve.Result = Resolve.sweep_with_bound(capsule, displacement, world, 0)
	assert_true(zero_bound.error != null and zero_bound.error.equals(Resolve.ResolveError.sweep_bound_exceeded(0)), "a zero bound errors naming zero")

func test_grounding_follows_the_support_face() -> void:
	var world := scene([])
	var on_floor := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3.ZERO, world)
	assert_true(on_floor.is_ok(), "at-rest resolve")
	assert_vec3_equal(on_floor.motion.displacement, Vector3.ZERO, "no displacement at rest")
	assert_true(on_floor.motion.grounded, "standing still on the floor reads grounded")
	assert_true(on_floor.motion.contact_normals.is_empty(), "no contacts at rest")
	var mid_air := Resolve.resolve_motion(standing(0.0, 3.0, 0.0), Vector3.ZERO, world)
	assert_true(mid_air.is_ok(), "mid-air resolve")
	assert_false(mid_air.motion.grounded, "mid-air reads ungrounded")
	var empty_world := ColliderSet.new()
	var nowhere := Resolve.resolve_motion(standing(0.0, 0.0, 0.0), Vector3.ZERO, empty_world)
	assert_true(nowhere.is_ok(), "empty world resolve")
	assert_false(nowhere.motion.grounded, "an empty world reads ungrounded")

func test_falling_lands_tolerance_short_and_reads_grounded() -> void:
	var world := scene([])
	var result := Resolve.resolve_motion(standing(0.0, 3.0, 0.0), Vector3(0.0, -5.0, 0.0), world)
	assert_true(result.is_ok(), "landing resolves")
	assert_close(result.motion.displacement, Vector3(0.0, -(3.0 - TOL), 0.0), "landing")
	assert_vec3_array_equal(result.motion.contact_normals, [Vector3.UP], "floor normal")
	assert_true(result.motion.grounded, "grounded after landing")

func test_start_penetration_is_an_error_naming_the_collider() -> void:
	var world := ColliderSet.new()
	world.insert(box_between(Vector3(-5.0, -5.0, -5.0), Vector3(-4.0, -4.0, -4.0)))
	world.insert(box_between(Vector3(-1.0, -1.0, -1.0), Vector3(1.0, 1.0, 1.0)))
	var embedded: Resolve.Capsule = Resolve.Capsule.new()
	embedded.foot = Vector3.ZERO
	embedded.head = Vector3(0.0, 1.15, 0.0)
	var result := Resolve.resolve_motion(embedded, Vector3(1.0, 0.0, 0.0), world)
	assert_true(result.error != null and result.error.equals(Resolve.ResolveError.start_penetration(1)), "an embedded start names the collider index")

func test_non_finite_inputs_are_rejected() -> void:
	var world := ColliderSet.new()
	var capsule := standing(0.0, 0.0, 0.0)
	var bad_foot_capsule: Resolve.Capsule = Resolve.Capsule.new()
	bad_foot_capsule.foot = Vector3(NAN, 0.0, 0.0)
	bad_foot_capsule.head = capsule.head
	var bad_foot := Resolve.resolve_motion(bad_foot_capsule, Vector3.ZERO, world)
	assert_true(bad_foot.error != null and bad_foot.error.equals(Resolve.ResolveError.non_finite_input(Resolve.ResolveError.NonFiniteInput.CAPSULE_FOOT)), "non-finite foot rejected")
	var bad_head_capsule: Resolve.Capsule = Resolve.Capsule.new()
	bad_head_capsule.foot = capsule.foot
	bad_head_capsule.head = Vector3(0.0, INF, 0.0)
	var bad_head := Resolve.resolve_motion(bad_head_capsule, Vector3.ZERO, world)
	assert_true(bad_head.error != null and bad_head.error.equals(Resolve.ResolveError.non_finite_input(Resolve.ResolveError.NonFiniteInput.CAPSULE_HEAD)), "non-finite head rejected")
	var bad_move := Resolve.resolve_motion(capsule, Vector3(1.0, NAN, 0.0), world)
	assert_true(bad_move.error != null and bad_move.error.equals(Resolve.ResolveError.non_finite_input(Resolve.ResolveError.NonFiniteInput.DISPLACEMENT)), "non-finite displacement rejected")

func test_resolved_displacement_reaches_the_final_foot_position() -> void:
	var world := scene([box_between(Vector3(2.0, 0.0, -4.0), Vector3(2.2, 3.2, 4.0))])
	var capsule := standing(0.0, 0.0, 0.0)
	var result := Resolve.resolve_motion(capsule, Vector3(5.0, 0.0, 0.0), world)
	assert_true(result.is_ok(), "first tick resolves")
	var expected: float = 2.0 - RADIUS - TOL
	assert_close(result.motion.displacement, Vector3(expected, 0.0, 0.0), "delta")
	var follow_capsule: Resolve.Capsule = Resolve.Capsule.new()
	follow_capsule.foot = capsule.foot + result.motion.displacement
	follow_capsule.head = capsule.head + result.motion.displacement
	var follow_up := Resolve.resolve_motion(follow_capsule, Vector3(5.0, 0.0, 0.0), world)
	assert_true(follow_up.is_ok(), "second tick resolves")
	assert_close(follow_up.motion.displacement, Vector3.ZERO, "held against the wall")
