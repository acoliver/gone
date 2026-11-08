extends SceneTree
## Windowed, matched-camera pilot captures. Additional prop factories implement
## apply(root, prop, state); no game environment or shared material is changed.

var output := "res://tmp/mat/locker"
var prop := &"storage_locker_module"
var asset := "res://assets/props/quarters/storage_locker_module.glb"
var aged_asset := ""
var factory_path := "res://app/quarters_props.gd"
var height := 2.4
var centre_y := NAN
var frame_size := NAN
var factory: GDScript
var stage: Node3D
var model: Node3D
var camera: Camera3D
var environment: Environment
var ceiling: OmniLight3D
var fill: DirectionalLight3D
var report: Dictionary = {}

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	for index: int in range(0, args.size(), 2):
		match args[index]:
			"--out": output = args[index + 1]
			"--prop": prop = StringName(args[index + 1])
			"--asset": asset = args[index + 1]
			"--aged-asset": aged_asset = args[index + 1]
			"--factory": factory_path = args[index + 1]
			"--height": height = args[index + 1].to_float()
			"--centre-y": centre_y = args[index + 1].to_float()
			"--frame-size": frame_size = args[index + 1].to_float()
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "captures require a windowed renderer")
	output = ProjectSettings.globalize_path(output)
	assert(DirAccess.make_dir_recursive_absolute(output) == OK, "create capture directory")
	root.size = Vector2i(1024, 1024)
	root.content_scale_size = Vector2i(1024, 1024)
	root.msaa_3d = Viewport.MSAA_4X
	factory = null if factory_path == "none" else load(factory_path)
	stage = Node3D.new()
	root.add_child(stage)
	var world := WorldEnvironment.new()
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.055, 0.065, 0.075)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = environment
	stage.add_child(world)
	var scene: PackedScene = load(asset)
	model = scene.instantiate()
	stage.add_child(model)
	var state_models := {&"as_built": model, &"aged": model}
	if aged_asset != "":
		var aged_scene: PackedScene = load(aged_asset)
		var aged_model: Node3D = aged_scene.instantiate()
		stage.add_child(aged_model)
		aged_model.visible = false
		state_models[&"aged"] = aged_model
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	stage.add_child(camera)
	camera.current = true
	ceiling = OmniLight3D.new()
	ceiling.position = Vector3(-0.6, height + 0.6, 1.25) + _camera_offset()
	ceiling.omni_range = Lighting.REGULAR_RANGE
	ceiling.shadow_enabled = true
	stage.add_child(ceiling)
	fill = DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, -25, 0)
	fill.light_specular = 0
	stage.add_child(fill)
	var initial := _parts(model)
	var cameras: Dictionary = {}
	for angle: String in ["hero", "front", "detail", "top"]:
		_camera(angle)
		cameras[angle] = {"position": _vec(camera.position), "target": _vec(_target(angle)), "size": camera.size, "image_size": [1024, 1024]}
		for state: StringName in [&"as_built", &"aged"]:
			model.visible = false
			model = state_models[state]
			model.visible = true
			if factory != null: factory.apply(model, prop, state)
			if aged_asset == "":
				assert(_parts(model) == initial, "rigid state swap preserves names, pivots and footprint")
			for light: String in ["remembered", "present", "neutral"]:
				_lighting(light)
				await _capture("%s-%s-%s.png" % [state, light, angle])
			_lighting("neutral")
			if _diagnostic(1):
				await _capture("%s-albedo-%s.png" % [state, angle])
				_diagnostic(2)
				await _capture("%s-ids-%s.png" % [state, angle])
				_diagnostic(0)
	for item: Array in [["before-after.png", "as_built-remembered-hero.png", "aged-present-hero.png"], ["neutral-pair.png", "as_built-neutral-hero.png", "aged-neutral-hero.png"], ["details.png", "as_built-neutral-detail.png", "aged-neutral-detail.png"], ["front-pair.png", "as_built-neutral-front.png", "aged-neutral-front.png"]]:
		_pair(item[0], item[1], item[2])
	report = {"prop": prop, "asset": asset, "cameras": cameras, "same_mesh": aged_asset == "", "same_pivots": aged_asset == "", "same_part_names": aged_asset == "", "same_footprint": aged_asset == "", "rigid_geometry_checked": aged_asset == "", "parts": initial, "present_colour": _vec(Vector3(Lighting.REGULAR_WHITE.r, Lighting.REGULAR_WHITE.g, Lighting.REGULAR_WHITE.b)), "present_energy": Lighting.regular_energy(), "diagnostics": "Unlit actual shader albedo for hue gates; IDs R=PaintedSteel G=up face B=prop coverage"}
	var file := FileAccess.open(output.path_join("preview.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print("CAPTURES ", output)
	stage.queue_free()
	await process_frame
	quit()

func _camera(angle: String) -> void:
	var scale := height / 2.4
	var positions := {"hero": Vector3(-2.0, 2.6, 3.5), "front": Vector3(0, 1.2, 4.5), "detail": Vector3(-0.6, 2.10, 2.5), "top": Vector3(-0.5, 3.7, 1.7)}
	camera.position = positions[angle] * scale + _camera_offset()
	camera.look_at(_target(angle), Vector3.UP)
	camera.size = (1.0 if angle == "detail" else (1.0 if angle == "top" else 2.85)) * scale
	if not is_nan(frame_size) and angle in ["hero", "front"]: camera.size = frame_size

func _target(angle: String) -> Vector3:
	return {"hero": Vector3(0, 1.2, 0), "front": Vector3(0, 1.2, 0), "detail": Vector3(0, 2.0, 0.27), "top": Vector3(0, 2.3, 0)}[angle] * (height / 2.4) + _camera_offset()

func _camera_offset() -> Vector3:
	return Vector3.ZERO if is_nan(centre_y) else Vector3(0, centre_y - height / 2, 0)

func _lighting(mode: String) -> void:
	ceiling.light_color = Lighting.REGULAR_WHITE if mode == "present" else (Color(1.0, 0.86, 0.68) if mode == "remembered" else Color.WHITE)
	ceiling.light_energy = Lighting.regular_energy() if mode == "present" else (2.0 if mode == "remembered" else 1.4)
	environment.ambient_light_energy = 0.20 if mode == "present" else (0.65 if mode == "remembered" else 0.55)
	fill.light_color = ceiling.light_color
	fill.light_energy = 0.18 if mode == "present" else 0.35

func _diagnostic(mode: int) -> bool:
	var pieces := model.find_children("*", "MeshInstance3D", true, false)
	for node: Node in pieces:
		var piece := node as MeshInstance3D
		if not piece.material_override is ShaderMaterial: return false
		var supported := false
		for uniform: Dictionary in (piece.material_override as ShaderMaterial).shader.get_shader_uniform_list():
			if uniform.name == "diagnostic": supported = true
		if not supported: return false
	# Preview-only copies keep diagnostics out of the shared runtime cache.
	for node: Node in pieces:
		var piece := node as MeshInstance3D
		if mode == 1: piece.material_override = piece.material_override.duplicate()
		(piece.material_override as ShaderMaterial).set_shader_parameter(&"diagnostic", mode)
	return true

func _capture(name: String) -> void:
	for index: int in range(3): await process_frame
	RenderingServer.force_draw(false)
	await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	assert(image.save_png(output.path_join(name)) == OK, "save capture: " + name)

func _pair(name: String, left: String, right: String) -> void:
	var a := Image.load_from_file(output.path_join(left))
	var b := Image.load_from_file(output.path_join(right))
	var sheet := Image.create(a.get_width() * 2, a.get_height(), false, a.get_format())
	sheet.blit_rect(a, Rect2i(Vector2i.ZERO, a.get_size()), Vector2i.ZERO)
	sheet.blit_rect(b, Rect2i(Vector2i.ZERO, b.get_size()), Vector2i(a.get_width(), 0))
	assert(sheet.save_png(output.path_join(name)) == OK)

func _parts(node: Node) -> Dictionary:
	var result := {}
	for child: Node in node.get_children():
		if child is Node3D:
			var entry := {"transform": str(child.transform), "mesh": 0, "bounds": ""}
			if child is MeshInstance3D:
				entry.mesh = child.mesh.get_instance_id()
				entry.bounds = str(child.get_aabb())
			entry.children = _parts(child)
			result[String(child.name)] = entry
	return result

func _vec(value: Vector3) -> Array:
	return [value.x, value.y, value.z]
