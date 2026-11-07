extends SimTestCase

func test_secondary_power_clears_density_in_480_ticks_without_respawn() -> void:
	var game := Game.new(71)
	var step := GameStep.new(game)
	for _tick in range(600):
		step.advance()
	assert_float_equal(game.ventilation.density(), 1.0, "unpowered bay keeps its smoke")
	step.advance()
	assert_float_equal(game.ventilation.density(), 1.0, "reading the inactive console does not ventilate")
	game.press_console()
	step.advance(true)
	assert_float_equal(game.ventilation.density(), 1.0, "paused clock cannot clear smoke")
	for tick in range(1, 481):
		step.advance()
		assert_float_equal(game.ventilation.density(), 1.0 - float(tick) / 480.0, "density follows fixed ticks")
	for _tick in range(1200):
		game.press_console()
		step.advance()
	assert_float_equal(game.ventilation.density(), 0.0, "powered bay stays clear")

func test_density_scales_exposure_and_cleared_bay_uses_hallway_recovery() -> void:
	var game := Game.new(71)
	var smoke := SmokeSymptoms.new(game.layout, game.ventilation)
	var hall := SmokeSymptoms.new(game.layout)
	var bay_position := game.layout.bay_to_world() * Vector3(0, 1.6, 0)
	var hall_position := game.layout.bay_to_world() * Vector3(7, 1.6, 0)
	for _tick in range(1080):
		smoke.tick(true, bay_position)
		hall.tick(true, bay_position)
	game.press_console()
	game.press_console()
	var step := GameStep.new(game)
	for _tick in range(240):
		step.advance()
	assert_float_equal(smoke.exposure_at(bay_position), 0.5, "exposure scales with density")
	assert_float_equal(smoke.exposure_at(game.layout.bay_to_world() * Vector3(5.75, 1.6, 0)), 0.25, "density preserves threshold taper")
	for _tick in range(240):
		step.advance()
	assert_float_equal(smoke.exposure_at(bay_position), 0.0, "ventilated bay has no exposure")
	for _tick in range(481):
		smoke.tick(true, bay_position)
		hall.tick(true, hall_position)
		assert_float_equal(smoke.dose(), hall.dose(), "bay and hallway use identical recovery")
	assert_float_equal(smoke.dose(), 0.0, "remaining in the cleared bay recovers symptoms")
	for _tick in range(600):
		smoke.tick(true, hall_position)
		smoke.tick(true, bay_position)
	assert_float_equal(smoke.dose(), 0.0, "returning cannot accumulate symptoms")
	assert_int_equal(smoke.drain_events().size(), 0, "no symptom events after recovery")

func test_single_tick_owner_advances_ventilation_before_exposure() -> void:
	var game := Game.new(71)
	var player := Player.build(game, null)
	player.scripted = true
	player._ready()
	var step := GameStep.new(game, player)
	step.smoke = SmokeSymptoms.new(game.layout, game.ventilation)
	game.phase.wake_complete()
	game.press_console()
	game.press_console()
	for _tick in range(480):
		step.advance()
	assert_float_equal(game.ventilation.density(), 0.0, "GameStep advances ventilation once per tick")
	assert_int_equal(step.smoke.sample().tick, 480, "symptoms share the logical clock")
	player.free()
