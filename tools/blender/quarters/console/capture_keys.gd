extends SceneTree
## Supplementary key detail only. Main room views stay in quarters-demo.json.

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "key detail requires actual windowed rendering")
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1, "usage: -s tools/blender/quarters/console/capture_keys.gd -- <output-dir>")
	var output := ProjectSettings.globalize_path(args[0])
	assert(DirAccess.make_dir_recursive_absolute(output) == OK, "capture output")
	root.size = Vector2i(1536, 864)
	root.msaa_3d = Viewport.MSAA_4X
	var game := Game.new(129)
	game.light_hallway()
	game.press_console()
	var stage := Node3D.new()
	root.add_child(stage)
	var ship := ShipScene.build_into(stage, game)
	ship._add_hatch(&"D16-C-001-H-AFT")
	ship.ensure_d16()
	var camera := Camera3D.new()
	stage.add_child(camera)
	camera.current = true
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = 55
	camera.global_position = QuartersLayout.to_world(Vector3(6.75, 1.70, 2.0))
	camera.look_at(QuartersLayout.to_world(Vector3(7.62, 1.13, 2.0)))
	for state: QuartersMemory.State in [QuartersMemory.State.REMEMBERED, QuartersMemory.State.PRESENT]:
		game.quarters.state = state
		ship.quarters.process_frame()
		for frame: int in range(12):
			await process_frame
			RenderingServer.force_draw()
		await RenderingServer.frame_post_draw
		var name := "remembered-keys" if state == QuartersMemory.State.REMEMBERED else "present-keys"
		assert(root.get_texture().get_image().save_png(output.path_join(name + ".png")) == OK, "key detail capture")
	print("KEY DETAIL CAPTURES: room-local eye=(6.75,1.70,2.0) target=(7.62,1.13,2.0), horizontal FOV=55; unchanged room lighting/materials")
	stage.queue_free()
	ship = null
	await process_frame
	await process_frame
	quit()
