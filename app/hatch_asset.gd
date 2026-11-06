class_name HatchAsset
extends RefCounted
## Imported part geometry and exporter-owned poses, shared across all hatch views.

const SOURCE := "res://assets/props/hatch/hatch.glb"
const MANIFEST := "res://assets/props/hatch/parts.json"

static var _document: Dictionary = {}
static var _nodes: Dictionary = {}
static var _leaf: Dictionary = {}
static var _fixed: Dictionary = {}
static var _rivet: Dictionary = {}
static var _groups: Dictionary = {}
static var _batches: Dictionary = {}

static func document() -> Dictionary:
	if _document.is_empty():
		_document = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
		assert(_document.schema_version == 1 and _document.coordinate_system == "godot_y_up", "supported hatch export schema")
		assert(_document.generated_sources.schema_version == 1 and _document.fit_recipe.schema_version == 1, "supported generated hatch provenance and fitting recipe")
		var packed: PackedScene = load(SOURCE)
		var scene := packed.instantiate()
		_collect(scene)
		scene.free()
		assert(_nodes.size() == _document.nodes.size(), "every imported hatch mesh has an export reservation")
		for name: String in _document.nodes:
			assert(_nodes.has(name), "missing imported hatch mesh: " + name)
			var row: Dictionary = _document.nodes[name]
			match row.kind:
				"leaf": _leaf[[int(row.variant), int(row.group), int(row.part)]] = _nodes[name]
				"frame": _fixed[[int(row.variant), String(row.id), int(row.side)]] = _nodes[name]
				"rivet":
					var key := [int(row.variant), int(row.side)]
					if not _rivet.has(key): _rivet[key] = _nodes[name]
		_nodes.clear()
	return _document

static func _collect(node: Node) -> void:
	if node is MeshInstance3D:
		assert(node.mesh is ArrayMesh and not _nodes.has(String(node.name)), "unique imported hatch mesh node")
		node.mesh.set_meta(&"imported_source", SOURCE)
		# Surfaces owns the finish; embedded materials would retain duplicate atlas textures.
		for surface: int in range(node.mesh.get_surface_count()): node.mesh.surface_set_material(surface, null)
		_nodes[String(node.name)] = node.mesh
	for child: Node in node.get_children(): _collect(child)

static func vector(values: Array) -> Vector3:
	return Vector3(values[0], values[1], values[2])

static func pose(row: Dictionary) -> Transform3D:
	return Transform3D(Basis(vector(row.basis[0]), vector(row.basis[1]), vector(row.basis[2])), vector(row.origin))

static func variant(spec: ShipLayout.DoorSpec) -> Dictionary:
	var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
	for row: Dictionary in document().variants:
		if row.hinge_sign == into:
			assert(Vector2(row.aperture[0], row.aperture[1]).is_equal_approx(spec.aperture()), "hatch asset matches the authored aperture")
			return row
	assert(false, "missing imported hatch hinge variant")
	return {}

static func group_mesh(variant_index: int, group: Dictionary) -> ArrayMesh:
	var key := [variant_index, int(group.index)]
	if _groups.has(key): return _groups[key]
	var result := ArrayMesh.new()
	var transforms: Dictionary = {}
	var ranges: Dictionary = {}
	var combined: Array = []
	combined.resize(Mesh.ARRAY_MAX)
	for part: Dictionary in group.parts:
		var source: ArrayMesh = _leaf[[variant_index, int(group.index), int(part.index)]]
		assert(source.get_surface_count() == 1, "one imported surface per physical hatch part")
		var local := pose(part.transform)
		var arrays := transformed_arrays(source, local)
		if part.id == "ForeSteel/plate": _front_cap_first(arrays)
		ranges[StringName(part.id)] = _append_arrays(combined, arrays)
		transforms[StringName(part.id)] = local
		_leaf.erase([variant_index, int(group.index), int(part.index)])
	result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, combined)
	result.set_meta(&"part_ranges", ranges)
	result.set_meta(&"part_transforms", transforms)
	result.set_meta(&"imported_source", SOURCE)
	_groups[key] = result
	return result

static func leaf_mesh(row: Dictionary, side: int) -> ArrayMesh:
	var key := [int(row.index), side, &"leaf"]
	if _groups.has(key): return _groups[key]
	var combined: Array = []
	combined.resize(Mesh.ARRAY_MAX)
	var transforms: Dictionary = {}
	var ranges: Dictionary = {}
	for group: Dictionary in row.groups:
		if int(group.side) != side or group.path in ["Wheel", "ReverseWheel"] or String(group.path).ends_with("Rivets"): continue
		var mesh := group_mesh(int(row.index), group)
		var local := pose(group.transform)
		var appended := _append_arrays(combined, transformed_arrays(mesh, local))
		var parts: Dictionary = mesh.get_meta(&"part_ranges")
		var poses: Dictionary = mesh.get_meta(&"part_transforms")
		for id: StringName in parts:
			var part: Dictionary = parts[id].duplicate()
			part.vertex_start += appended.vertex_start
			part.index_start += appended.index_start
			ranges[id] = part
			transforms[id] = local * poses[id]
	var result := ArrayMesh.new()
	result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, combined)
	result.set_meta(&"part_ranges", ranges)
	result.set_meta(&"part_transforms", transforms)
	result.set_meta(&"imported_source", SOURCE)
	_groups[key] = result
	return result

