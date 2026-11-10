class_name DemoStart
extends RefCounted

static func selected(args: PackedStringArray) -> String:
	var start := "stasis"
	for index: int in range(args.size()):
		if args[index] == "--start":
			assert(index + 1 < args.size() and args[index + 1] in ["stasis", "quarters"], "--start requires stasis or quarters")
			start = args[index + 1]
	return start

static func quarters(game: Game, player: Player) -> void:
	game.wake_state.mark_ready()
	while not game.wake_state.is_complete(): game.wake_state.tick()
	game.phase = Phase.Machine.new(Phase.Wake.STANDING)
	game.light_hallway()
	game.press_console()
	game.bay_exited = true
	var capsule := Resolve.Capsule.new()
	capsule.foot = Vector3(45, QuartersLayout.FLOOR_Y + 0.305, 0)
	capsule.head = capsule.foot + Vector3.UP * 1.15
	var walk := Walk.WalkState.start(game.phase, capsule)
	assert(walk.is_ok(), "quarters standing spawn")
	var locomotion := Locomotion.start(game.layout, game.collision, 16, walk.state)
	assert(locomotion.is_ok(), "quarters deck spawn")
	player.motion.locomotion = locomotion.state
	player._look_yaw = PI
	player._look_pitch = 0
	player._previous_eye = player.motion.eye(game)
	player._previous_look = Vector2(PI, 0)
	player.present()

static func prepare_ship(ship: ShipScene, player: Player) -> void:
	ship.stream.focus(&"C-001-LADDER", 16)
	ship.stream.build_next()
	ship.stream.update(player.motion)
