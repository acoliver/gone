extends SimTestCase

func test_near_locker_stile_uses_the_adjacent_door_paint_at_matching_scale() -> void:
	var model := QuartersFurnishings.build(&"aged")
	var cabinet := model.get_node("Placement_storage_left_near/storage_locker_module")
	var door := cabinet.get_node("Door") as MeshInstance3D
	var stile := cabinet.get_node("Carcass/SurroundStile_R") as MeshInstance3D
	var door_rect: Vector4 = door.get_instance_shader_parameter(&"face_rectangle")
	var stile_rect: Vector4 = stile.get_instance_shader_parameter(&"face_rectangle")
	var door_size: Vector4 = door.get_instance_shader_parameter(&"face_size")
	var stile_size: Vector4 = stile.get_instance_shader_parameter(&"face_size")
	assert_true(stile.material_override == door.material_override, "frame and door keep the same aged steel material")
	assert_true(stile_rect.x > door_rect.z, "stile keeps its own padded, disjoint atlas slot")
	assert_true(door_size == Vector4(0.514, 2.22, 0, 0) and stile_size == Vector4(0.04, 2.18, 0, 0), "frame and door retain their physical dimensions")
	var mapping: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(QuartersProps.FACE_ROOT + "face-layout.json"))
	assert_true(String(mapping.faces["stile-right"].get("material_source", "")).begins_with("door image pixels"), "stile uses the adjacent door paint rather than its old striped source")
	assert_true(stile.get_instance_shader_parameter(&"face_projection") == Vector4(0, 1, 0.26, 0.21), "front-stile geometry and physical projection stay unchanged")
	model.free()
