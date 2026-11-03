extends SceneTree
## Windowed input playthrough; authored bay-relative shots follow ShipLayout.
## Run: godot --path . --resolution 480x270 -s app/capture_gameplay.gd
const Route := preload("res://harness/route.gd")
var out_dir: String
var beats: Dictionary = {}

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	out_dir = "res://tmp/b3b-gameplay/%d-%d" % [int(Time.get_unix_time_from_system()), OS.get_process_id()]
	DirAccess.make_dir_recursive_absolute(out_dir)
	var game := Game.new(0)
	var scene := Node3D.new()
	var ship := ShipScene.build_into(scene, game)
	var player := Player.build(game, ship.hatch)
	player.scripted = true
	player.rod = ship.rod
	player.adapter = InputPlane.ScriptedAdapter.new()
	scene.add_child(player)
	root.add_child(scene)
	game.wake_state.mark_ready()
	var route := Route.new(player, 1800)
	route.stepper.door_views = ship.door_views
	route.stepper.fixtures.assign([ship.lighting, ship.hallway, ship.power_room])
	var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/gameplay-full.json"))
	var observer := Camera3D.new()
	scene.add_child(observer)
	var index := 0
	var shots := [{"name": "standing", "tick": 290}, {"name": "mid-room", "tick": 612}, {"name": "at-door", "tick": 1150}, {"name": "door-opened", "tick": 1215}]
	for beat: Dictionary in shots:
		while route.tick <= int(beat.tick):
			var offered: Array = []
			while index < scenario.actions.size() and int(scenario.actions[index].tick) == route.tick:
				offered.append(scenario.actions[index])
				index += 1
			route.step(offered)
		if beat.name in ["at-door", "door-opened"]:
			observer.position = game.layout.bay_to_world() * Vector3(4.2, 1.6, 0)
			observer.look_at(game.layout.bay_to_world() * Vector3(6, 1.2, 0))
			observer.make_current()
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		var path := out_dir + "/" + String(beat.name) + ".png"
		assert(image.save_png(path) == OK, "capture saved")
		beats[beat.name] = path
	assert(game.door_open and player.motion.rod_carried, "input route picked up rod and pried bay")
	_finish(_verify_beats())

## Machine-check every beat PNG; "" when all checks pass. Each must be
## decodable, exactly the window size, non-black, and red-dominant under
## the emergency lighting; the open-door frame must differ from the
## at-door frame (the door slab moved out of the doorway, trading the
## wall for the dark hallway).
func _verify_beats() -> String:
	var required: Array[String] = ["standing", "mid-room", "at-door", "door-opened"]
	var expected_size := Vector2i(root.get_size())
	var images: Dictionary = {}
	for beat: String in required:
		if not beats.has(beat):
			return "beat %s was never captured" % beat
		var image := Image.new()
		if image.load_png_from_buffer(FileAccess.get_file_as_bytes(beats[beat])) != OK:
			return "beat %s PNG is not decodable" % beat
		if image.get_size() != expected_size:
			return "beat %s size %s, expected %s" % [beat, str(image.get_size()), str(expected_size)]
		var mean := _mean_rgb(image)
		var luminance := (mean.x + mean.y + mean.z) / 3.0
		if luminance <= 3.0:
			return "beat %s is black: mean rgb %s" % [beat, str(mean)]
		if not (mean.x > mean.y + 3.0 and mean.x > mean.z + 3.0):
			return "beat %s is not red-dominant: mean rgb %s" % [beat, str(mean)]
		print("STAT %s mean_r=%.1f mean_g=%.1f mean_b=%.1f lum=%.1f" % [beat, mean.x, mean.y, mean.z, luminance])
		images[beat] = image
	var diff := _mean_abs_diff(images["at-door"], images["door-opened"])
	if diff <= 1.5:
		return "door-opened frame is identical to at-door: mean abs diff %.2f" % diff
	print("STAT opened-vs-atdoor mean_abs_diff=%.2f" % diff)
	return ""

## Mean red/green/blue of the whole image, 0..255.
func _mean_rgb(image: Image) -> Vector3:
	var size := image.get_size()
	var total := Vector3.ZERO
	for y: int in range(size.y):
		for x: int in range(size.x):
			var c := image.get_pixel(x, y)
			total += Vector3(c.r8, c.g8, c.b8)
	return total / float(size.x * size.y)

## Mean absolute per-channel byte difference of two same-size images.
func _mean_abs_diff(a: Image, b: Image) -> float:
	var left := a.get_data()
	var right := b.get_data()
	var total := 0.0
	var count := left.size()
	for index: int in range(count):
		total += absf(left[index] - right[index])
	return total / float(count)

func _finish(reason: String) -> void:
	if not reason.is_empty():
		print("RESULT FAIL %s" % reason)
		quit(1)
		return
	print("RESULT OK")
	quit(0)
