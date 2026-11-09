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
	if prop == &"dress_uniform":
		await _run_tunic()
		return
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
	for angle: String in ["hero", "front", "detail", "top", "streaks"]:
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
				_diagnostic(3)
				await _capture("%s-regions-%s.png" % [state, angle])
				_diagnostic(4)
				await _capture("%s-orm-%s.png" % [state, angle])
				_diagnostic(5)
				await _capture("%s-doorface-%s.png" % [state, angle])
				_diagnostic(0)
				if state == &"aged" and angle == "top":
					_set_dust(false)
					for light: String in ["neutral", "present"]:
						_lighting(light)
						await _capture("aged-nodust-%s-top.png" % light)
					_diagnostic(1)
					await _capture("aged-nodust-albedo-top.png")
					_diagnostic(0)
					_set_dust(true)
	for item: Array in [["before-after.png", "as_built-remembered-hero.png", "aged-present-hero.png"], ["neutral-pair.png", "as_built-neutral-hero.png", "aged-neutral-hero.png"], ["details.png", "as_built-neutral-detail.png", "aged-neutral-detail.png"], ["front-pair.png", "as_built-neutral-front.png", "aged-neutral-front.png"], ["streaks-closeup.png", "as_built-neutral-streaks.png", "aged-neutral-streaks.png"]]:
		_pair(item[0], item[1], item[2])
	if prop == &"storage_locker_module": _detail_sheet()
	report = {"prop": prop, "asset": asset, "cameras": cameras, "same_mesh": aged_asset == "", "same_pivots": aged_asset == "", "same_part_names": aged_asset == "", "same_footprint": aged_asset == "", "rigid_geometry_checked": aged_asset == "", "parts": initial, "present_colour": _vec(Vector3(Lighting.REGULAR_WHITE.r, Lighting.REGULAR_WHITE.g, Lighting.REGULAR_WHITE.b)), "present_energy": Lighting.regular_energy(), "diagnostics": "Unlit actual shader albedo for hue gates; IDs R=PaintedSteel G=up face B=prop coverage"}
	var file := FileAccess.open(output.path_join("preview.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	print("CAPTURES ", output)
	stage.queue_free()
	await process_frame
	quit()

func _camera(angle: String) -> void:
	var scale := height / 2.4
	var positions := {"hero": Vector3(-2.0, 2.6, 3.5), "front": Vector3(0, 1.2, 4.5), "detail": Vector3(-0.6, 2.10, 2.5), "top": Vector3(-0.5, 3.7, 1.7), "streaks": Vector3(-0.275, 2.15, 0.70)}
	camera.position = positions[angle] * scale + _camera_offset()
	camera.look_at(_target(angle), Vector3.UP)
	camera.size = (0.20 if angle == "streaks" else (1.0 if angle in ["detail", "top"] else 2.85)) * scale
	if not is_nan(frame_size) and angle in ["hero", "front"]: camera.size = frame_size

func _target(angle: String) -> Vector3:
	return {"hero": Vector3(0, 1.2, 0), "front": Vector3(0, 1.2, 0), "detail": Vector3(0, 2.0, 0.27), "top": Vector3(0, 2.3, 0), "streaks": Vector3(-0.275, 2.15, 0.30)}[angle] * (height / 2.4) + _camera_offset()

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
		(piece.material_override as ShaderMaterial).set_shader_parameter(&"diagnostic_door", piece.name == &"Door")
	return true

func _set_dust(enabled: bool) -> void:
	for node: Node in model.find_children("*", "MeshInstance3D", true, false):
		(node.material_override as ShaderMaterial).set_shader_parameter(&"dust_enabled", enabled)

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

func _detail_sheet() -> void:
	_pair("top-pair.png", "as_built-neutral-top.png", "aged-neutral-top.png")
	var upper := Image.load_from_file(output.path_join("details.png"))
	var top := Image.load_from_file(output.path_join("top-pair.png"))
	var sheet := Image.create(2048, 2048, false, upper.get_format())
	sheet.blit_rect(upper, Rect2i(0, 0, 2048, 1024), Vector2i.ZERO)
	sheet.blit_rect(top, Rect2i(0, 0, 2048, 1024), Vector2i(0, 1024))
	assert(sheet.save_png(output.path_join("details.png")) == OK)

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


var tunic_view: SubViewport
var tunic_states: Dictionary = {}
var tunic_lockers: Dictionary = {}

func _run_tunic() -> void:
	assert(DisplayServer.get_name() != "headless", "captures require a windowed renderer")
	output = ProjectSettings.globalize_path(output)
	assert(DirAccess.make_dir_recursive_absolute(output) == OK)
	root.size = Vector2i(960, 960)
	tunic_view = SubViewport.new()
	tunic_view.size = Vector2i(1024, 1024)
	tunic_view.own_world_3d = true
	tunic_view.msaa_3d = Viewport.MSAA_4X
	tunic_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(tunic_view)
	var display := TextureRect.new()
	display.texture = tunic_view.get_texture()
	display.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	display.size = Vector2(960, 960)
	root.add_child(display)
	stage = Node3D.new()
	tunic_view.add_child(stage)
	var world := WorldEnvironment.new()
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(.055, .065, .075)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = environment
	stage.add_child(world)
	camera = Camera3D.new()
	stage.add_child(camera)
	camera.current = true
	ceiling = OmniLight3D.new()
	ceiling.position = Vector3(.1, 2.65, 1.0)
	ceiling.omni_range = Lighting.REGULAR_RANGE
	ceiling.shadow_enabled = true
	stage.add_child(ceiling)
	fill = DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, -25, 0)
	fill.light_specular = 0
	stage.add_child(fill)
	for state: StringName in QuartersProps.STATES:
		var group := Node3D.new()
		stage.add_child(group)
		tunic_states[state] = group
		for debris: bool in [false, true]:
			var garment := (load(QuartersProps.TUNIC_SCENES[state]) as PackedScene).instantiate() as Node3D
			group.add_child(garment)
			var before := _parts(garment)
			QuartersProps.apply(garment, &"dress_uniform", state)
			assert(_parts(garment) == before, "tunic finish preserves imported geometry and hierarchy")
			for piece: MeshInstance3D in garment.find_children("*", "MeshInstance3D", true, false):
				var fallen := String(piece.name).begins_with("FallenHem") or piece.name in [&"FibreDust", &"HeapFibres"]
				piece.visible = fallen == debris
			garment.position = Vector3(-.015, 1.055, .10) if debris else Vector3(-.015, 1.65, .17)
			garment.rotation.y = deg_to_rad(55)
		var locker := (load("res://assets/props/quarters/storage_locker_module.glb") as PackedScene).instantiate() as Node3D
		stage.add_child(locker)
		QuartersProps.apply(locker, &"storage_locker_module", state)
		var hinge := Vector3(-.26, 0, .258)
		var swing := Transform3D(Basis(Vector3.UP, deg_to_rad(-112)), Vector3.ZERO)
		var door_pose := Transform3D(Basis.IDENTITY, hinge) * swing * Transform3D(Basis.IDENTITY, -hinge)
		for piece: MeshInstance3D in locker.find_children("*", "MeshInstance3D", true, false):
			if String(piece.name).begins_with("Door") or String(piece.name).begins_with("Handle"):
				piece.transform = door_pose * piece.transform
		var rail := MeshInstance3D.new()
		var cylinder := CylinderMesh.new()
		cylinder.top_radius = .009
		cylinder.bottom_radius = .009
		cylinder.height = .566
		rail.mesh = cylinder
		rail.position = Vector3(0, 1.633, .17)
		rail.rotation.z = PI / 2
		var rail_finish := StandardMaterial3D.new()
		rail_finish.albedo_color = Color(.22, .23, .24) if state == &"as_built" else Color(.15, .13, .11)
		rail_finish.metallic = .8 if state == &"as_built" else .15
		rail_finish.roughness = .3 if state == &"as_built" else .94
		rail.material_override = rail_finish
		locker.add_child(rail)
		tunic_lockers[state] = locker
		group.visible = false
		locker.visible = false
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(4, 4)
	floor.mesh = plane
	floor.position.y = .104
	var floor_finish := StandardMaterial3D.new()
	floor_finish.albedo_color = Color(.20, .21, .22)
	floor_finish.roughness = 1.0
	floor.material_override = floor_finish
	stage.add_child(floor)
	for state: StringName in QuartersProps.STATES:
		tunic_states[state].visible = true
		_tunic_camera("hero")
		for light: String in ["remembered", "present", "neutral"]:
			_lighting(light)
			await _tunic_capture("%s-%s-hero.png" % [state, light])
		_tunic_camera("shoulder")
		_lighting("neutral")
		await _tunic_capture("%s-neutral-shoulder.png" % state)
		tunic_lockers[state].visible = true
		_tunic_camera("locker")
		_lighting("remembered" if state == &"as_built" else "present")
		await _tunic_capture("%s-in-locker.png" % state)
		tunic_lockers[state].visible = false
		tunic_states[state].visible = false
	_pair("before-after.png", "as_built-remembered-hero.png", "aged-present-hero.png")
	_pair("neutral-pair.png", "as_built-neutral-hero.png", "aged-neutral-hero.png")
	_pair("closeup.png", "as_built-neutral-shoulder.png", "aged-neutral-shoulder.png")
	_pair("in-locker.png", "as_built-in-locker.png", "aged-in-locker.png")
	await _tunic_colour_capture()
	var file := FileAccess.open(output.path_join("preview.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify({"prop": "dress_uniform", "renderer": RenderingServer.get_current_rendering_method(), "shoulder_distance_m": .5, "shoulder_target": _vec(_tunic_shoulder()), "present_colour": [1.0, .97, .90], "present_energy": Lighting.regular_energy(), "door_open_degrees": 112, "garment_yaw_degrees": 55, "tonemap": "linear", "geometry_preserved_per_state": true}, "\t") + "\n")
	print("CAPTURES ", output)
	stage.queue_free()
	await process_frame
	quit()

func _tunic_shoulder() -> Vector3:
	return Vector3(-.015, 1.65, .17) + Basis(Vector3.UP, deg_to_rad(55)) * Vector3(.235, -.285, .01)

func _tunic_camera(view: String) -> void:
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 1.9
	camera.position = Vector3(1.15, 1.45, 3.2)
	var target := Vector3(0, .94, .10)
	if view == "locker":
		camera.size = 2.7
		camera.position = Vector3(.82, 1.9, 2.9)
		target = Vector3(0, 1.18, .02)
	if view == "shoulder":
		target = _tunic_shoulder()
		camera.position = target + Vector3(.16, .22, .96).normalized() * .5
		camera.projection = Camera3D.PROJECTION_PERSPECTIVE
		camera.fov = rad_to_deg(2 * atan(36.0 / (2 * 40.0)))
		assert(absf(camera.position.distance_to(target) - .5) < .00001)
	camera.look_at(target, Vector3.UP)

func _tunic_colour_capture() -> void:
	tunic_states[&"aged"].visible = true
	tunic_lockers[&"aged"].visible = true
	var target := Vector3(-.025945166, 1.292561531, .269643456)
	var normal := Vector3(.771218181, -.012322559, .636451721).normalized()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = .049
	camera.position = target + normal * .5
	camera.look_at(target, Vector3.UP)
	tunic_view.size = Vector2i(49, 49)
	ceiling.light_color = Color.WHITE
	ceiling.light_energy = 4.17
	environment.ambient_light_energy = .0072
	fill.light_energy = 0
	await _tunic_capture("aged-chest-neutral.png")
	# A co-located neutral reference separates illumination matching from wool calibration.
	var grey := MeshInstance3D.new()
	var plane := QuadMesh.new()
	plane.size = Vector2(.08, .08)
	grey.mesh = plane
	stage.add_child(grey)
	grey.position = target + normal * .005
	grey.look_at(grey.position + normal, Vector3.UP, true)
	var finish := StandardMaterial3D.new()
	finish.albedo_color = Color(.18, .18, .18).linear_to_srgb()
	finish.roughness = .97
	finish.metallic_specular = .12
	grey.material_override = finish
	await _tunic_capture("neutral-grey.png")
	grey.queue_free()

func _tunic_capture(name: String) -> void:
	for index: int in range(4): await process_frame
	await RenderingServer.frame_post_draw
	var image := tunic_view.get_texture().get_image()
	assert(image.save_png(output.path_join(name)) == OK, "save tunic capture: " + name)
