extends SimTestCase

func test_desk_items_rest_on_worktop_clear_of_console_and_each_other() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var top := furnishings.get_node("Placement_desk/desk").find_child("Worktop", true, false) as MeshInstance3D
		var worktop := ShipScene._world_frame(top) * top.get_aabb()
		var console := QuartersFurnishings._bounds(furnishings.get_node("Placement_console/console"))
		var placed: Array[AABB] = []
		for id: String in ["medal_case", "data_tablet_2"]:
			var item := furnishings.get_node("Item_" + id) as Node3D
			var bounds := QuartersFurnishings._bounds(item)
			assert_float_in_range(bounds.position.y - worktop.end.y, -0.00001, 0.002, "desk item rests on actual worktop: " + id)
			assert_false(bounds.grow(.02).intersects(console), "desk item clears console by 20 mm: " + id)
			assert_true(bounds.position.x >= worktop.position.x and bounds.end.x <= worktop.end.x and bounds.position.z >= worktop.position.z and bounds.end.z <= worktop.end.z, "desk item within worktop: " + id)
			for other: AABB in placed: assert_false(bounds.grow(.02).intersects(other), "desk items remain separated")
			placed.append(bounds)
			for mesh: MeshInstance3D in item.find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(mesh.mesh.get_surface_count()):
					assert_true(mesh.get_active_material(surface) == mesh.mesh.surface_get_material(surface), "authored item material: " + id)
		furnishings.free()
