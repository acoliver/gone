extends SceneTree
## Windowed optical regression fixture. Values are measured from linearized pixels.
## Run: godot --path . -s tools/glass_validation.gd -- --out tmp/pods/fix3/optics

var stage: Node3D
var camera: Camera3D
var pane: MeshInstance3D
var checker: MeshInstance3D
var card: MeshInstance3D
var probe: ReflectionProbe
var world: WorldEnvironment
var output := "res://tmp/pods/fix3/optics"
var results: Dictionary = {}
var failures: Array[String] = []
var opaque: StandardMaterial3D
var mirror: StandardMaterial3D
var glass: Material

func _initialize() -> void:
	for i: int in range(OS.get_cmdline_user_args().size() - 1):
		if OS.get_cmdline_user_args()[i] == "--out":
			output = OS.get_cmdline_user_args()[i + 1]
	DirAccess.make_dir_recursive_absolute(output)
	_run.call_deferred()

func _run() -> void:
	root.size = Vector2i(1152, 648)
	# Interior probes omit the Environment, including its background color.
	RenderingServer.set_default_clear_color(Color.BLACK)
	root.always_on_top = true
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	stage = Node3D.new()
	root.add_child(stage)
	world = Lighting._world_environment()
	stage.add_child(world)
	camera = Camera3D.new()
	camera.fov = 60
	# Parallel coupon rays isolate local incidence from perspective variation.
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 2.0
	camera.far = 10.0
	stage.add_child(camera)
	pane = MeshInstance3D.new()
	pane.mesh = _coupon()
	pane.sorting_use_aabb_center = true
	pane.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	stage.add_child(pane)
	glass = PodMesh.canopy_material()
	pane.material_override = glass
	opaque = StandardMaterial3D.new()
	opaque.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	opaque.albedo_color = Color.BLACK
	mirror = StandardMaterial3D.new()
	mirror.albedo_color = Color.WHITE
	mirror.metallic = 1.0
	# Godot's ambient-luminance occlusion otherwise zeros a valid probe capture.
	mirror.disable_specular_occlusion = true
	mirror.roughness = 0.07
	mirror.cull_mode = BaseMaterial3D.CULL_DISABLED
	checker = MeshInstance3D.new()
	checker.mesh = _checker_mesh()
	stage.add_child(checker)
	var transfers: Array[float] = []
	for angle: float in [0.0, 60.0, 80.0]:
		_pose(angle)
		pane.visible = false
		var reference := await _capture("transfer-%d-hidden" % angle)
		pane.visible = true
		pane.material_override = glass
		var candidate := await _capture("transfer-%d-glass" % angle)
		var measurement := _transfer(reference, candidate)
		results["transfer_%d" % angle] = measurement
		var target: float = {0.0: 0.9408, 60.0: 0.9114, 80.0: 0.5783}[angle]
		var tolerance: float = {0.0: 0.03, 60.0: 0.05, 80.0: 0.08}[angle]
		_gate("transfer_%d" % angle, absf(measurement.transfer - target) <= tolerance, measurement.transfer, [target - tolerance, target + tolerance])
		_gate("coverage_%d" % angle, measurement.pixels >= 1000 and measurement.cells >= 16, [measurement.pixels, measurement.cells], [1000,16])
		_gate("radiance_%d" % angle, measurement.reference_bright >= 0.10 and measurement.reference_bright <= 0.70, measurement.reference_bright, [0.10,0.70])
		if angle == 0.0:
			_gate("checker_correlation", measurement.correlation >= 0.98, measurement.correlation, 0.98)
			_gate("roi_pixels", measurement.pixels >= 1000, measurement.pixels, 1000)
			pane.material_override = opaque
			var black := _transfer(reference, await _capture("opaque-black"))
			_gate("opaque_control", black.transfer < 0.02, black.transfer, 0.02)
			pane.visible = false
			var removed := _transfer(reference, await _capture("removed-pane"))
			_gate("removed_control", absf(removed.transfer - 1.0) < 0.01, removed.transfer, [0.99, 1.01])
			pane.visible = true
			pane.material_override = glass
			var cap := MeshInstance3D.new()
			cap.mesh = pane.mesh
			cap.position.z = -0.005
			cap.material_override = opaque
			stage.add_child(cap)
			var capped := _transfer(reference, await _capture("opaque-cap"))
			_gate("opaque_cap_detected", capped.transfer < 0.02, capped.transfer, 0.02)
			cap.free()
		transfers.append(measurement.transfer)
	_gate("transmission_falloff", transfers[0] > transfers[1] and transfers[1] > transfers[2], transfers, "T0 > T60 > T80")
	checker.visible = false
	pane.visible = true
	var reflections: Array[float] = []
	for angle: float in [0.0, 60.0, 80.0]:
		_pose(angle)
		var r := await _reflection(angle)
		reflections.append(r)
	_gate("reflection_normal", reflections[0] >= 0.02 and reflections[0] <= 0.08, reflections[0], [0.02, 0.08])
	_gate("fresnel_60", reflections[0] > 0.0 and reflections[1] >= 1.15 * reflections[0], reflections[1] / maxf(reflections[0], 1e-9), 1.15)
	_gate("fresnel_80", reflections[2] / maxf(reflections[0], 1e-9) >= 4.0, reflections[2] / maxf(reflections[0], 1e-9), 4.0)
	_gate("reflection_grazing", reflections[2] >= 0.20 and reflections[2] <= 0.65, reflections[2], [0.20, 0.65])
	results["metadata"] = {"engine": Engine.get_version_info(), "renderer": RenderingServer.get_current_rendering_method(), "device": RenderingServer.get_video_adapter_name(), "resolution": [1152, 648], "exposure": 2.0, "asset_sha256": FileAccess.get_sha256(PodMesh.POD_PATH), "shader_sha256": FileAccess.get_sha256("res://app/pod_glass.gdshader"), "source_base": "ab4cb03", "failures": failures}
	FileAccess.open(output.path_join("measurements.json"), FileAccess.WRITE).store_string(JSON.stringify(results, "\t"))
	print("GLASS VALIDATION ", "PASS" if failures.is_empty() else "FAIL", " ", failures)
	quit(0 if failures.is_empty() else 1)

