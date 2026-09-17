extends SimTestCase
## Port of the power.rs inline test module.

func test_opening_grid_defaults_to_emergency() -> void:
	var grid := Power.Grid.new()
	assert_true(grid.state() == Power.State.EMERGENCY, "the opening grid is on emergency power")
	assert_true(grid.equals(Power.Grid.new()), "fresh grids agree")
	assert_true(Power.emergency_fixtures_lit(grid.state()), "the emergency fixtures are lit")

func test_cut_advances_emergency_to_dead_exactly_once() -> void:
	var grid := Power.Grid.new()
	assert_true(grid.cut_emergency_power().equals(Power.Transition.advanced(Power.State.EMERGENCY, Power.State.DEAD)), "the cut advances Emergency to Dead")
	assert_true(grid.state() == Power.State.DEAD, "the grid is Dead")
	assert_false(Power.emergency_fixtures_lit(grid.state()), "the fixtures are unlit")

func test_repeated_cuts_after_death_are_idempotent() -> void:
	var grid := Power.Grid.new()
	assert_true(grid.cut_emergency_power().kind == Power.Transition.Kind.ADVANCED, "the first cut advances")
	for _delivery: int in range(8):
		assert_true(grid.cut_emergency_power().equals(Power.Transition.unchanged(Power.State.DEAD)), "re-delivered cuts are no-ops")
		assert_true(grid.state() == Power.State.DEAD, "the grid holds Dead")

func test_dead_is_terminal_nothing_restores_power() -> void:
	var grid := Power.Grid.new()
	grid.cut_emergency_power()
	for _attempt: int in range(16):
		grid.cut_emergency_power()
		assert_true(grid.state() == Power.State.DEAD, "Dead is terminal")

func test_no_normal_lighting_state_is_reachable() -> void:
	var pending: Array[Power.Grid] = [Power.Grid.new()]
	var observed: Array[int] = []
	while not pending.is_empty():
		var grid: Power.Grid = pending.pop_back()
		if observed.has(grid.state()):
			continue
		observed.append(grid.state())
		if grid.state() == Power.State.EMERGENCY:
			assert_true(Power.emergency_fixtures_lit(grid.state()), "Emergency lights the emergency fixtures")
		else:
			assert_false(Power.emergency_fixtures_lit(grid.state()), "Dead lights nothing")
		var next := grid.copy()
		next.cut_emergency_power()
		pending.append(next)
	assert_int_equal(observed.size(), 2, "the reachable closure is the milestone state set")
	assert_true(observed.has(Power.State.EMERGENCY) and observed.has(Power.State.DEAD), "the closure is exactly Emergency and Dead")
	assert_true(Power.emergency_fixtures_lit(Power.State.EMERGENCY), "Emergency lights the fixtures")
	assert_false(Power.emergency_fixtures_lit(Power.State.DEAD), "Dead lights nothing")

func test_consumer_mirror_follows_sim_output_only() -> void:
	var grid := Power.Grid.new()
	var mirror: int = grid.state()
	assert_true(mirror == grid.state(), "the mirror starts aligned")
	var outcome := grid.cut_emergency_power()
	assert_true(outcome.kind == Power.Transition.Kind.ADVANCED, "the first cut from the opening grid must advance")
	mirror = outcome.to
	assert_true(mirror == grid.state(), "the mirror follows sim output")
	for _poll: int in range(3):
		var repeat := grid.cut_emergency_power()
		assert_true(repeat.equals(Power.Transition.unchanged(mirror)), "a no-op outcome reports exactly the mirrored state")
		assert_true(mirror == grid.state(), "the mirror never diverges")
