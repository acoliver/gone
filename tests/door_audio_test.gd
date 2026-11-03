extends SimTestCase

const CRANK: StringName = &"D14-C-000-H-FORE"

func test_imported_effects_preserve_pcm_rate_channels_and_no_loop() -> void:
	_check_imported_effects_preserve_pcm_rate_channels_and_no_loop()

func test_crank_events_map_to_grind_stall_release_and_silent_opened() -> void:
	_run_scene_check("_check_crank_events_map_to_grind_stall_release_and_silent_opened")

func test_refusal_mapping_and_selected_face_positions() -> void:
	_run_scene_check("_check_refusal_mapping_and_selected_face_positions")

func test_turn_size_scales_pitch_and_variants_repeat_without_resistance_changes() -> void:
	_run_scene_check("_check_turn_size_scales_pitch_and_variants_repeat_without_resistance_changes")

func test_pool_is_bounded_release_is_protected_and_batch_replays_are_silent() -> void:
	_run_scene_check("_check_pool_is_bounded_release_is_protected_and_batch_replays_are_silent")

func test_selection_rejection_has_no_sound_and_game_step_delivers_accepted_events() -> void:
	_run_scene_check("_check_selection_rejection_has_no_sound_and_game_step_delivers_accepted_events")

func _run_scene_check(method: String) -> void:
	var output: Array = []
	var exit_code := OS.execute(OS.get_executable_path(), [
		"--headless", "--path", ProjectSettings.globalize_path("res://"),
		"-s", "tests/door_audio_scene_checks.gd", "--", method,
	], output, true)
	var text := "".join(output)
	assert_int_equal(exit_code, 0, text)
	assert_false(text.contains("SCRIPT ERROR:"), text)
	assert_false(text.contains("ERROR:"), text)

func _audio(game: Game) -> DoorAudio:
	var audio := DoorAudio.build(game.layout)
	var tree := Engine.get_main_loop() as SceneTree
	tree.root.add_child(audio)
	return audio

func _press(game: Game, id: StringName, face_index: int = 0) -> void:
	var context := Doors.Context.new()
	context.face_id = game.layout.door(id).face_ids()[face_index]
	context.rod_carried = true
	game.doors.press(id, context)

func _check_imported_effects_preserve_pcm_rate_channels_and_no_loop() -> void:
	var streams: Array[AudioStreamWAV] = []
	streams.append_array(DoorAudio.GRINDS)
	streams.append_array(DoorAudio.STALLS)
	streams.append_array(DoorAudio.THUDS)
	streams.append_array([DoorAudio.RELEASE, DoorAudio.WHEEL_REFUSED])
	for stream: AudioStreamWAV in streams:
		assert_int_equal(stream.format, AudioStreamWAV.FORMAT_16_BITS, "effects remain uncompressed PCM16")
		assert_int_equal(stream.mix_rate, 48000, "import preserves sample rate")
		assert_false(stream.stereo, "effects remain mono for spatial playback")
		assert_int_equal(stream.loop_mode, AudioStreamWAV.LOOP_DISABLED, "effects never loop")

func _check_crank_events_map_to_grind_stall_release_and_silent_opened() -> void:
	var game := Game.new(0)
	var audio := _audio(game)
	var families: Dictionary = {}
	var released := 0
	for _attempt: int in range(10):
		_press(game, CRANK)
		for event: Doors.Event in game.doors.events():
			var cue := audio.describe(event)
			var family: StringName = &"grind" if event.kind() == Doors.EventKind.CRANK_MOVED else &"stall"
			assert_true(cue.family == family, "press selects its outcome family")
			assert_true(cue.stream.resource_path.contains("/%s-" % family), "family uses the generated stream")
			var bank := DoorAudio.GRINDS if family == &"grind" else DoorAudio.STALLS
			assert_true(cue.stream == bank[event.audio_variant() % bank.size()], "stable event index selects the exact variant")
			families[family] = true
		for _tick: int in range(6):
			game.advance_doors()
			for event: Doors.Event in game.doors.events():
				assert_true(event.kind() == Doors.EventKind.RELEASED, "only release follows wheel interpolation")
				assert_true(audio.describe(event).family == &"release", "final crank releases immediately, before completed swing")
				released += 1
	assert_true(families.has(&"grind") and families.has(&"stall"), "seed exercises movement and zero-progress presses")
	assert_int_equal(released, 1, "one release per hatch")
	for _tick: int in range(48):
		game.advance_doors()
	assert_int_equal(game.doors.events().size(), 1, "swing completion emits opened")
	assert_true(audio.describe(game.doors.events()[0]) == null, "opened does not play a second release")
	audio.free()

