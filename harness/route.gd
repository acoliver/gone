class_name HarnessRoute
extends RefCounted
## Compiles accepted Player input into ordinary scenario actions. Bay shots
## retain their relative look deltas; only post-portal routes need new headings.

const Scenario := preload("res://harness/scenario.gd")
var stepper: GameStep
var player: Player
var tick: int = 0
var actions: Array = []
var beats: Array = []
var budget: int

func _init(rig: Player, max_ticks: int) -> void:
	player = rig
	stepper = GameStep.new(rig.game, rig)
	budget = max_ticks

func step(offered: Array = []) -> void:
	assert(tick < budget, "route exhausted its unchanged scenario budget")
	for action: Dictionary in offered:
		var stamped := action.duplicate(true)
		stamped.tick = tick
		actions.append(stamped)
	var parser := Scenario.InputAdapter.new(offered.map(func(action: Dictionary) -> Dictionary:
		var copy := action.duplicate(true)
		copy.tick = 0
		return copy), 60)
	var input: Dictionary = parser.step()
	for edge: Dictionary in input.edges:
		player.adapter.press(InputPlane.Buttons.ACTIVATE if edge.button == "activate" else InputPlane.Buttons.INTERACT)
	player.adapter.look(deg_to_rad(input.look_deg.x) - input.key_turn * InputPlane.TURN_SPEED / 60.0, deg_to_rad(input.look_deg.y) + input.key_pitch * InputPlane.PITCH_SPEED / 60.0)
	player.adapter.hold(input.movement.x, input.movement.y)
	if input.climb != null:
		player.adapter.climb(input.climb)
	if input.objective != null:
		player.adapter.objective(input.objective)
	stepper.advance()
	assert(player.motion.failure().is_empty(), player.motion.failure())
	tick += 1

func replay_prefix(schedule: Array, until: int) -> void:
	var index := 0
	while tick <= until:
		var offered: Array = []
		while index < schedule.size() and int(schedule[index].tick) == tick:
			offered.append(schedule[index])
			index += 1
		step(offered)

func anchor(id: StringName, offset: Vector3 = Vector3.ZERO) -> Vector3:
	var layout := player.game.layout
	if id in [ShipLayout.BAY_DOOR_ID, ShipLayout.POWER_DOOR_ID]:
		return layout.door(id).frame() * offset
	return layout.anchor(id) * offset

func walk_to(target: Vector3, stop: float = 0.1) -> void:
	var start := tick
	while true:
		var foot := player.motion.capsule().foot
		var delta := Vector2(target.x - foot.x, target.z - foot.z)
		if delta.length() <= stop:
			return
		assert(tick - start < 1400, "route stuck approaching %s at %s" % [target, foot])
		var yaw := atan2(delta.x, delta.y)
		step([{"type": "look", "yaw_deg": rad_to_deg(InputPlane.wrap_angle(yaw - player.look_angles().x)), "pitch_deg": -rad_to_deg(player.look_angles().y)}, {"type": "move", "forward": 1.0, "strafe": 0.0}])

func climb_to(deck: int, capture_mid: bool = false) -> void:
	var state := player.motion.locomotion.ladder_state()
	var target := player.game.layout.floor_y(deck)
	var distance := target - state.height()
	var midpoint := state.height() + distance * 0.5
	var captured := false
	while absf(target - state.height()) >= Ladder.HEIGHT_EPSILON:
		var before := state.height() + state.pending()
		# Solve the eased tick's input for the remaining distance. Full input
		# drives the shaft; a fractional final tick lands without overshoot.
		var desired := (target - before) / Sim.LOGICAL_TICK_SECS
		var input := ClimbEase.intent_for_velocity(state.velocity(), desired, Ladder.CLIMB_SPEED)
		step([{"type": "climb", "value": input}])
		if capture_mid and not captured and (state.height() - midpoint) * signf(distance) >= 0:
			# New pod #88 route capture: face the lit landing rather than
			# the unlit back wall above it, without moving the climb pose.
			look_at(player.motion.eye(player.game) + Vector3(0, -1.5, 2), -35)
			beat("mid-shaft")
			captured = true
	assert(absf(state.height() - player.game.layout.floor_y(deck)) < 1e-8, "route reaches exact landing")

func look_at(target: Vector3, pitch: float = 0.0) -> void:
	var delta := target - player.motion.eye(player.game)
	var yaw := atan2(-delta.x, -delta.z)
	step([{"type": "look", "yaw_deg": rad_to_deg(InputPlane.wrap_angle(yaw - player.look_angles().x)), "pitch_deg": pitch - rad_to_deg(player.look_angles().y)}])

func press() -> void:
	step([{"type": "press", "button": "interact"}])

func hold(ticks: int) -> void:
	for _i: int in range(ticks):
		step()

func beat(name: String) -> void:
	beats.append({"name": name, "tick": tick})
	hold(2)

func corridor(name: String) -> void:
	# Align at the bay-side aperture before the straight crossing.
	walk_to(anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, 1.0)))
	walk_to(anchor(ShipLayout.BAY_DOOR_ID, Vector3(0, 0, -1.0)))
	if name == "hallway":
		walk_to(anchor(ShipLayout.BAY_DOOR_ID, Vector3(7, 0, -1)))
		look_at(anchor(ShipLayout.POWER_DOOR_ID), -2)
		beat("hall-dark")
	walk_to(anchor(&"D14-HALL-SWITCH", Vector3(0, -1.25, 0.8)))
	look_at(anchor(&"D14-HALL-SWITCH"), 4)
	press()
	hold(45)
	look_at(anchor(ShipLayout.POWER_DOOR_ID), -2)
	beat("hall-lit")
	if name == "hallway":
		walk_to(anchor(ShipLayout.BAY_DOOR_ID, Vector3(5, 0, -1)))
		look_at(anchor(ShipLayout.BAY_DOOR_ID), -2)
		beat("hall-corridor")
		return
	walk_to(anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, -1)))
	look_at(anchor(ShipLayout.POWER_DOOR_ID), -9)
	press()
	hold(60)
	beat("power-door-opened")
	walk_to(anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, 1.5)))
	walk_to(anchor(&"D14-POWER-CONSOLE", Vector3(2.45, 0, 3)))
	walk_to(anchor(&"D14-POWER-CONSOLE", Vector3(0.35, 0, 0)))
	look_at(anchor(&"D14-POWER-CONSOLE", Vector3(-1, 1.4, 0)), -1)
	hold(30)
	look_at(anchor(&"D14-POWER-CONSOLE", Vector3(-1, 1.4, 0)), -20)
	beat("console-inactive")
	press()
	hold(50)
	look_at(anchor(&"D14-POWER-CONSOLE", Vector3(4.95, 1.3, 1.8)), -12)
	beat("power-active")
	walk_to(anchor(&"D14-POWER-CONSOLE", Vector3(2.45, 0, 3)))
	walk_to(anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, 1.5)))
	walk_to(anchor(ShipLayout.POWER_DOOR_ID, Vector3(0, 0, -1)))
	look_at(anchor(ShipLayout.BAY_DOOR_ID), -3)
	beat("hall-white")
