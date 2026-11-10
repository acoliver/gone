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
	var valid := true
	for state: int in [Game.ConsoleState.INACTIVE, Game.ConsoleState.ACTIVE]:
		if state == Game.ConsoleState.ACTIVE:
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
			print("CONSOLE_SAMPLE state=", state, " perceive=", perceive)
			if not check_background(root.get_texture().get_image(), camera, station):
				valid = false
	scene.queue_free()
	await process_frame
	if valid:
		print("CONSOLE_SCREEN_PIXELS_OK")
	else:
		push_error("console screen pixel regression failed")
	quit(0 if valid else 1)

static func check_background(image: Image, camera: Camera3D, station: Node3D) -> bool:
	var surface := station.get_node("ShipDisplay/TextSurface") as MeshInstance3D
	var material := surface.material_override as ShaderMaterial
	var perceive: float = material.get_shader_parameter("perceive")
	assert(perceive == 0.0 or perceive == 1.0, "contrast samples use fully native or perceived text")
	var texture := material.get_shader_parameter("native_ink" if perceive == 0.0 else "perceived_ink") as Texture2D
	assert(texture != null, "text has rasterized before contrast measurement")
	var mask := texture.get_image()
	var size := (surface.mesh as QuadMesh).size
	var bounds := Rect2(camera.unproject_position(surface.global_position), Vector2.ZERO)
	for x: float in [-0.45, 0.45]:
		for y: float in [-0.45, 0.45]:
			bounds = bounds.expand(camera.unproject_position(surface.global_transform * Vector3(size.x * x, size.y * y, 0)))
	var plane := Plane(surface.global_basis.z.normalized(), surface.global_position)
	var ink: Array[Color] = []
	var background: Array[Color] = []
	for y in range(ceili(bounds.position.y), floori(bounds.end.y)):
		for x in range(ceili(bounds.position.x), floori(bounds.end.x)):
			var pixel := Vector2(x, y)
			var hit: Vector3 = plane.intersects_ray(camera.project_ray_origin(pixel), camera.project_ray_normal(pixel))
			var local := surface.to_local(hit)
			var uv := Vector2(local.x / size.x + 0.5, 0.5 - local.y / size.y)
			if uv.x < 0.05 or uv.x > 0.95 or uv.y < 0.05 or uv.y > 0.95:
				continue
			var texel := Vector2i((uv * Vector2(mask.get_size())).floor())
			# Keep only glyph interiors and clear background, excluding antialiased edges.
			var minimum_alpha := 1.0
			var maximum_alpha := 0.0
			for dy in range(-1, 2):
				for dx in range(-1, 2):
					var alpha := mask.get_pixelv(texel + Vector2i(dx, dy)).a
					minimum_alpha = minf(minimum_alpha, alpha)
					maximum_alpha = maxf(maximum_alpha, alpha)
			if minimum_alpha >= 0.95:
				ink.append(image.get_pixel(x, y))
			elif maximum_alpha <= 0.01:
				background.append(image.get_pixel(x, y))
	assert(ink.size() >= 20 and background.size() >= 100, "screen rect contains glyph cores and background pixels")
	var ink_color := _median_color(ink)
	var screen_color := _median_color(background)
	var ink_luma := ink_color.srgb_to_linear().get_luminance()
	var screen_luma := screen_color.srgb_to_linear().get_luminance()
	var contrast := (maxf(ink_luma, screen_luma) + 0.05) / (minf(ink_luma, screen_luma) + 0.05)
	var glass := station.get_node("ScreenGlass") as MeshInstance3D
	var glass_size := (glass.mesh as BoxMesh).size
	# Compare with the centre of the body fascia immediately above the screen.
	var world := glass.global_transform * Vector3(0, glass_size.y * 0.55, -0.02)
	var pixel := Vector2i(camera.unproject_position(world).round())
	var body := _patch_color(image, pixel)
	var distance := Vector3(body.r - screen_color.r, body.g - screen_color.g, body.b - screen_color.b).length() * 255.0
	print("BODY_SAMPLE pixel=", pixel, " rgb=", _rgb(body), " screen_distance=", distance)
	print("SCREEN_CONTRAST background_rgb=", _rgb(screen_color), " ink_rgb=", _rgb(ink_color), " ratio=", contrast, " ink_pixels=", ink.size(), " background_pixels=", background.size())
	if distance < 60.0 or contrast < 3.0:
		push_error("screen requires sRGB body distance >= 60 and text contrast >= 3:1")
		return false
	return true

static func _median_color(colors: Array[Color]) -> Color:
	colors.sort_custom(func(a: Color, b: Color) -> bool: return a.get_luminance() < b.get_luminance())
	return colors[colors.size() / 2]

static func _patch_color(image: Image, center: Vector2i) -> Color:
	assert(Rect2i(Vector2i.ZERO, image.get_size()).encloses(Rect2i(center - Vector2i.ONE, Vector2i(3, 3))), "sample stays within the capture")
	var sum := Color(0, 0, 0, 0)
	for y in range(center.y - 1, center.y + 2):
		for x in range(center.x - 1, center.x + 2):
			sum += image.get_pixel(x, y)
	return sum / 9.0

static func _rgb(color: Color) -> Vector3i:
	return Vector3i(roundi(color.r * 255.0), roundi(color.g * 255.0), roundi(color.b * 255.0))