func _coupon() -> ArrayMesh:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for v: Vector3 in [Vector3(-2,-2,0), Vector3(2,2,0), Vector3(2,-2,0), Vector3(-2,-2,0), Vector3(-2,2,0), Vector3(2,2,0)]:
		tool.set_normal(Vector3.BACK)
		tool.set_color(Color(0,0,0,1))
		tool.add_vertex(v)
	return tool.commit()

func _checker_mesh() -> ArrayMesh:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.vertex_color_use_as_albedo = true
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	tool.set_material(material)
	for x: int in range(-30,30):
		for y: int in range(-60,60):
			# With production exposure 2, the bright witness remains below clipping.
			var value := 0.175 if (x + y) % 2 == 0 else 0.025
			for offset: Vector2 in [Vector2(0,0),Vector2(1,0),Vector2(1,1),Vector2(0,0),Vector2(1,1),Vector2(0,1)]:
				tool.set_color(Color(value,value,value,1))
				tool.set_normal(Vector3.BACK)
				tool.add_vertex(Vector3((x + offset.x) * 0.15,(y + offset.y) * 0.08,-0.15))
	return tool.commit()

func _pose(angle: float) -> void:
	var radians := deg_to_rad(angle)
	camera.position = Vector3(sin(radians), 0, cos(radians)) * 2.0
	camera.look_at(Vector3.ZERO)
	camera.force_update_transform()

func _capture(label: String) -> Image:
	for frame: int in range(4):
		await process_frame
		await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	image.save_png(output.path_join(label + ".png"))
	if not results.has("views"):
		results.views = {}
	var frame := camera.global_transform
	results.views[label] = {"eye": [frame.origin.x,frame.origin.y,frame.origin.z], "basis": [frame.basis.x.x,frame.basis.x.y,frame.basis.x.z,frame.basis.y.x,frame.basis.y.y,frame.basis.y.z,frame.basis.z.x,frame.basis.z.y,frame.basis.z.z], "fov": camera.fov, "projection": camera.projection, "orthogonal_size": camera.size, "near": camera.near, "far": camera.far}
	return image

func _linear(image: Image, x: int, y: int) -> float:
	var color := image.get_pixel(x,y).srgb_to_linear()
	return color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722

func _transfer(reference: Image, candidate: Image) -> Dictionary:
	var low: Array[float] = []
	var high: Array[float] = []
	var ref_low: Array[float] = []
	var ref_high: Array[float] = []
	var pairs: Array[Vector2] = []
	var cells: Dictionary[Vector2i, bool] = {}
	var target_angle := rad_to_deg(acos(absf(camera.global_position.normalized().z)))
	# The coupon fills this central ROI even at 80 degrees. Exclude checker edges
	# using the independent pane-hidden witness's local flatness, not glass color.
	for y: int in range(132,516):
		for x: int in range(546,606):
			var direction := camera.project_ray_normal(Vector2(x+0.5,y+0.5))
			var local_angle := rad_to_deg(acos(absf(direction.z)))
			if target_angle >= 59.0 and absf(local_angle-target_angle) > 1.0:
				continue
			var value := _linear(reference,x,y)
			if absf(value - _linear(reference,x+2,y)) > 0.005 or absf(value - _linear(reference,x-2,y)) > 0.005 or absf(value - _linear(reference,x,y+2)) > 0.005 or absf(value - _linear(reference,x,y-2)) > 0.005:
				continue
			var actual := _linear(candidate,x,y)
			if value > 0.15:
				high.append(actual)
				ref_high.append(value)
			else:
				low.append(actual)
				ref_low.append(value)
			pairs.append(Vector2(value,actual))
			var origin := camera.project_ray_origin(Vector2(x+0.5,y+0.5))
			var hit := origin + direction * ((-0.15-origin.z)/direction.z)
			cells[Vector2i(floori(hit.x/0.15),floori(hit.y/0.08))] = true
	var mx := 0.0
	var my := 0.0
	for pair: Vector2 in pairs:
		mx += pair.x / maxf(pairs.size(),1)
		my += pair.y / maxf(pairs.size(),1)
	var covariance := 0.0
	var vx := 0.0
	var vy := 0.0
	for pair: Vector2 in pairs:
		covariance += (pair.x-mx)*(pair.y-my)
		vx += (pair.x-mx)*(pair.x-mx)
		vy += (pair.y-my)*(pair.y-my)
	return {"transfer": (_mean(high)-_mean(low))/maxf(_mean(ref_high)-_mean(ref_low),1e-9), "correlation": covariance/maxf(sqrt(vx*vy),1e-9), "pixels": pairs.size(), "cells": cells.size(), "reference_bright": _mean(ref_high), "mean": my}

