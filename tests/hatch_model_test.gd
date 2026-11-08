extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-000-H-FORE", &"D14-C-000-H-AFT", &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]

func test_exported_local_recipes_ignore_world_translation_without_mutating_specs() -> void:
	var exporter: GDScript = load("res://tools/export_hatch_parts.gd")
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var source := layout.door(id)
		var original_frame := source.frame()
		var relocated := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D(Basis(Vector3.UP, PI / 2), Vector3(100000, -10000, 400000)), source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
		var original: Dictionary = exporter.variant(source, 0)
		var moved: Dictionary = exporter.variant(relocated, 0)
		assert_true(JSON.stringify(original) == JSON.stringify(moved), "every exported part, fixed pose and rivet station is independent of world placement: " + String(id))
		assert_true(source.frame() == original_frame, "export never mutates authored records")

func test_baked_reflections_keep_front_faces_and_do_not_mutate_source_arrays() -> void:
	var source := HatchModel.box_mesh(Vector3.ONE)
	var original := source.surface_get_arrays(0).duplicate(true)
	var mirror := Transform3D(Basis.from_scale(Vector3(-1, 1, 1)), Vector3(3, 4, 5))
	var arrays := HatchAsset.transformed_arrays(source, mirror)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	for index: int in range(0, indices.size(), 3):
		var normal := (vertices[indices[index + 2]] - vertices[indices[index]]).cross(vertices[indices[index + 1]] - vertices[indices[index]]).normalized()
		for corner: int in range(3): assert_true(normal.dot(normals[indices[index + corner]]) > 0.999999, "baked reflections retain outward-facing imported triangles")
	var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
	for index: int in range(0, tangents.size(), 4):
		assert_float_equal(tangents[index + 3], -original[Mesh.ARRAY_TANGENT][index + 3], "baked reflections flip tangent-space handedness")
	assert_true(arrays[Mesh.ARRAY_TEX_UV] == original[Mesh.ARRAY_TEX_UV], "baking reflections preserves every UV")
	assert_true(source.surface_get_arrays(0) == original, "baking never mutates shared imported source arrays")
	var unmirrored := HatchAsset.transformed_arrays(source, Transform3D.IDENTITY)
	assert_true(unmirrored[Mesh.ARRAY_INDEX] == original[Mesh.ARRAY_INDEX], "proper transforms preserve imported winding")

func test_front_cap_ordering_preserves_each_indexed_attribute_and_source_mesh() -> void:
	var source := HatchModel.box_mesh(Vector3.ONE)
	var original := source.surface_get_arrays(0).duplicate(true)
	var arrays := original.duplicate(true)
	HatchAsset._front_cap_first(arrays)
	assert_true(arrays[Mesh.ARRAY_NORMAL][0].z < -0.999999, "front-cap ordering places the exposed normal first")
	assert_int_equal(arrays[Mesh.ARRAY_INDEX].size(), original[Mesh.ARRAY_INDEX].size(), "front-cap ordering retains every triangle")
	for index: int in range(original[Mesh.ARRAY_INDEX].size()):
		var before: int = original[Mesh.ARRAY_INDEX][index]
		var after: int = arrays[Mesh.ARRAY_INDEX][index]
		for channel: int in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_TEX_UV]:
			assert_true(arrays[channel][after] == original[channel][before], "front-cap ordering preserves indexed geometry, normals and UVs")
		for component: int in range(4):
			assert_float_equal(arrays[Mesh.ARRAY_TANGENT][after * 4 + component], original[Mesh.ARRAY_TANGENT][before * 4 + component], "front-cap ordering preserves tangent-space attributes")
	assert_true(source.surface_get_arrays(0) == original, "front-cap ordering never mutates the shared source mesh")

func test_runtime_imported_triangle_counts_match_the_producer_manifest() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [IDS[3], IDS[4]]:
		var spec := layout.door(id)
		var variant := HatchAsset.variant(spec)
		var view := DoorView.build(spec)
		var expected := int(HatchAsset.document().measurements.triangles_per_variant[str(int(variant.index))])
		assert_int_equal(_imported_triangles(view), expected, "actual imported and instanced geometry matches the freshly built asset: " + String(id))
		view.free()

