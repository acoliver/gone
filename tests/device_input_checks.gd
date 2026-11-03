extends SceneTree

class EdgeChecks extends Node:
	var player: Player
	var frame := 0
	var activate_count := 0
	var interact_count := 0

	func _ready() -> void:
		player = Player.build(Game.new(0), null)
		player.scripted = true
		add_child(player)
		player.scripted = false

	func _physics_process(_delta: float) -> void:
		if frame in [1, 4, 7, 10, 12]:
			var event := InputEventKey.new()
			event.physical_keycode = KEY_SPACE
			event.pressed = frame != 12
			event.echo = frame in [4, 7, 10]
			Input.parse_input_event(event)
			Input.flush_buffered_events()
		if frame == 15:
			Input.action_press("interact")
		if frame == 16:
			Input.action_release("interact")
		player._collect_device_input(Sim.LOGICAL_TICK_SECS)
		if player.plane.take_press(InputPlane.Buttons.ACTIVATE):
			activate_count += 1
		if player.plane.take_press(InputPlane.Buttons.INTERACT):
			interact_count += 1
		player.plane.end_frame()
		if frame == 18:
			if activate_count == 1 and interact_count == 2:
				print("DEVICE EDGE PASS activate=1 interact=2: one Space press, no echoes, one direct action press")
				get_tree().quit()
			else:
				print("DEVICE EDGE FAIL activate=%d interact=%d" % [activate_count, interact_count])
				get_tree().quit(1)
		frame += 1

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	root.add_child(EdgeChecks.new())
