extends SceneTree
## Each prop and the finished locker share neutral light and physical image scale.

const OUTPUT := "res://tmp/mat2/render"
var stage: Node3D
var camera: Camera3D
var viewport: SubViewport

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "material captures require a windowed renderer")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	root.size = Vector2i(640, 640)
	viewport = SubViewport.new()
	viewport.size = Vector2i(1024, 1024)
	viewport.own_world_3d = true
	viewport.msaa_3d = Viewport.MSAA_4X
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	stage = Node3D.new()
	viewport.add_child(stage)
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(.055, .065, .075)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.ambient_light_energy = .55
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = environment
	stage.add_child(world)
	var ceiling := OmniLight3D.new()
	ceiling.position = Vector3(-.6, 3.0, 1.25)
	ceiling.omni_range = 8
	ceiling.light_color = Color.WHITE
	ceiling.light_energy = 1.4
	ceiling.shadow_enabled = true
	stage.add_child(ceiling)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, -25, 0)
	fill.light_energy = .35
	fill.light_specular = 0
	stage.add_child(fill)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.current = true
	stage.add_child(camera)
	var locker := (load("res://assets/props/quarters/storage_locker_module.glb") as PackedScene).instantiate() as Node3D
	stage.add_child(locker)
	locker.visible = false
	var metadata_path := OUTPUT.path_join("capture.json")
	var metadata: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(metadata_path)) if FileAccess.file_exists(metadata_path) else {}
	var requested := OS.get_cmdline_user_args()
	for prop: StringName in QuartersSteelLibrary.PROPS:
		if not requested.is_empty() and not requested.has(String(prop)): continue
		var model := (load("res://assets/props/quarters/%s.glb" % prop) as PackedScene).instantiate() as Node3D
		stage.add_child(model)
		model.visible = false
		var bounds := _bounds(model)
		var centre := bounds.get_center()
		var scale := maxf(maxf(bounds.size.x, bounds.size.y), bounds.size.z)
		var detail_target := centre
		var detail_size := minf(1.1, maxf(.5, scale*.6))
		if prop == &"view_screen":
			detail_target = Vector3(centre.x, bounds.end.y-.025, bounds.end.z)
			detail_size = .7
		var views := {
			"hero": [centre + Vector3(-.6, .55, 1.4)*scale, centre, maxf(3.2, scale*1.4)],
			"front": [centre + Vector3(0, 0, 2)*scale, centre, maxf(3.2, scale*1.4)],
			"top": [centre + Vector3(0, 2, .15)*scale, centre, maxf(1.2, maxf(bounds.size.x, bounds.size.z)*1.3)],
			"detail": [detail_target + Vector3(-.4, .3, 1.4)*scale, detail_target, detail_size],
		}
		metadata[prop] = {}
		for view: String in views:
			var pose: Array = views[view]
			metadata[prop][view] = {"position": str(pose[0]), "target": str(pose[1]), "size_m": pose[2]}
			if prop == &"wardrobe":
				camera.position = pose[0]
				camera.look_at(pose[1], Vector3.UP)
				camera.size = pose[2]
				model.visible = true
				for state: StringName in QuartersProps.STATES:
					QuartersProps._apply_wardrobe(model, state)
					await _capture("wardrobe-legacy-%s-%s.png" % [state, view])
				model.visible = false
			for reference: bool in [false, true]:
				var shown := locker if reference else model
				var identity := "locker" if reference else String(prop)
				var target: Vector3 = Vector3(0, 1.2, 0) if reference else centre
				if view == "top" and reference: target = Vector3(0, 2.38, 0)
				if view == "detail" and prop == &"view_screen" and reference: target = Vector3(0, 2.35, .30)
				camera.position = target + pose[0] - pose[1]
				camera.look_at(target, Vector3.UP)
				camera.size = pose[2]
				shown.visible = true
				for state: StringName in QuartersProps.STATES:
					if reference: QuartersProps.apply(shown, &"storage_locker_module", state)
					else: QuartersSteelLibrary.apply(shown, prop, state)
					await _capture("%s-%s-%s-%s.png" % [prop, identity, state, view])
					if not reference:
						var diagnostic := QuartersSteelLibrary.material(prop, state).duplicate() as ShaderMaterial
						var original_materials := _override(shown, diagnostic)
						for mode: int in [1, 2]:
							diagnostic.set_shader_parameter(&"diagnostic", mode)
							await _capture("%s-%s-%s-%s-%s.png" % [prop, identity, state, view, "albedo" if mode == 1 else "regions"])
						_restore(original_materials)
				shown.visible = false
		model.queue_free()
		await process_frame
		FileAccess.open(metadata_path, FileAccess.WRITE).store_string(JSON.stringify(metadata, "\t")+"\n")
	print("LIBRARY CAPTURES COMPLETE")
	quit()

func _bounds(model: Node3D) -> AABB:
	var result := AABB()
	var first := true
	for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		var bounds := part.global_transform * part.get_aabb()
		result = bounds if first else result.merge(bounds)
		first = false
	return result

func _override(model: Node3D, finish: ShaderMaterial) -> Array:
	var snapshots := []
	var excluded := StandardMaterial3D.new()
	excluded.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	excluded.albedo_color = Color.BLACK
	for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		var previous := []
		for surface: int in range(part.mesh.get_surface_count()):
			previous.append(part.get_surface_override_material(surface))
		snapshots.append([part, part.material_override, previous])
		part.material_override = null
		for surface: int in range(part.mesh.get_surface_count()):
			var source := part.mesh.surface_get_material(surface)
			var role := source.resource_name.to_lower()
			var keep := role.contains("display") or role.contains("glass") or role == "screen"
			part.set_surface_override_material(surface, excluded if keep else finish)
	return snapshots

func _restore(snapshots: Array) -> void:
	for snapshot: Array in snapshots:
		var part: MeshInstance3D = snapshot[0]
		part.material_override = snapshot[1]
		for surface: int in range(snapshot[2].size()):
			part.set_surface_override_material(surface, snapshot[2][surface])

func _capture(filename: String) -> void:
	for i: int in range(3): await process_frame
	RenderingServer.force_draw(false)
	await process_frame
	await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	assert(image.save_png(OUTPUT.path_join(filename)) == OK, "save matched image")
