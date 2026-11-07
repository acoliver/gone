extends RefCounted
## Render-surface witnesses for tools/blender/pod_v4/diagnose_views.py.

static func save_scene(meshes: Array[MeshInstance3D], output: String) -> void:
	var parts: Array[Dictionary] = []
	for instance: MeshInstance3D in meshes:
		if not instance.is_visible_in_tree() or instance.mesh == null:
			continue
		for surface: int in range(instance.mesh.get_surface_count()):
			var arrays := instance.mesh.surface_get_arrays(surface)
			var material := instance.get_active_material(surface)
			var vertices: Array = []
			var normals: Array = []
			var frame := instance.global_transform
			var normal_frame := frame.basis.inverse().transposed()
			for point: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
				var p := frame * point
				vertices.append([p.x,p.y,p.z])
			for normal: Vector3 in arrays[Mesh.ARRAY_NORMAL]:
				var n := normal_frame * normal
				normals.append([n.x,n.y,n.z])
			var indices: Array = []
			if arrays[Mesh.ARRAY_INDEX] != null:
				indices = Array(arrays[Mesh.ARRAY_INDEX])
			else:
				indices = range(vertices.size())
			parts.append({"path":String(instance.get_path()),"material":material.resource_name if material else "", "vertices":vertices,"normals":normals,"indices":indices,"cull_mode":material.cull_mode if material is BaseMaterial3D else BaseMaterial3D.CULL_DISABLED})
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify(parts))
