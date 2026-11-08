extends SceneTree
## Evaluate the production band shader and imported mask with lighting removed.

func _init() -> void: _run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "stripe probe needs native rendering")
	root.size = Vector2i(900, 160)
	DisplayServer.window_set_size(root.size)
	var scene := Node3D.new()
	root.add_child(scene)
	var view := DoorView.build(ShipLayout.authored().layout.door(&"D14-C-001-H-FORE"))
	var source: MeshInstance3D = view.label_leaf().get_node("Wheel").get_child(0)
	var ranges: Dictionary = source.mesh.get_meta(&"part_ranges")
	var row: Dictionary = ranges[&"Wheel/hazard-band"]
	var arrays := source.mesh.surface_get_arrays(0).duplicate(true)
	arrays[Mesh.ARRAY_INDEX] = arrays[Mesh.ARRAY_INDEX].slice(int(row.index_start), int(row.index_start + row.index_count))
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var material := Surfaces.material(&"modelled_hatch").duplicate() as ShaderMaterial
	var shader := Shader.new()
	shader.code = Surfaces.STEEL.code.replace("render_mode cull_back;", "render_mode cull_back, unshaded;").replace('#include "steel_sampling.gdshaderinc"', '#include "res://app/shaders/steel_sampling.gdshaderinc"')
	material.shader = shader
	var piece := HatchModel.mesh_piece(mesh, Transform3D.IDENTITY, 1, material)
	scene.add_child(piece)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 0.13
	camera.position = Vector3(0, -0.15, -1)
	scene.add_child(camera)
	camera.look_at(Vector3(0, -0.15, 0))
	camera.current = true
	for frame: int in range(12): await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	var bright := 0
	var dark := 0
	var changes := 0
	var last := -1
	for x: int in range(130, 770):
		var colour := image.get_pixel(x, 80)
		var value := maxf(colour.r, maxf(colour.g, colour.b))
		var state := 1 if value > 0.20 and colour.r > colour.b * 1.5 else (0 if value < 0.14 else -1)
		if state == 1: bright += 1
		if state == 0: dark += 1
		if state >= 0 and last >= 0 and state != last: changes += 1
		if state >= 0: last = state
	print("HATCH_STRIPES yellow_pixels=%d dark_pixels=%d transitions=%d" % [bright, dark, changes])
	var args := OS.get_cmdline_user_args()
	if args.size() == 1: image.save_png(args[0])
	view.free()
	quit(0 if bright >= 40 and dark >= 40 and changes >= 6 else 1)
