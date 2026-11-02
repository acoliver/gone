class_name GameStep
extends RefCounted
## The only logical clock. Presentation may run while advance is paused.

var game: Game
var player: Player
var smoke: SmokeSymptoms
var fixtures: Array[Node] = []
var logical_tick: int = 0
var sampled_eye := Vector3.ZERO
var door_events: Array[Doors.Event] = []
var door_views: Array[DoorView] = []
var ship_scene: ShipScene

func _init(p_game: Game, p_player: Player = null) -> void:
	game = p_game
	player = p_player

func advance(paused: bool = false) -> void:
	if paused:
		return
	logical_tick += 1
	var was_complete := game.wake_state.is_complete()
	game.wake_state.tick()
	if game.wake_state.is_complete() and not was_complete:
		var transition := game.phase.wake_complete()
		assert(transition.kind == Phase.Transition.Kind.ADVANCED)
	game.advance_doors()
	if player != null:
		sampled_eye = player.motion.eye(game)
		if smoke != null:
			smoke.tick(game.phase.look_allowed(), sampled_eye)
		player.step()
	if ship_scene != null and player != null and player.motion.capsule() != null:
		ship_scene.prepare_near(player.motion.capsule().foot)
	for fixture: Node in fixtures:
		fixture.process_frame(Sim.LOGICAL_TICK_SECS)
	door_events = game.doors.events()
	for view: DoorView in door_views:
		view.present(game.doors.snapshot(view.door_id()))
	if player != null:
		player.present()
