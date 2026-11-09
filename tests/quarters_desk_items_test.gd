extends SimTestCase

func test_desk_items_rest_on_worktop_clear_of_console_and_each_other() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var top := furnishings.get_node("Placement_desk/desk").find_child("Worktop", true, false) as MeshInstance3D
		var worktop := ShipScene._world_frame(top) * top.get_aabb()
		var console := QuartersFurnishings._bounds(furnishings.get_node("Placement_console/console"))
		var placed: Array[AABB] = []
		for id: String in ["medal_case", "data_tablet_2"]:
			var item := furnishings.get_node("Standin_" + id) as MeshInstance3D
			var bounds := ShipScene._world_frame(item) * item.get_aabb()
			assert_float_in_range(bounds.position.y - worktop.end.y, -0.00001, 0.002, "desk item rests on actual worktop: " + id)
			assert_false(bounds.grow(.02).intersects(console), "desk item clears console by 20 mm: " + id)
			assert_true(bounds.position.x >= worktop.position.x and bounds.end.x <= worktop.end.x and bounds.position.z >= worktop.position.z and bounds.end.z <= worktop.end.z, "desk item within worktop: " + id)
			for other: AABB in placed: assert_false(bounds.grow(.02).intersects(other), "desk items remain separated")
			placed.append(bounds)
			var finish := item.material_override as StandardMaterial3D
			assert_true(finish != null and absf(finish.albedo_color.r - finish.albedo_color.g) < .02 and absf(finish.albedo_color.g - finish.albedo_color.b) < .02, "neutral item stand-in: " + id)
		furnishings.free()
