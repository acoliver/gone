extends "res://tools/capture_ship_surfaces.gd"

func _run() -> void:
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = Vector2i(2304, 1296)
	root.size = root.content_scale_size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	for white: bool in [true, false]:
		game = Game.new(SEED)
		game.light_hallway()
		if white: game.press_console()
		for tick: int in range(BayVentilation.CLEAR_TICKS): game.ventilation.tick(true)
		var circuit := "secondary-white" if white else "emergency"
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
		await _settle(36)
		await _shot(circuit, "hall-end-wall", &"D14-S-041", Vector3(27.7, 2.05, -0.1), Vector3(30.1, 2.85, 0.05))
		await _shot(circuit, "connector-bulkhead", &"D14-C-001", Vector3(32.6, 2.05, 0.1), Vector3(30.1, 2.85, 0.05))
		await _shot(circuit, "along-connector", &"D14-C-001", Vector3(30.7, 2.05, 0.1), Vector3(35.9, 2.85, 0.05))
		await _shot(circuit, "ship-end-wall", &"D14-S-042", Vector3(57.7, 2.05, -0.1), Vector3(60.1, 2.85, 0.05))
		camera.fov = 64
		await _shot(circuit, "generator-ceiling", ShipLayout.POWER_ID, Vector3(24.5, 1.9, -3.7), Vector3(27, 2.8, -5.7))
		camera.fov = 40
		for side: int in range(2):
			var space_id: StringName = &"D14-S-041" if side == 0 else &"D14-C-001"
			var spine := game.layout.ceiling_services(space_id).spine
			var face := 1 if side == 0 else 0
			var pipe_target: Vector3 = spine.pipe_collars[face].origin
			var duct_target: Vector3 = spine.duct_collars[face * 4].origin
			duct_target.y = spine.ducts[0].origin.y - 0.025
			var offset := Vector3(-2 if side == 0 else 2, -0.25, 0)
			var label := "hall-side" if side == 0 else "connector-side"
			await _shot(circuit, "pipe-collar-2m-" + label, space_id, pipe_target + offset, pipe_target)
			await _shot(circuit, "duct-collar-2m-" + label, space_id, duct_target + offset, duct_target)
			var inspection_target := duct_target
			var oblique := Vector3(-0.75, -1.06066, -0.75)
			if side == 1:
				inspection_target.z = 1.44
				oblique = Vector3(1.06066, -1.06066, 0)
			await _shot(circuit, "duct-collar-1p5m-up45-" + label, space_id, inspection_target + oblique, inspection_target)
		world.free()
		await process_frame
	FileAccess.open(output_dir.path_join("captures.json"), FileAccess.WRITE).store_string(JSON.stringify(records, "\t") + "\n")
	print("CEILING EDGE VIEWS COMPLETE captures=", records.size())
	quit(0)

func _shot(circuit: String, title: String, owner: StringName, eye: Vector3, target: Vector3) -> void:
	camera.position = eye
	camera.look_at(target)
	# UPDATE_ONCE probe cubemaps are initialized over several draw frames.
	await _settle(72)
	await super._shot(circuit, title, owner, eye, target)
