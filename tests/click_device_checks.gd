extends SceneTree
## Native device events through Player, with optional windowed capture output.

var player: Player
var game: Game
var stepper: GameStep
var check := SimTestCase.new()
var capture_dir: String

func _initialize() -> void:
	if not OS.get_cmdline_user_args().is_empty():
		capture_dir = OS.get_cmdline_user_args()[0]
	call_deferred("run")

func _fixture(foot: Vector3) -> void:
	game.phase = Phase.Machine.new(Phase.Wake.STANDING)
	var capsule := Resolve.Capsule.new()
	capsule.foot = foot
	capsule.head = foot + Vector3.UP * 1.15
	player.motion.locomotion = Locomotion.start(game.layout, game.collision, 14, Walk.WalkState.start(game.phase, capsule).state).state
	player.motion.objectives.cancel()
	player.present()

func _aim(target: Vector3) -> void:
	var delta := (target - player.motion.eye(game)).normalized()
	player._look_yaw = atan2(-delta.x, -delta.z)
	player._look_pitch = asin(delta.y)
	player.present()

func _key(code: Key, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func _click(pixel: Vector2, pressed: bool = true) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = pressed
	event.position = pixel
	event.global_position = pixel
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func _motion(pixels: Vector2) -> void:
	var event := InputEventMouseMotion.new()
	event.relative = pixels
	Input.parse_input_event(event)
	Input.flush_buffered_events()

func _capture(name: String) -> void:
	if capture_dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	check.assert_int_equal(image.get_width(), 2304, "capture width")
	check.assert_int_equal(image.get_height(), 1296, "capture height")
	check.assert_int_equal(image.save_png(capture_dir.path_join(name + ".png")), OK, "capture writes")

func run() -> void:
	game = Game.new(0)
	var scene := Node3D.new()
	root.add_child(scene)
	var ship: ShipScene
	if not capture_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(capture_dir)
		ship = ShipScene.build_into(scene, game, false)
	player = Player.build(game, null)
	player.scripted = true
	scene.add_child(player)
	player.scripted = false
	if ship != null:
		player.rod = ship.rod
	stepper = GameStep.new(game, player)
	_fixture(Vector3(18, 0.305, 0))
	_aim(Vector3(20, 0, 0.5))
	root.grab_focus()
	var capture_deadline := Time.get_ticks_msec() + 10_000
	while true:
		if Time.get_ticks_msec() >= capture_deadline:
			print("DEVICE CLICK FAIL startup timed out after 10 s waiting for window focus and captured mouse mode (focused=%s, mouse_mode=%d)" % [root.has_focus(), Input.mouse_mode])
			quit(1)
			return
		if root.has_focus():
			player._set_mouse_capture(true)
		await process_frame
		if root.has_focus() and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			break
	await _capture("crosshair-captured")
	# A corner-position event while captured must still aim at screen center.
	_click(Vector2(2, 2))
	var objective := player.plane.take_objective()
	if objective == null:
		var center := root.get_visible_rect().size * 0.5
		print("CLICK DEBUG origin=%s ray=%s mode=%d direct=%s" % [player.camera.project_ray_origin(center), player.camera.project_ray_normal(center), Input.mouse_mode, ClickPicker.pick(player.camera.project_ray_origin(center), player.camera.project_ray_normal(center), game, player.motion, player.interactions)])
	check.assert_true(objective != null and objective.kind == ClickObjective.Kind.FLOOR, "captured click resolves floor")
	if objective != null:
		check.assert_close(objective.point, Vector3(20, 0, 0.5), "captured click uses screen center, not event position")
		player.plane.offer_objective(objective)
	check.assert_int_equal(player.plane.pending_edges(), 0, "click never also activates or interacts")
	stepper.advance()
	_click(Vector2(2, 2), false)
	await process_frame
	await _capture("floor-marker-walking")
	check.assert_true(player.motion.objectives.current != null, "floor marker has active objective")
	_motion(Vector2(20, -10))
	var before_look := player.look_angles()
	stepper.advance()
	check.assert_true(player.look_angles() != before_look, "captured mouse turns head while following")
	check.assert_true(player.motion.objectives.current != null, "look does not cancel walking")
	_key(KEY_TAB, true)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_VISIBLE, "Tab frees cursor")
	check.assert_true(player._mouse_pixels == Vector2.ZERO, "release clears mouse motion")
	await process_frame
	await _capture("tab-free-cursor")
	before_look = player.look_angles()
	_motion(Vector2(80, 40))
	stepper.advance()
	check.assert_true(player.look_angles() == before_look, "free cursor motion does not turn head")
	# The free cursor can select a point away from the center ray.
	var pixel := root.get_visible_rect().size * Vector2(0.63, 0.58)
	var expected := ClickPicker.pick(player.camera.project_ray_origin(pixel), player.camera.project_ray_normal(pixel), game, player.motion, player.interactions)
	_click(pixel)
	objective = player.plane.take_objective()
	check.assert_true(expected != null and objective != null, "released click resolves under pointer")
	if expected != null and objective != null:
		check.assert_vec3_equal(objective.point, expected.point, "free click uses cursor pixel")
	_click(pixel, false)
	_key(KEY_D, true)
	stepper.advance()
	check.assert_true(player.look_angles().x != before_look.x, "keyboard look works while free")
	_key(KEY_D, false)
	player._device_released_at.clear()
	_key(KEY_TAB, false)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_CAPTURED, "Tab release recaptures")
	_motion(Vector2(10, 10))
	_key(KEY_ESCAPE, true)
	_key(KEY_ESCAPE, false)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_VISIBLE, "Escape releases")
	check.assert_true(player._mouse_pixels == Vector2.ZERO, "Escape clears relative motion")
	_key(KEY_TAB, true)
	_key(KEY_TAB, false)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_CAPTURED, "Tab deliberately recaptures after Escape")
	_key(KEY_TAB, true)
	player.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_OUT)
	_key(KEY_TAB, false)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_VISIBLE, "focus loss cancels pending recapture")
	player.notification(MainLoop.NOTIFICATION_APPLICATION_FOCUS_IN)
	check.assert_int_equal(Input.mouse_mode, Input.MOUSE_MODE_VISIBLE, "focus gain does not capture")
	_key(KEY_TAB, true)
	_key(KEY_TAB, false)
	# The real mouse-button path walks to and picks up the visible rod.
	_fixture(Vector3(15, 0.305, 8.3))
	_aim(game.layout.anchor(&"D14-BAY-ROD").origin + Vector3.UP * 0.03)
	_click(Vector2(1, 1))
	check.assert_int_equal(player.plane.pending_edges(), 0, "rod click is an objective, not a direct edge")
	for tick: int in range(180):
		stepper.advance()
		if tick % 30 == 0:
			await process_frame
	_click(Vector2(1, 1), false)
	check.assert_true(player.motion.rod_carried, "device click walks to and picks up rod")
	check.assert_true(player.motion.objectives.current == null, "pickup objective is complete")
	check.assert_true(player.motion.capsule().foot.x < 15, "device pickup required approach")
	check.assert_true(player.motion.failure().is_empty(), player.motion.failure())
	await _capture("rod-click-picked-up")
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	print("DEVICE CLICK %s %s" % ["PASS" if check.failure.is_empty() else "FAIL", check.failure])
	quit(0 if check.failure.is_empty() else 1)
