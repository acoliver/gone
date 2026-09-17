extends SceneTree
## B2 lit-capture smoke: runs the main scene windowed, waits for the
## emergency fade to settle, captures an inter-spark frame and a
## spark-active frame under tmp/b2-lit/<unique>/, machine-checks both
## via Image (nonblack pixel fraction, red channel dominance; the scene
## authors no UI, so whole-frame stats are outside any UI), prints
## stats, self-terminates: exit 0 on success, 1 on any failure.
## Run: godot --path . -s app/capture_lit.gd

const SETTLE_HOLD_SECS: float = 2.5
const SPARK_MID_SECS: float = 0.12
const NONBLACK_LEVEL: int = 8
const NONBLACK_FRACTION_MIN: float = 0.02
const DOMINANCE_MARGIN: float = 0.001

var _capture_dir: String = ""
var _failure: String = ""

func _initialize() -> void:
	var packed: PackedScene = load("res://main.tscn")
	root.add_child(packed.instantiate())
	_run_smoke()

func _run_smoke() -> void:
	await create_timer(SETTLE_HOLD_SECS).timeout
	var wake := _find_node(root, "WakePresent") as WakePresent
	if wake == null:
		_fail("the WakePresent node is missing from the scene")
		return
	var woken := 0.0
	while not wake.is_complete() and woken < 20.0:
		await create_timer(0.2).timeout
		woken += 0.2
	if not wake.is_complete():
		_fail("the wake opening did not complete")
		return
	var lighting := _find_node(root, "Lighting") as Lighting
	if lighting == null:
		_fail("the Lighting node is missing from the scene")
		return
	if not lighting.is_settled():
		_fail("the emergency fade did not settle")
		return
	var hazards := _find_node(root, "Hazards") as Hazards
	if hazards == null:
		_fail("the Hazards node is missing from the scene")
		return
	hazards.auto_bursts = false
	var waited := 0.0
	while hazards.is_spark_active() and waited < 3.0:
		await create_timer(0.2).timeout
		waited += 0.2
	var inter_path := await _capture("interspark.png")
	if _failure != "":
		return
	hazards.fire_burst()
	await create_timer(SPARK_MID_SECS).timeout
	var spark_path := await _capture("sparkactive.png")
	if _failure != "":
		return
	var inter_stats := _analyze(inter_path)
	var spark_stats := _analyze(spark_path)
	if _failure != "":
		return
	print(_stats_line("interspark", inter_path, inter_stats))
	print(_stats_line("sparkactive", spark_path, spark_stats))
	_check(inter_stats, "interspark")
	_check(spark_stats, "sparkactive")
	if _failure != "":
		return
	print("LIT OK")
	quit(0)

## Captures the root viewport after the next completed draw.
func _capture(file_name: String) -> String:
	await RenderingServer.frame_post_draw
	var image: Image = root.get_texture().get_image()
	if image == null:
		_fail("the viewport produced no image")
		return ""
	if _capture_dir == "":
		var output_dir := "res://tmp/b2-lit/%d-%d" % [
			Time.get_unix_time_from_system(), OS.get_process_id()
		]
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_dir))
		_capture_dir = output_dir
	var path := _capture_dir + "/" + file_name
	if image.save_png(path) != OK:
		_fail("save_png failed for %s" % path)
		return ""
	return ProjectSettings.globalize_path(path)

## Reloads one saved capture and computes mean RGB plus the fraction of
## pixels with any channel above the near-black level.
func _analyze(path: String) -> Dictionary:
	var probe := Image.new()
	if probe.load(path) != OK:
		_fail("the saved PNG does not decode: %s" % path)
		return {}
	var bytes_per_pixel := 0
	match probe.get_format():
		Image.FORMAT_RGB8:
			bytes_per_pixel = 3
		Image.FORMAT_RGBA8:
			bytes_per_pixel = 4
		_:
			_fail("unexpected capture format %d" % probe.get_format())
			return {}
	var data := probe.get_data()
	var red := 0.0
	var green := 0.0
	var blue := 0.0
	var nonblack := 0
	var pixels := 0
	var offset := 0
	while offset + bytes_per_pixel <= data.size():
		var r := data[offset]
		var g := data[offset + 1]
		var b := data[offset + 2]
		red += r
		green += g
		blue += b
		if r > NONBLACK_LEVEL or g > NONBLACK_LEVEL or b > NONBLACK_LEVEL:
			nonblack += 1
		pixels += 1
		offset += bytes_per_pixel
	if pixels == 0:
		_fail("the capture holds no pixels: %s" % path)
		return {}
	return {
		"mean": Vector3(red / pixels / 255.0, green / pixels / 255.0, blue / pixels / 255.0),
		"nonblack": float(nonblack) / float(pixels),
		"size": Vector2i(probe.get_width(), probe.get_height()),
	}

func _stats_line(label: String, path: String, stats: Dictionary) -> String:
	var mean: Vector3 = stats["mean"]
	var size: Vector2i = stats["size"]
	return "LIT %s path=%s size=%dx%d mean_rgb=(%.4f, %.4f, %.4f) nonblack=%.4f" % [
		label,
		path,
		size.x,
		size.y,
		mean.x,
		mean.y,
		mean.z,
		stats["nonblack"],
	]

func _check(stats: Dictionary, label: String) -> void:
	if _failure != "":
		return
	var mean: Vector3 = stats["mean"]
	if stats["nonblack"] < NONBLACK_FRACTION_MIN:
		_fail(
			"%s capture is effectively black: nonblack fraction %.4f"
			% [label, stats["nonblack"]]
		)
		return
	if not (mean.x > mean.y + DOMINANCE_MARGIN and mean.x > mean.z + DOMINANCE_MARGIN):
		_fail(
			"%s capture lacks red channel dominance: mean rgb (%.4f, %.4f, %.4f)"
			% [label, mean.x, mean.y, mean.z]
		)

func _find_node(from: Node, node_name: String) -> Node:
	if from.name == node_name:
		return from
	for child: Node in from.get_children():
		var found := _find_node(child, node_name)
		if found != null:
			return found
	return null

func _fail(message: String) -> void:
	if _failure != "":
		return
	_failure = message
	print("LIT FAIL :: ", message)
	quit(1)
