extends SimTestCase

func test_bay_fixture_frames_have_independent_local_and_world_pins() -> void:
	var layout := ShipLayout.authored().layout
	var bay := layout.bay()
	var lights := bay.regular_light_frames()
	var vents := bay.ceiling_vent_frames()
	# The generated fixture mounts to the sealed ceiling plane while retaining each authored local frame.
	var local_lights := [Vector3(-4.2, 3.12, -1.5), Vector3(-4.2, 3.12, 1.5), Vector3(-0.6, 3.12, -1.5), Vector3(-0.6, 3.12, 1.5), Vector3(4.2, 3.12, -1.5), Vector3(4.2, 3.12, 1.5)]
	var world_lights := [Vector3(13.5, 3.12, 11.9), Vector3(16.5, 3.12, 11.9), Vector3(13.5, 3.12, 8.3), Vector3(16.5, 3.12, 8.3), Vector3(13.5, 3.12, 3.5), Vector3(16.5, 3.12, 3.5)]
	var local_vents := [Vector3(-3, 3.05, 0), Vector3(3, 3.05, 0)]
	var world_vents := [Vector3(15, 3.05, 10.7), Vector3(15, 3.05, 4.7)]
	assert_int_equal(lights.size(), 6, "six ordered regular fixtures")
	assert_int_equal(vents.size(), 2, "two ordered ceiling vents")
	var asset := CeilingFixture.ASSET.instantiate() as Node3D
	var asset_bounds: Array[AABB] = []
	_collect_mesh_bounds(asset, Transform3D.IDENTITY, asset_bounds)
	asset.free()
	assert_true(not asset_bounds.is_empty(), "generated fixture exposes rendered geometry")
	var housing := asset_bounds[0]
	for bounds: AABB in asset_bounds.slice(1): housing = housing.merge(bounds)
	assert_close(housing.size, Vector3(1.1, 0.1, 0.22), "fixture clearance uses the generated beam bounds")
	for frame: Transform3D in lights:
		var mount := frame
		mount.origin.y = Pods.ROOM_CEILING_HEIGHT
		var bounds := mount * housing
		assert_float_in_range(bounds.position.y, 3.0999, 3.1001, "generated fixture underside clears the seated panel grid")
		assert_float_in_range(bounds.end.y, 3.1999, 3.2001, "generated fixture top meets the unchanged ceiling plane")
	var panel_cells: Dictionary = {}
	for row: Dictionary in BayCeiling.layout(): panel_cells[row.cell] = true
	for frame: Transform3D in lights:
		var cell := Vector2i(roundi((frame.origin.x + 5.4) / BayCeiling.CELL_X), roundi((frame.origin.z + 3.3) / BayCeiling.CELL_Z))
		assert_false(panel_cells.has(cell), "each generated beam reserves its fitted cassette aperture instead of an obscuring panel: %s" % cell)
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

func _collect_mesh_bounds(node: Node, parent: Transform3D, bounds: Array[AABB]) -> void:
	var pose := parent
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D:
		var mesh_node := node as MeshInstance3D
		bounds.append(pose * mesh_node.mesh.get_aabb())
	for child: Node in node.get_children(): _collect_mesh_bounds(child, pose, bounds)
