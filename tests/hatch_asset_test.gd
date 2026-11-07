extends SimTestCase

const ASSET := "res://assets/props/hatch/"

func test_build_inputs_are_exported_from_sim_not_external_dimensions() -> void:
	assert_true(FileAccess.file_exists("res://tools/export_hatch_parts.gd"), "Godot source exporter exists")
	assert_true(FileAccess.file_exists("res://tools/blender/build_hatch.py"), "Blender consumer exists")
	if not FileAccess.file_exists(ASSET + "parts.json"): return
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ASSET + "parts.json"))
	assert_int_equal(manifest.schema_version, 1, "explicit schema version")
	assert_int_equal(manifest.variants.size(), 2, "both hinge signs")
	var layout := ShipLayout.authored().layout
	for variant: Dictionary in manifest.variants:
		var door := layout.door(StringName(variant.door_id))
		var groups := HatchParts.leaf(door)
		assert_int_equal(groups.size(), variant.groups.size(), "all original groups")
		for index: int in range(groups.size()):
			var group := groups[index]
			var exported: Dictionary = variant.groups[index]
			assert_true(String(group.path) == exported.path, "group path is source owned")
			assert_true(group.side == exported.side and group.steel == exported.steel, "original group rendering ownership")
			assert_true(group.transform.is_equal_approx(_pose(exported.transform)), "original group transform including reflections")
			assert_int_equal(group.parts.size(), exported.parts.size(), "all original physical parts")
			for part_index: int in range(group.parts.size()):
				var part := group.parts[part_index]
				var row: Dictionary = exported.parts[part_index]
				assert_true(String(part.id) == row.id and String(part.shape) == row.shape, "source part identity")
				assert_true(part.size.distance_to(_v3(row.size)) < 1e-8, "no repeated dimensions")
				assert_true(part.transform.is_equal_approx(_pose(row.transform)), "original part pose")
				assert_true(absf(part.radius - row.radius) < 1e-8 and absf(part.inner_radius - row.inner_radius) < 1e-8, "original radius envelope")
				assert_int_equal(part.contour.size(), row.contour.size(), "all source contour vertices")
				for point: int in range(part.contour.size()):
					assert_true(part.contour[point].distance_to(Vector2(row.contour[point][0], row.contour[point][1])) < 1e-8, "source contour, no external dimensions")
		assert_int_equal(ShipGeometry.hatch_frame_solids(door).size(), variant.frame_solids.size(), "all fixed reservations")

func test_imported_meshes_keep_original_part_local_bounds_and_uvs() -> void:
	assert_true(FileAccess.file_exists(ASSET + "parts.json"), "part/node map was built")
	assert_true(ResourceLoader.exists(ASSET + "hatch.glb"), "shared GLB imported")
	if not FileAccess.file_exists(ASSET + "parts.json") or not ResourceLoader.exists(ASSET + "hatch.glb"): return
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ASSET + "parts.json"))
	var packed: PackedScene = load(ASSET + "hatch.glb")
	var root := packed.instantiate()
	var found: Dictionary = {}
	_collect(root, found)
	assert_int_equal(found.size(), manifest.nodes.size(), "one mapped node per physical part or fixed face side")
	for name: String in manifest.nodes:
		assert_true(found.has(name), "deterministic imported name: " + name)
		if not found.has(name): continue
		var node: MeshInstance3D = found[name]
		var row: Dictionary = manifest.nodes[name]
		var actual := _geometry_bounds(node.mesh)
		assert_true(actual.position.distance_to(_v3(row.bounds.position)) < 1e-6, "local minimum survived export: " + name)
		assert_true(actual.size.distance_to(_v3(row.bounds.size)) < 1e-6, "local extents survived export: " + name)
		if row.kind == "leaf":
			var part: Dictionary = manifest.variants[row.variant].groups[row.group].parts[row.part]
			assert_true(actual.position.distance_to(-_v3(part.size) / 2) < 1e-6, "exact original sight minimum: " + name)
			assert_true(actual.size.distance_to(_v3(part.size)) < 1e-6, "exact original sight extents: " + name)
		for surface: int in range(node.mesh.get_surface_count()):
			var arrays := node.mesh.surface_get_arrays(surface)
			assert_true(arrays[Mesh.ARRAY_TEX_UV] != null and arrays[Mesh.ARRAY_TEX_UV].size() == arrays[Mesh.ARRAY_VERTEX].size(), "real UV atlas: " + name)
	root.free()

