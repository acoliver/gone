extends SimTestCase
## Port of the lib.rs ShipState inline test module.

func test_damage_reduces_hull_and_clamps_at_loss() -> void:
	var ship: Sim.ShipState = Sim.ShipState.new(10)
	assert_true(ship.is_intact(), "a fresh ship is intact")

	ship.apply_damage(4)
	assert_int_equal(ship.hull(), 6, "damage reduces hull")
	assert_true(ship.is_intact(), "still intact")

	ship.apply_damage(10)
	assert_int_equal(ship.hull(), 0, "damage clamps at total loss")
	assert_false(ship.is_intact(), "a zero-hull ship is not intact")
