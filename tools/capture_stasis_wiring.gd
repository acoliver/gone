extends SceneTree
## Rendered-window proof rig. Does not alter normal game lighting or startup.

const Presenter = preload("res://app/stasis_wiring.gd")
const SHOTS := [
	{"id":"transition-neutral-close", "kind":"supported-transition", "eye":[-4.95,2.34,-2.24], "target":[-5.23,2.77,-3.48], "fov":52.0, "red":false},
	{"id":"transition-red-close", "kind":"supported-transition", "eye":[-4.95,2.34,-2.24], "target":[-5.23,2.77,-3.48], "fov":52.0, "red":true},
	{"id":"transition-standing", "kind":"supported-transition", "eye":[-3.5,1.65,-1.36], "target":[-5.05,1.57,-3.62], "fov":65.0, "red":false},
	{"id":"fault-close", "kind":"fault-frame-pair", "eye":[-0.6,2.20,0.32], "target":[-0.85,2.86,-.58], "fov":55.0, "red":false},
	{"id":"fault-frame-pair", "kind":"fault-frame-pair", "eye":[1.45,1.62,1.7], "target":[-0.6,1.56,-1.06], "fov":64.0, "red":false},
	{"id":"isolated-fragment", "kind":"fault-frame-pair", "eye":[0.5,0.48,-0.8], "target":[-0.6,0.0275,-1.4], "fov":49.0, "red":false, "isolate":true},
]
var output_dir: String

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		printerr("usage: godot --path . -s tools/capture_stasis_wiring.gd -- <output-dir>")
		quit(2)
		return
	output_dir = args[0]
	_run.call_deferred()

func _vec(values: Array) -> Vector3:
	return Vector3(float(values[0]),float(values[1]),float(values[2]))

func _readback_statistics(image: Image) -> Dictionary:
	var count := 0
	var total := 0.0
	var squared := 0.0
	var low := 1.0
	var high := 0.0
	for y: int in range(0,image.get_height(),8):
		for x: int in range(0,image.get_width(),8):
			var color := image.get_pixel(x,y)
			var value := (color.r+color.g+color.b)/3.0
			total += value
			squared += value*value
			low = minf(low,value)
			high = maxf(high,value)
			count += 1
	var mean := total/count
	return {"mean":mean,"range":high-low,"variance":squared/count-mean*mean}

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		printerr("Proof capture requires an actual rendering window")
		quit(2)
		return
	if DirAccess.make_dir_recursive_absolute(output_dir) != OK:
		quit(2)
		return
	root.size = Vector2i(1280, 960)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = root.size
	DisplayServer.window_set_size(root.size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	var source_snapshot := _source_hashes()
	var captures: Array[Dictionary] = []
	for shot: Dictionary in SHOTS:
		var world := Node3D.new()
		root.add_child(world)
		var assembly := Presenter.build(StringName(shot.kind))
		world.add_child(assembly)
		if shot.get("isolate",false): Presenter.isolate_fragment(assembly)
		var environment := WorldEnvironment.new()
		environment.environment = Environment.new()
		environment.environment.background_mode = Environment.BG_COLOR
		environment.environment.background_color = Color(0.025,0.028,0.032)
		environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		environment.environment.ambient_light_color = Color(0.55,0.60,0.68)
		environment.environment.ambient_light_energy = 0.10
		world.add_child(environment)
		var lights: Array[OmniLight3D] = []
		var center := Vector3(-5.0,1.65,-3.2) if shot.kind == "supported-transition" else Vector3(-0.6,1.65,-0.9)
		var positions: Array[Vector3] = [center+Vector3(0.2,0.7,1.5),center+Vector3(-1.5,0.2,0.5),center+Vector3(1.0,0.9,-0.3)]
		for index: int in range(3):
			var light := OmniLight3D.new()
			light.position = positions[index]
			light.omni_range = 5.0
			light.omni_attenuation = 1.6
			light.light_energy = [3.8,2.2,1.4][index]
			light.light_color = Color(1.0,0.035,0.012) if shot.red else Color(1.0,0.95,0.86)
			light.shadow_enabled = true
			world.add_child(light)
			lights.append(light)
		var camera := Camera3D.new()
		camera.near = 0.015
		camera.far = 20.0
		camera.fov = shot.fov
		world.add_child(camera)
		camera.position = _vec(shot.eye)
		camera.look_at(_vec(shot.target))
		camera.current = true
		for frame: int in range(12): await process_frame
		RenderingServer.force_draw(false)
		await RenderingServer.frame_post_draw
		await process_frame
		RenderingServer.force_draw(false)
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		if image == null or image.get_width() != 1280 or image.get_height() != 960:
			printerr("Invalid render readback for ",shot.id)
			quit(1)
			return
		var statistics := _readback_statistics(image)
		if statistics.range < 0.015 or statistics.variance < 0.00001:
			printerr("Uniform or black render readback for ",shot.id)
			quit(1)
			return
		var output := output_dir.path_join(String(shot.id)+".png")
		if image.save_png(output) != OK:
			quit(1)
			return
		var row := shot.duplicate(true)
		row["path"] = output
		row["sha256"] = FileAccess.get_sha256(output)
		row["size"] = [image.get_width(),image.get_height()]
		row["readback_statistics"] = statistics
		row["lights"] = positions.map(func(p: Vector3) -> Array: return [p.x,p.y,p.z])
		captures.append(row)
		world.free()
		await process_frame
	var sources := _source_hashes()
	if sources != source_snapshot:
		printerr("Proof source changed during capture; manifest not written")
		quit(1)
		return
	var manifest := {"issue":110,"renderer":RenderingServer.get_video_adapter_name(),"display":DisplayServer.get_name(),"render_exit":0,"captures":captures,"sources_sha256":sources,"materials":"Imported enclosure PBR; healthy jacket PBR roughness 0.7; production Surfaces weathered_steel for clamps/frame/pipes; production BayCeilingMaterial panels. No clay override.","lighting":"Isolated proof only: three fixed finite-range lights, neutral/red variants. Game globals unchanged."}
	FileAccess.open(output_dir.path_join("capture-manifest.json"),FileAccess.WRITE).store_string(JSON.stringify(manifest,"\t")+"\n")
	print("STASIS_WIRING_CAPTURE_PASS ", captures.size())
	quit(0)

func _source_hashes() -> Dictionary:
	var sources: Dictionary = {}
	for path: String in ["res://tools/capture_stasis_wiring.gd","res://app/stasis_wiring.gd","res://assets/props/stasis-wiring/proof-assemblies.json","res://assets/props/stasis-wiring/supported-transition.glb","res://assets/props/stasis-wiring/fault-frame-pair.glb","res://assets/props/stasis-wiring/stasis-wiring-enclosure.glb","res://assets/props/stasis-wiring/sockets.json","res://app/shaders/weathered_steel.gdshader","res://assets/props/bay-ceiling/intact.glb"]:
		assert(FileAccess.file_exists(path),"Required proof source is missing: "+path)
		sources[path] = FileAccess.get_sha256(path)
	return sources
