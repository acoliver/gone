class_name QuartersRoute
extends HarnessRoute

func compile() -> void:
	hold(20)
	beat("corridor-door")
	press()
	hold(49)
	assert(player.game.doors.snapshot(QuartersLayout.DOOR).state == Doors.State.OPEN, "manual release through ordinary input")
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, 0.6)))
	hold(20)
	assert(player.game.quarters.state == QuartersMemory.State.REMEMBERED, "accepted doorway crossing remembers")
	beat("remembered-doorway")
	beats.back().quarters_view = "doorway"
	beat("remembered-wide")
	beats.back().quarters_view = "wide"
	beat("remembered-console")
	beats.back().quarters_view = "console"
	beat("remembered-bed")
	beats.back().quarters_view = "bed"
	for view: String in ["bedside", "table", "desk", "boots"]:
		beat("remembered-" + view)
		beats.back().quarters_view = view
	_console_path()
	look_at(QuartersLayout.console_frame().origin, -8)
	press()
	assert(player.game.quarters.state == QuartersMemory.State.PLAYING, "console through existing interaction dispatch")
	beat("console-corruption")
	beats.back().quarters_view = "console"
	hold(QuartersMemory.CORRUPT_TICKS)
	beat("console-message")
	beats.back().quarters_view = "console"
	hold(QuartersMemory.MESSAGE_TICKS)
	beat("console-fault")
	beats.back().quarters_view = "console"
	hold(QuartersMemory.FAULT_TICKS)
	assert(player.game.quarters.state == QuartersMemory.State.PRESENT, "tick-driven memory completion")
	_doorway_path()
	beat("present-doorway")
	beats.back().quarters_view = "doorway"
	beat("present-wide")
	beats.back().quarters_view = "wide"
	beat("present-console")
	beats.back().quarters_view = "console"
	beat("present-bed")
	beats.back().quarters_view = "bed"
	for view: String in ["bedside", "table", "desk", "boots"]:
		beat("present-" + view)
		beats.back().quarters_view = view
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, -0.6)))
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, 0.6)))
	assert(player.game.quarters.state == QuartersMemory.State.PRESENT, "re-entry remains present")
	hold(5)

func _console_path() -> void:
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, 3.1)))
	walk_to(QuartersLayout.to_world(Vector3(6.2, 0.305, 3.1)))
	walk_to(QuartersLayout.to_world(Vector3(6.2, 0.305, 2)))

func _doorway_path() -> void:
	walk_to(QuartersLayout.to_world(Vector3(6.2, 0.305, 3.1)))
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, 3.1)))
	walk_to(QuartersLayout.to_world(Vector3(4, 0.305, 0.6)))
