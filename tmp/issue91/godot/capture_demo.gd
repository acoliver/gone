extends SceneTree

const GameModule = preload("res://app/game.gd")
const ShipSceneModule = preload("res://app/ship_scene.gd")
const Geometry = preload("res://sim/ship_geometry.gd")
const OUT := "res://tmp/issue91/godot/demo"
const SIZE := Vector2i(1600, 900)

var scene_root: Node3D
var game
var ship
var camera: Camera3D
var capture_names: Array[String] = []

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "windowed renderer required")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	root.size = SIZE
	DisplayServer.window_set_size(SIZE)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	await _setup(false)
	await _shot("room-overview-red-west", Vector3(23.5, 1.65, -2.4), Vector3(29.5, 1.45, -9.4), 80.0, "Generator")
	await _shot("room-overview-red-east", Vector3(30.5, 1.65, -2.4), Vector3(24.5, 1.45, -9.4), 80.0, "Generator")
	var board: StatusBoard = ship.power_room.status_board
	var board_center: Vector3 = board.global_position
	var board_eye_3m := board_center + Vector3(1.1, -0.45, 2.79)
	board_eye_3m.y = 1.65
	await _shot("north-board-native-3m", board_eye_3m, board_center, 66.0, "StatusBoard")
	await _shot("north-board-native-2m", Vector3(board_center.x, 1.65, board_center.z + 2.0), board_center, 66.0, "StatusBoard")
	board.perception.text_changed()
	var board_forward := (board_center - board_eye_3m).normalized()
	for _tick: int in range(DisplayPerception.FIRST_HOLD + DisplayPerception.FIRST_RAMP):
		board.tick_attention(board_eye_3m, board_forward)
	assert(is_equal_approx(board.perception.perceive, 1.0), "simulated player attention fully resolves the board")
	await _shot("north-board-perceived-3m", board_eye_3m, board_center, 66.0, "StatusBoard")
	await _shot("north-board-perceived-2m", Vector3(board_center.x, 1.65, board_center.z + 2.0), board_center, 66.0, "StatusBoard")
	var board_texture := load("res://assets/props/status_panel/board-native.png") as Texture2D
	assert(board_texture != null, "status board image is available")
	var texture_image := board_texture.get_image()
	assert(texture_image != null and texture_image.get_width() > 0, "status board image has decoded pixels")
	var board_path := ProjectSettings.globalize_path("res://tmp/issue91/godot/board-viewport.png")
	assert(texture_image.save_png(board_path) == OK, "status board texture readback saves")
	var active: Node3D = ship.power_room.get_node("ConsoleStation1")
	var facing := Vector3(sin(Geometry.console_stations()[1].yaw), 0.0, cos(Geometry.console_stations()[1].yaw))
	var keyboard: Node3D = active.get_node("KeyboardModel")
	var keyboard_bounds := _combined_aabb(keyboard)
	var lip := _front_lip(keyboard_bounds, facing)
	var keyboard_center := keyboard_bounds.get_center()
	var console_eye := active.global_transform * Vector3(0, 1.65, 1.10)
	var display_target: Vector3 = active.get_node("ShipDisplay").global_position
	assert(game.console_state == GameModule.ConsoleState.INACTIVE, "inactive captures happen before generator activation")
	ship.power_room.console_display.perception.perceive = 1.0
	ship.power_room.console_display._apply_perception()
	print("CONSOLE_CAPTURE_STATE active-console-inactive ", game.console_state)
	await _shot("active-console-inactive", console_eye, display_target, 60.0, "TextSurface")
	ship.power_room.console_display.perception.perceive = 0.0
	ship.power_room.console_display._apply_perception()
	assert(game.console_state == GameModule.ConsoleState.INACTIVE, "inactive native capture happens before generator activation")
	print("CONSOLE_CAPTURE_STATE active-console-inactive-native ", game.console_state)
	await _shot("active-console-inactive-native", console_eye, display_target, 60.0, "TextSurface")
	game.press_console()
	for i in range(36):
		await process_frame
		ship.power_room.process_frame(1.0 / 60.0)
	await _shot("room-overview-white-west", Vector3(23.5, 1.65, -2.4), Vector3(29.5, 1.45, -9.4), 80.0, "Generator")
	await _shot("room-overview-white-east", Vector3(30.5, 1.65, -2.4), Vector3(24.5, 1.45, -9.4), 80.0, "Generator")
	ship.power_room.console_display.perception.perceive = 0.0
	ship.power_room.console_display._apply_perception()
	assert(game.console_state == GameModule.ConsoleState.ACTIVE, "running captures follow generator activation")
	print("CONSOLE_CAPTURE_STATE active-console-running-native ", game.console_state)
	await _shot("active-console-running-native", console_eye, display_target, 60.0, "TextSurface")
	ship.power_room.console_display.perception.perceive = 1.0
	ship.power_room.console_display._apply_perception()
	assert(game.console_state == GameModule.ConsoleState.ACTIVE, "running perceived capture follows generator activation")
	print("CONSOLE_CAPTURE_STATE active-console-running ", game.console_state)
	await _shot("active-console-running", console_eye, display_target, 60.0, "TextSurface")
	var active_glass := active.get_node("ScreenGlass") as MeshInstance3D
	await _shot("active-console-oblique-left", _oblique_eye(active_glass, -1.0), display_target, 60.0, "TextSurface")
	var dead_glass := ship.power_room.get_node("ConsoleStation0/ScreenGlass") as MeshInstance3D
	await _shot("dead-console-oblique-right", _oblique_eye(dead_glass, 1.0), dead_glass.global_position, 60.0, "ScreenGlass")
	await _shot("west-wall", Vector3(25.0, 1.65, -5.7), Vector3(21.5, 1.35, -5.7), 84.0, "PowerWallWest")
	await _shot("east-wall", Vector3(29.0, 1.65, -5.7), Vector3(32.5, 1.35, -5.7), 84.0, "PowerWallEast")
	var keyboard_eye := lip + facing * 0.45
	keyboard_eye.y = 1.65
	await _shot("keyboard-close", keyboard_eye, keyboard_center, 54.0, "KeyboardModel")
	await _teardown()
	print("DEMO_CAPTURES_OK ", JSON.stringify(capture_names))
	quit(0)

