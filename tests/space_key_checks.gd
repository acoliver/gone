extends SceneTree
## Issue #142: Space key events through the production main scene, the way
## the window delivers them. Input.parse_input_event is the entry the
## display server uses for a physical key, so it updates the engine's action
## state and then dispatches to the viewport. Presses are queued from
## _process, outside any physics tick, and held for a realistic number of
## frames. Viewport.push_input dispatches a key to the scene without touching
## the action state, which stands in for a key that reaches game code but
## yields no interact edge.

class SpaceMain:
	extends "res://app/main.gd"
	var check := SimTestCase.new()
	var schedule: Array[Dictionary] = []
	var index := -1
	var frame := 0
	var stage := ""
	var foot := Vector3.ZERO

	func _ready() -> void:
		super._ready()
		game.wake_state.mark_ready()
		while not game.wake_state.is_complete():
			game.wake_state.tick()
		game.phase = Phase.Machine.new(Phase.Wake.STANDING)
		var well := game.layout.well(&"C-001-LADDER")
		foot = Vector3(well.climb_line().origin.x, game.layout.floor_y(14) + Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE, -2.95)
		# Hold lengths in 60 Hz frames: about 40, 80 and 150 ms.
		for look: Vector2 in [Vector2(-20, -48), Vector2(0, 0), Vector2(0, -30)]:
			for hold: int in [3, 5, 9]:
				schedule.append({"look": look, "hold": hold, "path": "key"})
		schedule.append({"look": Vector2(-20, -48), "hold": 5, "path": "viewport"})
		_next()

	func _next() -> void:
		index += 1
		if index == schedule.size():
			if check.failure.is_empty():
				print("SPACE KEY PASS cases=%d" % schedule.size())
			else:
				print("SPACE KEY FAIL: %s" % check.failure)
			get_tree().quit(0 if check.failure.is_empty() else 1)
			stage = "done"
			return
		var capsule := Resolve.Capsule.new()
		capsule.foot = foot
		capsule.head = foot + Vector3.UP * 1.15
		player.motion.locomotion = Locomotion.start(game.layout, game.collision, 14, Walk.WalkState.start(game.phase, capsule).state).state
		var look: Vector2 = schedule[index].look
		player._look_yaw = deg_to_rad(look.x)
		player._look_pitch = deg_to_rad(look.y)
		player.present()
		stage = "settle"
		frame = 0

	func _space(pressed: bool) -> void:
		var event := InputEventKey.new()
		event.keycode = KEY_SPACE
		event.physical_keycode = KEY_SPACE
		event.key_label = KEY_SPACE
		event.unicode = 32 if pressed else 0
		event.pressed = pressed
		if schedule[index].path == "key":
			Input.parse_input_event(event)
		else:
			get_viewport().push_input(event)

	func _process(_delta: float) -> void:
		if stage == "done":
			return
		frame += 1
		var case: Dictionary = schedule[index]
		if stage == "settle" and frame == 3:
			_space(true)
			stage = "held"
			frame = 0
		elif stage == "held" and frame == case.hold:
			_space(false)
			stage = "observe"
			frame = 0
		elif stage == "observe" and frame == 30:
			var label := "%s look %s held %d frames" % [case.path, case.look, case.hold]
			if case.path == "key":
				check.assert_true(player.motion.mounted(), "Space key mounts: " + label)
			else:
				check.assert_false(player.motion.mounted(), "a key without an action edge cannot mount: " + label)
			print("SPACE KEY CASE %s mounted=%s" % [label, player.motion.mounted()])
			_next()

func _initialize() -> void:
	call_deferred("_start")

func _start() -> void:
	var scene := SpaceMain.new()
	root.add_child(scene)
	current_scene = scene