static func _front_cap_first(arrays: Array) -> void:
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var front := -1
	for index: int in range(normals.size()):
		if normals[index].z < -0.999999:
			front = index
			break
	assert(front >= 0, "imported front plate has a flat exposed cap")
	# Keep the front cap's stable vertex ordering without changing any imported triangles.
	for channel: int in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_COLOR, Mesh.ARRAY_TEX_UV, Mesh.ARRAY_TEX_UV2]:
		if arrays[channel] == null or arrays[channel].is_empty(): continue
		var values = arrays[channel]
		var first = values[0]
		values[0] = values[front]
		values[front] = first
		arrays[channel] = values
	var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
	for component: int in range(4):
		var first := tangents[component]
		tangents[component] = tangents[front * 4 + component]
		tangents[front * 4 + component] = first
	arrays[Mesh.ARRAY_TANGENT] = tangents
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	for index: int in range(indices.size()):
		if indices[index] == 0: indices[index] = front
		elif indices[index] == front: indices[index] = 0
	arrays[Mesh.ARRAY_INDEX] = indices

static func transformed_arrays(source: Mesh, transform: Transform3D) -> Array:
	var arrays := source.surface_get_arrays(0).duplicate(true)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
	var normal_basis := transform.basis.inverse().transposed()
	var handedness := signf(transform.basis.determinant())
	for index: int in range(vertices.size()):
		vertices[index] = transform * vertices[index]
		normals[index] = (normal_basis * normals[index]).normalized()
		if not tangents.is_empty():
			var tangent := (transform.basis * Vector3(tangents[index * 4], tangents[index * 4 + 1], tangents[index * 4 + 2])).normalized()
			for axis: int in range(3): tangents[index * 4 + axis] = tangent[axis]
			tangents[index * 4 + 3] *= handedness
	if handedness < 0:
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for triangle: int in range(0, indices.size(), 3):
			var second := indices[triangle + 1]
			indices[triangle + 1] = indices[triangle + 2]
			indices[triangle + 2] = second
		arrays[Mesh.ARRAY_INDEX] = indices
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TANGENT] = tangents
	return arrays

static func leaf_rivets(variant_index: int, group: Dictionary) -> MultiMesh:
	var key := [variant_index, int(group.index), &"leaf"]
	if _batches.has(key): return _batches[key]
	var source: Mesh = _leaf[[variant_index, int(group.index), 0]]
	var transforms: Array[Transform3D] = []
	for part: Dictionary in group.parts:
		transforms.append(pose(part.transform))
		_leaf.erase([variant_index, int(group.index), int(part.index)])
	var result := batch(source, transforms)
	_batches[key] = result
	return result

static func fixed_mesh(variant_index: int, id: String, side: int) -> Mesh:
	document()
	return _fixed[[variant_index, id, side]]

static func frame_rivets(row: Dictionary, side: int) -> MultiMesh:
	var key := [int(row.index), side, &"frame"]
	if _batches.has(key): return _batches[key]
	var transforms: Array[Transform3D] = []
	for rivet: Dictionary in row.frame_rivets:
		if int(rivet.side) == side: transforms.append(pose(rivet.transform))
	var result := batch(_rivet[[int(row.index), side]], transforms)
	_batches[key] = result
	return result

static func surround_mesh(row: Dictionary, side: int) -> ArrayMesh:
	var key := [int(row.index), side, &"surround"]
	if _groups.has(key): return _groups[key]
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	var reservations: Dictionary = {}
	for solid: Dictionary in row.frame_solids:
		var source := fixed_mesh(int(row.index), solid.id, side)
		assert(source.get_surface_count() == 1, "one imported surface per fixed reservation side")
		var local := pose(solid.transform)
		var reservation := _append_arrays(arrays, transformed_arrays(source, local))
		reservation.transform = local
		reservations[String(solid.id)] = reservation
		_fixed.erase([int(row.index), String(solid.id), side])
	var result := ArrayMesh.new()
	result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	result.set_meta(&"hatch_reservations", reservations)
	result.set_meta(&"imported_source", SOURCE)
	_groups[key] = result
	return result

static func _append_arrays(target: Array, source: Array) -> Dictionary:
	var vertex_start: int = 0 if target[Mesh.ARRAY_VERTEX] == null else target[Mesh.ARRAY_VERTEX].size()
	var indices := PackedInt32Array() if target[Mesh.ARRAY_INDEX] == null else target[Mesh.ARRAY_INDEX] as PackedInt32Array
	var index_start := indices.size()
	for channel: int in range(Mesh.ARRAY_MAX):
		if channel == Mesh.ARRAY_INDEX or source[channel] == null: continue
		if target[channel] == null:
			target[channel] = source[channel].duplicate()
		else:
			var values = target[channel]
			values.append_array(source[channel])
			target[channel] = values
	var source_indices: PackedInt32Array = source[Mesh.ARRAY_INDEX]
	assert(not source_indices.is_empty(), "imported fixed faces have indexed triangles")
	for index: int in source_indices: indices.append(index + vertex_start)
	target[Mesh.ARRAY_INDEX] = indices
	return {"vertex_start": vertex_start, "vertex_count": source[Mesh.ARRAY_VERTEX].size(), "index_start": index_start, "index_count": source_indices.size()}

static func batch(mesh: Mesh, transforms: Array[Transform3D]) -> MultiMesh:
	var result := MultiMesh.new()
	result.transform_format = MultiMesh.TRANSFORM_3D
	result.mesh = mesh
	result.instance_count = transforms.size()
	for index: int in range(transforms.size()): result.set_instance_transform(index, transforms[index])
	result.set_meta(&"instance_poses", transforms)
	return result
