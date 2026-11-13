extends SceneTree
## Native-window transition-only captures. No game scene or global lighting changes.

const Presenter = preload("res://app/stasis_wiring.gd")
const Probe = preload("res://tools/stasis_wiring_material_probe.gd")
const SHOTS := [
	{"id":"aligned-transition-white", "eye":[-3.15,1.75,-1.35], "target":[-4.9,1.62,-3.35], "fov":60.0, "red":false},
	{"id":"aligned-transition-red", "eye":[-3.15,1.75,-1.35], "target":[-4.9,1.62,-3.35], "fov":60.0, "red":true},
	{"id":"aligned-power-data-clamps", "eye":[-5.03,2.35,-2.45], "target":[-5.10,2.80,-3.13], "fov":42.0, "red":false},
	{"id":"aligned-source-glands", "eye":[-5.50,2.53,-2.80], "target":[-5.87,2.75,-3.10], "fov":34.0, "red":false},
	{"id":"aligned-pipe-entry", "eye":[-3.65,2.33,-3.03], "target":[-4.50,2.68,-3.62], "fov":43.0, "red":false},
	{"id":"aligned-floor-entry-standing", "eye":[-3.2,1.65,-2.1], "target":[-4.5,0.16,-3.9], "fov":44.0, "red":false},
]
var output_dir: String

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size()!=1:
		quit(2)
		return
	output_dir = args[0]
	_run.call_deferred()

func _vec(values: Array) -> Vector3:
	return Vector3(float(values[0]), float(values[1]), float(values[2]))

func _readback(image: Image) -> Dictionary:
	var count := 0
	var total := 0.0
	var squared := 0.0
	var low := 1.0
	var high := 0.0
	var clipped := 0
	for y: int in range(0, image.get_height(), 8):
		for x: int in range(0, image.get_width(), 8):
			var pixel := image.get_pixel(x,y)
			var value := (pixel.r+pixel.g+pixel.b)/3.0
			total += value
			squared += value*value
			low = minf(low,value)
			high = maxf(high,value)
			if maxf(pixel.r,maxf(pixel.g,pixel.b))>=0.995: clipped += 1
			count += 1
	var mean := total/count
	return {"mean":mean,"range":high-low,"variance":squared/count-mean*mean,"clipped_pixel_fraction":float(clipped)/count}

func _labels(anchors: Array[Dictionary]) -> CanvasLayer:
	var overlay := CanvasLayer.new()
	root.add_child(overlay)
	var row := 0
	for anchor: Dictionary in anchors:
		if anchor.visible_pixel_anchor.is_empty(): continue
		var part: String = anchor.requested_node.get_file()
		if not (part.contains("compression") or part.begins_with("Cast")): continue
		var point := Vector2(anchor.visible_pixel_anchor.pixel_xy[0], anchor.visible_pixel_anchor.pixel_xy[1])
		var label := Label.new()
		label.text = part
		label.position = Vector2(14, 14+row*25)
		label.add_theme_font_size_override("font_size", 14)
		label.add_theme_color_override("font_shadow_color", Color.BLACK)
		label.add_theme_constant_override("shadow_offset_x", 1)
		label.add_theme_constant_override("shadow_offset_y", 1)
		overlay.add_child(label)
		var marker := Line2D.new()
		marker.width = 1.5
		marker.default_color = Color(0.85,0.68,0.32,0.8)
		var legend_end := label.position+Vector2(minf(470.0, float(part.length())*7.5), 11)
		marker.points = PackedVector2Array([legend_end,point,point+Vector2(-4,0),point+Vector2(4,0),point,point+Vector2(0,-4),point+Vector2(0,4)])
		overlay.add_child(marker)
		row += 1
	return overlay

func _render() -> void:
	for frame: int in range(12): await process_frame
	# Subscribe before the forced draw executes, including when an occluded
	# native window is not producing automatic frame_post_draw signals.
	RenderingServer.call_deferred("force_draw", false)
	await RenderingServer.frame_post_draw
	await process_frame
	RenderingServer.call_deferred("force_draw", false)
	await RenderingServer.frame_post_draw

