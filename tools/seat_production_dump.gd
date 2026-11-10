extends RefCounted
## Numeric readback from native production instances, consumed by the mesh audit.

static func _v(p: Vector3) -> Array:
	return [p.x,p.y,p.z]

static func _pose(pose: Transform3D) -> Array:
	return [[pose.basis.x.x,pose.basis.y.x,pose.basis.z.x,pose.origin.x],[pose.basis.x.y,pose.basis.y.y,pose.basis.z.y,pose.origin.y],[pose.basis.x.z,pose.basis.y.z,pose.basis.z.z,pose.origin.z],[0,0,0,1]]

static func _mesh(mesh: Mesh, data: Dictionary) -> String:
	var id := str(mesh.get_instance_id())
	if data.meshes.has(id): return id
	var surfaces: Array = []
	for index in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(index)
		var vertices: Array = []
		var normals: Array = []
		var uv: Array = []
		for point: Vector3 in arrays[Mesh.ARRAY_VERTEX]: vertices.append(_v(point))
		for point: Vector3 in arrays[Mesh.ARRAY_NORMAL]: normals.append(_v(point))
		if arrays[Mesh.ARRAY_TEX_UV] != null:
			for point: Vector2 in arrays[Mesh.ARRAY_TEX_UV]: uv.append([point.x,point.y])
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		surfaces.append({"vertices":vertices,"normals":normals,"uv":uv,"indices":Array(indices)})
	data.meshes[id] = {"surfaces":surfaces,"resource":mesh.resource_path,"shared_material":mesh.surface_get_material(0)==SeatRailComponent.material()}
	return id

static func _collect(node: Node, parent: Transform3D, path: String, data: Dictionary) -> void:
	var pose := parent
	path += "/"+String(node.name)
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MeshInstance3D:
		data.instances.append({"path":path,"mesh":_mesh((node as MeshInstance3D).mesh,data),"pose":_pose(pose)})
	if node is MultiMeshInstance3D:
		var batch := (node as MultiMeshInstance3D).multimesh
		var id := _mesh(batch.mesh,data)
		for i in range(batch.instance_count): data.instances.append({"path":path,"mesh":id,"pose":_pose(pose*batch.get_instance_transform(i))})
	for child: Node in node.get_children(): _collect(child,pose,path,data)

static func write(ceiling: Node3D, path: String) -> void:
	var data := {"meshes":{},"instances":[],"cache_size":BayCeiling.SeatMesh.cache_size()}
	_collect(ceiling,Transform3D.IDENTITY,"",data)
	var rod := Rod.build()
	_collect(rod,Transform3D.IDENTITY,"",data)
	rod.free()
	for part: StringName in [&"full",&"left",&"middle",&"right"]:
		var source := SeatRailComponent.build(part)
		_collect(source,Transform3D.IDENTITY,"/Source_"+String(part),data)
		source.free()
	var file := FileAccess.open(path,FileAccess.WRITE)
	assert(file!=null,"numeric production readback output")
	file.store_string(JSON.stringify(data)+"\n")