func _setup(white: bool) -> void:
	game = GameModule.new(9101)
	game.hallway_lit = true
	if white:
		game.press_console()
	scene_root = Node3D.new()
	scene_root.name = "DemoRoot"
	root.add_child(scene_root)
	ship = ShipSceneModule.build_into(scene_root, game)
	camera = Camera3D.new()
	camera.name = "DemoCamera"
	camera.current = true
	camera.fov = 76.0
	camera.near = 0.05
	scene_root.add_child(camera)
	for i in range(38):
		await process_frame
		ship.power_room.process_frame(1.0 / 60.0)
	if white:
		ship.power_room.console_display.perception.perceive = 1.0
		ship.power_room.console_display._apply_perception()
		ship.power_room.status_board.perception.perceive = 1.0
		ship.power_room.status_board.tick_attention(Vector3(27, 1.65, -8), Vector3(0, 0, -1))
	await _settle()

func _teardown() -> void:
	if scene_root != null:
		scene_root.queue_free()
		await process_frame
		scene_root = null

func _shot(name: String, eye: Vector3, target: Vector3, fov: float, intended: String = "") -> void:
	_assert_eye_clear(eye)
	var hit := _first_mesh_hit(eye, eye + (target - eye) * 1.02)
	print("RAY_HIT ", name, " eye=", eye, " target=", target, " first=", hit)
	assert(not hit.is_empty(), "camera ray reaches visible geometry for " + name)
	if intended != "":
		assert(hit.contains(intended) or intended.contains(hit), "camera first hit is the intended object for " + name + ": " + hit)
	camera.fov = fov
	camera.global_position = eye
	camera.look_at(target, Vector3.UP)
	await _settle()
	var path := ProjectSettings.globalize_path(OUT.path_join(name + ".png"))
	var image: Image = root.get_texture().get_image()
	var error := image.save_png(path)
	assert(error == OK, "PNG save succeeds for " + name)
	if name.begins_with("active-console"):
		print("CONSOLE_MEASUREMENT ", name)
		var checked: bool = load("res://tests/console_screen_capture.gd").check_background(image, camera, ship.power_room.get_node("ConsoleStation1"))
		assert(checked, "captured console text contrasts with its lit glass, distinct from the body")
	capture_names.append(path)
	print("CAPTURE ", name, " camera_transform=", camera.global_transform)

