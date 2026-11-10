extends SceneTree
## Fixed overview poses also drive the display-luma regression.

var world: Node3D
var camera: Camera3D
var directory: String
var shots: Array[Dictionary] = []

func _init() -> void:
	directory = OS.get_cmdline_user_args()[0]
	_run.call_deferred()

func _run() -> void:
	DirAccess.make_dir_recursive_absolute(directory)
	root.size = Vector2i(1600, 900)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	for white: bool in [false, true]:
		Engine.time_scale = 1.0
		var game := Game.new(91)
		game.light_hallway()
		if white: game.press_console()
		world = Node3D.new()
		root.add_child(world)
		var ship := ShipScene.build_into(world, game)
		ship.prepare_near(Vector3(10, 0, 0))
		ship.prepare_near(Vector3(26, 0, 0))
		ship.hazards.auto_bursts = false
		ship.hazards.set_physics_process(false)
		ship.hazards._smoke_field.use_fixed_seed = true
		ship.hazards._smoke_field.seed = 91
		ship.hazards._smoke_field.restart()
		camera = Camera3D.new()
		camera.current = true
		camera.fov = 55
		world.add_child(camera)
		# Keep the full smoke field while pinning its random and animated capture inputs.
		for frame: int in range(30): await process_frame
		ship.hazards._smoke_field.speed_scale = 0.0
		Engine.time_scale = 0.0
		var circuit := "white" if white else "emergency"
		await _shot(circuit + "-hall-overview", Vector3(6.8, 1.65, 0), Vector3(25, 2.05, 0))
		await _shot(circuit + "-hall-eye-height", Vector3(10, 1.65, 0), Vector3(29, 1.65, 0))
		await _shot(circuit + "-bay-overview", Vector3(15, 1.65, 2.5), Vector3(15, 2.05, 11.5))
		await _shot(circuit + "-power-overview", Vector3(22, 1.65, -2.5), Vector3(29, 2.1, -8.8))
		await _shot(circuit + "-connector-overview", Vector3(0.6, 1.65, 0), Vector3(5.5, 1.8, 0))
		if "--overviews-only" not in OS.get_cmdline_user_args():
			for owner: Node3D in [ship.lighting, ship.hallway, ship.power_room]:
				for light: Light3D in owner.find_children("EmergencyFill*", "Light3D", true, false):
					if light.name == "EmergencyFillEnd": continue
					var emitter: MeshInstance3D = light.get_meta(&"fixture_emitter")
					var target := Surfaces.world_frame(emitter) * emitter.mesh.get_aabb().get_center()
					var steel: MeshInstance3D = light.get_meta(&"fixture_housing")
					var outward := Surfaces.world_frame(steel).basis.z.normalized()
					var eye := target - outward * 1.35 + Vector3(0.30, -0.35, 0.20)
					if directory.get_file() == "before": eye = target + Vector3(0.6, -0.55, 0.8)
					await _shot("%s-%s-%s" % [circuit, owner.name, light.name], eye, target)
		world.free()
		await process_frame
	FileAccess.open(directory.path_join("views.json"), FileAccess.WRITE).store_string(JSON.stringify(shots, "\t"))
	print("CAPTURES COMPLETE count=", shots.size())
	quit()

func _shot(label: String, eye: Vector3, target: Vector3) -> void:
	camera.position = eye
	camera.look_at(target)
	for index: int in range(12): await process_frame
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(directory.path_join(label + ".png")) == OK)
	shots.append({"name": label, "eye": str(eye), "target": str(target)})
	print("CAPTURE ", directory.path_join(label + ".png"))
