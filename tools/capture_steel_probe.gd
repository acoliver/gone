extends SceneTree
## Native import and instance-coordinate contract. Inspection lights exist only here.
## Run: godot --path . -s tools/capture_steel_probe.gd -- <output-dir>

var output_dir: String
var world: Node3D
var camera: Camera3D
var failures: Array[String] = []
var result: Dictionary = {}

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1 or args[0].strip_edges().is_empty():
		printerr("usage: godot --path . -s tools/capture_steel_probe.gd -- <output-dir>")
		quit(2)
		return
	output_dir = args[0]
	_run.call_deferred()

func _check(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
		push_error(message)

func _settle(count: int = 12) -> void:
	for index: int in range(count): await process_frame
	await RenderingServer.frame_post_draw

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "Forward+ native renderer required")
	DirAccess.make_dir_recursive_absolute(output_dir)
	root.size = Vector2i(1152, 648)
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	world = Node3D.new()
	root.add_child(world)
	await _imports()
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color.BLACK
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	world.add_child(environment)
	var rig := Node3D.new()
	world.add_child(rig)
	camera = Camera3D.new()
	rig.add_child(camera)
	camera.position = Vector3(0, 0.3, 4)
	camera.look_at_from_position(camera.position, Vector3.ZERO)
	camera.current = true
	var light := OmniLight3D.new()
	light.position = Vector3(-1, 2, 3)
	light.omni_range = 10
	light.light_energy = 8
	rig.add_child(light)
	var mesh := BoxMesh.new()
	mesh.size = Vector3(0.8, 1.4, 0.3)
	var layout := ShipLayout.authored().layout
	var frame := Surfaces.surface_frame(layout, &"D30-C-001", &"PORT")
	frame.world_from_surface = Transform3D.IDENTITY
	frame.bounds = AABB(Vector3(-2, -1, -1), Vector3(4, 3, 2))
	frame.floor_datum = -1
	var regular := Node3D.new()
	rig.add_child(regular)
	var pieces: Array[GeometryInstance3D] = []
	var poses: Array[Transform3D] = [Transform3D(Basis(Vector3.UP, 0.3), Vector3(-0.7, 0, 0)), Transform3D(Basis(Vector3.RIGHT, 0.25), Vector3(0.7, 0, 0))]
	for pose: Transform3D in poses:
		var piece := HatchModel.mesh_piece(mesh, pose, 1, Surfaces.material(&"wall"))
		Surfaces.bind(piece, &"wall", frame)
		pieces.append(piece)
		regular.add_child(piece)
	var multi := MultiMeshInstance3D.new()
	multi.multimesh = MultiMesh.new()
	multi.multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multi.multimesh.mesh = mesh
	multi.multimesh.instance_count = poses.size()
	for index: int in range(poses.size()): multi.multimesh.set_instance_transform(index, poses[index])
	Surfaces.bind(multi, &"wall", frame)
	rig.add_child(multi)
	multi.visible = false
	await _settle()
	var reference := root.get_texture().get_image()
	reference.save_png(output_dir.path_join("mesh-neutral.png"))
	regular.visible = false
	multi.visible = true
	await _settle()
	var batch := root.get_texture().get_image()
	batch.save_png(output_dir.path_join("multimesh-neutral.png"))
	var batch_error := _difference(reference, batch)
	_check(batch_error < 0.0001, "MultiMesh uses the same owner-frame instance rows as separate meshes")
	pieces.append(multi)
	rig.transform = Transform3D(Basis(Vector3.UP, 0.6), Vector3(12, -88, 5))
	Surfaces.present_frame(pieces, rig.transform)
	await _settle()
	var moved := root.get_texture().get_image()
	moved.save_png(output_dir.path_join("multimesh-relocated.png"))
	var motion_error := _difference(batch, moved)
	_check(motion_error < 0.001, "native scan does not slide when owner/camera/light are rigidly relocated")
	result["multimesh_mean_absolute_error"] = batch_error
	result["relocation_mean_absolute_error"] = motion_error
	rig.transform = Transform3D.IDENTITY
	multi.visible = false
	var pipe := CylinderMesh.new()
	pipe.top_radius = 0.15
	pipe.bottom_radius = 0.15
	pipe.height = 1.4
	pipe.radial_segments = 32
	for side: int in [-1, 1]:
		var piece := HatchModel.mesh_piece(pipe, Transform3D(Basis(Vector3.BACK, side * 0.6), Vector3(side * 0.6, 0, 0)), 1, Surfaces.material(&"hardware"))
		Surfaces.bind(piece, &"hardware", frame)
		rig.add_child(piece)
	var tape := HatchModel.mesh_piece(HatchModel.box_mesh(Vector3(0.65, 0.08, 0.01)), Transform3D(Basis(), Vector3(0, -0.85, 0.2)), 1, Surfaces.tape_material())
	rig.add_child(tape)
	await _settle()
	var hardware := root.get_texture().get_image()
	hardware.save_png(output_dir.path_join("tilted-hardware-tape-neutral.png"))
	_check(_mean(hardware).length() > 0.001, "curved signed projections and tape compile on native Forward+")
	rig.free()
	await _hatch_faces(layout)
	for child: Node in world.get_children(): child.free()
	await _channel_behavior()
	await _normal_direction(layout)
	result["failures"] = failures
	FileAccess.open(output_dir.path_join("probe.json"), FileAccess.WRITE).store_string(JSON.stringify(result, "\t") + "\n")
	print("STEEL PROBE ", JSON.stringify(result))
	quit(0 if failures.is_empty() else 1)

