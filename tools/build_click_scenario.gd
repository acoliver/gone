extends SceneTree
## Compile click-only standing movement/actions through the actual fixed tick.

class ClickRoute:
	extends HarnessRoute

	func floor_click(point: Vector3) -> void:
		point.y = player.game.layout.floor_y(14)
		step([{"type": "objective", "kind": "floor", "deck": 14, "point": [point.x, point.y, point.z]}])
		finish_objective()
		assert(Vector2(player.motion.capsule().foot.x - point.x, player.motion.capsule().foot.z - point.z).length() <= 0.25, "floor click reaches its point")

	func act_click(id: StringName) -> void:
		step([{"type": "objective", "kind": "act", "deck": 14, "target": String(id)}])
		finish_objective()

	func finish_objective() -> void:
		var start := tick
		while player.motion.objectives.current != null:
			assert(tick - start < 1500, "objective must finish within route budget")
			step()
		hold(30)
		print("CLICK ROUTE tick=%d foot=%s" % [tick, player.motion.capsule().foot])

func _initialize() -> void:
	call_deferred("build")

func build() -> void:
	var game := Game.new(0)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	root.add_child(player)
	game.wake_state.mark_ready()
	var route := ClickRoute.new(player, 10000)
	route.beat("eyes-closed")
	route.hold(90)
	route.beat("first-blink")
	route.hold(200)
	route.step([{"type": "press", "button": "activate"}])
	route.hold(8 + Player.GET_UP_LOOK_TICKS)
	route.look_at(game.layout.anchor(&"D14-BAY-ROD").origin, -12)
	route.beat("standing")
	route.floor_click(Vector3(15, 0, 11.5))
	route.floor_click(Vector3(15, 0, 8.3))
	route.act_click(&"D14-BAY-ROD")
	assert(player.motion.rod_carried, "click picked up rod")
	route.beat("rod-picked-up")
	route.floor_click(game.layout.door(ShipLayout.BAY_DOOR_ID).frame() * Vector3(0, 0, 2.5))
	route.act_click(ShipLayout.BAY_DOOR_ID)
	route.hold(60)
	assert(game.door_open, "click pried door")
	route.look_at(game.layout.door(ShipLayout.BAY_DOOR_ID).frame().origin, -10)
	route.beat("door-opened")
	route.floor_click(game.layout.door(ShipLayout.BAY_DOOR_ID).frame() * Vector3(0, 0, -1))
	route.floor_click(Vector3(18, 0, 0))
	route.act_click(&"D14-HALL-SWITCH")
	assert(game.hallway_lit, "click lit hall")
	route.look_at(game.layout.door(ShipLayout.POWER_DOOR_ID).frame().origin, -2)
	route.hold(45)
	route.beat("hall-lit")
	route.floor_click(Vector3(25, 0, 0))
	route.act_click(ShipLayout.POWER_DOOR_ID)
	route.hold(60)
	assert(game.power_door_open, "click opened power room")
	route.look_at(game.layout.door(ShipLayout.POWER_DOOR_ID).frame().origin, -9)
	route.beat("power-door-opened")
	route.floor_click(Vector3(27, 0, -0.2))
	route.floor_click(Vector3(27, 0, -3))
	route.floor_click(game.layout.anchor(&"D14-POWER-CONSOLE").origin + Vector3(2.45, 0, 3))
	route.floor_click(game.layout.anchor(&"D14-POWER-CONSOLE").origin + Vector3(0.35, 0, 0))
	assert(player.motion.console_presses == 0 and not game.power_active, "arrival precedes console click")
	route.look_at(game.layout.anchor(&"D14-POWER-CONSOLE").origin + Vector3(-1, 1.4, 0), -20)
	route.beat("console-inactive")
	route.act_click(&"D14-POWER-CONSOLE")
	route.hold(60)
	assert(game.power_active, "one console click starts power")
	route.look_at(game.layout.anchor(&"D14-POWER-CONSOLE").origin + Vector3(4.95, 1.3, 1.8), -12)
	route.beat("power-active")
	var data := {"name": "click-route", "seed": 0, "ticks_per_second": 60, "mode": "capture", "content": "gameplay", "max_frames": 10000, "logical_steps_per_present": 4, "actions": route.actions, "beats": route.beats}
	FileAccess.open("res://scenarios/click-route.json", FileAccess.WRITE).store_string(JSON.stringify(data, "\t") + "\n")
	print("CLICK ROUTE COMPLETE ticks=%d actions=%d" % [route.tick, route.actions.size()])
	quit()
