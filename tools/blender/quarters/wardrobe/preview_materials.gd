extends SceneTree
## Equal physical image scale and fixed white lighting for candidate and locker.

const OUTPUT := "res://tmp/mat1/wardrobe/render"
var stage: Node3D
var camera: Camera3D
var capture_viewport: SubViewport
var models: Dictionary = {}

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	assert(DisplayServer.get_name() != "headless", "material review needs a windowed renderer")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUTPUT))
	root.size = Vector2i(640, 640)
	capture_viewport = SubViewport.new()
	capture_viewport.size = Vector2i(1024, 1024)
	capture_viewport.own_world_3d = true
	capture_viewport.msaa_3d = Viewport.MSAA_4X
	capture_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(capture_viewport)
	stage = Node3D.new()
	capture_viewport.add_child(stage)
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
	ceiling.omni_range = 8.0
	ceiling.light_color = Color.WHITE
	ceiling.light_energy = 1.4
	ceiling.shadow_enabled = true
	stage.add_child(ceiling)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, -25, 0)
	fill.light_color = Color.WHITE
	fill.light_energy = .35
	fill.light_specular = 0
	stage.add_child(fill)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.current = true
	stage.add_child(camera)
	for prop: StringName in [&"wardrobe", &"storage_locker_module"]:
		var scene: PackedScene = load("res://assets/props/quarters/%s.glb" % prop)
		var model := scene.instantiate() as Node3D
		stage.add_child(model)
		model.visible = false
		models[prop] = model
	var views := {
		"hero": [Vector3(-2.0, 2.6, 3.5), Vector3(0, 1.2, 0), 3.2],
		"front": [Vector3(0, 1.2, 4.5), Vector3(0, 1.2, 0), 3.2],
		"top": [Vector3(-.5, 3.7, 1.7), Vector3(0, 2.18, 0), 1.15],
		"roof": [Vector3(0, 4, 0), Vector3(0, 2.2, 0), 1.15],
		"detail": [Vector3(-1.4, 2.0, 2.4), Vector3(-.35, 1.85, .25), .55],
		"hardware": [Vector3(-.61, 1.4, 1.101), Vector3(-.26, 1.25, .301), .35],
		"trim": [Vector3(0, .22, 1.4), Vector3(0, .08, .33), 1.2],
	}
	for view: String in views:
		var pose: Array = views[view]
		camera.position = pose[0]
		camera.look_at(pose[1], Vector3.FORWARD if view == "roof" else Vector3.UP)
		camera.size = pose[2]
		for prop: StringName in models:
			var model: Node3D = models[prop]
			if view == "hardware":
				var hinge := Vector3(.5, 1.12, .34) if prop == &"wardrobe" else Vector3(-.26, 1.25, .301)
				camera.position = hinge + Vector3(-.35, .15, .8)
				camera.look_at(hinge, Vector3.UP)
			model.visible = true
			for state: StringName in QuartersProps.STATES:
				QuartersProps.apply(model, prop, state)
				await _capture("%s-%s-%s.png" % [prop, state, view])
				if prop == &"wardrobe":
					var control := QuartersProps.material(prop, state).duplicate() as ShaderMaterial
					for piece: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
						piece.material_override = control
					for mode: int in [1, 2, 3]:
						control.set_shader_parameter(&"diagnostic", mode)
						await _capture("%s-%s-%s-%s.png" % [prop, state, view, ["", "albedo", "regions", "materials"][mode]])
				if state == &"aged":
					var flat := QuartersProps.material(prop, state).duplicate() as ShaderMaterial
					if prop == &"wardrobe":
						flat.set_shader_parameter(&"relief_enabled", false)
					else:
						flat.set_shader_parameter(&"diagnostic", 8)
					for piece: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
						piece.material_override = flat
					await _capture("%s-%s-%s-flat.png" % [prop, state, view])
			model.visible = false
	var metadata := {"views": {}, "orthographic": true, "hero_pixels_per_metre": 1024.0 / 3.2, "lights": "white; ambient .55, omni 1.4 at (-.6,3,1.25), directional .35; linear tonemap"}
	metadata["hardware_targets"] = {"wardrobe": [.5, 1.12, .34], "storage_locker_module": [-.26, 1.25, .301], "camera_offset": [-.35, .15, .8], "size_m": .35}
	for view: String in views:
		metadata.views[view] = {"position": str(views[view][0]), "target": str(views[view][1]), "size_m": views[view][2], "camera_up": str(Vector3.FORWARD if view == "roof" else Vector3.UP)}
	FileAccess.open(OUTPUT.path_join("capture.json"), FileAccess.WRITE).store_string(JSON.stringify(metadata, "\t") + "\n")
	print("MATCHED MATERIAL CAPTURES ", OUTPUT)
	quit()

func _capture(filename: String) -> void:
	for index: int in range(3): await process_frame
	RenderingServer.force_draw(false)
	await process_frame
	await RenderingServer.frame_post_draw
	var image := capture_viewport.get_texture().get_image()
	assert(image.get_size() == Vector2i(1024, 1024), "fixed physical image scale")
	assert(image.save_png(OUTPUT.path_join(filename)) == OK, "save matched capture")
