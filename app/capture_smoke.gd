extends SceneTree
## B1 render smoke test: runs the main scene windowed for a few seconds,
## captures the viewport to a PNG under tmp/b1-smoke/<unique>/, then
## machine-checks the capture (written, decodable, viewport-sized, mean
## RGB computed) and exits 0 on success, 1 on any failure. The run quits
## by itself. Run: godot --path . -s app/capture_smoke.gd

const HOLD_SECS: float = 2.5

func _initialize() -> void:
	var packed: PackedScene = load("res://main.tscn")
	root.add_child(packed.instantiate())
	_run_smoke()

func _run_smoke() -> void:
	await create_timer(HOLD_SECS).timeout
	await RenderingServer.frame_post_draw
	var image: Image = root.get_texture().get_image()
	var output_dir := "res://tmp/b1-smoke/%d-%d" % [Time.get_unix_time_from_system(), OS.get_process_id()]
	var absolute_dir: String = ProjectSettings.globalize_path(output_dir)
	DirAccess.make_dir_recursive_absolute(absolute_dir)
	var path := output_dir + "/frame0.png"
	var save_error: int = image.save_png(path)
	if save_error != OK:
		_fail("save_png failed with error %d" % save_error)
		return
	var probe := Image.new()
	var load_error: int = probe.load(ProjectSettings.globalize_path(path))
	if load_error != OK:
		_fail("the saved PNG does not decode: error %d" % load_error)
		return
	var viewport_size: Vector2i = root.get_size()
	if Vector2i(image.get_width(), image.get_height()) != viewport_size:
		_fail(
			"capture size %dx%d does not match the viewport %s"
			% [image.get_width(), image.get_height(), str(viewport_size)]
		)
		return
	if Vector2i(probe.get_width(), probe.get_height()) != viewport_size:
		_fail("decoded PNG size does not match the viewport")
		return
	var mean := _mean_rgb(image)
	if is_nan(mean.x):
		return
	print("SMOKE path=%s" % ProjectSettings.globalize_path(path))
	print(
		"SMOKE size=%dx%d format=%d mean_rgb=(%.4f, %.4f, %.4f)" % [
			image.get_width(),
			image.get_height(),
			image.get_format(),
			mean.x,
			mean.y,
			mean.z,
		]
	)
	print("SMOKE OK")
	quit(0)

## Mean RGB over every pixel of an RGB8 or RGBA8 image; a NaN vector
## fails the run for any other format or an empty capture.
func _mean_rgb(image: Image) -> Vector3:
	var bytes_per_pixel := 0
	match image.get_format():
		Image.FORMAT_RGB8:
			bytes_per_pixel = 3
		Image.FORMAT_RGBA8:
			bytes_per_pixel = 4
		_:
			_fail("unexpected capture format %d" % image.get_format())
			return Vector3(NAN, NAN, NAN)
	var data := image.get_data()
	var red := 0.0
	var green := 0.0
	var blue := 0.0
	var pixels := 0
	var offset := 0
	while offset + bytes_per_pixel <= data.size():
		red += data[offset]
		green += data[offset + 1]
		blue += data[offset + 2]
		pixels += 1
		offset += bytes_per_pixel
	if pixels == 0:
		_fail("the capture holds no pixels")
		return Vector3(NAN, NAN, NAN)
	return Vector3(red / pixels / 255.0, green / pixels / 255.0, blue / pixels / 255.0)

func _fail(message: String) -> void:
	print("SMOKE FAIL :: ", message)
	quit(1)
