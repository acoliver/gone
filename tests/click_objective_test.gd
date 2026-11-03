extends SimTestCase

const Objective := preload("res://sim/click_objective.gd")

func test_follower_reaches_point_with_normal_walk_and_free_look() -> void:
	var game := Game.new(0)
	game.phase = Phase.Machine.new(Phase.Wake.STANDING)
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(18, 0.305, 0)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var walk := Walk.WalkState.start(game.phase, capsule).state
	var follower := Objective.Follower.new()
	var goal := Vector3(22, 0, 0)
	follower.set_objective(Objective.floor_point(goal, 14))
	for tick: int in range(500):
		var before := walk.capsule().foot
		var yaw := float(tick) / 50.0
		var movement: Vector2 = follower.movement(before, yaw, Vector2.ZERO)
		var result := walk.step(Walk.MoveIntent.try_new(yaw, movement.x, movement.y).intent, Sim.LOGICAL_TICK_SECS, game.collision.deck_set(14))
		assert_true(result.is_ok(), "objective uses ordinary collision walk")
		walk.end_tick()
		follower.observe(before, walk.capsule().foot)
	assert_true(follower.current == null, "reached objective expires")
	assert_true(Vector2(walk.capsule().foot.x - goal.x, walk.capsule().foot.z - goal.z).length() <= 0.25, "including normal stop easing, ends within 25cm")

func test_blocked_objective_expires_after_thirty_no_progress_ticks() -> void:
	var follower := Objective.Follower.new()
	follower.set_objective(Objective.floor_point(Vector3(4, 0, 0), 14))
	for tick: int in range(29):
		follower.movement(Vector3.ZERO, 0, Vector2.ZERO)
		follower.observe(Vector3.ZERO, Vector3.ZERO)
	assert_true(follower.current != null, "not expired before half second")
	follower.observe(Vector3.ZERO, Vector3.ZERO)
	assert_true(follower.current == null, "blocked for half second cancels")

func test_keys_cancel_and_scripted_objectives_are_single_consumption() -> void:
	var follower := Objective.Follower.new()
	follower.set_objective(Objective.floor_point(Vector3(4, 0, 0), 14))
	assert_true(follower.movement(Vector3.ZERO, 0, Vector2(0, -1)) == Vector2(0, -1), "key wins")
	assert_true(follower.current == null, "key cancels objective")
	var adapter := InputPlane.ScriptedAdapter.new()
	var plane := InputPlane.new()
	adapter.objective(Objective.act(&"D14-BAY-ROD", 14))
	adapter.offer_tick(plane)
	assert_true(plane.take_objective().target_id == &"D14-BAY-ROD", "typed objective crosses shared input")
	assert_true(plane.take_objective() == null, "take once")
	adapter.offer_tick(plane)
	assert_true(plane.take_objective() == null, "not offered again")
	plane.offer_objective(Objective.floor_point(Vector3.ONE, 14))
	plane.end_frame()
	assert_true(plane.take_objective() == null, "unconsumed objectives expire")

func test_follower_is_deterministic() -> void:
	var a := Objective.Follower.new()
	var b := Objective.Follower.new()
	a.set_objective(Objective.floor_point(Vector3(5, 0, -3), 14))
	b.set_objective(Objective.floor_point(Vector3(5, 0, -3), 14))
	var position := Vector3.ZERO
	for tick: int in range(120):
		var intent_a: Vector2 = a.movement(position, tick * 0.1, Vector2.ZERO)
		var intent_b: Vector2 = b.movement(position, tick * 0.1, Vector2.ZERO)
		assert_true(intent_a == intent_b, "identical fixed-tick intents")
		var next := position + Walk.MoveIntent.try_new(tick * 0.1, intent_a.x, intent_a.y).intent.world_direction() * 0.01
		a.observe(position, next)
		b.observe(position, next)
		position = next
