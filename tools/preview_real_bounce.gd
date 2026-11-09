extends "res://tools/capture_ship_surfaces.gd"

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "GI requires native rendering")
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(2304, 1296)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	print("GI renderer=", RenderingServer.get_current_rendering_method(), " driver=", RenderingServer.get_current_rendering_driver_name(), " mode=", OS.get_environment("GONE_REAL_BOUNCE"))
	for white: bool in [true, false]:
		game = Game.new(SEED)
		game.light_hallway()
		if white: game.press_console()
		for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
		world = Node3D.new()
		root.add_child(world)
		scene = ShipScene.build_into(world, game, false)
		scene.hazards.auto_bursts = false
		scene.prepare_near(Vector3(10, 0, 0))
		scene.prepare_near(Vector3(26, 0, 0))
		camera = Camera3D.new()
		world.add_child(camera)
		camera.current = true
		camera.fov = 80
		var circuit := "secondary-white" if white else "emergency"
		await _shot(circuit, "connector-bulkhead", &"D14-C-001", Vector3(32.6, 2.05, 0.1), Vector3(30.1, 2.85, 0.05))
		await _shot(circuit, "hall-end-wall", &"D14-S-041", Vector3(27.7, 2.05, -0.1), Vector3(30.1, 2.85, 0.05))
		await _shot(circuit, "along-connector", &"D14-C-001", Vector3(30.7, 2.05, 0.1), Vector3(35.9, 2.85, 0.05))
		await _shot(circuit, "ship-end-wall", &"D14-S-042", Vector3(57.7, 2.05, -0.1), Vector3(60.1, 2.85, 0.05))
		camera.fov = 40
		var spine := game.layout.ceiling_services(&"D14-C-001").spine
		var target: Vector3 = spine.duct_collars[0].origin
		target.y = spine.ducts[0].origin.y - 0.025
		await _shot(circuit, "duct-collar-2m-connector-side", &"D14-C-001", target + Vector3(2, -0.25, 0), target)
		await _beams(circuit)
		camera.fov = 76
		await _shot(circuit, "hall-overview", &"D14-S-041", Vector3(18, 1.6, 0.25), Vector3(29.6, 1.5, 0))
		await _shot(circuit, "connector-overview", &"D14-C-001", Vector3(32.8, 1.6, 0), Vector3(30, 1.4, 0))
		(world.get_node("RoomEnvironment") as WorldEnvironment).environment.sdfgi_enabled = false
		await process_frame
		await RenderingServer.frame_post_draw
		world.free()
		await process_frame
	FileAccess.open(output_dir.path_join("captures.json"), FileAccess.WRITE).store_string(JSON.stringify(records, "\t") + "\n")
	print("GI CAPTURES COMPLETE count=", records.size())
	quit()

func _beams(circuit: String) -> void:
	camera.fov = 55
	for owner: StringName in [ShipLayout.BAY_ID, &"D14-S-041", ShipLayout.POWER_ID]:
		var room: Node3D = scene.lighting if owner == ShipLayout.BAY_ID else (scene.power_room if owner == ShipLayout.POWER_ID else scene.hallway)
		var anchor := game.layout.bay_to_world() * Vector3(0, 3.1, 0) if owner == ShipLayout.BAY_ID else Vector3(21, 3.1, 0)
		if owner == ShipLayout.POWER_ID: anchor = Vector3(24, 3.1, -3.7)
		var nearest: MeshInstance3D
		var best := INF
		for source: Light3D in room.white_lights():
			var lens: MeshInstance3D = source.get_meta(&"fixture_emitter")
			var center := Surfaces.world_frame(lens) * lens.mesh.get_aabb().get_center()
			if center.distance_to(anchor) < best:
				best = center.distance_to(anchor)
				nearest = lens
		var target := Surfaces.world_frame(nearest) * nearest.mesh.get_aabb().get_center()
		var label := "bay" if owner == ShipLayout.BAY_ID else ("power" if owner == ShipLayout.POWER_ID else "hall")
		for close: bool in [false, true]:
			var name := "%s-beam-%s" % [label, "close" if close else "2p5m"]
			var offset := Vector3(-0.40, -0.64, 0.65) if close else Vector3(0, -sqrt(2.5 * 2.5 - 0.025 * 0.025), 0.025)
			await _shot(circuit, name, owner, target + offset, target)
			if OS.get_environment("GONE_REAL_BOUNCE").is_empty() and circuit == "secondary-white": await _beam_mask(name, nearest)

func _beam_mask(name: String, lens: MeshInstance3D) -> void:
	var black := StandardMaterial3D.new()
	black.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	black.albedo_color = Color.BLACK
	var shader := Shader.new()
	shader.code = "shader_type spatial; render_mode unshaded, cull_back; varying vec3 n; varying float y; uniform float lens_y; void vertex(){ n = MODEL_NORMAL_MATRIX * NORMAL; y = (MODEL_MATRIX * vec4(VERTEX,1.0)).y; } void fragment(){ ALBEDO = n.y < -0.9 && y < lens_y - 0.005 ? vec3(1.0) : vec3(0.0); }"
	var mask := ShaderMaterial.new()
	mask.shader = shader
	mask.set_shader_parameter("lens_y", (Surfaces.world_frame(lens) * lens.mesh.get_aabb().get_center()).y)
	var saved := {}
	for mesh: GeometryInstance3D in world.find_children("*", "GeometryInstance3D", true, false):
		saved[mesh] = mesh.material_override
		mesh.material_override = black
	for mesh: MeshInstance3D in lens.get_parent().find_children("*", "MeshInstance3D", true, false):
		if mesh.mesh.surface_get_material(0).resource_name == "OliveSteel_StructuredWeather": mesh.material_override = mask
	await _settle(2)
	assert(root.get_texture().get_image().save_png(output_dir.path_join(name + ".mask.png")) == OK)
	for mesh: GeometryInstance3D in saved: mesh.material_override = saved[mesh]

func _settle(count: int) -> void:
	for index: int in range(maxi(count, 120)):
		await process_frame
		await RenderingServer.frame_post_draw
