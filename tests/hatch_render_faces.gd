class_name HatchRenderFaces
extends RefCounted
## Triangle visibility follows the native material cull mode, including reflected instances.

static func _opaque_cull_mode(material: Material) -> int:
	assert(material != null, "seal queries require an explicit material")
	if material is BaseMaterial3D:
		assert(material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED, "seal steel must be opaque")
		return material.cull_mode
	assert(material is ShaderMaterial and material.shader in [Surfaces.STEEL, Surfaces.TAPE, preload("res://app/shaders/fixture_steel.gdshader")], "seal queries require a known opaque steel shader")
	var code: String = material.shader.code
	assert(code.contains("render_mode cull_back;"), "steel shader must retain back-face culling")
	assert(not code.contains("ALPHA") and not code.contains("discard"), "seal shader must retain opaque depth-writing surfaces")
	return BaseMaterial3D.CULL_BACK

static func collect(node: Node3D, eye: Vector3, mask: int, faces: PackedVector3Array) -> void:
	if not node.visible: return
	var world := ShipScene._world_frame(node)
	if node is MeshInstance3D and (node.layers & mask) != 0:
		_append(node.mesh, world, node.material_override, node, eye, faces)
	if node is MultiMeshInstance3D and (node.layers & mask) != 0:
		var count: int = node.multimesh.instance_count
		if node.multimesh.visible_instance_count >= 0: count = node.multimesh.visible_instance_count
		var poses: Array = node.multimesh.get_meta(&"instance_poses")
		for index: int in range(count):
			_append(node.multimesh.mesh, world * poses[index], node.material_override, null, eye, faces)
	for child: Node3D in node.get_children(): collect(child, eye, mask, faces)

static func _append(mesh: Mesh, world: Transform3D, override: Material, instance: MeshInstance3D, eye: Vector3, faces: PackedVector3Array) -> void:
	for surface: int in range(mesh.get_surface_count()):
		var material := override
		if material == null and instance != null: material = instance.get_surface_override_material(surface)
		if material == null: material = mesh.surface_get_material(surface)
		var cull_mode := _opaque_cull_mode(material)
		var arrays := mesh.surface_get_arrays(surface)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices := PackedInt32Array()
		if arrays[Mesh.ARRAY_INDEX] != null: indices = arrays[Mesh.ARRAY_INDEX]
		if indices.is_empty():
			for index: int in range(vertices.size()): indices.append(index)
		for index: int in range(0, indices.size(), 3):
			var a := world * vertices[indices[index]]
			var b := world * vertices[indices[index + 1]]
			var c := world * vertices[indices[index + 2]]
			var facing := (c - a).cross(b - a).dot(eye - a) * signf(world.basis.determinant())
			if cull_mode == BaseMaterial3D.CULL_BACK and facing <= 0: continue
			if cull_mode == BaseMaterial3D.CULL_FRONT and facing >= 0: continue
			faces.append_array(PackedVector3Array([a, b, c]))
