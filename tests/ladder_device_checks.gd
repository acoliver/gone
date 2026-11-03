extends SceneTree
## Exercise the engine's physics/input edge lifetime, including Main's callback.

class TracedPlane:
	extends InputPlane
	var interact_taken: bool = false
	func take_press(button: int) -> bool:
		var taken := super.take_press(button)
		if button == InputPlane.Buttons.INTERACT and taken:
			interact_taken = true
		return taken

class DeviceMain:
	extends "res://app/main.gd"
	var check: SimTestCase
	var mode: String
	var cases: Array[Dictionary] = []
	var case_index: int = -1
	var stage: String = ""
	var ticks: int = 0
	var total_ticks: int = 0
	var direction: float
	var target: float
	var destination: int
	var action: String
	var trace: TracedPlane
	var diagnostics: String

	func _ready() -> void:
		check = SimTestCase.new()
		for well: StringName in [&"C-000-LADDER", &"C-001-LADDER"]:
			for deck: int in [1, 13, 15, 30]:
				for side: float in ([-1.0, 1.0] if mode == "settle" else [-1.0]):
					cases.append({"well": well, "deck": deck, "side": side})
		_next_case()

	func _next_case() -> void:
		_release_all()
		if player != null:
			player.free()
		case_index += 1
		if case_index == cases.size():
			if check.failure.is_empty():
				print("DEVICE LADDER PASS %s cases=%d" % [mode, cases.size()])
			else:
				print("DEVICE LADDER FAIL %s: %s" % [mode, check.failure])
			get_tree().quit(0 if check.failure.is_empty() else 1)
			set_physics_process(false)
			return
		var fixture := cases[case_index]
		destination = fixture.deck
		direction = -1.0 if destination in [15, 30] else 1.0
		action = "climb_up" if direction > 0 else "climb_down"
		var start_deck := destination + int(direction)
		game = Game.new(0)
		game.phase = Phase.Machine.new(Phase.Wake.STANDING)
		player = Player.build(game, null)
		player.scripted = false
		player.interpolate_view = true
		add_child(player)
		player._look_yaw = 0.0
		player._look_pitch = 0.0
		trace = TracedPlane.new()
		player.plane = trace
		var capsule := Resolve.Capsule.new()
		capsule.foot = game.layout.well(fixture.well).landing(start_deck).origin + Vector3.UP * 0.305
		capsule.head = capsule.foot + Vector3.UP * 1.15
		var walk := Walk.WalkState.start(game.phase, capsule)
		check.assert_true(walk.is_ok(), "standing fixture starts")
		player.motion.locomotion = Locomotion.start(game.layout, game.collision, start_deck, walk.state).state
		step = GameStep.new(game, player)
		smoke_symptoms = SmokeSymptoms.new(game.layout, game.ventilation)
		target = game.layout.floor_y(destination)
		stage = "mount"
		ticks = 0
		diagnostics = ""
		_space(true)

	func _physics_process(delta: float) -> void:
		total_ticks += 1
		if total_ticks > 12000:
			print("DEVICE LADDER FAIL timeout %s %s" % [mode, stage])
			get_tree().quit(1)
			return
		trace.interact_taken = false
		var ladder := player.motion.locomotion.ladder_state()
		if stage == "mount" and ticks == 1:
			_space(false)
		if stage == "climb":
			var distance := direction * (ladder.height() - target)
			var threshold := -0.1 if mode in ["release", "held"] else -0.2
			if mode == "delayed":
				threshold = 0.0 if destination in [1, 30] else 0.12
			if mode == "settle" and cases[case_index].side > 0:
				threshold = 0.0 if destination in [1, 30] else 0.12
			if mode == "bounds":
				threshold = 0.0 if destination in [1, 30] else -2.5
			if distance >= threshold - 1e-10:
				diagnostics = _snapshot(ladder)
				if mode != "held" and not (mode == "bounds" and destination in [1, 30]):
					Input.action_release(action)
					Input.action_release("look_up" if direction > 0 else "look_down")
				stage = "stop"
				ticks = 0
				if mode in ["release", "held"] or (mode == "bounds" and destination not in [1, 30]):
					_space(true)
		if stage == "stop" and ticks == 3 and mode == "delayed":
			diagnostics += " delayed_press=" + _snapshot(ladder)
			_space(true)
		if stage == "stop" and ticks == 1:
			_space(false)
		if stage == "stop" and ticks == 4 and mode == "delayed":
			_space(false)
		if stage == "stop" and ticks == 30 and mode == "settle":
			check.assert_float_equal(ladder.height(), target, "release capture settles at D%02d: %s final=%s" % [destination, diagnostics, _snapshot(ladder)])
			check.assert_float_equal(ladder.velocity(), 0.0, "captured stop has no residual velocity")
			diagnostics += " settled=" + _snapshot(ladder)
			_space(true)
		if stage == "stop" and ticks == 30 and mode == "bounds":
			if destination in [1, 30]:
				check.assert_float_equal(ladder.height(), target, "held endpoint is exact")
				check.assert_float_equal(ladder.velocity(), 0.0, "endpoint clips velocity")
			else:
				check.assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.CLIMBING, "midshaft Space is a no-op")
				print("DEVICE %s D%02d %s midshaft_rejected %s" % [cases[case_index].well, destination, mode, diagnostics])
				_next_case()
				return
			_space(true)
		var before_press := _snapshot(ladder) if ladder != null else "walking"
		# Call the production callback once per actual engine physics frame.
		super._physics_process(delta)
		if trace.interact_taken:
			print("DEVICE %s D%02d %s tick=%d Space consumed_by=PlayerMotion mode=%d press_state=%s %s" % [cases[case_index].well, destination, mode, ticks, player.motion.locomotion.mode(), before_press, diagnostics])
		if stage == "mount" and ticks == Ladder.TRANSFER_TICKS:
			check.assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.CLIMBING, "mount edge does not also dismount")
			Input.action_press(action)
			Input.action_press("look_up" if direction > 0 else "look_down")
			stage = "climb"
			ticks = -1
		if stage == "stop" and ticks == 60:
			check.assert_int_equal(player.motion.locomotion.mode(), Locomotion.Mode.WALK, "Space reaches WALK D%02d: %s" % [destination, diagnostics])
			check.assert_int_equal(player.motion.deck(), destination, "walking deck commits")
			_next_case()
			return
		ticks += 1

	func _snapshot(ladder: Ladder.State) -> String:
		return "h=%.9f v=%.9f distance=%.9f pending=%.9f" % [ladder.height(), ladder.velocity(), absf(ladder.height() - target), ladder.pending()]

	func _space(pressed: bool) -> void:
		for name: String in ["activate", "interact"]:
			if pressed:
				Input.action_press(name)
			else:
				Input.action_release(name)

	func _release_all() -> void:
		for name: String in ["activate", "interact", "climb_up", "climb_down", "look_up", "look_down"]:
			Input.action_release(name)

func _initialize() -> void:
	call_deferred("_start")

func _start() -> void:
	var driver := DeviceMain.new()
	driver.mode = OS.get_cmdline_user_args()[0]
	root.add_child(driver)
