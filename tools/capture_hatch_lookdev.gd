extends SceneTree
## Fixed neutral calibration rig. Optional atlas override is for zero/unit response measurements.

const SETTINGS := {
	"size": [1199, 1312], "msaa": 2, "ambient": 0.13,
	"background": [0.025, 0.025, 0.025], "key_position": [1.1, 2.9, -1.5],
	"key_energy": 2.6, "key_range": 7.0, "camera_position": [0.0, 1.28, -3.65],
	"camera_target": [0.0, 1.28, 0.0], "fov": 46.0,
}
var output_dir: String
var atlas_override := ""
var camera: Camera3D
var scene: Node3D

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() not in [1, 3] or (args.size() == 3 and args[1] != "--paint-atlas"):
		printerr("usage: godot --path . -s tools/capture_hatch_lookdev.gd -- <output-dir> [--paint-atlas <png>]")
		quit(2)
		return
	output_dir = args[0]
	if args.size() == 3: atlas_override = args[2]
	_run.call_deferred()

func _run() -> void:
	if DisplayServer.get_name() == "headless":
		printerr("Native lookdev rendering requires a window")
		quit(2)
		return
	if DirAccess.make_dir_recursive_absolute(output_dir) != OK:
		printerr("Cannot create capture directory: " + output_dir)
		quit(2)
		return
	var capture_size := Vector2i(SETTINGS.size[0], SETTINGS.size[1])
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	root.content_scale_size = capture_size
	root.size = capture_size
	DisplayServer.window_set_size(capture_size)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d = Viewport.MSAA_2X
	scene = Node3D.new()
	root.add_child(scene)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color(0.025, 0.025, 0.025)
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color.WHITE
	environment.environment.ambient_light_energy = SETTINGS.ambient
	scene.add_child(environment)
	var source := ShipLayout.authored().layout.door(&"D14-C-001-H-FORE")
	var spec := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
	var view := DoorView.build(spec)
	scene.add_child(view)
	if atlas_override != "":
		var image := Image.load_from_file(atlas_override)
		if image == null or image.get_size() != Vector2i(Surfaces.HATCH_PAINTED.get_size()):
			printerr("Response atlas must match the production paint dimensions")
			quit(2)
			return
		image.generate_mipmaps()
		Surfaces.material(&"modelled_hatch").set_shader_parameter(&"hatch_painted", ImageTexture.create_from_image(image))
	var key := OmniLight3D.new()
	key.position = HatchAsset.vector(SETTINGS.key_position)
	key.omni_range = SETTINGS.key_range
	key.light_energy = SETTINGS.key_energy
	key.light_color = Color(1.0, 0.86, 0.70)
	scene.add_child(key)
	camera = Camera3D.new()
	camera.position = HatchAsset.vector(SETTINGS.camera_position)
	camera.fov = SETTINGS.fov
	scene.add_child(camera)
	camera.look_at(HatchAsset.vector(SETTINGS.camera_target))
	camera.current = true
	if not await _shot("lookdev-warm.png"): return
	key.light_color = Color.WHITE
	if not await _shot("lookdev-neutral.png"): return
	var record := FileAccess.open(output_dir.path_join("lookdev-settings.json"), FileAccess.WRITE)
	if record == null:
		printerr("Cannot write capture settings")
		quit(2)
		return
	record.store_string(JSON.stringify({"settings": SETTINGS, "atlas_override": atlas_override}, "\t") + "\n")
	record.close()
	camera.position = Vector3(-1.6, 1.4, -3.5)
	camera.look_at(Vector3(0, 1.25, 0.05))
	if not await _shot("lookdev-three-quarter.png"): return
	if atlas_override != "":
		# Release the transient GPU texture while the renderer is still running.
		Surfaces.material(&"modelled_hatch").set_shader_parameter(&"hatch_painted", Surfaces.HATCH_PAINTED)
		await process_frame
		await RenderingServer.frame_post_draw
	quit(0)

func _shot(file: String) -> bool:
	for index: int in range(12): await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	if image.get_size() != Vector2i(1199, 1312):
		printerr("Lookdev viewport differs from the fixed calibration size")
		quit(2)
		return false
	if image.save_png(output_dir.path_join(file)) != OK:
		printerr("Cannot save capture: " + file)
		quit(2)
		return false
	print("LOOKDEV ", output_dir.path_join(file))
	return true
