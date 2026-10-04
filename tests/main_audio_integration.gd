extends SceneTree

# Windowed command: godot --path . -s tests/main_audio_integration.gd
# Requires a rendered window; RenderingServer.frame_post_draw does not fire in headless mode.
const WAIT_TIMEOUT_MSEC := 15000

class SignalCounts:
	extends RefCounted
	var starts := 0
	var finishes := 0

func _initialize() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("FAIL main audio integration: requires a rendered window; do not run with --headless")
		quit(1)
		return
	call_deferred("_run")

func _run() -> void:
	var packed: PackedScene = load("res://main.tscn")
	var main: Node = packed.instantiate()
	if main == null:
		_fail("production scene failed to instantiate")
		return
	root.add_child(main)
	var game: Game = main.game
	var wake_present: WakePresent = main.wake_present
	var rig: Player = main.player
	var camera: Camera3D = rig.camera
	var player := main.get_node("WakeRespiratoryTrial") as AudioStreamPlayer
	var checks := 0
	main.set_physics_process(false)
	if player == null:
		_fail("production scene has its non-positional wake player")
		return
	if player.stream == null or player.stream != main.get("WAKE_AUDIO"):
		_fail("production scene assigns the preloaded wake stream")
		return
	checks += 1
	if player.playing:
		_fail("wake audio is not playing before the readiness frame")
		return
	checks += 1
	var counts := SignalCounts.new()
	player.finished.connect(func() -> void: counts.finishes += 1)
	wake_present.wake_started.connect(func() -> void: counts.starts += 1)
	await process_frame
	await RenderingServer.frame_post_draw
	if not player.playing:
		_fail("wake audio starts after the rendered-frame readiness barrier")
		return
	checks += 1
	var first_position := player.get_playback_position()
	var first_stream: AudioStream = player.stream
	var start_connections: int = wake_present.wake_started.get_connections().size()
	if start_connections != 2:
		_fail("wake readiness has one production audio connection plus the test observer, got %d" % start_connections)
		return
	checks += 1
	if counts.finishes != 0 or counts.starts != 1:
		_fail("readiness observer records zero finishes and exactly one initial start; starts=%d finishes=%d" % [counts.starts, counts.finishes])
		return
	checks += 1
	if not await _test_smoke_audio_completion_latch(main):
		return
	main.set_physics_process(true)
	for _frame: int in range(3):
		await process_frame
	wake_present.begin()
	await process_frame
	if not player.playing or player.stream != first_stream:
		_fail("duplicate begin leaves the assigned stream playing")
		return
	checks += 1
	var later_position := player.get_playback_position()
	if later_position < first_position:
		_fail("duplicate begin does not rewind the playback position")
		return
	checks += 1
	if counts.finishes != 0:
		_fail("stream did not finish during the short integration check")
		return
	checks += 1
	if counts.starts != 1:
		_fail("duplicate begin emitted another wake-start signal; got %d" % counts.starts)
		return
	checks += 1
	wake_present.wake_started.emit()
	if counts.starts != 2:
		_fail("injected wake-start signal reaches observer; got %d" % counts.starts)
		return
	checks += 1
	var deadline := Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while game.wake_state.current_tick() < 241 and Time.get_ticks_msec() < deadline:
		await process_frame
		await RenderingServer.frame_post_draw
	var tick: int = game.wake_state.current_tick()
	if tick < 241:
		_fail("timed out waiting for wake tick 241; current tick is %d" % tick)
		return
	if tick > 261:
		_fail("missed active cough tick window 240..261; current tick is %d" % tick)
		return
	await RenderingServer.frame_post_draw
	tick = game.wake_state.current_tick()
	if tick > 261:
		_fail("missed active cough tick window while awaiting render; current tick is %d" % tick)
		return
	var sample: Wake.WakeSample = game.wake_state.sample()
	var tremor := WakePresent.respiratory_tremor(tick)
	if not is_equal_approx(rig.rotation.y, rig.look_angles().x + sample.sway_offset.x + tremor.x):
		_fail("production Player yaw does not include sample sway and cough tremor at tick %d" % tick)
		return
	checks += 1
	if not is_equal_approx(camera.rotation.x, clampf(rig.look_angles().y + sample.sway_offset.y + tremor.y, -InputPlane.PITCH_LIMIT, InputPlane.PITCH_LIMIT)):
		_fail("production Player camera pitch does not include sample sway and cough tremor at tick %d" % tick)
		return
	checks += 1

	deadline = Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while game.wake_state.current_tick() < 262 and Time.get_ticks_msec() < deadline:
		await process_frame
		await RenderingServer.frame_post_draw
	tick = game.wake_state.current_tick()
	if tick < 262:
		_fail("timed out waiting for cough end tick 262; current tick is %d" % tick)
		return
	await RenderingServer.frame_post_draw
	sample = game.wake_state.sample()
	if WakePresent.respiratory_tremor(tick) != Vector2.ZERO:
		_fail("cough tremor is nonzero at or after tick 262")
		return
	if not is_equal_approx(rig.rotation.y, rig.look_angles().x + sample.sway_offset.x) or not is_equal_approx(camera.rotation.x, clampf(rig.look_angles().y + sample.sway_offset.y, -InputPlane.PITCH_LIMIT, InputPlane.PITCH_LIMIT)):
		_fail("production Player rig does not return to base plus sample sway after cough")
		return
	checks += 1

	deadline = Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while game.wake_state.current_tick() < 282 and Time.get_ticks_msec() < deadline:
		await process_frame
		await RenderingServer.frame_post_draw
	if game.wake_state.current_tick() < 282:
		_fail("timed out waiting for authored wake completion tick 282; current tick is %d" % game.wake_state.current_tick())
		return
	await RenderingServer.frame_post_draw
	if not game.phase.in_phase(Phase.Wake.AWAKE_IN_POD):
		_fail("authored completion did not hand off to AWAKE_IN_POD")
		return
	if not is_equal_approx(rig.rotation.y, rig.look_angles().x) or not is_equal_approx(camera.rotation.x, rig.look_angles().y):
		_fail("production Player rig is not neutral after authored wake completion")
		return
	checks += 1
	print("PASS main audio integration: %d checks; position monotonicity does not prove audible output" % checks)
	quit(0)

