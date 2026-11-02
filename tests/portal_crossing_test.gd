extends SimTestCase

func test_oriented_finite_aperture_and_permissions() -> void:
	var door := ShipLayout.authored().layout.door(ShipLayout.BAY_DOOR_ID)
	var inside := Vector3(15, 0.305, 1.71)
	var hall := Vector3(15, 0.305, 1.49)
	assert_true(PortalCrossing.exits(inside, hall, door, 14, true, true), "crosses whole wall band")
	assert_false(PortalCrossing.exits(hall, inside, door, 14, true, true), "return does not exit")
	assert_false(PortalCrossing.exits(inside, Vector3(15, 0.305, 1.6), door, 14, true, true), "bay face alone does not cross hall face")
	assert_false(PortalCrossing.exits(inside, hall, door, 14, true, false), "closed passage")
	assert_false(PortalCrossing.exits(inside, hall, door, 13, true, true), "wrong deck")
	assert_false(PortalCrossing.exits(inside, hall, door, 14, false, true), "not walking")
	assert_false(PortalCrossing.exits(inside + Vector3.RIGHT, hall + Vector3.RIGHT, door, 14, true, true), "infinite plane outside aperture")
	assert_false(PortalCrossing.exits(inside + Vector3.UP * 5.5, hall + Vector3.UP * 5.5, door, 14, true, true), "other floor")

func test_game_latches_physical_exit_once_not_opening() -> void:
	var game := Game.new()
	game.open_doorway()
	assert_false(game.bay_exited, "opening is not crossing")
	game.observe_bay_crossing(Vector3(15, 0.305, 1.7), Vector3(15, 0.305, 1.49), true)
	assert_true(game.bay_exited, "accepted exit latches")
	game.observe_bay_crossing(Vector3(15, 0.305, 1.49), Vector3(15, 0.305, 1.7), true)
	assert_true(game.bay_exited, "return retains first exit")
