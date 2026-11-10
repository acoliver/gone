class_name QuartersClothing
extends RefCounted

const REFLECTION := Basis(Vector3.LEFT, Vector3.UP, Vector3.BACK)
static var _reflected_meshes: Dictionary = {}

static func prepare(root: Node3D) -> void:
	for piece: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if ShipScene._world_frame(piece).basis.determinant() > 0: continue
		var two_sided := false
		for surface: int in range(piece.mesh.get_surface_count()):
			var material := piece.get_active_material(surface) as BaseMaterial3D
			assert(material != null, "imported clothing uses PBR materials")
			two_sided = two_sided or material.cull_mode == BaseMaterial3D.CULL_DISABLED
		if not two_sided: continue
		# Explicit front/back plies keep their imported draw frames. Only
		# two-sided shaders need positive parity for FRONT_FACING normals.
		piece.mesh = _reflected(piece.mesh)
		piece.basis *= REFLECTION
		for child: Node in piece.get_children():
			if child is Node3D: child.transform = Transform3D(REFLECTION, Vector3.ZERO) * child.transform

static func _reflected(source: Mesh) -> ArrayMesh:
	if _reflected_meshes.has(source): return _reflected_meshes[source]
	var result := ArrayMesh.new()
	for surface: int in range(source.get_surface_count()):
		assert(source.surface_get_primitive_type(surface) == Mesh.PRIMITIVE_TRIANGLES, "clothes use triangle surfaces")
		var arrays := source.surface_get_arrays(surface).duplicate(true)
		for slot: int in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL]:
			var vectors: PackedVector3Array = arrays[slot]
			for index: int in range(vectors.size()): vectors[index].x *= -1
			arrays[slot] = vectors
		if arrays[Mesh.ARRAY_TANGENT] != null:
			var tangents: PackedFloat32Array = arrays[Mesh.ARRAY_TANGENT]
			for index: int in range(0, tangents.size(), 4):
				tangents[index] *= -1
				tangents[index + 3] *= -1
			arrays[Mesh.ARRAY_TANGENT] = tangents
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		if indices.is_empty():
			for index: int in range(arrays[Mesh.ARRAY_VERTEX].size()): indices.append(index)
		for index: int in range(0, indices.size(), 3):
			var swap := indices[index + 1]
			indices[index + 1] = indices[index + 2]
			indices[index + 2] = swap
		arrays[Mesh.ARRAY_INDEX] = indices
		result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		result.surface_set_material(surface, source.surface_get_material(surface))
	_reflected_meshes[source] = result
	return result