func _check_refusal_mapping_and_selected_face_positions() -> void:
	var game := Game.new(0)
	var audio := _audio(game)
	var ids: Array[StringName] = [game.layout.section(&"D14-S-040").opening_ids()[0], &"D14-S-041-SIDE-003-PORT", game.layout.lift(&"D14-C-000-LIFT").door_id(), &"D01-C-000-H-FORE"]
	for id: StringName in ids:
		var spec := game.layout.door(id)
		assert_int_equal(spec.policy(), ShipLayout.Policy.NEVER_OPENS, "fixture is locked")
		for face: int in range(spec.face_ids().size()):
			game.advance_doors()
			_press(game, id, face)
			var event := game.doors.events()[0]
			var cue := audio.describe(event)
			assert_true(cue.family == (&"wheel-refused" if spec.has_wheel() else &"thud"), "locked wheels strain; side/lift leaves thud")
			assert_true(cue.stream == (DoorAudio.WHEEL_REFUSED if spec.has_wheel() else DoorAudio.THUDS[event.audio_variant() % DoorAudio.THUDS.size()]), "refusal selects its exact deterministic variant")
			var frame := spec.frame() * game.layout.face(event.face_id()).surface_frame()
			assert_true(cue.position.is_equal_approx(frame * Vector3(0, spec.aperture().y / 2, 0)), "sound originates at the selected door face, not the observer")
			audio.consume(game.doors.events())
			var slot: DoorAudio.Voice = audio.voices[audio.last_voice]
			assert_true(slot.player.global_position.is_equal_approx(cue.position), "3D player sits at door")
			assert_true(slot.player.bus == &"Master", "existing project has only the Master bus")
		assert_int_equal(game.doors.snapshot(id).work, 0, "refusal adds no work")
	audio.free()

func _check_turn_size_scales_pitch_and_variants_repeat_without_resistance_changes() -> void:
	var game := Game.new(0)
	var replay := Game.new(0)
	var audio := _audio(game)
	var pitches: Array[float] = []
	var paths: Dictionary = {}
	for _attempt: int in range(10):
		_press(game, CRANK)
		_press(replay, CRANK)
		var event := game.doors.events()[-1]
		var cue := audio.describe(event)
		var again := audio.describe(replay.doors.events()[-1])
		assert_true(cue.stream == again.stream and cue.pitch == again.pitch, "replay chooses the same stream and pitch")
		assert_true(cue.stream == audio.describe(event).stream, "describing the same event cannot draw randomness")
		if event.kind() == Doors.EventKind.CRANK_MOVED:
			assert_float_equal(cue.pitch, lerpf(1.4, 0.8, clampf(event.angle_delta() / 90.0, 0.0, 1.0)), "larger turns grind longer at lower pitch")
			pitches.append(cue.pitch)
			paths[cue.stream.resource_path] = true
		audio.consume(game.doors.events())
		assert_int_equal(game.doors.snapshot(CRANK).work, replay.doors.snapshot(CRANK).work, "audio cannot consume resistance RNG")
		for _tick: int in range(6):
			game.advance_doors()
			replay.advance_doors()
	assert_true(pitches.min() < pitches.max(), "different turn sizes have different durations/pitches")
	assert_true(paths.size() > 1, "attempts use distinct grind variants")
	audio.free()

