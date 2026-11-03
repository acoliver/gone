extends SceneTree
## Real-input ladder departure followed by positional playback and completion.

const Driver := preload("res://tests/connector_route_driver.gd")
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
	main.player.scripted = true
	main.player.adapter = InputPlane.ScriptedAdapter.new()
	game.wake_state.mark_ready()
	var route := Driver.new(main.player, 10000)
	route.stepper = main.step
	route.opening()
	route.enter_well(1)
	route.climb_to(13)
	route.dismount(13)
	if main.hallway.visible or main.player.motion.deck() != 13:
		_fail("real ladder departure must hide D14 and commit D13")
		return
	var connector := game.layout.connector(&"D13-C-001")
	route.walk_to(Vector3(connector.port_opening().origin.x, game.layout.floor_y(13), -0.5))
	var listener := AudioListener3D.new()
	main.add_child(listener)
	listener.make_current()
	var ids: Array[StringName] = [&"D13-C-001-H-FORE", &"D13-C-001-LIFT-DOOR"]
	for id: StringName in ids:
		var spec := game.layout.door(id)
		var approach := spec.frame().origin + Vector3(1.7, 0, 0) if spec.kind() == ShipLayout.DoorKind.HATCH else Vector3(33, game.layout.floor_y(13), 0)
		route.walk_to(approach)
		route.look_at(spec.frame().origin)
		listener.global_position = main.player.motion.eye(game)
		var before := game.doors.snapshot(id).attempt
		route.press()
		if game.doors.snapshot(id).attempt != before + 1 or game.doors.events().back().kind() != Doors.EventKind.REFUSED:
			_fail("remote input must refuse the selected door: %s" % id)
			return
		var voice: DoorAudio.Voice = audio.voices[audio.last_voice]
		var completion := {"finished": false}
		voice.player.finished.connect(func() -> void: completion.finished = true, CONNECT_ONE_SHOT)
		var initial := voice.player.get_playback_position()
		var advanced := false
		var deadline := Time.get_ticks_msec() + TIMEOUT_MSEC
		while not completion.finished and Time.get_ticks_msec() < deadline:
			await process_frame
			advanced = advanced or voice.player.get_playback_position() > initial + 0.01
		if not advanced or not completion.finished or voice.active or voice.player.playing:
			_fail("%s playback must advance and emit finished off D14 (advanced=%s finished=%s position=%s audio_process_mode=%s)" % [id, advanced, completion.finished, voice.player.get_playback_position(), audio.process_mode])
			return
		print("PASS remote door audio %s: playback advanced and finished signal arrived" % id)
	print("PASS remote door audio integration: real ladder departure, hatch and lift refusals play and finish off D14")
	quit(0)

func _fail(message: String) -> void:
	push_error("FAIL remote door audio integration: " + message)
	quit(1)
