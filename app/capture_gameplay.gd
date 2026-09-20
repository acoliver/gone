extends SceneTree
## Windowed self-terminating gameplay capture lane, mirroring gone_app's
## bootstrap gameplay harness: a scripted input adapter drives the real
## player rig through the whole beat — wake, get-up out of the pod,
## steadying walk across the room, arrival at the door, the interact
## that opens it into the hallway — while PNGs are captured at four
## beats and machine-checked (decodable, exact size, non-black,
## red-dominant, the open-door frame differs from at-door). Prints
## stats and exits 0 only when every check passes.
## Run: godot --path . --resolution 480x270 -s app/capture_gameplay.gd

const WAKE_BATCH: int = 16
const SETTLE_FRAMES: int = 20
const WARMUP_FRAMES: int = 4
const MAX_FRAMES: int = 4000
const STOP_DISTANCE: float = 1.9

var game: Game
var player: Player
var wake_present: WakePresent
var adapter: InputPlane.ScriptedAdapter
var out_dir: String
var stage: int = 0
var frame: int = 0
var settle: int = 0
var start_distance: float = 0.0
var midroom_captured: bool = false
var beats: Dictionary = {}

func _initialize() -> void:
	out_dir = "tmp/b3b-gameplay/%d" % int(Time.get_unix_time_from_system())
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	game = Game.new()
	var scene := Node3D.new()
	scene.name = "CaptureRoot"
	var hatch := Hatch.build()
	scene.add_child(RoomGeometry.build(true))
	scene.add_child(StasisPods.build(game.registry))
	scene.add_child(hatch)
	scene.add_child(Lighting.build(game))
	scene.add_child(Hazards.build())
	var rod := Rod.build()
	scene.add_child(rod)
	var hallway := Hallway.build(game)
	scene.add_child(hallway)
	player = Player.build(game, hatch)
	player.scripted = true
	player.rod = rod
	adapter = InputPlane.ScriptedAdapter.new()
	player.adapter = adapter
	scene.add_child(player)
	root.add_child(scene)
	_wire_after_first_frame()

## Node _ready is deferred until the first frame processes, so the pass
## and driver wire up only after the rig exists.
func _wire_after_first_frame() -> void:
	await process_frame
	var wake_pass := WakePass.build()
	root.get_node("CaptureRoot").add_child(wake_pass)
	wake_present = WakePresent.build(game, player.camera, wake_pass, player)
	root.get_node("CaptureRoot").add_child(wake_present)
	process_frame.connect(_drive)

func _drive() -> void:
	frame += 1
	if frame > MAX_FRAMES:
		_finish("frame budget exhausted at stage %d" % stage)
		return
	if not player.motion.failure().is_empty():
		_finish("motion failure: " + player.motion.failure())
		return
	match stage:
		0:
			_warm_then_wake()
		1:
			_wait_for_wake_complete()
		2:
			_press_activate()
		3:
			_wait_standing()
		4:
			_level_eyes()
		5:
			_captured_standing()
		6:
			_walk_room()
		7:
			_arrive_and_open()
		8:
			_verify_and_exit()

func _warm_then_wake() -> void:
	if frame <= WARMUP_FRAMES or not wake_present.is_begun():
		return
	for _tick: int in range(WAKE_BATCH):
		game.wake_state.tick()
	stage = 1

func _wait_for_wake_complete() -> void:
	if not game.wake_state.is_complete():
		for _tick: int in range(WAKE_BATCH):
			game.wake_state.tick()
		return
	stage = 2

func _press_activate() -> void:
	adapter.press(InputPlane.Buttons.ACTIVATE)
	stage = 3

func _wait_standing() -> void:
	if player.motion.state() == PlayerMotion.BodyState.WALK:
		stage = 4

func _level_eyes() -> void:
	var foot := player.motion.capsule().foot
	var hatch := game.registry.hatch().center
	var to_hatch := Vector2(hatch.x - foot.x, hatch.y - foot.z)
	var target_yaw := atan2(to_hatch.x, to_hatch.y)
	var angles := player.look_angles()
	adapter.look(InputPlane.wrap_angle(target_yaw - angles.x), -angles.y)
	settle = SETTLE_FRAMES
	stage = 5

func _captured_standing() -> void:
	if settle > 0:
		settle -= 1
		return
	start_distance = _distance_to_hatch()
	_capture("standing")
	adapter.hold(1.0, 0.0)
	stage = 6

func _walk_room() -> void:
	var distance := _distance_to_hatch()
	if not midroom_captured and distance <= start_distance * 0.55:
		_capture("mid-room")
		midroom_captured = true
	if distance <= STOP_DISTANCE or player.motion.failure() != "":
		adapter.release()
		settle = SETTLE_FRAMES
		stage = 7

func _arrive_and_open() -> void:
	if settle > 0:
		settle -= 1
		return
	if player.motion.door_state == PlayerMotion.DoorState.CLOSED:
		_capture("at-door")
		adapter.press(InputPlane.Buttons.INTERACT)
		# The door's opening animation runs its whole authored duration
		# (retract, then slide) before the open frame is worth capturing.
		settle = PlayerMotion.DOOR_RETRACT_TICKS + PlayerMotion.DOOR_SLIDE_TICKS + 12
		return
	_capture("door-opened")
	stage = 8

func _verify_and_exit() -> void:
	var failure := _verify_beats()
	if failure.is_empty():
		_finish("")
	else:
		_finish(failure)

func _distance_to_hatch() -> float:
	var foot := player.motion.capsule().foot
	var hatch := game.registry.hatch().center
	return Vector2(foot.x - hatch.x, foot.z - hatch.y).length()

func _capture(beat: String) -> void:
	var image := root.get_texture().get_image()
	var path := out_dir + "/" + beat + ".png"
	image.save_png(path)
	beats[beat] = path
	print("BEAT %s path=%s size=%s" % [beat, path, str(image.get_size())])

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
	process_frame.disconnect(_drive)
	if not reason.is_empty():
		print("RESULT FAIL %s" % reason)
		quit(1)
		return
	print("RESULT OK")
	quit(0)