func _mean(values: Array[float]) -> float:
	var sum := 0.0
	for v: float in values:
		sum += v
	return sum / maxf(values.size(),1)

func _patch(image: Image) -> float:
	var sum := 0.0
	for y: int in range(304,344):
		for x: int in range(556,596):
			sum += _linear(image,x,y)
	return sum / 1600.0

func _refresh() -> void:
	if probe != null:
		probe.free()
	probe = Lighting.bay_reflection_probe()
	probe.position = Vector3(0, 0, 0.25)
	probe.size = Vector3(8,8,8)
	stage.add_child(probe)
	for i: int in range(18):
		await process_frame
		await RenderingServer.frame_post_draw

func _reflection(angle: float) -> float:
	camera.far = 2.5
	if card != null:
		card.free()
	card = MeshInstance3D.new()
	var mesh := QuadMesh.new()
	mesh.size = Vector2(4,4)
	card.mesh = mesh
	card.layers = 1
	camera.cull_mask = 1
	var material := StandardMaterial3D.new()
	material.albedo_color = Color.BLACK
	material.emission_enabled = true
	# Unshaded black ignores emission; the source gate must see actual radiance.
	material.emission = Color(0.35,0.35,0.35)
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	card.material_override = material
	var direction := Vector3(-sin(deg_to_rad(angle)),0,cos(deg_to_rad(angle)))
	card.position = direction * 3.0
	stage.add_child(card)
	card.look_at(Vector3.ZERO)
	var old_camera := camera.transform
	camera.position = card.position * 1.25
	camera.look_at(card.position)
	camera.far = 10.0
	var source := _patch(await _capture("reflection-%d-source" % angle))
	_gate("emissive_source_%d" % angle, source >= 0.1 and source <= 0.7, source, [0.1,0.7])
	camera.transform = old_camera
	camera.far = 2.5
	card.visible = false
	await _refresh()
	pane.material_override = mirror
	var mirror_off := _patch(await _capture("reflection-%d-mirror-off" % angle))
	pane.material_override = glass
	var off := _patch(await _capture("reflection-%d-off" % angle))
	card.visible = true
	await _refresh()
	var enabled := _patch(await _capture("reflection-%d-glass" % angle))
	pane.material_override = mirror
	var normalized := _patch(await _capture("reflection-%d-mirror" % angle))
	var card_signal := enabled - off
	var mirror_signal := normalized - mirror_off
	var diffuse := StandardMaterial3D.new()
	diffuse.albedo_color = Color.WHITE
	diffuse.metallic_specular = 0.0
	diffuse.roughness = 1.0
	pane.material_override = diffuse
	var fill := _patch(await _capture("reflection-%d-diffuse-fill" % angle))
	_gate("zero_diffuse_fill_%d" % angle, fill < 0.001, fill, 0.001)
	_gate("mirror_positive_control_%d" % angle, mirror_signal >= 0.005, mirror_signal, 0.005)
	_gate("reflection_card_signal_%d" % angle, card_signal >= 0.005, card_signal, 0.005)
	pane.material_override = glass
	pane.visible = false
	var removed := _patch(await _capture("reflection-%d-removed" % angle))
	_gate("reflection_removed_%d" % angle, removed < card_signal * 0.01, removed, card_signal * 0.01)
	pane.visible = true
	probe.free()
	probe = null
	var no_probe := _patch(await _capture("reflection-%d-no-probe" % angle))
	_gate("reflection_probe_%d" % angle, no_probe - off < card_signal * 0.1, no_probe-off, card_signal*0.1)
	return card_signal / maxf(mirror_signal,1e-9)

func _gate(label: String, passed: bool, value: Variant, threshold: Variant) -> void:
	results[label] = {"pass": passed, "measured": value, "threshold": threshold}
	print(label, ": ", results[label])
	if not passed:
		failures.append(label)
