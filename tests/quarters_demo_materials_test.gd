extends SimTestCase

const QuartersRealFurnitureTest := preload("res://tests/quarters_real_furniture_test.gd")

func test_both_demo_states_use_routed_finishes_for_every_furniture_instance() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		assert_true(furnishings.name == ("Remembered" if state == &"as_built" else "Present"), "demo state selects finish state")
		for id: String in QuartersRealFurnitureTest.REPLACED:
			var prop := StringName(QuartersRealFurnitureTest.REPLACED[id])
			var asset := furnishings.get_node("Placement_%s/%s" % [id, prop])
			var finish := QuartersProps.material(prop, state)
			assert_true(finish == (QuartersProps._wardrobe_material(state) if prop == &"wardrobe" else QuartersSteelLibrary.material(prop, state)), "public routed finish: " + id)
			for piece: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(piece.mesh.get_surface_count()):
					var role := StringName(piece.mesh.surface_get_material(surface).resource_name)
					var expected: Material = finish
					if prop == &"bedside" and piece.name == &"LampLens":
						expected = QuartersProps.bedside_lens(state)
					elif role in [&"Display", &"Glass"]:
						expected = QuartersProps.interim_material(role, state)
					assert_true(piece.get_active_material(surface) == expected, "%s/%s/%s/%d uses routed finish" % [state, id, piece.name, surface])
		furnishings.free()

func test_demo_instances_share_cached_materials_without_cross_state_aliasing() -> void:
	var first := QuartersFurnishings.build(&"as_built")
	var second := QuartersFurnishings.build(&"as_built")
	var present := QuartersFurnishings.build(&"aged")
	var cache := QuartersSteelLibrary.cache_size()
	for id: String in QuartersRealFurnitureTest.REPLACED:
		var prop := StringName(QuartersRealFurnitureTest.REPLACED[id])
		var path := "Placement_%s/%s" % [id, prop]
		var clean := QuartersProps.material(prop, &"as_built")
		var aged := QuartersProps.material(prop, &"aged")
		assert_true(clean != aged, "states never alias: " + id)
		for root: Node3D in [first, second, present]:
			var expected := aged if root == present else clean
			for mesh: MeshInstance3D in root.get_node(path).find_children("*", "MeshInstance3D", true, false):
				for surface: int in range(mesh.mesh.get_surface_count()):
					var role := mesh.mesh.surface_get_material(surface).resource_name
					var state := &"aged" if root == present else &"as_built"
					var active: Material = expected
					if prop == &"bedside" and mesh.name == &"LampLens":
						active = QuartersProps.bedside_lens(state)
					elif role in ["Display", "Glass"]:
						active = QuartersProps.interim_material(StringName(role), state)
					assert_true(mesh.get_active_material(surface) == active, "instances share factory identity: " + id)
	assert_int_equal(QuartersSteelLibrary.cache_size(), cache, "repeated builds and lookups add no library resources")
	first.free()
	second.free()
	present.free()

func test_demo_build_preserves_every_pilot_material_and_parameter() -> void:
	for state: StringName in QuartersProps.STATES:
		var snapshots := {}
		for prop: StringName in [&"storage_locker_module", &"sofa", &"dress_uniform"]:
			var suffix := "_aged.glb" if state == &"aged" and prop != &"storage_locker_module" else ".glb"
			var path := QuartersFurnishings.ROOT + String(prop) + suffix
			var reference := (load(path) as PackedScene).instantiate() as Node3D
			QuartersProps.apply(reference, prop, state)
			var parts := {}
			for mesh: MeshInstance3D in reference.find_children("*", "MeshInstance3D", true, false):
				var slots := []
				for surface: int in range(mesh.mesh.get_surface_count()):
					var finish := mesh.get_active_material(surface) as ShaderMaterial
					var parameters := {}
					for parameter: Dictionary in finish.shader.get_shader_uniform_list():
						parameters[parameter.name] = finish.get_shader_parameter(parameter.name)
					slots.append([finish, parameters])
				parts[mesh.name] = slots
			snapshots[path] = parts
			reference.free()
		var furnishings := QuartersFurnishings.build(state)
		var seen := {}
		for asset: Node3D in furnishings.find_children("*", "Node3D", true, false):
			if not snapshots.has(asset.scene_file_path): continue
			seen[asset.scene_file_path] = true
			for mesh: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				var slots: Array = snapshots[asset.scene_file_path][mesh.name]
				for surface: int in range(mesh.mesh.get_surface_count()):
					var finish := mesh.get_active_material(surface) as ShaderMaterial
					assert_true(finish == slots[surface][0], "pilot factory identity unchanged: " + String(mesh.name))
					for parameter: String in slots[surface][1]:
						assert_true(finish.get_shader_parameter(parameter) == slots[surface][1][parameter], "pilot parameter unchanged: " + parameter)
		assert_int_equal(seen.size(), 3, "locker, sofa and tunic all exercised")
		furnishings.free()

func test_routed_shaders_keep_opaque_front_back_and_reflected_seal_queries() -> void:
	for prop: StringName in QuartersSteelLibrary.PROPS:
		for state: StringName in QuartersProps.STATES:
			var piece := HatchModel.mesh_piece(QuadMesh.new(), Transform3D.IDENTITY, 4, QuartersProps.material(prop, state))
			for reflected: bool in [false, true]:
				piece.basis = Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD) if reflected else Basis.IDENTITY
				var front := Vector3.FORWARD if reflected else Vector3.BACK
				var faces := PackedVector3Array()
				HatchRenderFaces.collect(piece, front, 4, faces)
				assert_int_equal(faces.size(), 6, "opaque routed shader draws transformed front: %s/%s" % [prop, state])
				faces.clear()
				HatchRenderFaces.collect(piece, -front, 4, faces)
				assert_true(faces.is_empty(), "routed shader cannot seal from its back: %s/%s" % [prop, state])
			piece.free()
