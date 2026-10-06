extends SceneTree

const WAIT_TIMEOUT_MSEC := 30000

class Events:
	extends RefCounted
	var starts: Array[int] = []
	var finishes: Array[int] = []
	var start_times: Array[int] = []

func _initialize() -> void:
	if DisplayServer.get_name() == "headless":
		push_error("FAIL voice audio integration: requires a rendered window")
		quit(1)
		return
	call_deferred("_run")

func _run() -> void:
	var packed: PackedScene = load("res://main.tscn")
	var main: Node = packed.instantiate()
	root.add_child(main)
	var game: Game = main.game
	var voice: VoicePresentation = main.voice_presentation
	var observed := Events.new()
	voice.line_started.connect(func(number: int) -> void:
		observed.starts.append(number)
		observed.start_times.append(Time.get_ticks_usec())
	)
	voice.line_finished.connect(func(number: int) -> void: observed.finishes.append(number))
	var deadline := Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while game.wake_state.current_tick() < 282 and Time.get_ticks_msec() < deadline:
		await process_frame
		await RenderingServer.frame_post_draw
		if game.wake_state.current_tick() < 282 and not observed.starts.is_empty():
			_fail("voice remains silent before authored wake tick 282; starts=%s" % observed.starts)
			return
	if game.wake_state.current_tick() < 282 or observed.starts != [1]:
		_fail("tick 282 handoff starts voice line 1 exactly once; tick=%d starts=%s" % [game.wake_state.current_tick(), observed.starts])
		return
	var deadline_usec := Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while observed.finishes.size() < 1 and Time.get_ticks_msec() < deadline_usec:
		await process_frame
	if observed.starts != [1] or observed.finishes != [1]:
		_fail("line 1 finishes naturally exactly once; starts=%s finishes=%s" % [observed.starts, observed.finishes])
		return

	var rig: Player = main.player
	rig.scripted = true
	var game_motion := rig.motion
	var plane: InputPlane = rig.plane
	plane.offer_press(InputPlane.Buttons.ACTIVATE)
	game_motion.advance(plane, game, 0.0, 1.0 / 60.0)
	for _segment: int in range(Exit.EXIT_POSE_COUNT):
		game_motion.advance(plane, game, 0.0, 1.0 / 60.0)
	if game_motion.state() != PlayerMotion.BodyState.WALK:
		_fail("production PlayerMotion reaches standing before the hallway event")
		return
	# Exercise the production rod pickup and the real opening sequence.
	var walk_state: Walk.WalkState = game_motion.get("_walk")
	var capsule: Resolve.Capsule = walk_state.get("_capsule")
	var rod_center: Vector2 = Rod.floor_center()
	capsule.foot.x = rod_center.x
	capsule.foot.z = rod_center.y
	plane.offer_press(InputPlane.Buttons.INTERACT)
	if not game_motion.pickup_rod(plane):
		_fail("production motion picks up the rod through its interact channel")
		return
	capsule.foot.x = 4.9
	capsule.foot.z = 0.0
	plane.offer_press(InputPlane.Buttons.INTERACT)
	if not game_motion.interact_with_door(plane, game):
		_fail("rod-carried interact starts the hatch opening")
		return
	for _tick: int in range(PlayerMotion.DOOR_RETRACT_TICKS + PlayerMotion.DOOR_SLIDE_TICKS):
		game_motion.advance(plane, game, 0.0, 1.0 / 60.0)
	if not game.door_open or game_motion.door_state != PlayerMotion.DoorState.OPEN:
		_fail("actual PlayerMotion hatch sequence opens the doorway")
		return
	voice.poll_events()
	if observed.starts != [1]:
		_fail("hatch opening without a hallway crossing does not trigger line 2")
		return
	capsule.foot.x = 5.9
	voice.poll_events()
	capsule.foot.x = 6.01
	voice.poll_events()
	if observed.starts != [1, 2]:
		_fail("physical capsule crossing x=6 starts line 2 once; starts=%s" % observed.starts)
		return
	plane.offer_press(InputPlane.Buttons.INTERACT)
	if not game_motion.flip_hallway_switch(plane, game) or not game.hallway_lit:
		_fail("production interact at the hallway switch changes hallway_lit")
		return
	plane.offer_press(InputPlane.Buttons.INTERACT)
	if game_motion.flip_hallway_switch(plane, game) or not game.hallway_lit or game_motion.door_state != PlayerMotion.DoorState.OPEN:
		_fail("repeated switch press is a no-op and leaves gameplay doorway state intact")
		return
	voice.poll_events()
	var switch_wall_usec := Time.get_ticks_usec()
	while Time.get_ticks_usec() - switch_wall_usec < 900000:
		await process_frame
		if observed.starts != [1, 2]:
			_fail("line 3 starts before the one-second wall-clock gate; starts=%s" % observed.starts)
			return
	deadline_usec = Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while observed.finishes.size() < 2 and Time.get_ticks_msec() < deadline_usec:
		await process_frame
	if observed.starts != [1, 2] or observed.finishes != [1, 2]:
		_fail("line 2 finishes naturally exactly once; starts=%s finishes=%s" % [observed.starts, observed.finishes])
		return
	voice.poll_events()
	if observed.starts != [1, 2, 3]:
		_fail("line 3 starts after natural line 2 completion and its time gate; starts=%s" % observed.starts)
		return
	deadline_usec = Time.get_ticks_msec() + WAIT_TIMEOUT_MSEC
	while observed.finishes.size() < 3 and Time.get_ticks_msec() < deadline_usec:
		await process_frame
	if observed.finishes != [1, 2, 3]:
		_fail("line 3 finishes naturally exactly once; finishes=%s" % observed.finishes)
		return
	game.hallway_lit = false
	game.hallway_lit = true
	voice.poll_events()
	if observed.starts != [1, 2, 3] or observed.finishes != [1, 2, 3]:
		_fail("three natural one-shot lines finish without replay; starts=%s finishes=%s" % [observed.starts, observed.finishes])
		return

	# State-directed setup isolates the production monotonic poll from audio playback.
	voice._wake_seen = true
	voice._hallway_seen = true
	voice._switch_seen = true
	voice._line2_finished = true
	voice._switch_at_usec = 100
	voice._line3_seen = false
	var boundary_usec: Array[int] = [100 + VoicePresentation.SWITCH_DELAY_USEC - 1]
	voice.clock_usec = func() -> int: return boundary_usec[0]
	voice.poll_events()
	if observed.starts != [1, 2, 3]:
		_fail("idle-player poll does not pass at 999999 usec; starts=%s" % observed.starts)
		return
	boundary_usec[0] += 1
	voice.poll_events()
	if observed.starts != [1, 2, 3, 3]:
		_fail("idle-player production poll passes at exactly 1000000 usec; starts=%s" % [observed.starts])
		return
	print("PASS voice audio integration: physical rod/door/crossing/switch; natural starts=%s finishes=%s; wall-clock switch delay usec=%d; idle-player boundary 999999/1000000 usec" % [observed.starts.slice(0, 3), observed.finishes, observed.start_times[2] - switch_wall_usec])
	quit(0)

func _fail(message: String) -> void:
	push_error("FAIL voice audio integration: " + message)
	quit(1)
