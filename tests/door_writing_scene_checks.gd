extends SceneTree

class NoParticlePresentation:
	extends Hazards
	func process_frame(_delta: float) -> void:
		pass

var checks := SimTestCase.new()
var game: Game
var scene: ShipScene
var player: Player
var step: GameStep
var world: Node3D

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	checks.begin_test()
	game = Game.new(0)
	game.phase.wake_complete()
	world = Node3D.new()
	# Use the production navigation builders without the unrelated bay particles.
	scene = ShipScene.new()
	scene._parent = world
	scene._game = game
	scene.text_cache = ShipTextCache.new()
	scene.text_cache.pair_ready.connect(scene._labels_ready)
	world.add_child(scene.text_cache)
	scene.hatch = Hatch.build()
	scene.hatch.transform = game.layout.bay_to_world()
	world.add_child(scene.hatch)
	scene.hazards = NoParticlePresentation.new()
	scene.hazards.auto_bursts = false
	world.add_child(scene.hazards)
	for id: StringName in [&"D14-C-000-H-AFT", &"D14-C-001-H-FORE"]: scene._add_hatch(id)
	scene.stream = ShipStream.build(scene, game, world)
	world.add_child(scene.stream)
	root.add_child(world)
	player = Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	world.add_child(player)
	step = GameStep.new(game, player)
	step.ship_scene = scene
	step.door_views = scene.door_views
	player.adapter.press(InputPlane.Buttons.ACTIVATE)
	for _tick: int in range(Exit.EXIT_POSE_COUNT): step.advance()
	checks.assert_int_equal(player.motion.state(), PlayerMotion.BodyState.WALK, "real Player stands")
	await call(OS.get_cmdline_user_args()[0])
	world.queue_free()
	await process_frame
	if not checks.failure.is_empty(): printerr(checks.failure)
	quit(0 if checks.failure.is_empty() else 1)

func _stand(foot: Vector3, yaw: float) -> void:
	# Fixture placement only. All look, attention and door work uses real input ticks.
	var capsule := player.motion.capsule()
	var offset := Vector3(foot.x - capsule.foot.x, 0, foot.z - capsule.foot.z)
	capsule.foot += offset
	capsule.head += offset
	player.motion.locomotion = Locomotion.start(game.layout, game.collision, 14, Walk.WalkState.start(game.phase, capsule).state).state
	player.adapter.look(yaw - player.look_angles().x, -player.look_angles().y)
	scene.prepare_near(foot)
	var frames := 0
	while scene.text_cache.pending_count() > 0:
		await process_frame
		frames += 1
		assert(frames < 120, "door writing raster completes before reading")

func _reading(id: StringName) -> void:
	var state := game.label_attention.state(id)
	checks.assert_false(game.writing_memory.has_resolved, "fresh Game has no completed reading")
	checks.assert_float_equal(state.perceive, 0, "fresh face is native")
	for _tick: int in range(DisplayPerception.FIRST_HOLD): step.advance()
	checks.assert_float_equal(state.perceive, 0, "full first native hold is preserved")
	for _tick: int in range(DisplayPerception.FIRST_RAMP + 3): step.advance()
	checks.assert_float_equal(player.look_angles().y, 0, "logical gaze remains level")
	checks.assert_float_equal(player.sim_forward().y, 0, "no camera aiming")
	checks.assert_float_equal(state.perceive, 1, "level door-center gaze resolves within first hold+ramp+3")
	checks.assert_true(game.writing_memory.has_resolved, "navigation completes the shared first-reading memory")
	var console := DisplayPerception.new(game.writing_memory)
	for _tick: int in range(DisplayPerception.LATER_HOLD + DisplayPerception.LATER_RAMP): console.tick(true)
	checks.assert_float_equal(console.perceive, 1, "console inherits navigation's completed reading")
	player.adapter.look(PI / 2, 0)
	for _tick: int in range(DisplayPerception.DECAY): step.advance()
	checks.assert_float_equal(state.perceive, 0, "turning real Player away restores native")

func check_hatch() -> void:
	var id: StringName = &"D14-C-001-H-FORE/FORE"
	await _stand(Vector3(28.5, 0, 0), -PI / 2)
	_reading(id)
	var label: ShipLabel = scene.labels[id]
	var closed := label.global_transform
	checks.assert_true(label.get_parent().name == "Leaf", "writing is a child of the swinging leaf, not a bulkhead sign")
	var local := label.transform
	player.adapter.look(-PI / 2, 0)
	step.advance()
	for _attempt: int in range(HatchResistance.schedule(0, &"D14-C-001-H-FORE").weights.size()):
		player.adapter.press(InputPlane.Buttons.INTERACT)
		step.advance()
		for _tick: int in range(6): step.advance()
	for _tick: int in range(48): step.advance()
	checks.assert_int_equal(game.doors.snapshot(&"D14-C-001-H-FORE").state, Doors.State.OPEN, "real selected presses open the hatch")
	checks.assert_true(label.transform == local, "label retains its leaf-local placement")
	checks.assert_true(label.global_position.distance_to(closed.origin) > 0.5, "opened leaf carries writing away from closed anchor")
	checks.assert_true(label.global_basis.z.dot(closed.basis.z) < 0.01, "writing turns ninety degrees with leaf")
	var face: LabelAttention.Face = game.label_attention._faces[id]
	checks.assert_true(face.frame.is_equal_approx(label.global_transform), "attention uses the swung face, never the old bulkhead anchor")
	# Preparing the aft section now also builds its six regular-door plates.
	checks.assert_int_equal(scene.labels.size(), 15, "nine hatch/lift faces plus six regular-door plates")

func check_lift() -> void:
	await _stand(Vector3(33, 0, 0), PI)
	_reading(&"D14-C-001-LIFT")
	var label: ShipLabel = scene.labels[&"D14-C-001-LIFT"]
	checks.assert_true(label.get_parent().name == "LiftDoors", "lift writing is on the door pair")
	checks.assert_close(label.global_position, Vector3(33, 1.82, 1.488), "aft lift door anchor")
	checks.assert_vec3_equal(label.global_basis.z, Vector3.FORWARD, "lift writing reads straight on")
