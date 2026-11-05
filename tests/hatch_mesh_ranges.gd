extends RefCounted
## Test-side extraction from actual submitted vertex/index buffers, not source bounds.

static var _bounds: Dictionary = {}

static func parts(mesh: Mesh, metadata: StringName = &"part_ranges") -> Dictionary:
	var key := [mesh.get_rid(), metadata]
	if _bounds.has(key): return _bounds[key]
	assert(mesh.get_surface_count() == 1, "one submitted atlas surface")
	var arrays := mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var ranges: Dictionary = mesh.get_meta(metadata)
	var poses: Dictionary = mesh.get_meta(&"part_transforms", {})
	var result: Dictionary = {}
	var vertex_end := 0
	var index_end := 0
	for id: Variant in ranges:
		var row: Dictionary = ranges[id]
		assert(int(row.vertex_start) == vertex_end and int(row.index_start) == index_end, "complete nonoverlapping physical ranges")
		assert(row.vertex_count > 0 and row.index_count > 0 and int(row.index_count) % 3 == 0, "complete physical triangles")
		vertex_end += int(row.vertex_count)
		index_end += int(row.index_count)
		var pose: Transform3D = row.transform if metadata == &"hatch_reservations" else poses[id]
		var inverse := pose.affine_inverse()
		var bounds := AABB(inverse * vertices[int(row.vertex_start)], Vector3.ZERO)
		for index: int in range(int(row.vertex_start), vertex_end): bounds = bounds.expand(inverse * vertices[index])
		for index: int in range(int(row.index_start), index_end):
			assert(indices[index] >= int(row.vertex_start) and indices[index] < vertex_end, "triangles stay in their physical range")
		result[StringName(id)] = {"pose": pose, "bounds": bounds, "row": row}
	assert(vertex_end == vertices.size() and index_end == indices.size(), "every rendered vertex and index is tested")
	_bounds[key] = result
	return result

static func faces(node: MeshInstance3D, id: String, result: PackedVector3Array, metadata: StringName, reference_inverse: Transform3D = Transform3D.IDENTITY) -> void:
	var part: Dictionary = parts(node.mesh, metadata)[StringName(id)]
	var arrays := node.mesh.surface_get_arrays(0)
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var world := reference_inverse * Surfaces.world_frame(node)
	for index: int in range(int(part.row.index_start), int(part.row.index_start + part.row.index_count)):
		result.append(world * vertices[indices[index]])

static func remove_seals(view: DoorView) -> void:
	for side: String in ["ForeSteel", "AftSteel"]:
		var piece: MeshInstance3D = view.label_leaf().get_node(side)
		var arrays := piece.mesh.surface_get_arrays(0).duplicate(true)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var kept := PackedInt32Array()
		for id: StringName in parts(piece.mesh):
			if "SealSteel/" in String(id): continue
			var row: Dictionary = parts(piece.mesh)[id].row
			kept.append_array(indices.slice(int(row.index_start), int(row.index_start + row.index_count)))
		arrays[Mesh.ARRAY_INDEX] = kept
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		piece.mesh = mesh
