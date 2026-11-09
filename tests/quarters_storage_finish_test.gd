extends SimTestCase

func test_storage_standins_share_the_real_furniture_steel_in_both_states() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var count := 0
		for mesh: MeshInstance3D in furnishings.find_children("Standin_storage_*", "MeshInstance3D", true, false):
			count += 1
			assert_true(mesh.material_override == QuartersProps.interim_material(&"PaintedSteel", state), "storage steel matches real furniture: " + String(mesh.name))
			if state == &"aged":
				assert_true(mesh.get_instance_shader_parameter(&"floor_datum") == QuartersLayout.FLOOR_Y, "aged stand-in uses room floor")
				assert_true(mesh.get_instance_shader_parameter(&"lateral_bounds") == Vector4(41, 49, 1.7, 7.7), "aged stand-in uses room weather bounds")
		assert_true(count > 0, "remaining drawer, shelf and infill stand-ins covered")
		furnishings.free()