func test_bake_provenance_and_shared_maps_exist() -> void:
	if not FileAccess.file_exists(ASSET + "parts.json"): return
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ASSET + "parts.json"))
	assert_true(manifest.measurements.ao_method == "cycles_geometry_ao", "actual geometry AO bake")
	assert_true(manifest.measurements.ao_min < manifest.measurements.ao_max, "AO has measured variation")
	for texture: Dictionary in manifest.textures:
		assert_true(FileAccess.file_exists(ASSET + texture.file), "rebuildable shared texture: " + texture.file)

func _v3(values: Array) -> Vector3:
	return Vector3(values[0], values[1], values[2])

func _collect(node: Node, found: Dictionary) -> void:
	if node is MeshInstance3D: found[String(node.name)] = node
	for child: Node in node.get_children(): _collect(child, found)

func _geometry_bounds(mesh: Mesh) -> AABB:
	# Godot pads planar render AABBs to 10 micrometres. Test actual vertices,
	# as the sight/seal contracts do, without changing the physical tolerance.
	var first: PackedVector3Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var bounds := AABB(first[0], Vector3.ZERO)
	for surface: int in range(mesh.get_surface_count()):
		var vertices: PackedVector3Array = mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex: Vector3 in vertices: bounds = bounds.expand(vertex)
	return bounds

func test_fixed_source_corrections_and_seal_normals_are_preserved() -> void:
	if not FileAccess.file_exists(ASSET + "parts.json") or not ResourceLoader.exists(ASSET + "hatch.glb"): return
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ASSET + "parts.json"))
	var packed: PackedScene = load(ASSET + "hatch.glb")
	var root := packed.instantiate()
	var found: Dictionary = {}
	_collect(root, found)
	var layout := ShipLayout.authored().layout
	for variant: Dictionary in manifest.variants:
		var source := layout.door(StringName(variant.door_id))
		var door := ShipLayout.DoorSpec.new(source.id(), source.deck_number(), source.kind(), source.policy(), Transform3D.IDENTITY, source.aperture(), source.spaces(), source.face_ids(), source.owner_id(), source.animation(), source.has_wheel())
		var solids := ShipGeometry.hatch_frame_solids(door)
		for index: int in range(solids.size()):
			var solid := solids[index]
			var row: Dictionary = variant.frame_solids[index]
			assert_true(solid.size.distance_to(_v3(row.size)) < 1e-8, "fixed size is source owned")
			assert_true((door.frame().affine_inverse() * solid.transform).is_equal_approx(_pose(row.transform)), "fixed pose is portal-relative")
			if not solid.section.is_empty(): continue
			if "/HINGE/KNUCKLE-" in String(solid.id) or "/HINGE/CAP-" in String(solid.id) or "/HINGE/BOLT-" in String(solid.id):
				# Circular fixed hardware no longer exports box corners. Its
				# actual vertices must fill the exact cylindrical reservation.
				var bounds := AABB(_v3(row.vertices[0]), Vector3.ZERO)
				for vertex: Array in row.vertices:
					var point := _v3(vertex)
					bounds = bounds.expand(point)
					var radial := Vector2(point.x / (solid.size.x / 2), point.z / (solid.size.z / 2))
					assert_true(radial.length_squared() <= 1.000001, "fixed hardware remains inside its cylinder")
				assert_true(bounds.position.distance_to(-solid.size / 2) < 1e-8 and bounds.size.distance_to(solid.size) < 1e-8, "fixed cylinder fills its source-owned axial and diameter bounds")
				continue
			var corner := 0
			for z: int in [-1, 1]:
				for y: int in [-1, 1]:
					for x: int in [-1, 1]:
						var expected := ShipGeometry.hatch_frame_vertex(door, solid, solid.size * Vector3(x, y, z) / 2)
						assert_true(expected.distance_to(_v3(row.vertices[corner])) < 1e-8, "source-corrected collar corner")
						corner += 1
	for name: String in manifest.nodes:
		var row: Dictionary = manifest.nodes[name]
		if row.kind != "leaf": continue
		var group: Dictionary = manifest.variants[row.variant].groups[row.group]
		var part: Dictionary = group.parts[row.part]
		if not group.steel or part.shape != "box": continue
		var mesh: Mesh = found[name].mesh
		var arrays := mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for i: int in range(0, indices.size(), 3):
			var normal := (vertices[indices[i + 2]] - vertices[indices[i]]).cross(vertices[indices[i + 1]] - vertices[indices[i]]).normalized()
			for j: int in range(3): assert_true(normal.dot(normals[indices[i + j]]) > 0.999999, "flat imported square seal: " + name)
	root.free()

func _pose(row: Dictionary) -> Transform3D:
	return Transform3D(Basis(_v3(row.basis[0]), _v3(row.basis[1]), _v3(row.basis[2])), _v3(row.origin))
