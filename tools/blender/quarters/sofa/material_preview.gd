extends "res://tools/quarters_pilot_preview.gd"

var floor_mesh: MeshInstance3D

func _lighting(mode: String) -> void:
	super._lighting(mode)
	if floor_mesh == null:
		floor_mesh = MeshInstance3D.new()
		var plane := PlaneMesh.new()
		plane.size = Vector2(8, 8)
		floor_mesh.mesh = plane
		floor_mesh.position.y = -.001
		var finish := ShaderMaterial.new()
		var shader := Shader.new()
		shader.code = "shader_type spatial; void fragment() { ALBEDO = vec3(.32, .31, .29); ROUGHNESS = 1.0; }"
		finish.shader = shader
		floor_mesh.material_override = finish
		stage.add_child(floor_mesh)

func _capture(name: String) -> void:
	await super._capture(name)
	if name == "aged-present-hero.png":
		var changed: Array[MeshInstance3D] = []
		for node: Node in model.find_children("*", "MeshInstance3D", true, false):
			if node.name == &"FoamDebris" or String(node.name).begins_with("FineFloorPowder"):
				changed.append(node as MeshInstance3D)
				node.visible = false
		await super._capture("debris-off.png")
		for node: MeshInstance3D in changed: node.visible = true
		await super._capture("debris-on.png")
		var saved: Array[ShaderMaterial] = []
		for node: Node in model.find_children("*", "MeshInstance3D", true, false):
			var piece := node as MeshInstance3D
			saved.append(piece.material_override)
			var mask := ShaderMaterial.new()
			var shader := Shader.new()
			shader.code = "shader_type spatial; render_mode unshaded, cull_disabled; uniform sampler2D cutout : filter_linear_mipmap_anisotropic, repeat_disable; uniform bool debris; varying float height; void vertex() { height = (MODEL_MATRIX * vec4(VERTEX, 1.0)).y; } void fragment() { ALPHA = texture(cutout, UV).a; ALPHA_SCISSOR_THRESHOLD = .5; ALBEDO = vec3(debris && height < .04 ? 1.0 : 0.0); }"
			if String(piece.name).contains("Powder"):
				shader.code = shader.code.replace("ALPHA_SCISSOR_THRESHOLD = .5;", "")
			mask.shader = shader
			mask.set_shader_parameter("cutout", QuartersProps.SOFA_SETS[&"aged"]["albedo"])
			mask.set_shader_parameter("debris", piece in changed)
			piece.material_override = mask
		floor_mesh.visible = false
		var background := environment.background_color
		environment.background_color = Color.BLACK
		await super._capture("debris-mask.png")
		environment.background_color = background
		floor_mesh.visible = true
		var index := 0
		for node: Node in model.find_children("*", "MeshInstance3D", true, false):
			node.material_override = saved[index]
			node.visible = true
			index += 1
	if name in ["as_built-neutral-detail.png", "aged-neutral-detail.png"]:
		var position := camera.position
		var target := _target("detail")
		var rail := Vector3(0, .23, .475)
		camera.position = rail + Vector3(0, .12, .6).normalized() * .6
		camera.look_at(rail, Vector3.UP)
		await super._capture(name.replace("detail", "rail"))
		camera.position = position
		camera.look_at(target, Vector3.UP)

func _camera(angle: String) -> void:
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.8
	match angle:
		"hero": camera.position = Vector3(3.1, 2.2, 3.5)
		"front": camera.position = Vector3(0, .55, 4.0)
		"top":
			camera.position = Vector3(-.4, 2.4, 1.4)
			camera.size = 2.55
		"detail", "streaks":
			camera.projection = Camera3D.PROJECTION_PERSPECTIVE
			camera.fov = 43.6028
			camera.position = _target(angle) + Vector3(-.18, .28, .50).normalized() * .6
	camera.look_at(_target(angle), Vector3.UP)

func _target(angle: String) -> Vector3:
	match angle:
		"detail": return Vector3(-.18, .46, .29)
		"streaks": return Vector3(1.05, .50, .18)
		_: return Vector3(0, .43, 0)