func _imports() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(Surfaces.ROOT + "manifest.json"))
	var before := RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED)
	var payload := 0
	var formats: Dictionary = {}
	var channel_errors: Dictionary = {}
	for file: String in manifest.images:
		var texture := Surfaces.texture(file)
		var image := texture.get_image()
		var expected := Image.FORMAT_RGTC_RG if manifest.images[file].normal else Image.FORMAT_BPTC_RGBA
		formats[file] = image.get_format()
		_check(image.get_format() == expected, "native BC5/BC7 format: " + file)
		_check(image.has_mipmaps() and image.get_size() == Vector2i(1024, 1024), "full 1K mip chain: " + file)
		payload += image.get_data().size()
		if manifest.images[file].normal:
			_check(image.decompress() == OK, "BC5 readback decompresses: " + file)
			var source := Image.load_from_file(Surfaces.ROOT + file)
			var error := 0.0
			for y: int in range(0, 1024, 8):
				for x: int in range(0, 1024, 8):
					var a := image.get_pixel(x, y)
					var b := source.get_pixel(x, y)
					error += absf(a.r - b.r) + absf(a.g - b.g)
			error /= 32768.0
			channel_errors[file] = error
			_check(error < 0.03, "OpenGL signed XY channels retained: " + file)
	await _settle()
	var after := RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED)
	_check(payload <= int(manifest.max_gpu_payload_bytes), "compressed GPU payload stays below 16.1 MiB")
	result.merge({"formats": formats, "gpu_payload_bytes": payload, "engine_texture_memory_delta_bytes": after - before, "normal_xy_mean_absolute_errors": channel_errors})

func _hatch_faces(layout: ShipLayout) -> void:
	var spec := layout.door(&"D14-C-001-H-FORE")
	var hatch := DoorView.build(spec, 1, 2)
	world.add_child(hatch)
	var game := Game.new(0)
	hatch.present(game.doors.snapshot(spec.id()))
	camera = Camera3D.new()
	world.add_child(camera)
	camera.current = true
	var light := OmniLight3D.new()
	light.omni_range = 6
	light.light_energy = 10
	world.add_child(light)
	var centers: Array[Vector3] = []
	for side: int in [-1, 1]:
		var center := Surfaces.world_frame(hatch.label_leaf()) * Vector3(spec.leaf_aperture().x / 2, 1.25, side * 0.1)
		camera.position = center + spec.frame().basis.z * side * 1.85
		camera.look_at(center)
		light.position = camera.position + Vector3(0.3, 0.4, 0)
		light.light_cull_mask = 1 if side < 0 else 2
		for red: bool in [false, true]:
			light.light_color = Color.RED if red else Color.WHITE
			await _settle()
			var image := root.get_texture().get_image()
			image.save_png(output_dir.path_join("hatch-%s-%s.png" % ["fore" if side < 0 else "aft", "red" if red else "neutral"]))
			var mean := _mean(image)
			_check(mean.length() > 0.001, "masked hatch face is rendered, including reflected reverse winding")
			centers.append(mean)
	result["hatch_face_means_rgb"] = centers.map(func(value: Vector3) -> Array: return [value.x, value.y, value.z])

