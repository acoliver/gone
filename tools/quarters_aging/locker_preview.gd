extends "res://tools/quarters_pilot_preview.gd"
## The pilot views stay fixed. Hardware gets a measured 0.3 m close-up.

func _parts(node: Node) -> Dictionary:
	if node == model: QuartersProps.prepare_geometry(model)
	return super._parts(node)

func _capture(name: String) -> void:
	await super._capture(name)
	if name == "aged-neutral-streaks.png": await _hardware_closeup()

func _hardware_closeup() -> void:
	# A native window is clamped to the display height on macOS. An offscreen
	# viewport retains the requested pixel count and square camera framing.
	var viewport := SubViewport.new()
	viewport.size = Vector2i(4096, 4096)
	viewport.msaa_3d = root.msaa_3d
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.world_3d = stage.get_world_3d()
	root.add_child(viewport)
	var close_camera := Camera3D.new()
	close_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	viewport.add_child(close_camera)
	close_camera.position = Vector3(-0.015, 1.075, 0.600)
	close_camera.look_at(Vector3(-0.015, 1.075, 0.300), Vector3.UP)
	close_camera.size = 0.64
	close_camera.current = true
	await _viewport_capture(viewport, "closeup-hinge.png")
	_diagnostic(7)
	await _viewport_capture(viewport, "closeup-hardware-ids.png")
	_diagnostic(0)
	var metrics := {"image_size": [viewport.size.x, viewport.size.y], "size_m": close_camera.size, "nominal_distance_m": 0.3, "measurement": "hardware-ID silhouette pixels divided by physical width; locker_face_gates.py"}
	var file := FileAccess.open(output.path_join("closeup.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(metrics, "\t") + "\n")
	viewport.queue_free()

func _viewport_capture(viewport: SubViewport, name: String) -> void:
	for index: int in range(3): await process_frame
	RenderingServer.force_draw(false)
	await process_frame
	await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	assert(image.get_size() == Vector2i(4096, 4096), "hardware capture retains requested pixel count")
	assert(image.save_png(output.path_join(name)) == OK, "save hardware capture")
