extends SimTestCase

func test_sofa_finishes_are_cached_distinct_and_complete() -> void:
	var clean := QuartersProps.material(&"sofa", &"as_built")
	var aged := QuartersProps.material(&"sofa", &"aged")
	assert_true(clean != aged, "sofa states use different shared resources")
	for state: StringName in [&"as_built", &"aged"]:
		var finish := QuartersProps.material(&"sofa", state)
		assert_true(finish == QuartersProps.material(&"sofa", state), "sofa cache shares each state")
		for kind: String in ["albedo", "normal", "orm", "masks", "nodust"]:
			var texture: Texture2D = finish.get_shader_parameter("baked_" + kind)
			assert_true(texture != null and texture.get_width() >= 2048, "sofa atlas exists: " + kind)
			assert_true(clean.get_shader_parameter("baked_" + kind) != aged.get_shader_parameter("baked_" + kind), "sofa state atlases differ: " + kind)

func test_both_sofa_mesh_states_receive_the_shared_finish_without_changing_pivots() -> void:
	for state: StringName in [&"as_built", &"aged"]:
		var scene: PackedScene = load("res://assets/props/quarters/sofa%s.glb" % ("_aged" if state == &"aged" else ""))
		var model := scene.instantiate() as Node3D
		var pieces := model.find_children("*", "MeshInstance3D", true, false)
		var meshes: Array = []
		var transforms: Array = []
		for piece: MeshInstance3D in pieces:
			meshes.append(piece.mesh)
			transforms.append(piece.transform)
		QuartersProps.apply(model, &"sofa", state)
		for index: int in range(pieces.size()):
			var piece := pieces[index] as MeshInstance3D
			assert_true(piece.mesh == meshes[index] and piece.transform == transforms[index], "materials preserve mesh and pivot")
			assert_true(piece.material_override == QuartersProps.material(&"sofa", state), "every surface uses the cached finish")
		for name: String in ["Frame", "Feet", "Rivets", "SeatCushion_C", "SeatCushion_L", "SeatCushion_R", "BackCushion_C", "BackCushion_L", "BackCushion_R", "Throw"]:
			assert_true(model.find_child(name, true, false) != null, "retained sofa part: " + name)
		model.free()

func test_sofa_construction_does_not_mutate_locker_material_or_mapping() -> void:
	var locker := (load("res://assets/props/quarters/storage_locker_module.glb") as PackedScene).instantiate() as Node3D
	QuartersProps.apply(locker, &"storage_locker_module", &"aged")
	var finish := QuartersProps.material(&"storage_locker_module", &"aged")
	var shader := finish.shader
	var parameters := {}
	for uniform: Dictionary in shader.get_shader_uniform_list():
		parameters[uniform.name] = finish.get_shader_parameter(uniform.name)
	var door := locker.find_child("Door", true, false) as MeshInstance3D
	var rectangle: Vector4 = door.get_instance_shader_parameter(&"face_rectangle")
	for state: StringName in [&"as_built", &"aged"]:
		QuartersProps.material(&"sofa", state)
	assert_true(finish == QuartersProps.material(&"storage_locker_module", &"aged"), "locker cache identity unchanged")
	assert_true(finish.shader == shader and finish.shader != QuartersProps.material(&"sofa", &"aged").shader, "locker shader is untouched")
	for parameter: String in parameters:
		assert_true(finish.get_shader_parameter(parameter) == parameters[parameter], "locker parameter unchanged: " + parameter)
	assert_true(door.get_instance_shader_parameter(&"face_rectangle") == rectangle, "locker mapping unchanged")
	locker.free()

func test_sofa_imports_preserve_transparency_and_mask_role_data() -> void:
	for state: String in ["as_built", "aged"]:
		for kind: String in ["albedo", "normal", "orm", "masks", "nodust"]:
			var settings := ConfigFile.new()
			assert_int_equal(settings.load("res://assets/props/quarters/sofa/%s_%s.png.import" % [state, kind]), OK, "explicit sofa import")
			assert_false(settings.get_value("params", "process/fix_alpha_border"), "packed roles and surviving cloth RGB stay independent of alpha")
			assert_true(settings.get_value("params", "mipmaps/generate"), "sofa uses minification mips")
