extends SceneTree
## B3a wake-capture smoke: runs the main scene windowed, lets the sim's
## authored wake timeline play through its presentation driver, and
## captures the four named beats — eyes-closed, first-blink,
## second-blink, eyes-held — under tmp/b3a-wake/<unique>/ as PNGs,
## machine-checks each via Image (decodable, size, mean RGB, luminance,
## dark coverage), asserts the beats differ measurably (each peek is
## brighter than the last: the opening's authored arc), prints stats,
## self-terminates: exit 0 on success, 1 on any failure.
## Run: godot --path . -s app/capture_wake.gd

const BEAT_TIMEOUT_SECS: float = 20.0
const BEAT_MARGIN: float = 0.003
const CLOSED_DARK_LEVEL: int = 8
const CLOSED_DARK_FRACTION_MIN: float = 0.98
const NONBLACK_LEVEL: int = 8
const NONBLACK_FRACTION_MIN: float = 0.02
const DOMINANCE_MARGIN: float = 0.001

## One beat's capture target: a logical tick and a file name. Ticks pin
## the authored table (beat starts 0/75/117/144/198/222, complete 282):
## the closed hold well inside its 75-tick rest, the last tick of each
## opening (116 and 197, the widest each peek reaches), and the neutral
## hold past completion.
const BEATS: Array = [
	{"name": "eyes-closed", "tick": 10},
	{"name": "first-blink", "tick": 116},
	{"name": "second-blink", "tick": 197},
	{"name": "eyes-held", "tick": 292},
]

var _capture_dir: String = ""
var _failure: String = ""

func _initialize() -> void:
	var packed: PackedScene = load("res://main.tscn")
	root.add_child(packed.instantiate())
	_run_smoke()

func _run_smoke() -> void:
	await process_frame
	var main := _find_node(root, "Main") as Node3D
	if main == null:
		_fail("the Main node is missing from the scene")
		return
	var game: Game = main.game
	if game == null:
		_fail("the Main node holds no Game (its _ready did not run)")
		return
	var waited := 0.0
	while not game.wake_state.is_started() and waited < BEAT_TIMEOUT_SECS:
		await process_frame
		waited += _frame_secs()
	if not game.wake_state.is_started():
		_fail("the wake timeline never started")
		return
	var stats: Array = []
	for beat: Dictionary in BEATS:
		var path := await _capture_beat(game, beat["name"], beat["tick"])
		if _failure != "":
			return
		var beat_stats := _analyze(path)
		if _failure != "":
			return
		print(_stats_line(beat["name"], path, beat_stats))
		stats.append(beat_stats)
	_check_beats(stats)
	if _failure != "":
		return
	print("WAKE OK")
	quit(0)

func _capture_beat(game: Game, beat_name: String, tick: int) -> String:
	var waited := 0.0
	while game.wake_state.current_tick() < tick and waited < BEAT_TIMEOUT_SECS:
		await process_frame
		waited += _frame_secs()
	if game.wake_state.current_tick() < tick:
		_fail("beat %s never reached tick %d" % [beat_name, tick])
		return ""
	await RenderingServer.frame_post_draw
	var image: Image = root.get_texture().get_image()
	if image == null:
		_fail("the viewport produced no image for %s" % beat_name)
		return ""
	if _capture_dir == "":
		var output_dir := "res://tmp/b3a-wake/%d-%d" % [
			Time.get_unix_time_from_system(), OS.get_process_id()
		]
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_dir))
		_capture_dir = output_dir
	var path := _capture_dir + "/" + beat_name + ".png"
	if image.save_png(path) != OK:
		_fail("save_png failed for %s" % path)
		return ""
	return ProjectSettings.globalize_path(path)

## Reloads one saved capture and computes mean RGB, luminance, the
## near-black (lid-covered) fraction, and the nonblack (lit room) fraction.
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
	var dark := 0
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
		if r <= CLOSED_DARK_LEVEL and g <= CLOSED_DARK_LEVEL and b <= CLOSED_DARK_LEVEL:
			dark += 1
		if r > NONBLACK_LEVEL or g > NONBLACK_LEVEL or b > NONBLACK_LEVEL:
			nonblack += 1
		pixels += 1
		offset += bytes_per_pixel
	if pixels == 0:
		_fail("the capture holds no pixels: %s" % path)
		return {}
	var mean := Vector3(red / pixels / 255.0, green / pixels / 255.0, blue / pixels / 255.0)
	return {
		"mean": mean,
		"luminance": (mean.x + mean.y + mean.z) / 3.0,
		"dark": float(dark) / float(pixels),
		"nonblack": float(nonblack) / float(pixels),
		"size": Vector2i(probe.get_width(), probe.get_height()),
	}

func _stats_line(label: String, path: String, stats: Dictionary) -> String:
	var mean: Vector3 = stats["mean"]
	var size: Vector2i = stats["size"]
	return "WAKE %s path=%s size=%dx%d mean_rgb=(%.4f, %.4f, %.4f) luminance=%.4f dark=%.4f nonblack=%.4f" % [
		label,
		path,
		size.x,
		size.y,
		mean.x,
		mean.y,
		mean.z,
		stats["luminance"],
		stats["dark"],
		stats["nonblack"],
	]

## The beats differ measurably: the closed hold is effectively all lid,
## the held frame is the lit room with red dominance, and each authored
## peek is brighter than the one before it.
func _check_beats(stats: Array) -> void:
	var first: Dictionary = stats[0]
	var second: Dictionary = stats[1]
	var third: Dictionary = stats[2]
	var held: Dictionary = stats[3]
	if float(first["dark"]) < CLOSED_DARK_FRACTION_MIN:
		_fail(
			"eyes-closed is not lid-covered: dark fraction %.4f"
			% float(first["dark"])
		)
		return
	if float(held["nonblack"]) < NONBLACK_FRACTION_MIN:
		_fail(
			"eyes-held is effectively black: nonblack fraction %.4f"
			% float(held["nonblack"])
		)
		return
	var held_mean: Vector3 = held["mean"]
	if not (held_mean.x > held_mean.y + DOMINANCE_MARGIN and held_mean.x > held_mean.z + DOMINANCE_MARGIN):
		_fail(
			"eyes-held lacks red channel dominance: mean rgb (%.4f, %.4f, %.4f)"
			% [held_mean.x, held_mean.y, held_mean.z]
		)
		return
	var luminances: Array = [first["luminance"], second["luminance"], third["luminance"], held["luminance"]]
	for index: int in range(luminances.size() - 1):
		if float(luminances[index + 1]) < float(luminances[index]) + BEAT_MARGIN:
			_fail(
				"beat %d (%.4f) is not measurably brighter than beat %d (%.4f)"
				% [index + 1, float(luminances[index + 1]), index, float(luminances[index])]
			)
			return

func _frame_secs() -> float:
	return 1.0 / 60.0

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
	print("WAKE FAIL :: ", message)
	quit(1)