func _constant_texture(color: Color) -> ImageTexture:
	var image := Image.create(4, 4, false, Image.FORMAT_RGBAF)
	image.fill(color)
	return ImageTexture.create_from_image(image)

# Expose the real fragment outputs as unlit colour, leaving their production
# expressions and signed sampling intact. Readback is decoded from display sRGB.
func _diagnostic_material(output: String, orm: Color, normal: Color, mutation: String = "") -> ShaderMaterial:
	var material := Surfaces.material(&"wall").duplicate() as ShaderMaterial
	var source := FileAccess.get_file_as_string("res://app/shaders/weathered_steel.gdshader")
	source = source.replace('#include "steel_sampling.gdshaderinc"', FileAccess.get_file_as_string("res://app/shaders/steel_sampling.gdshaderinc"))
	if mutation == "swap": source = source.replace("orm.g*0.10", "orm.r*0.10").replace("1.0,orm.r", "1.0,orm.g")
	if mutation == "normal": source = source.replace("-v.x * signs.x", "v.x * signs.x").replace("-v.y * signs.y", "v.y * signs.y").replace("v.x * signs.z", "-v.x * signs.z")
	source = source.replace("render_mode cull_back;", "render_mode cull_back, unshaded;")
	source = source.left(source.rfind("}")) + "\n ALBEDO=" + output + ";\n}"
	var shader := Shader.new()
	shader.code = source
	material.shader = shader
	for suffix: String in ["a", "b", "c"]:
		material.set_shader_parameter("orm_" + suffix, _constant_texture(orm))
		material.set_shader_parameter("normal_" + suffix, _constant_texture(normal))
	material.set_shader_parameter(&"oxide_grain", _constant_texture(Color.WHITE))
	material.set_shader_parameter(&"oxide_normal", _constant_texture(Color(0.5, 0.5, 1)))
	return material

func _diagnostic_camera(center: Vector3, normal: Vector3) -> void:
	camera.position = center + normal * 3
	camera.look_at(center, Vector3.FORWARD if absf(normal.y) > 0.5 else Vector3.UP)

func _read_center() -> Vector3:
	await _settle(4)
	var image := root.get_texture().get_image()
	var color := image.get_pixelv(image.get_size() / 2).srgb_to_linear()
	return Vector3(color.r, color.g, color.b)

func _channel_behavior() -> void:
	camera = Camera3D.new()
	world.add_child(camera)
	camera.current = true
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	var piece := MeshInstance3D.new()
	piece.mesh = quad
	piece.position = Vector3(0.375, 1.5, 0.375)
	world.add_child(piece)
	_diagnostic_camera(piece.position, Vector3.BACK)
	var values: Array[Dictionary] = []
	for orm: Color in [Color(0, 0, 0), Color(1, 0, 0), Color(0, 1, 0), Color(0, 0, 1)]:
		piece.material_override = _diagnostic_material("vec3(AO,ROUGHNESS,METALLIC)", orm, Color(0.5, 0.5, 1))
		var actual := await _read_center()
		var expected := Vector2(lerpf(0.86, 1.0, orm.r), clampf(0.84 + orm.g * 0.10, 0.88, 0.97))
		_check(absf(actual.x - expected.x) < 0.006 and absf(actual.y - expected.y) < 0.006, "ORM.R drives AO and ORM.G drives roughness, independently: %s -> %s" % [orm, actual])
		values.append({"input": [orm.r, orm.g, orm.b], "output": [actual.x, actual.y, actual.z]})
	var base: Array = values[0].output
	var blue: Array = values[3].output
	_check(Vector3(base[0], base[1], base[2]).distance_to(Vector3(blue[0], blue[1], blue[2])) < 0.001, "ORM.B deliberately does not drive metallic or either other output")
	piece.material_override = _diagnostic_material("vec3(AO,ROUGHNESS,METALLIC)", Color(1, 0, 0), Color(0.5, 0.5, 1), "swap")
	var swapped := await _read_center()
	_check(absf(swapped.x - 1.0) > 0.05 and absf(swapped.y - 0.88) > 0.03, "negative control detects swapped AO/roughness channels")
	result["channel_behavior"] = values
	piece.free()

