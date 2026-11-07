extends SceneTree
## Regenerate the corridor tails from layout ids without changing the authored
## bay-local input schedules, beats or scenario budgets.
const Route := preload("res://harness/route.gd")

func _initialize() -> void:
	call_deferred("_build")

func _build() -> void:
	if "--connector-only" in OS.get_cmdline_user_args():
		_build_connector()
		quit(0)
		return
	for name: String in ["gameplay-full", "gameplay-keyboard-turn", "rod-pickup", "hallway", "power-room"]:
		var path := "res://scenarios/%s.json" % name
		var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
		var game := Game.new(0)
		var player := Player.build(game, null)
		player.scripted = true
		player.rod = Rod.build()
		player.adapter = InputPlane.ScriptedAdapter.new()
		root.add_child(player)
		player.set_physics_process(false)
		game.wake_state.mark_ready()
		var route := Route.new(player, int(scenario.max_frames))
		var cutoff := 1113 if name == "hallway" else 1256
		if name not in ["hallway", "power-room"]:
			cutoff = int(scenario.beats.back().tick) + 1
		route.replay_prefix(scenario.actions, cutoff)
		if name in ["hallway", "power-room"]:
			for beat: Dictionary in scenario.beats:
				if int(beat.tick) <= cutoff:
					route.beats.append(beat)
			route.corridor(name)
			scenario.actions = route.actions
			scenario.beats = route.beats
			FileAccess.open(path, FileAccess.WRITE).store_string(JSON.stringify(scenario, "\t") + "\n")
		assert(player.motion.rod_carried and game.door_open, "opening replay preserves rod and pry")
		print("ROUTE %s ticks=%d foot=%s" % [name, route.tick, player.motion.capsule().foot])
		player.rod.free()
		player.free()
	_build_connector()
	quit(0)

class CaptureRoute:
	extends "res://harness/connector_route.gd"
	var evidence := preload("res://harness/connector_evidence.gd").new()
	func step(offered: Array = []) -> void:
		super.step(offered)
		evidence.observe(player, tick, 0)

func _build_connector() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/power-room.json"))
	var game := Game.new(int(source.seed))
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	root.add_child(player)
	player.set_physics_process(false)
	game.wake_state.mark_ready()
	var route := CaptureRoute.new(player, 40000)
	route.journey()
	route.hold(3)
	var digest := route.evidence.finish_digest()
	for beat: Dictionary in route.beats:
		if beat.name in route.white_beats:
			beat.light = "white"
			if beat.name not in ["power-active", "hall-white"]:
				beat.camera_back = 3.0
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scenarios/connector-route.json"))
	assert(route.tick < int(data.max_frames), "connector route preserves its scenario budget")
	data.actions = route.actions
	data.beats = route.beats
	data.connector = {"digest": digest, "route_ticks": route.tick, "labels": route.label_beats, "white_beats": route.white_beats}
	FileAccess.open("res://scenarios/connector-route.json", FileAccess.WRITE).store_string(JSON.stringify(data, "\t") + "\n")
	print("CONNECTOR ROUTE ticks=%d budget=%d digest=%s" % [route.tick, data.max_frames, digest])
	for beat: Dictionary in route.beats:
		print("  %s %d" % [beat.name, beat.tick])
	player.free()
