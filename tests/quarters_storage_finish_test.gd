extends SimTestCase

func test_storage_standins_share_the_real_furniture_steel_in_both_states() -> void:
	var layout: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(QuartersProps.FACE_ROOT + "face-layout.json"))
	var front: Array = layout.faces.door.uv_rectangle
	var top: Array = layout.faces.top.uv_rectangle
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var count := 0
		for mesh: MeshInstance3D in furnishings.find_children("Standin_storage*", "MeshInstance3D", true, false):
			count += 1
			assert_true(mesh.material_override == QuartersProps.storage_material(state), "storage steel is shared and cached: " + String(mesh.name))
			if state == &"as_built":
				assert_true(mesh.material_override == QuartersProps.interim_material(&"PaintedSteel", state), "remembered storage paint stays unchanged")
			else:
				var bounds := mesh.get_aabb()
				assert_true(mesh.material_override.get_shader_parameter(&"face_albedo") == QuartersProps.FACE_ALBEDO, "storage uses the accepted pilot face images")
				assert_true(mesh.material_override.get_shader_parameter(&"face_orm") == QuartersProps.FACE_ORM, "storage preserves pilot roughness")
				assert_true(mesh.get_instance_shader_parameter(&"local_low") == Vector4(bounds.position.x, bounds.position.y, bounds.position.z, 0), "aged projection starts at the actual box bounds")
				assert_true(mesh.get_instance_shader_parameter(&"local_size") == Vector4(bounds.size.x, bounds.size.y, bounds.size.z, 0), "aged projection spans each whole box face")
				assert_true(mesh.get_instance_shader_parameter(&"projection") == Vector4(2, 0, 1, 0), "all box normals select broad faces, not panel-edge strips")
				assert_true(mesh.get_instance_shader_parameter(&"face_front") == Vector4(front[0], front[1], front[2], front[3]), "vertical storage faces use the pilot door source")
				assert_true(mesh.get_instance_shader_parameter(&"face_dust") == Vector4(top[0], top[1], top[2], top[3]), "horizontal storage faces receive pilot settled dust")
				assert_true(2240.0 / bounds.size.y >= 600 and 512.0 / maxf(bounds.size.x, bounds.size.z) >= 600, "source density stays above 600 px/m in both directions")
		assert_true(count > 0, "remaining drawer, shelf and infill stand-ins covered")
		furnishings.free()