func _normal_direction(layout: ShipLayout) -> void:
	var piece := MeshInstance3D.new()
	world.add_child(piece)
	var results: Array[Dictionary] = []
	var tilted := Color(0.8, 0.7, 1)
	for normal: Vector3 in [Vector3.RIGHT, Vector3.LEFT, Vector3.UP, Vector3.DOWN, Vector3.BACK, Vector3.FORWARD]:
		var quad := QuadMesh.new()
		quad.size = Vector2.ONE
		piece.mesh = quad
		piece.transform = Transform3D(Basis(Quaternion(Vector3.BACK, normal)), Vector3(0.375, 1.5, 0.375))
		_diagnostic_camera(piece.position, normal)
		var perturbation := Vector3(0, 0.4, -0.6 * signf(normal.x)) if absf(normal.x) > 0.5 else (Vector3(0.6, 0, -0.4 * signf(normal.y)) if absf(normal.y) > 0.5 else Vector3(0.6 * signf(normal.z), 0.4, 0))
		piece.material_override = _diagnostic_material("NORMAL*0.5+0.5", Color.WHITE, tilted)
		var actual := (await _read_center()) * 2 - Vector3.ONE
		var expected := camera.global_basis.inverse() * (normal + perturbation * 0.26).normalized()
		_check(actual.distance_to(expected) < 0.015, "signed normal direction %s: expected %s got %s" % [normal, expected, actual])
		piece.material_override = _diagnostic_material("NORMAL*0.5+0.5", Color.WHITE, Color(0.5, 0.5, 1))
		var flat := (await _read_center()) * 2 - Vector3.ONE
		_check(actual.distance_to(flat) > 0.10, "independent XY normal input changes rendered direction: %s" % normal)
		piece.material_override = _diagnostic_material("NORMAL*0.5+0.5", Color.WHITE, tilted, "normal")
		var reversed := (await _read_center()) * 2 - Vector3.ONE
		_check(reversed.distance_to(expected) > 0.10, "negative control detects reversed signed projection: %s" % normal)
		results.append({"face": str(normal), "actual": str(actual), "expected": str(expected)})
	# Use the real reflected leaf mesh and winding conversion, not a rotated quad.
	var spec := layout.door(&"D14-C-001-H-FORE")
	var reverse: HatchParts.Group = HatchParts.leaf(spec)[HatchParts.leaf(spec).size() / 2]
	for group: HatchParts.Group in HatchParts.leaf(spec):
		if group.path == NodePath("AftSteel"): reverse = group
	piece.mesh = HatchModel._leaf_mesh(reverse, spec.leaf_aperture())
	piece.transform = reverse.transform
	_diagnostic_camera(Vector3(spec.leaf_aperture().x / 2, 1.5, 0.1), Vector3.BACK)
	piece.material_override = _diagnostic_material("NORMAL*0.5+0.5", Color.WHITE, tilted)
	var actual := (await _read_center()) * 2 - Vector3.ONE
	var expected := camera.global_basis.inverse() * (Vector3.BACK + Vector3(0.6, 0.4, 0) * 0.26).normalized()
	_check(actual.distance_to(expected) < 0.015, "reflected AftSteel winding retains the outward signed normal")
	result["normal_direction"] = results
	result["reflected_hatch_normal"] = {"actual": str(actual), "expected": str(expected)}
	piece.free()

func _difference(a: Image, b: Image) -> float:
	var total := 0.0
	for y: int in range(0, a.get_height(), 4):
		for x: int in range(0, a.get_width(), 4):
			var delta := a.get_pixel(x, y) - b.get_pixel(x, y)
			total += absf(delta.r) + absf(delta.g) + absf(delta.b)
	return total / (float(a.get_width() * a.get_height()) / 16.0 * 3.0)

func _mean(image: Image) -> Vector3:
	var total := Vector3.ZERO
	for y: int in range(0, image.get_height(), 4):
		for x: int in range(0, image.get_width(), 4):
			var value := image.get_pixel(x, y)
			total += Vector3(value.r, value.g, value.b)
	return total / (float(image.get_width() * image.get_height()) / 16.0)