func _check_pool_is_bounded_release_is_protected_and_batch_replays_are_silent() -> void:
	var game := Game.new(0)
	var audio := _audio(game)
	_press(game, ShipLayout.BAY_DOOR_ID)
	audio.consume(game.doors.events())
	var release: DoorAudio.Voice = audio.voices[audio.last_voice]
	var sequence := release.sequence
	var stream := release.player.stream
	var count := audio.play_count
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, count, "same event batch plays once")
	for _attempt: int in range(20):
		game.advance_doors()
		_press(game, &"D14-S-041-SIDE-003-PORT")
		audio.consume(game.doors.events())
	assert_int_equal(audio.voices.size(), 6, "fixed small voice pool")
	assert_int_equal(audio.get_child_count(), 6, "pool never grows on rapid input")
	assert_true(release.release and release.sequence == sequence and release.player.stream == stream, "pool exhaustion never cuts a release")
	assert_int_equal(audio.voices[audio.last_voice].sequence, game.doors.events()[-1].sequence(), "oldest non-release can be replaced")
	game.advance_doors()
	_press(game, ShipLayout.POWER_DOOR_ID)
	audio.consume(game.doors.events())
	for id: StringName in [&"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		for _attempt: int in range(32):
			_press(game, id)
			audio.consume(game.doors.events())
			for _tick: int in range(6):
				game.advance_doors()
				audio.consume(game.doors.events())
			if game.doors.snapshot(id).state == Doors.State.OPENING:
				break
	for voice: DoorAudio.Voice in audio.voices:
		assert_true(voice.active and voice.release, "all six openable doors retain their releases")
	count = audio.play_count
	game.advance_doors()
	_press(game, &"D14-S-041-SIDE-003-PORT")
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, count, "all protected voices stay intact")
	audio.free()

func _check_selection_rejection_has_no_sound_and_game_step_delivers_accepted_events() -> void:
	var game := Game.new(0)
	var audio := _audio(game)
	var coordinator := Interactions.new(game.layout)
	var context := Interactions.Context.new()
	context.game = game
	context.motion = PlayerMotion.new()
	context.walking = true
	context.foot = Vector3(18, .305, 0)
	context.eye = Vector3(18, 1.6, 0)
	context.forward = Vector3.DOWN
	var plane := InputPlane.new()
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == &"", "nothing facing this press")
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, 0, "unrouted input stays silent")
	plane.end_frame()
	context.foot = game.layout.anchor(&"D14-HALL-SWITCH").origin
	context.eye = context.foot + Vector3.UP * 1.6
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == &"D14-HALL-SWITCH", "rodless door falls through to the selected switch")
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, 0, "a consumed non-door press has no door sound")
	plane.end_frame()
	var door := game.layout.door(CRANK)
	var frame := door.frame() * game.layout.face(door.face_ids()[0]).surface_frame()
	context.foot = frame * Vector3(0, .305, 1.8)
	context.eye = context.foot + Vector3.UP * 1.295
	context.forward = frame.basis.z
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == &"", "looking away from an in-range door is rejected")
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, 0, "rejected in-range input stays silent")
	plane.end_frame()
	context.forward = -frame.basis.z
	plane.offer_press(InputPlane.Buttons.INTERACT)
	assert_true(coordinator.process(plane, context) == door.face_ids()[0], "selection routes a new facing press")
	audio.consume(game.doors.events())
	assert_int_equal(audio.play_count, 1, "accepted selected door sounds once")
	# A release produced during advance must reach the same observer automatically.
	var step := GameStep.new(game)
	step.door_audio = audio
	for _attempt: int in range(9):
		for _tick: int in range(6):
			step.advance()
		_press(game, CRANK)
	for _tick: int in range(6):
		step.advance()
	assert_true(audio.voices[audio.last_voice].release, "GameStep publishes release after the logical step")
	var count := audio.play_count
	step.advance(true)
	assert_int_equal(audio.play_count, count, "paused logical step cannot replay sound")
	audio.free()
