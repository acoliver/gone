extends SceneTree

func _initialize() -> void:
	call_deferred("_build")

func _build() -> void:
	var game := Game.new(114)
	var player := Player.build(game, null)
	player.scripted = true
	player.adapter = InputPlane.ScriptedAdapter.new()
	player._ready()
	DemoStart.quarters(game, player)
	var route := QuartersRoute.new(player, 10000)
	route.compile()
	var scenario := {
		"name": "quarters-demo", "seed": 114, "ticks_per_second": 60,
		"mode": "capture", "content": "gameplay", "start": "quarters",
		"logical_steps_per_present": 4, "max_frames": route.tick + 100,
		"actions": route.actions, "beats": route.beats,
	}
	var file := FileAccess.open("res://scenarios/quarters-demo.json", FileAccess.WRITE)
	assert(file != null, "quarters scenario output")
	file.store_string(JSON.stringify(scenario, "\t"))
	file.close()
	print("QUARTERS SCENARIO ticks=%d actions=%d beats=%d" % [route.tick, route.actions.size(), route.beats.size()])
	player.free()
	quit()
