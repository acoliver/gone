extends SimTestCase

func test_all_batch_finishes_are_built_distinct_and_cached() -> void:
	var count := QuartersProps.cache_size()
	for prop: StringName in QuartersSteelLibrary.PROPS:
		var clean := QuartersSteelLibrary.material(prop, &"as_built")
		var aged := QuartersSteelLibrary.material(prop, &"aged")
		assert_true(clean != aged, "distinct states: " + prop)
		for state: StringName in QuartersProps.STATES:
			var finish := QuartersSteelLibrary.material(prop, state)
			assert_true(finish == QuartersSteelLibrary.material(prop, state), "cached finish: " + prop)
			for kind: String in ["albedo", "normal", "orm"]:
				var texture: Texture2D = finish.get_shader_parameter("baked_" + kind)
				assert_true(texture != null and texture.get_width() >= 2048, "built atlas: %s/%s" % [prop, kind])
				assert_true(texture != clean.get_shader_parameter("baked_"+kind) if state == &"aged" else true, "state-specific atlas")
	assert_int_equal(QuartersProps.cache_size(), count, "candidate library cannot mutate pilot cache")
	assert_int_equal(QuartersSteelLibrary.cache_size(), 22, "one resource for each prop and state")

func test_accepted_library_props_use_the_public_cached_factory() -> void:
	for prop: StringName in QuartersSteelLibrary.ACCEPTED:
		assert_true(QuartersSteelLibrary.PROPS.has(prop), "accepted prop belongs to batch 1")
		var model := (load("res://assets/props/quarters/%s.glb" % prop) as PackedScene).instantiate() as Node3D
		for state: StringName in [&"as_built", &"aged", &"as_built"]:
			var finish := QuartersProps.material(prop, state)
			assert_true(finish == QuartersSteelLibrary.material(prop, state), "public factory shares library cache")
			QuartersProps.apply(model, prop, state)
			for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(part.mesh.get_surface_count()):
					var role := part.mesh.surface_get_material(surface).resource_name.to_lower()
					if not (role.contains("display") or role.contains("glass") or role == "screen"):
						assert_true(part.get_active_material(surface) == finish, "public state swap reaches every steel/fabric slot")
		model.free()

func test_state_swaps_preserve_geometry_and_display_glass() -> void:
	for prop: StringName in QuartersSteelLibrary.PROPS:
		var model := (load("res://assets/props/quarters/%s.glb" % prop) as PackedScene).instantiate() as Node3D
		var parts := model.find_children("*", "MeshInstance3D", true, false)
		assert_true(not parts.is_empty(), "fitted meshes exist: " + prop)
		var snapshots := {}
		for piece: MeshInstance3D in parts:
			snapshots[piece.name] = [piece.mesh, piece.transform, piece.get_aabb()]
		for state: StringName in [&"as_built", &"aged", &"as_built"]:
			QuartersSteelLibrary.apply(model, prop, state)
			for piece: MeshInstance3D in parts:
				var prior: Array = snapshots[piece.name]
				assert_true(piece.mesh == prior[0] and piece.transform == prior[1] and piece.get_aabb() == prior[2], "unchanged fitted geometry: " + piece.name)
				for surface: int in range(piece.mesh.get_surface_count()):
					var imported := piece.mesh.surface_get_material(surface)
					var role := imported.resource_name.to_lower()
					if role.contains("display") or role.contains("glass") or role == "screen":
						assert_true(piece.get_active_material(surface) == imported, "display/glass unchanged: " + prop)
					else:
						assert_true(piece.get_active_material(surface) == QuartersSteelLibrary.material(prop, state), "all steel/fabric surfaces routed: " + prop)
		model.free()

func test_library_imports_preserve_data_and_mips() -> void:
	for prop: StringName in QuartersSteelLibrary.PROPS:
		for state: StringName in QuartersProps.STATES:
			for kind: String in ["albedo", "normal", "orm"]:
				var settings := ConfigFile.new()
				var path := "res://assets/props/quarters/steel/%s/%s_%s.png.import" % [prop, state, kind]
				assert_int_equal(settings.load(path), OK, "explicit import: " + path)
				assert_false(settings.get_value("params", "process/fix_alpha_border"), "do not bleed colour by alpha")
				assert_true(settings.get_value("params", "mipmaps/generate"), "distant texture filtering")
				assert_int_equal(settings.get_value("params", "compress/mode"), 2, "bounded GPU storage")

func test_library_diagnostic_copy_cannot_contaminate_runtime_or_pilots() -> void:
	var locker := QuartersProps.material(&"storage_locker_module", &"aged")
	var sofa := QuartersProps.material(&"sofa", &"aged")
	var tunic := QuartersProps.material(&"dress_uniform", &"aged")
	var finish := QuartersSteelLibrary.material(&"desk", &"aged")
	var control := finish.duplicate() as ShaderMaterial
	control.set_shader_parameter(&"diagnostic", 2)
	assert_int_equal(finish.get_shader_parameter(&"diagnostic"), 0, "diagnostics stay local")
	assert_true(finish.shader != locker.shader and finish.shader != sofa.shader and finish.shader != tunic.shader, "pilot shading stays separate")
	assert_true(locker == QuartersProps.material(&"storage_locker_module", &"aged"), "pilot cache identity unchanged")

func test_live_display_overrides_survive_pure_and_mixed_mesh_swaps() -> void:
	for roles: Array in [["Display"], ["Display", "PaintedSteel"]]:
		var mesh := ArrayMesh.new()
		for role: String in roles:
			var source := StandardMaterial3D.new()
			source.resource_name = role
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, BoxMesh.new().surface_get_arrays(0))
			mesh.surface_set_material(mesh.get_surface_count()-1, source)
		var model := Node3D.new()
		var panel := MeshInstance3D.new()
		panel.mesh = mesh
		model.add_child(panel)
		var live_display := StandardMaterial3D.new()
		panel.material_override = live_display
		for state: StringName in [&"as_built", &"aged", &"as_built"]:
			QuartersSteelLibrary.apply(model, &"console", state)
			assert_true(panel.get_active_material(0) == live_display, "preserve a live display override")
			if roles.size() == 2:
				assert_true(panel.get_active_material(1) == QuartersSteelLibrary.material(&"console", state), "mixed steel slot swaps independently")
		model.free()
