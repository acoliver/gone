extends SceneTree
## Windowed playback/completion contracts, separate from the headless suite.

const HATCH: StringName = &"D14-C-000-H-FORE"
const TIMEOUT_MSEC: int = 6000

func _initialize() -> void:
	if DisplayServer.get_name() == "headless":
		_fail("requires a rendered window")
		return
	call_deferred("_run")

func _run() -> void:
	var main: Node3D = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.set_physics_process(false)
	await process_frame
	await RenderingServer.frame_post_draw
	var game: Game = main.game
	var audio: DoorAudio = main.door_audio
	if audio != main.step.door_audio or audio.get_parent() != main:
		_fail("production root must wire the scene-level audio observer")
		return
	var coordinator := Interactions.new(game.layout)
	var context := Interactions.Context.new()
	context.game = game
	context.motion = main.player.motion
	context.walking = true
	var spec := game.layout.door(HATCH)
	var frame := spec.frame() * game.layout.face(spec.face_ids()[0]).surface_frame()
	context.foot = frame * Vector3(0, .305, 1.8)
	context.eye = context.foot + Vector3.UP * 1.295
	context.forward = -frame.basis.z
	var listener := AudioListener3D.new()
	main.add_child(listener)
	listener.global_position = context.eye
	listener.make_current()
	var plane := InputPlane.new()
	var families: Dictionary = {}
	var pitches: Dictionary = {}
	for _attempt: int in range(32):
		plane.offer_press(InputPlane.Buttons.INTERACT)
		if coordinator.process(plane, context) != spec.face_ids()[0]:
			_fail("selected press did not route to hatch")
			return
		var event := game.doors.events()[-1]
		var cue := audio.describe(event)
		audio.consume(game.doors.events())
		var voice: DoorAudio.Voice = audio.voices[audio.last_voice]
		if voice.player.stream != cue.stream or not voice.player.playing or not voice.player.global_position.is_equal_approx(cue.position):
			_fail("selected family must actually play at the selected door face")
			return
		families[cue.family] = true
		pitches[voice.player.pitch_scale] = true
		var count := audio.play_count
		audio.consume(game.doors.events())
		if count != audio.play_count:
			_fail("repeated batch duplicated playback")
			return
		for _tick: int in range(6):
			main.step.advance()
		if game.doors.snapshot(HATCH).state == Doors.State.OPENING:
			break
	if not families.has(&"grind") or not families.has(&"stall") or pitches.size() < 2:
		_fail("must exercise moving, stalled and scaled turns")
		return
	var release: DoorAudio.Voice = audio.voices[audio.last_voice]
	if not release.release or release.player.stream != DoorAudio.RELEASE or not release.player.playing:
		_fail("final wheel interpolation must start the release through GameStep")
		return
	var release_sequence := release.sequence
	for _attempt: int in range(20):
		game.advance_doors()
		var press := Doors.Context.new()
		press.face_id = game.layout.door(&"D14-S-041-SIDE-003-PORT").face_ids()[0]
		game.doors.press(&"D14-S-041-SIDE-003-PORT", press)
		audio.consume(game.doors.events())
	if not release.release or not release.player.playing or release.sequence != release_sequence:
		_fail("rapid refusals interrupted the release")
		return
	var count := audio.play_count
	for _tick: int in range(48):
		main.step.advance()
	if audio.play_count != count:
		_fail("OPENED must not duplicate the release")
		return
	var deadline := Time.get_ticks_msec() + TIMEOUT_MSEC
	while release.active and Time.get_ticks_msec() < deadline:
		await process_frame
	if release.active or release.release or release.player.playing:
		_fail("release must finish naturally and return its voice to the pool")
		return
	print("PASS door audio integration: production wiring, grind/stall scaling, positional playback, duplicate suppression, protected release and natural completion; listening acceptance remains separate")
	quit(0)

func _fail(message: String) -> void:
	push_error("FAIL door audio integration: " + message)
	quit(1)
