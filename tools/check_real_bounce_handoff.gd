extends SceneTree

func _init() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless")
	var output := OS.get_cmdline_user_args()[0]
	DirAccess.make_dir_recursive_absolute(output)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(1152,648)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	var game := Game.new(91)
	game.light_hallway()
	for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
	var world := Node3D.new()
	root.add_child(world)
	var ship := ShipScene.build_into(world, game, false)
	ship.hazards.auto_bursts = false
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.current = true
	camera.fov = 76
	camera.position = Vector3(18,1.6,.25)
	camera.look_at(Vector3(29.6,1.5,0))
	for frame: int in range(120):
		await process_frame
		await RenderingServer.frame_post_draw
	game.press_console()
	var records: Array[Dictionary] = []
	for frame: int in range(121):
		if frame > 0:
			for room: Node in [ship.lighting, ship.hallway, ship.power_room]: room.process_frame(1.0 / 60)
		await process_frame
		await RenderingServer.frame_post_draw
		var white := 0.0
		for source: Light3D in ship.hallway.white_lights(): white += source.light_energy
		var red := 0.0
		for source: Light3D in ship.hallway.lights(): red += source.light_energy
		records.append({"frame": frame, "white_energy": white, "red_energy": red})
		if frame in [0,15,30,60,120]:
			assert(root.get_texture().get_image().save_png(output.path_join("frame-%03d.png" % frame)) == OK)
	assert(records[0].white_energy == 0.0)
	assert(records[0].red_energy > 0.0)
	assert(records[30].white_energy > 0.0)
	assert(records[30].red_energy == 0.0)
	for index: int in range(1, records.size()):
		assert(records[index].white_energy >= records[index-1].white_energy)
		assert(records[index].red_energy <= records[index-1].red_energy)
	FileAccess.open(output.path_join("handoff.json"), FileAccess.WRITE).store_string(JSON.stringify(records, "\t") + "\n")
	print("GI HANDOFF PASS frame0=", records[0], " frame15=", records[15], " frame30=", records[30])
	(world.get_node("RoomEnvironment") as WorldEnvironment).environment.sdfgi_enabled = false
	await process_frame
	await RenderingServer.frame_post_draw
	world.free()
	quit()
