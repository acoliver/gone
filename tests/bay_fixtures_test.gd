extends SimTestCase

func test_bay_fixture_frames_have_independent_local_and_world_pins() -> void:
	var layout := ShipLayout.authored().layout
	var bay := layout.bay()
	var lights := bay.regular_light_frames()
	var vents := bay.ceiling_vent_frames()
	# Six strips occupy service openings, 100 mm below the rails because their 1.15 m housing is 5 mm wider than the 1.145 m opening.
	var local_lights := [Vector3(-4.2, 3.02, -1.5), Vector3(-4.2, 3.02, 1.5), Vector3(-0.6, 3.02, -1.5), Vector3(-0.6, 3.02, 1.5), Vector3(4.2, 3.02, -1.5), Vector3(4.2, 3.02, 1.5)]
	var world_lights := [Vector3(13.5, 3.02, 11.9), Vector3(16.5, 3.02, 11.9), Vector3(13.5, 3.02, 8.3), Vector3(16.5, 3.02, 8.3), Vector3(13.5, 3.02, 3.5), Vector3(16.5, 3.02, 3.5)]
	var local_vents := [Vector3(-3, 3.05, 0), Vector3(3, 3.05, 0)]
	var world_vents := [Vector3(15, 3.05, 10.7), Vector3(15, 3.05, 4.7)]
	assert_int_equal(lights.size(), 6, "six ordered regular fixtures")
	assert_int_equal(vents.size(), 2, "two ordered ceiling vents")
	for frame: Transform3D in lights:
		var housing_top: float = frame.origin.y + 0.012 + Hallway.REGULAR_LENS_SIZE.y / 2.0
		assert_true(housing_top < 3.12 - 0.055 / 2.0, "lowered light housing clears the carrier-rail underside")
	for collection: int in range(2):
		var frames: Array = lights if collection == 0 else vents
		var locals: Array = local_lights if collection == 0 else local_vents
		var worlds: Array = world_lights if collection == 0 else world_vents
		for index: int in range(frames.size()):
			assert_close(frames[index].origin, locals[index], "local anchor %d/%d" % [collection, index])
			assert_true(frames[index].basis == Basis.IDENTITY, "local fixture orientation")
			var world: Transform3D = layout.bay_to_world() * frames[index]
			assert_close(world.origin, worlds[index], "world anchor %d/%d" % [collection, index])
			assert_true(world.basis == Basis(Vector3.FORWARD, Vector3.UP, Vector3.RIGHT), "world fixture orientation")
	lights.clear()
	vents.clear()
	assert_int_equal(bay.regular_light_frames().size(), 6, "fixture frames cannot be mutated by consumers")
	assert_int_equal(bay.ceiling_vent_frames().size(), 2, "vent frames cannot be mutated by consumers")

func test_presenters_use_bay_fixture_frames_under_one_transform() -> void:
	var game := Game.new(0)
	var bay := game.layout.bay()
	var root := Node3D.new()
	root.transform = game.layout.bay_to_world()
	var lighting := Lighting.build(game)
	var hazards := Hazards.build(game.ventilation, bay)
	root.add_child(lighting)
	root.add_child(hazards)
	var frames: Array = bay.regular_light_frames()
	for index: int in range(frames.size()):
		var fixture: Node3D = lighting.white_lights()[index].get_parent()
		assert_true(fixture.transform == frames[index], "regular fixture consumes local frame")
		assert_true(root.transform * lighting.transform * fixture.transform == game.layout.bay_to_world() * frames[index], "regular fixture transformed once")
		assert_close(lighting.white_lights()[index].position, Vector3(0, -0.12, 0), "light mesh-relative offset unchanged")
	frames = bay.ceiling_vent_frames()
	for index: int in range(frames.size()):
		assert_true(hazards._vents[index].transform == frames[index], "vent consumes local frame")
		assert_true(root.transform * hazards.transform * hazards._vents[index].transform == game.layout.bay_to_world() * frames[index], "vent transformed once")
	root.free()
