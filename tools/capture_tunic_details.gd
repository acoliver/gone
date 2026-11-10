extends SceneTree
## Issue #130: actual windowed game, unchanged wardrobe camera and room lights.

var output: String
var main: Node3D
var cameras: Dictionary = {}
var provenance: Dictionary = {}

func _garment_provenance(garment: Node3D, state: String) -> Dictionary:
	var asset := "res://assets/props/quarters/dress_uniform%s.glb" % ("_aged" if state == "present" else "")
	var settings := ConfigFile.new()
	assert(settings.load(asset + ".import") == OK)
	var native: String = settings.get_value("remap", "path")
	var md5 := FileAccess.get_md5(asset)
	assert(FileAccess.get_file_as_string(native.get_basename() + ".md5").contains('source_md5="%s"' % md5), "stale native garment import")
	var materials: Dictionary = {}
	for part: String in ["Placket", "Buttons"]:
		var mesh := garment.find_child(part, true, false) as MeshInstance3D
		var material := mesh.mesh.surface_get_material(0) as StandardMaterial3D
		var uvs: PackedVector2Array = mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
		var low := Vector2(INF, INF)
		var high := Vector2(-INF, -INF)
		for uv: Vector2 in uvs:
			low = low.min(uv)
			high = high.max(uv)
		materials[part] = {"texture": material.albedo_texture.resource_path if material.albedo_texture != null else "",
			"primary_uv_min": [low.x, low.y], "primary_uv_max": [high.x, high.y],
			"texture_pixel_hex_sha256": material.albedo_texture.get_image().get_data().hex_encode().sha256_text() if material.albedo_texture != null else ""}
	var buttons := garment.find_child("Buttons", true, false) as MeshInstance3D
	assert(buttons != null)
	var adjacency: Dictionary = {}
	var faces := buttons.mesh.get_faces()
	for index: int in range(0, faces.size(), 3):
		for corner: int in range(3):
			var a := faces[index + corner]
			var b := faces[index + (corner + 1) % 3]
			if not adjacency.has(a): adjacency[a] = []
			if not adjacency.has(b): adjacency[b] = []
			adjacency[a].append(b)
			adjacency[b].append(a)
	var remaining := adjacency.duplicate()
	var centers: Array = []
	while not remaining.is_empty():
		var pending: Array = [remaining.keys()[0]]
		remaining.erase(pending[0])
		var sum := Vector3.ZERO
		var count := 0
		while not pending.is_empty():
			var point: Vector3 = pending.pop_back()
			sum += point
			count += 1
			for neighbor: Vector3 in adjacency[point]:
				if remaining.has(neighbor):
					remaining.erase(neighbor)
					pending.append(neighbor)
		var center := sum / count
		centers.append([center.x, center.y, center.z])
	return {"asset": asset, "source_md5": md5, "source_sha256": FileAccess.get_sha256(asset),
		"native": native, "native_sha256": FileAccess.get_sha256(native),
		"native_md5_record": FileAccess.get_file_as_string(native.get_basename() + ".md5"),
		"button_components": centers.size(), "button_centers": centers,
		"button_triangles": faces.size() / 3, "imported_materials": materials}

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1, "usage: -- <output directory>")
	output = ProjectSettings.globalize_path(args[0])
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "windowed rendering required")
	assert(DirAccess.make_dir_recursive_absolute(output) == OK)
	root.size = Vector2i(1536, 864)
	root.content_scale_size = Vector2i(1536, 864)
	root.msaa_3d = Viewport.MSAA_4X
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	main.set_physics_process(false)
	DemoStart.quarters(main.game, main.player)
	DemoStart.prepare_ship(main.step.ship_scene, main.player)
	main.player.set_process(false)
	main.player.set_physics_process(false)
	var ship: ShipScene = main.step.ship_scene
	assert(ship.quarters != null)
	var camera: Camera3D = main.camera
	camera.current = true
	for state: String in ["remembered", "present"]:
		main.game.quarters.state = QuartersMemory.State.REMEMBERED if state == "remembered" else QuartersMemory.State.PRESENT
		for index: int in range(60): ship.tick_rooms()
		var furnishings: Node3D = ship.quarters.remembered if state == "remembered" else ship.quarters.present
		var garment := furnishings.get_node("Placement_wardrobe/HangingUniform") as Node3D
		provenance[state] = _garment_provenance(garment, state)
		var frame := ShipScene._world_frame(garment)
		for view: String in ["wardrobe", "buttons", "medal"]:
			camera.projection = Camera3D.PROJECTION_PERSPECTIVE
			if view == "wardrobe":
				QuartersCapture.pose(camera, "wardrobe")
			else:
				var local := Vector3(.1108, -.3782, .0552) if view == "medal" else Vector3(.005, -.515, .055)
				var target := frame * local
				var normal := (frame.basis.inverse().transposed() * Vector3.BACK).normalized()
				camera.global_position = target + normal * (.18 if view == "medal" else 1.5)
				camera.look_at(target)
				camera.keep_aspect = Camera3D.KEEP_WIDTH
				camera.fov = 30.0 if view == "medal" else 50.0
			cameras[state + "-" + view] = {"transform": str(camera.global_transform), "fov": camera.fov, "size": [1536, 864]}
			for index: int in range(12): await process_frame
			RenderingServer.force_draw(false)
			await process_frame
			await RenderingServer.frame_post_draw
			var image := root.get_texture().get_image()
			assert(image.save_png(output.path_join(state + "-" + view + "-raw.png")) == OK)
			var crop := image.get_region(Rect2i(0, HarnessProtocol.chip_size().y, 1536, 824))
			assert(crop.save_png(output.path_join(state + "-" + view + ".png")) == OK)
	var file := FileAccess.open(output.path_join("cameras.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(cameras, "\t") + "\n")
	file = FileAccess.open(output.path_join("provenance.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(provenance, "\t") + "\n")
	main.queue_free()
	await process_frame
	print("TUNIC GAME CAPTURES ", output)
	quit()
