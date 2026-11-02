extends SceneTree
## Regenerate the corridor tails from layout ids without changing the authored
## bay-local input schedules, beats or scenario budgets.
const Route := preload("res://harness/route.gd")

func _initialize() -> void:
	call_deferred("_build")

func _build() -> void:
	for name: String in ["gameplay-full", "gameplay-keyboard-turn", "rod-pickup", "hallway", "power-room"]:
		var path := "res://scenarios/%s.json" % name
		var scenario: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
		var game := Game.new()
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
	quit(0)
