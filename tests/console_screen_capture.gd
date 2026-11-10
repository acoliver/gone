extends SceneTree
## Windowed regression: godot --path . --resolution 1600x900 -s res://tests/console_screen_capture.gd

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "pixel regression requires the windowed renderer")
	root.size = Vector2i(1600, 900)
	var game := Game.new(9101)
	game.hallway_lit = true
	var scene := Node3D.new()
	root.add_child(scene)
	var ship := ShipScene.build_into(scene, game)
	var station := ship.power_room.get_node("ConsoleStation1") as Node3D
	var camera := Camera3D.new()
	camera.fov = 60.0
	camera.near = 0.05
	camera.current = true
	scene.add_child(camera)
	camera.global_position = station.global_transform * Vector3(0, 1.65, 1.10)
	camera.look_at(station.get_node("ShipDisplay").global_position, Vector3.UP)
	game.press_console()
	for tick in range(48):
		ship.power_room.process_frame(1.0 / 60.0)
		await process_frame
	for perceive: float in [0.0, 1.0]:
		ship.power_room.console_display.perception.perceive = perceive
		ship.power_room.console_display._apply_perception()
		for frame in range(8):
			await process_frame
		await RenderingServer.frame_post_draw
		if not check_background(root.get_texture().get_image(), camera, station):
			push_error("console screen pixel regression failed")
			quit(1)
			return
	print("CONSOLE_SCREEN_PIXELS_OK")
	quit()

static func check_background(image: Image, camera: Camera3D, station: Node3D) -> bool:
	var glass := station.get_node("ScreenGlass") as MeshInstance3D
	var size := (glass.mesh as BoxMesh).size
	var maximum_screen := 0.0
	for x: float in [-0.35, 0.0, 0.35]:
		for y: float in [-0.43, 0.43]:
			var world := glass.global_transform * Vector3(size.x * x, size.y * y, 0.001)
			var pixel := Vector2i(camera.unproject_position(world).round())
			var luma := _patch_luma(image, pixel)
			maximum_screen = maxf(maximum_screen, luma)
			print("SCREEN_PIXEL ", pixel, " luma=", luma)
			if luma >= 0.12:
				push_error("active screen background must stay dark: %s luma=%f" % [pixel, luma])
	var minimum_body := 1.0
	for side: float in [-1.0, 1.0]:
		var world := glass.global_transform * Vector3(side * (size.x * 0.5 + 0.025), 0, -0.02)
		var pixel := Vector2i(camera.unproject_position(world).round())
		var luma := _patch_luma(image, pixel)
		minimum_body = minf(minimum_body, luma)
		print("BODY_PIXEL ", pixel, " luma=", luma)
	print("SCREEN_CONTRAST max_screen=", maximum_screen, " min_body=", minimum_body)
	return maximum_screen < 0.12 and minimum_body > maximum_screen + 0.10

static func _patch_luma(image: Image, center: Vector2i) -> float:
	assert(Rect2i(Vector2i.ZERO, image.get_size()).encloses(Rect2i(center - Vector2i.ONE, Vector2i(3, 3))), "sample stays within the capture")
	var sum := 0.0
	for y in range(center.y - 1, center.y + 2):
		for x in range(center.x - 1, center.x + 2):
			sum += image.get_pixel(x, y).get_luminance()
	return sum / 9.0