func _test_smoke_audio_completion_latch(main: Node) -> bool:
	var audio: AudioStreamPlayer = main.smoke_audio
	var first := SmokeSymptoms.Event.new(1, SmokeSymptoms.BREATH_MILD, 0.0, 1)
	var second := SmokeSymptoms.Event.new(2, SmokeSymptoms.COUGH, 0.0, 2)
	main._smoke_audio_queue.clear()
	main._smoke_audio_queue.append(first)
	main._smoke_audio_queue.append(second)
	main._smoke_audio_in_flight = true
	var original_stream: AudioStream = audio.stream
	main._play_next_smoke_event()
	if audio.stream != original_stream or main._smoke_audio_queue.size() != 2:
		_fail("pending smoke event waits while the completion signal is outstanding even with playback stopped")
		return false
	var finished_at := Time.get_ticks_usec()
	audio.finished.emit()
	var deadline: int = main._smoke_silence_until_usec
	if main._smoke_audio_in_flight or deadline - finished_at < 200000:
		_fail("finished releases the latch and arms at least 200000 usec of silence")
		return false
	main._play_next_smoke_event()
	if audio.stream != original_stream or main._smoke_audio_queue.size() != 2:
		_fail("pending smoke event remains queued throughout the silence deadline")
		return false
	while Time.get_ticks_usec() < deadline:
		await process_frame
	var wait_elapsed := Time.get_ticks_usec() - finished_at
	main._play_next_smoke_event()
	print("smoke latch diagnostic: stream=%s original=%s queue=%d in_flight=%s playing=%s deadline_remaining_usec=%d actual_wait_usec=%d" % [audio.stream, original_stream, main._smoke_audio_queue.size(), main._smoke_audio_in_flight, audio.playing, deadline - Time.get_ticks_usec(), wait_elapsed])
	if audio.stream == original_stream or main._smoke_audio_queue.size() != 1 or not main._smoke_audio_in_flight or not audio.playing:
		_fail("first queued smoke event starts only after the silence deadline")
		return false
	audio.stop()
	audio.stream = original_stream
	main._smoke_audio_queue.clear()
	main._smoke_audio_in_flight = false
	main._smoke_silence_until_usec = 0
	return true

func _fail(message: String) -> void:
	push_error("FAIL main audio integration: " + message)
	quit(1)
