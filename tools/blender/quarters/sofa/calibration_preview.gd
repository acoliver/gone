extends "res://tools/blender/quarters/sofa/material_preview.gd"

func _run() -> void:
	assert(DisplayServer.get_name() != "headless")
	output = ProjectSettings.globalize_path(output)
	DirAccess.make_dir_recursive_absolute(output)
	root.size = Vector2i(1024, 1024)
	root.content_scale_size = root.size
	root.msaa_3d = Viewport.MSAA_4X
	stage = Node3D.new()
	root.add_child(stage)
	var world := WorldEnvironment.new()
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(.055, .065, .075)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color.WHITE
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = environment
	stage.add_child(world)
	ceiling = OmniLight3D.new()
	ceiling.position = Vector3(-.6, 1.46, 1.25)
	ceiling.omni_range = Lighting.REGULAR_RANGE
	ceiling.shadow_enabled = true
	stage.add_child(ceiling)
	fill = DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, -25, 0)
	fill.light_specular = 0
	stage.add_child(fill)
	camera = Camera3D.new()
	stage.add_child(camera)
	camera.current = true
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = .25
	var inputs: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(output.path_join("swatches.json")))
	for role: String in inputs:
		var entry: Dictionary = inputs[role]
		_lighting(entry.light)
		var swatch := MeshInstance3D.new()
		var plane := QuadMesh.new()
		plane.size = Vector2(.2, .2)
		swatch.mesh = plane
		swatch.position = Vector3(entry.position[0], entry.position[1], entry.position[2])
		var normal := Vector3(entry.normal[0], entry.normal[1], entry.normal[2]).normalized()
		stage.add_child(swatch)
		swatch.look_at(swatch.position + normal, Vector3.FORWARD if absf(normal.y) > .9 else Vector3.UP, true)
		var pigment := ShaderMaterial.new()
		var shader := Shader.new()
		shader.code = "shader_type spatial; render_mode cull_disabled; uniform vec3 pigment; void fragment() { ALBEDO = pigment; ROUGHNESS = .96; METALLIC = 0.0; }"
		pigment.shader = shader
		pigment.set_shader_parameter("pigment", Vector3(entry.albedo[0], entry.albedo[1], entry.albedo[2]))
		swatch.material_override = pigment
		camera.position = swatch.position + normal * .6
		camera.look_at(swatch.position, Vector3.FORWARD if absf(normal.y) > .9 else Vector3.UP)
		await _capture(role + ".png")
		swatch.queue_free()
		await process_frame
	quit()