func _imported_triangles(node: Node) -> int:
	var source: Mesh
	var instances := 1
	if node is MeshInstance3D: source = node.mesh
	elif node is MultiMeshInstance3D:
		source = node.multimesh.mesh
		instances = node.multimesh.instance_count
	var triangles := 0
	if source != null and source.get_meta(&"imported_source", "") == HatchAsset.SOURCE:
		for surface: int in range(source.get_surface_count()):
			var indices: PackedInt32Array = source.surface_get_arrays(surface)[Mesh.ARRAY_INDEX]
			assert_true(indices.size() % 3 == 0, "imported triangle surfaces have complete index triplets")
			triangles += int(indices.size() / 3) * instances
	for child: Node in node.get_children(): triangles += _imported_triangles(child)
	return triangles

func _leaf_parts(node: Node3D, pose: Transform3D, result: Dictionary) -> void:
	pose *= node.transform
	if node is MeshInstance3D:
		assert_true(node.mesh.get_meta(&"imported_source", "") == "res://assets/props/hatch/hatch.glb", "leaf mesh comes from the shared Blender asset: " + String(node.name))
		var transforms: Dictionary = node.mesh.get_meta(&"part_transforms", {})
		var parts: Dictionary = preload("res://tests/hatch_mesh_ranges.gd").parts(node.mesh)
		for id: StringName in parts:
			assert_true(transforms.has(id), "imported range has a simulation reservation")
			var local: Transform3D = transforms[id]
			result[id] = {"pose": pose * local, "bounds": parts[id].bounds}
	if node is MultiMeshInstance3D:
		assert_true(node.multimesh.mesh.get_meta(&"imported_source", "") == "res://assets/props/hatch/hatch.glb", "rivet instances use the imported mesh")
		var transforms: Array = node.multimesh.get_meta(&"instance_poses")
		for index: int in range(transforms.size()):
			result[StringName("%s/%03d" % [node.name, index])] = {"pose": pose * transforms[index], "bounds": node.multimesh.mesh.get_aabb()}
	for child: Node3D in node.get_children(): _leaf_parts(child, pose, result)

func test_imported_leaf_parts_fit_each_reservation_through_the_full_swing() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var imported: Dictionary = {}
		_leaf_parts(view.label_leaf(), Transform3D.IDENTITY, imported)
		var reservations: Dictionary = {}
		for group: HatchParts.Group in HatchParts.leaf(spec):
			for part: HatchParts.Part in group.parts:
				reservations[part.id] = {"pose": group.transform * part.transform, "bounds": AABB(-part.size / 2, part.size)}
		assert_int_equal(imported.size(), reservations.size(), "every physical part is imported once")
		var angles: Array[float] = []
		for degree: int in range(131): angles.append(signf(spec.swing_radians()) * deg_to_rad(degree))
		for seed: int in [0, 7, -913]: angles.append(spec.swing_radians(seed))
		for angle: float in angles:
			var hinge := spec.hinge_frame()
			hinge.basis = Basis(Vector3.UP, angle)
			for part_id: StringName in imported:
				assert_true(reservations.has(part_id), "imported part is simulation-owned: " + String(part_id))
				if not reservations.has(part_id): continue
				var actual: AABB = spec.frame() * hinge * imported[part_id].pose * imported[part_id].bounds
				var reserved: AABB = spec.frame() * hinge * reservations[part_id].pose * reservations[part_id].bounds
				assert_true(reserved.grow(0.001).encloses(actual), "%s part %s at %.3f degrees stays inside its 1mm reservation" % [id, part_id, rad_to_deg(angle)])
		view.free()

func test_imported_frame_meshes_fit_their_fixed_reservations() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var solids: Dictionary = {}
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec): solids[String(solid.id).trim_prefix(String(id) + "/")] = solid
		var checked := _frame_parts(view, spec.frame().affine_inverse(), solids)
		assert_true(checked >= solids.size(), "all fixed solid reservations have imported geometry")
		view.free()

func _frame_parts(node: Node3D, inverse: Transform3D, solids: Dictionary) -> int:
	var checked := 0
	if node is MeshInstance3D and node.has_meta(&"hatch_reservation"):
		var id: String = node.get_meta(&"hatch_reservation")
		assert_true(solids.has(id), "fixed imported mesh matches a simulation solid")
		assert_true(node.mesh.get_meta(&"imported_source", "") == "res://assets/props/hatch/hatch.glb", "fixed mesh uses the Blender asset")
		if solids.has(id):
			var solid: ShipGeometry.SolidSpec = solids[id]
			var relative := solid.transform.affine_inverse() * Surfaces.world_frame(node)
			for surface: int in range(node.mesh.get_surface_count()):
				var vertices: PackedVector3Array = node.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
				for vertex: Vector3 in vertices:
					assert_true(AABB(-solid.size / 2, solid.size).grow(0.001).has_point(relative * vertex), "fixed mesh vertex stays inside its 1mm reservation: " + id)
		checked += 1
	if node is MeshInstance3D and node.mesh.has_meta(&"hatch_reservations"):
		checked += _batched_frame_parts(node, inverse, solids)
	for child: Node3D in node.get_children(): checked += _frame_parts(child, inverse, solids)
	return checked