func _assert_eye_clear(eye: Vector3) -> void:
	var stack: Array[Node] = [scene_root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node is MeshInstance3D and node.mesh != null:
			var bounds: AABB = _world_aabb(node.get_aabb(), node.global_transform)
			assert(not bounds.has_point(eye), "camera eye is inside mesh " + str(node.get_path()))
		for child: Node in node.get_children():
			stack.append(child)

func _first_mesh_hit(eye: Vector3, target: Vector3) -> String:
	var best := INF
	var result := ""
	var stack: Array[Node] = [scene_root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node is MeshInstance3D and node.mesh != null and node.is_visible_in_tree():
			var faces: PackedVector3Array = node.mesh.get_faces()
			for index: int in range(0, faces.size(), 3):
				var a: Vector3 = node.global_transform * faces[index]
				var b: Vector3 = node.global_transform * faces[index + 1]
				var c: Vector3 = node.global_transform * faces[index + 2]
				var point: Variant = Geometry3D.segment_intersects_triangle(eye, target, a, b, c)
				if point != null:
					var distance := eye.distance_to(point)
					if distance < best:
						best = distance
						result = str(node.get_path())
		for child: Node in node.get_children():
			stack.append(child)
	if result.is_empty():
		return _first_aabb_hit(eye, target)
	return result

func _first_aabb_hit(eye: Vector3, target: Vector3) -> String:
	var direction := target - eye
	var distance := direction.length()
	if distance <= 0.001:
		return ""
	direction /= distance
	var best := distance + 1.0
	var result := ""
	var stack: Array[Node] = [scene_root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node is MeshInstance3D and node.mesh != null and node.is_visible_in_tree():
			var bounds: AABB = _world_aabb(node.get_aabb(), node.global_transform)
			var entry := _ray_aabb(eye, direction, bounds)
			if entry >= 0.0 and entry < best:
				best = entry
				result = str(node.get_path())
		for child: Node in node.get_children():
			stack.append(child)
	return result

func _world_aabb(local_bounds: AABB, transform: Transform3D) -> AABB:
	var result := AABB()
	var initialized := false
	for x: float in [local_bounds.position.x, local_bounds.end.x]:
		for y: float in [local_bounds.position.y, local_bounds.end.y]:
			for z: float in [local_bounds.position.z, local_bounds.end.z]:
				var point := transform * Vector3(x, y, z)
				if initialized:
					result = result.expand(point)
				else:
					result = AABB(point, Vector3.ZERO)
					initialized = true
	return result

func _ray_aabb(origin: Vector3, direction: Vector3, bounds: AABB) -> float:
	var near := 0.0
	var far := INF
	for axis: int in range(3):
		var o: float = origin[axis]
		var d: float = direction[axis]
		var low: float = bounds.position[axis]
		var high: float = low + bounds.size[axis]
		if is_zero_approx(d):
			if o < low or o > high:
				return -1.0
			continue
		var a := (low - o) / d
		var b := (high - o) / d
		if a > b:
			var swap := a
			a = b
			b = swap
		near = maxf(near, a)
		far = minf(far, b)
		if near > far:
			return -1.0
	return near

func _combined_aabb(parent: Node3D) -> AABB:
	var result := AABB()
	var initialized := false
	var stack: Array[Node] = [parent]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node is MeshInstance3D and node.mesh != null:
			var bounds: AABB = _world_aabb(node.get_aabb(), node.global_transform)
			result = bounds if not initialized else result.merge(bounds)
			initialized = true
		for child: Node in node.get_children():
			stack.append(child)
	assert(initialized, "placed model has visual geometry")
	return result

func _front_lip(bounds: AABB, facing: Vector3) -> Vector3:
	var lip := bounds.get_center()
	var support := 0.0
	for x: float in [bounds.position.x, bounds.end.x]:
		for z: float in [bounds.position.z, bounds.end.z]:
			support = maxf(support, Vector3(x - lip.x, 0.0, z - lip.z).dot(facing))
	lip += facing * support
	return lip

func _settle() -> void:
	for i in range(8):
		await process_frame
	await RenderingServer.frame_post_draw

func _oblique_eye(glass: MeshInstance3D, side: float) -> Vector3:
	var normal_distance := cos(deg_to_rad(50.0))
	var up_distance := (1.65 - glass.global_position.y - glass.global_basis.z.y * normal_distance) / glass.global_basis.y.y
	var right_distance := side * sqrt(pow(sin(deg_to_rad(50.0)), 2) - up_distance * up_distance)
	return glass.global_position + glass.global_basis.z * normal_distance + glass.global_basis.y * up_distance + glass.global_basis.x * right_distance