func _run() -> void:
	if DisplayServer.get_name()=="headless":
		printerr("Native rendering window required")
		quit(2)
		return
	if DirAccess.make_dir_recursive_absolute(output_dir)!=OK:
		quit(2)
		return
	root.size = Vector2i(1280,960)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = root.size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	var snapshot := _source_hashes()
	var captures: Array[Dictionary] = []
	var native_materials: Array[Dictionary] = []
	var texture_hashes: Dictionary = {}
	for shot: Dictionary in SHOTS:
		print("CAPTURE_START ",shot.id)
		var world := Node3D.new()
		root.add_child(world)
		var assembly := Presenter.build(&"supported-transition")
		world.add_child(assembly)
		var environment := WorldEnvironment.new()
		environment.environment = Environment.new()
		var env := environment.environment
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.025,0.028,0.032)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.55,0.60,0.68)
		env.ambient_light_energy = 0.1
		# Finite neutral reflection source, retained identically for both lamps.
		var sky_material := ProceduralSkyMaterial.new()
		sky_material.sky_top_color = Color(0.17,0.20,0.24)
		sky_material.sky_horizon_color = Color(0.32,0.34,0.36)
		sky_material.ground_bottom_color = Color(0.08,0.09,0.10)
		sky_material.ground_horizon_color = sky_material.sky_horizon_color
		sky_material.sky_energy_multiplier = 0.35
		sky_material.ground_energy_multiplier = 0.35
		env.sky = Sky.new()
		env.sky.sky_material = sky_material
		env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
		world.add_child(environment)
		var positions: Array[Vector3] = [Vector3(-4.8,2.35,-1.7),Vector3(-5.3,1.85,-2.7),Vector3(-3.9,2.55,-3.3)]
		for index: int in range(3):
			var light := OmniLight3D.new()
			light.position = positions[index]
			light.omni_range = 5.0
			light.omni_attenuation = 1.6
			light.light_energy = [1.4,0.8,0.4][index]
			light.light_color = Color(1.0,0.035,0.012) if shot.red else Color(1.0,0.95,0.86)
			light.shadow_enabled = true
			world.add_child(light)
		var camera := Camera3D.new()
		camera.near = 0.012
		camera.far = 20.0
		camera.fov = shot.fov
		world.add_child(camera)
		camera.position = _vec(shot.eye)
		camera.look_at(_vec(shot.target))
		camera.current = true
		Probe.add_colliders(assembly)
		await physics_frame
		await physics_frame
		await _render()
		var image := root.get_texture().get_image()
		if image==null or image.get_width()!=1280 or image.get_height()!=960:
			quit(1)
			return
		var statistics := _readback(image)
		if statistics.range<0.015 or statistics.variance<0.00001:
			printerr("Uniform readback: ",shot.id)
			quit(1)
			return
		var anchors := Probe.anchors(assembly,camera,image)
		var materials := Probe.material_map(assembly)
		var current_textures := Probe.texture_hashes(assembly)
		if texture_hashes.is_empty(): texture_hashes = current_textures
		assert(texture_hashes == current_textures,"Material texture changed between shots")
		if shot.id=="aligned-source-glands": native_materials = materials
		var overlay: CanvasLayer
		if shot.id=="aligned-source-glands":
			overlay = _labels(anchors)
			await _render()
			image = root.get_texture().get_image()
		var output := output_dir.path_join(String(shot.id)+".png")
		if image.save_png(output)!=OK:
			quit(1)
			return
		var row := shot.duplicate(true)
		row["path"] = output
		row["sha256"] = FileAccess.get_sha256(output)
		row["size"] = [image.get_width(),image.get_height()]
		row["readback_statistics_before_labels"] = statistics
		row["material_map"] = materials
		row["pixel_first_hit_anchors_before_labels"] = anchors
		row["lights"] = positions.map(func(p: Vector3) -> Array: return [p.x,p.y,p.z])
		row["light_energies"] = [1.4,0.8,0.4]
		row["near_m"] = camera.near
		captures.append(row)
		print("CAPTURE_SAVED ",shot.id)
		if overlay!=null: overlay.free()
		world.free()
		await process_frame
	var sources := _source_hashes()
	for path: String in texture_hashes:
		assert(FileAccess.get_sha256(path)==texture_hashes[path],"Material texture changed during capture")
		sources[path] = texture_hashes[path]
	if _source_hashes()!=snapshot:
		printerr("Sources changed during capture")
		quit(1)
		return
	var manifest := {"issue":110,"process_id":OS.get_process_id(),"display":DisplayServer.get_name(),"renderer":RenderingServer.get_video_adapter_name(),
		"render_exit":0,"sources_sha256":sources,"captures":captures,
		"lighting":"Isolated neutral reflection sky and three fixed lamps; white/red share camera and energies; game settings unchanged.",
		"labels":"Actual visible first-hit node names only. Numeric anchor RGB sampled before overlay."}
	FileAccess.open(output_dir.path_join("capture-manifest.json"),FileAccess.WRITE).store_string(JSON.stringify(manifest,"\t")+"\n")
	FileAccess.open(output_dir.path_join("native-material-map.json"),FileAccess.WRITE).store_string(JSON.stringify(native_materials,"\t")+"\n")
	print("SUPPORTED_TRANSITION_CAPTURE_PASS ",captures.size())
	quit(0)

func _source_hashes() -> Dictionary:
	var result: Dictionary = {}
	for path: String in ["res://tools/capture_supported_transition.gd","res://tools/stasis_wiring_material_probe.gd",
		"res://app/stasis_wiring.gd","res://assets/props/stasis-wiring/supported-transition-aligned.json",
		"res://assets/props/stasis-wiring/supported-transition-aligned.glb","res://assets/props/stasis-wiring/stasis-wiring-enclosure.glb",
		"res://assets/props/stasis-wiring/sockets.json","res://assets/props/bay-ceiling/intact.glb",
		"res://app/bay_ceiling.gd","res://app/bay_ceiling_material.gd","res://app/surfaces.gd","res://app/shaders/weathered_steel.gdshader"]:
		assert(FileAccess.file_exists(path),"Missing capture source: "+path)
		result[path] = FileAccess.get_sha256(path)
	return result