func _batched_frame_parts(node: MeshInstance3D, inverse: Transform3D, solids: Dictionary) -> int:
	assert_true(node.mesh.get_meta(&"imported_source", "") == "res://assets/props/hatch/hatch.glb", "batched fixed meshes use the Blender asset")
	assert_int_equal(node.mesh.get_surface_count(), 1, "shared fixed atlas uses one draw per mask")
	var reservations: Dictionary = node.mesh.get_meta(&"hatch_reservations")
	var arrays := node.mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var vertex_end := 0
	var index_end := 0
	for id: String in reservations:
		assert_true(solids.has(id), "batched fixed range matches a named simulation solid")
		if not solids.has(id): continue
		var reservation: Dictionary = reservations[id]
		var solid: ShipGeometry.SolidSpec = solids[id]
		var local: Transform3D = reservation.transform
		var parent := Transform3D(inverse.basis * solid._parent.basis, Vector3(0, 0, ShipLayout.WALL if "/SURROUND/AFT/" in String(solid.id) else 0.0))
		var expected := parent * Transform3D(Basis(solid._local_rotation), solid._local_center)
		assert_true(expected.origin.distance_to(local.origin) < 1e-6, "batched fixed part keeps the original local recipe pose: %s expected=%s imported=%s drift_m=%.9f" % [id, expected.origin, local.origin, expected.origin.distance_to(local.origin)])
		for axis: int in range(3): assert_true(expected.basis[axis].distance_to(local.basis[axis]) < 1e-6, "batched fixed part keeps its original basis")
		assert_int_equal(reservation.vertex_start, vertex_end, "reservation vertex ranges are complete and nonoverlapping")
		assert_int_equal(reservation.index_start, index_end, "reservation triangle ranges are complete and nonoverlapping")
		vertex_end += int(reservation.vertex_count)
		index_end += int(reservation.index_count)
		assert_true(reservation.vertex_count > 0 and reservation.index_count > 0 and int(reservation.index_count) % 3 == 0, "every reservation has complete imported triangles")
		var relative := solid.transform.affine_inverse() * Surfaces.world_frame(node)
		for index: int in range(int(reservation.vertex_start), vertex_end):
			assert_true(AABB(-solid.size / 2, solid.size).grow(0.001).has_point(relative * vertices[index]), "batched fixed vertex stays inside its 1mm reservation: " + id)
		for index: int in range(int(reservation.index_start), index_end):
			assert_true(indices[index] >= int(reservation.vertex_start) and indices[index] < vertex_end, "each imported triangle stays within its original part range")
		for index: int in range(int(reservation.index_start), index_end, 3):
			var normal := (vertices[indices[index + 2]] - vertices[indices[index]]).cross(vertices[indices[index + 1]] - vertices[indices[index]]).normalized()
			for corner: int in range(3): assert_true(normal.dot(normals[indices[index + corner]]) > 0.999999, "batched imported fixed faces retain flat outward normals: " + id)
	assert_int_equal(vertex_end, vertices.size(), "all batched vertices have checked reservations")
	assert_int_equal(index_end, indices.size(), "all batched triangles have checked reservations")
	return reservations.size()

func test_imported_frame_covers_every_named_solid_not_just_the_total_count() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var covered: Dictionary = {}
		_fixed_ids(view, covered)
		var solids := ShipGeometry.hatch_frame_solids(spec)
		assert_int_equal(covered.size(), solids.size(), "every fixed reservation is covered exactly by identity")
		for solid: ShipGeometry.SolidSpec in solids:
			assert_true(covered.has(String(solid.id).trim_prefix(String(id) + "/")), "imported fixed geometry covers " + String(solid.id))
		view.free()

func _fixed_ids(node: Node, covered: Dictionary) -> void:
	if node is MeshInstance3D and node.has_meta(&"hatch_reservation"):
		covered[node.get_meta(&"hatch_reservation")] = true
	if node is MeshInstance3D and node.mesh.has_meta(&"hatch_reservations"):
		var reservations: Dictionary = node.mesh.get_meta(&"hatch_reservations")
		for id: String in reservations: covered[id] = true
	for child: Node in node.get_children(): _fixed_ids(child, covered)

