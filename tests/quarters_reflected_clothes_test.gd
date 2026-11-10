extends SimTestCase

func test_reflected_single_sided_dresses_keep_imported_meshes_in_both_states() -> void:
	for state: StringName in QuartersProps.STATES:
		var room := QuartersFurnishings.build(state)
		var dresses := room.get_node("Placement_wardrobe/her_dresses") as Node3D
		var source := QuartersFurnishings._clothing("her_dresses", state)
		assert_true(dresses.basis.determinant() < 0, "layout reflection stays on clothing root")
		for piece: MeshInstance3D in dresses.find_children("*", "MeshInstance3D", true, false):
			var original := source.find_child(piece.name, true, false) as MeshInstance3D
			assert_true(piece.mesh == original.mesh, "explicit cloth plies need no two-sided draw correction: " + piece.name)
			assert_true(ShipScene._world_frame(piece).basis.determinant() < 0, "single-sided draw keeps furniture reflection")
			for surface: int in range(piece.mesh.get_surface_count()):
				var material := piece.get_active_material(surface) as BaseMaterial3D
				assert_true(material != null and material.cull_mode == BaseMaterial3D.CULL_BACK, "physical plies retain single-sided authored materials")
		source.free()
		room.free()

func test_reflection_preserves_world_vertices_normals_uvs_and_imported_materials() -> void:
	for state: StringName in QuartersProps.STATES:
		var room := QuartersFurnishings.build(state)
		var dresses := room.get_node("Placement_wardrobe/her_dresses") as Node3D
		var source := QuartersFurnishings._clothing("her_dresses", state)
		source.transform = dresses.transform
		_assert_preserved(dresses, source)
		source.free()
		room.free()

func test_two_sided_reflection_correction_preserves_geometry_and_is_idempotent() -> void:
	for state: StringName in QuartersProps.STATES:
		var source := QuartersFurnishings._clothing("her_dresses", state)
		source.basis = QuartersClothing.REFLECTION * Basis(Vector3.UP, -PI / 2)
		# Retain coverage for the previous two-sided import contract without
		# changing the shared imported material resources.
		for piece: MeshInstance3D in source.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(piece.mesh.get_surface_count()):
				var material := piece.get_active_material(surface).duplicate() as BaseMaterial3D
				material.cull_mode = BaseMaterial3D.CULL_DISABLED
				piece.set_surface_override_material(surface, material)
		var corrected := source.duplicate() as Node3D
		QuartersClothing.prepare(corrected)
		_assert_preserved(corrected, source)
		for piece: MeshInstance3D in corrected.find_children("*", "MeshInstance3D", true, false):
			assert_true(ShipScene._world_frame(piece).basis.determinant() > 0, "two-sided imported material sees correct front facing: " + piece.name)
			var mesh := piece.mesh
			var frame := piece.transform
			QuartersClothing.prepare(corrected)
			assert_true(piece.mesh == mesh and piece.transform == frame, "preparation is idempotent")
		corrected.free()
		source.free()

func _assert_preserved(actual_root: Node3D, source: Node3D) -> void:
	for piece: MeshInstance3D in actual_root.find_children("*", "MeshInstance3D", true, false):
		var original := source.find_child(piece.name, true, false) as MeshInstance3D
		var actual_frame := ShipScene._world_frame(piece)
		var source_frame := ShipScene._world_frame(original)
		assert_true(piece.mesh.get_surface_count() == original.mesh.get_surface_count(), "every physical ply and fibre surface retained")
		for surface: int in range(piece.mesh.get_surface_count()):
			var actual := piece.mesh.surface_get_arrays(surface)
			var expected := original.mesh.surface_get_arrays(surface)
			assert_true(piece.mesh.surface_get_array_index_len(surface) == original.mesh.surface_get_array_index_len(surface), "every triangle retained")
			assert_true(actual[Mesh.ARRAY_TEX_UV] == expected[Mesh.ARRAY_TEX_UV], "cloth UVs unchanged")
			assert_true(actual[Mesh.ARRAY_TEX_UV2] == expected[Mesh.ARRAY_TEX_UV2], "separate weave UVs unchanged")
			assert_true(piece.mesh.surface_get_material(surface) == original.mesh.surface_get_material(surface), "authored material resource retained")
			assert_true(piece.get_active_material(surface) == original.get_active_material(surface), "active material retained")
			for index: int in range(actual[Mesh.ARRAY_VERTEX].size()):
				assert_true((actual_frame * actual[Mesh.ARRAY_VERTEX][index]).distance_to(source_frame * expected[Mesh.ARRAY_VERTEX][index]) < 0.00001, "same world vertex")
				var normal: Vector3 = actual_frame.basis.inverse().transposed() * actual[Mesh.ARRAY_NORMAL][index]
				var wanted: Vector3 = source_frame.basis.inverse().transposed() * expected[Mesh.ARRAY_NORMAL][index]
				# ArrayMesh re-encodes octahedral normals on a 16-bit grid.
				assert_close(normal, wanted, "same world normal after packed-normal round trip")
