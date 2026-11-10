extends SceneTree
## Run against a scratch copy of the demo, never the integration worktree.

func _initialize() -> void:
	call_deferred("_capture")

func _capture() -> void:
	root.size = Vector2i(1536, 864)
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1, "capture output directory required")
	var output := args[0]
	DirAccess.make_dir_recursive_absolute(output)
	var game := Game.new(114)
	var owner := Node3D.new()
	root.add_child(owner)
	var player := Player.build(game, null)
	player.scripted = true
	owner.add_child(player)
	DemoStart.quarters(game, player)
	var context := Doors.Context.new()
	context.face_id = game.layout.door(QuartersLayout.DOOR).face_ids()[0]
	game.doors.press(QuartersLayout.DOOR, context)
	for tick: int in range(48): game.advance_doors()
	var ship := ShipScene.build_into(owner, game)
	DemoStart.prepare_ship(ship, player)
	ship.ensure_d16()
	var camera := Camera3D.new()
	owner.add_child(camera)
	camera.make_current()
	for state: String in ["remembered", "aged"]:
		game.quarters.state = QuartersMemory.State.REMEMBERED if state == "remembered" else QuartersMemory.State.PRESENT
		ship.quarters.process_frame()
		for view: String in ["wardrobe", "doorway"]:
			QuartersCapture.pose(camera, view)
			await process_frame
			RenderingServer.force_draw()
			await RenderingServer.frame_post_draw

			var image := root.get_texture().get_image()
			var top := HarnessProtocol.chip_size().y
			var crop := image.get_region(Rect2i(0, top, image.get_width(), image.get_height() - top))
			assert(crop.save_png(output.path_join(state + "-" + view + ".png")) == OK)
	owner.queue_free()
	await process_frame
	quit()