func test_imported_frame_rivets_use_each_uniform_station_and_its_reservation() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var stations := ShipGeometry.hatch_frame_rivet_stations(spec.aperture())
		var variant := HatchAsset.variant(spec)
		var ring_min := INF
		var ring_max := -INF
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_frame_solids(spec):
			if not "/RING/" in String(solid.id): continue
			var bounds := spec.frame().affine_inverse() * solid.transform * AABB(-solid.size / 2, solid.size)
			ring_min = minf(ring_min, bounds.position.z)
			ring_max = maxf(ring_max, bounds.end.z)
		for side: int in range(2):
			var reservations: Array[Dictionary] = []
			for row: Dictionary in variant.frame_rivets:
				if int(row.side) == side: reservations.append(row)
			var rivets: MultiMeshInstance3D = view.get_node("Frame/ForeRivets" if side == 0 else "Frame/AftRivets")
			assert_true(rivets.multimesh.mesh.get_meta(&"imported_source", "") == "res://assets/props/hatch/hatch.glb", "uniform frame rivet is imported")
			var poses: Array = rivets.multimesh.get_meta(&"instance_poses")
			assert_int_equal(poses.size(), stations.size(), "one imported rivet per uniform station")
			assert_int_equal(reservations.size(), stations.size(), "one exported reservation per uniform station")
			var size := Vector3(ShipGeometry.HATCH_RIVET_RADIUS * 2, ShipGeometry.HATCH_RIVET_DEPTH, ShipGeometry.HATCH_RIVET_RADIUS * 2)
			for index: int in range(poses.size()):
				var expected := stations[index]
				expected.origin.z = float(reservations[index].transform.origin[2])
				assert_true(absf(expected.origin.z - (ring_min if side == 0 else ring_max)) < ShipGeometry.HATCH_RIVET_DEPTH / 2, "rivet reservation seats on its physical ring face")
				var first_origin := HatchAsset.vector(reservations[0].transform.origin)
				assert_float_equal(expected.origin.z, first_origin.z, "all heads share one seating depth per face")
				var actual: Transform3D = view.transform.affine_inverse() * Surfaces.world_frame(rivets) * poses[index]
				assert_true(actual.origin.distance_to(expected.origin) < 1e-6, "imported frame rivet uses source station and face depth")
				for axis: int in range(3): assert_true(actual.basis[axis].distance_to(expected.basis[axis]) < 1e-6, "imported rivet keeps source orientation")
				var bounds: AABB = actual * rivets.multimesh.mesh.get_aabb()
				assert_true((expected * AABB(-size / 2, size)).grow(0.001).encloses(bounds), "frame rivet stays inside its 1mm reservation")
		view.free()

func test_modelled_hatches_use_shared_baked_maps_without_changing_other_consumers() -> void:
	var layout := ShipLayout.authored().layout
	var first := DoorView.build(layout.door(IDS[1]))
	var second := DoorView.build(layout.door(IDS[2]))
	var material: ShaderMaterial = first.get_node("Hinge/Leaf/ForeSteel").material_override
	assert_true(material == second.get_node("Hinge/Leaf/ForeSteel").material_override, "both hinge variants share one baked material")
	assert_true(material.get_shader_parameter(&"baked_hatch") == true, "imported hatches select the baked UV shader branch")
	for kind: String in ["albedo", "normal", "orm"]:
		var texture: Texture2D = material.get_shader_parameter("baked_" + kind)
		assert_true(texture != null and texture.resource_path == "res://assets/props/hatch/hatch_%s.png" % kind, "production samples baked " + kind)
	assert_true(material == first.get_node("Frame/ForeSteel").material_override, "fixed steel shares the baked finish")
	assert_true(material == first.get_node("Hinge/Leaf/Wheel").get_child(0).material_override, "wheel and hazard tape use the baked atlas")
	assert_false(Surfaces.material(&"hatch_leaf").get_shader_parameter(&"baked_hatch") == true, "side/lift doors retain their original surface recipe")
	assert_false(Surfaces.material(&"hardware").get_shader_parameter(&"baked_hatch") == true, "service hardware retains its original surface recipe")
	assert_true(first.get_node("ForePanel/Housing").material_override == Surfaces.material(&"frame"), "service housing keeps its shared procedural material")
	for role: StringName in Surfaces.ROLES: Surfaces.material(role)
	Surfaces.tape_material()
	assert_true(Surfaces.cache_size() <= Surfaces.ROLES.size() + 1, "baked material counts toward the finite shared-role budget")
	first.free()
	second.free()
