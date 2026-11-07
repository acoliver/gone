extends SceneTree
## #88: export the actual prepared arrays for CPU aperture and normal checks.
var output := "res://tmp/pods/fix3/runtime-geometry.json"

func _initialize() -> void:
	var arguments := OS.get_cmdline_user_args()
	for i: int in range(arguments.size()-1):
		if arguments[i] == "--out":
			output = arguments[i+1]
	var cases: Array[Dictionary] = []
	for state: int in [Pods.PodState.SEALED,Pods.PodState.EMPTY_OPEN,Pods.PodState.PLAYER]:
		var shell := PodMesh.make_shell(state)
		var parts: Array[Dictionary] = []
		_collect(shell,Transform3D.IDENTITY,parts)
		cases.append({"state":state,"closed":state==Pods.PodState.SEALED,"angle":PodGeometry.lid_angle(state),"parts":parts})
		shell.free()
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"cases":cases,"asset_sha256":FileAccess.get_sha256(PodMesh.POD_PATH)}))
	print("Exported prepared pod geometry to ",output)
	quit()

func _collect(node: Node3D,parent: Transform3D,parts: Array[Dictionary]) -> void:
	var frame := parent*node.transform
	if node is MeshInstance3D:
		var normal_frame := frame.basis.inverse().transposed()
		for surface: int in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface)
			var vertices: Array = []
			var normals: Array = []
			for value: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
				var point := frame*value
				vertices.append([point.x,point.y,point.z])
			for value: Vector3 in arrays[Mesh.ARRAY_NORMAL]:
				var normal := normal_frame*value
				normals.append([normal.x,normal.y,normal.z])
			var material: Material = node.mesh.surface_get_material(surface)
			var part := {"node":String(node.name),"material":material.resource_name,"vertices":vertices,"normals":normals,"indices":Array(arrays[Mesh.ARRAY_INDEX])}
			if material.resource_name == "WindowTint":
				var mask: Array[float] = []
				for color: Color in arrays[Mesh.ARRAY_COLOR]:
					mask.append(color.r)
				part.mask = mask
			parts.append(part)
	for child: Node3D in node.get_children():
		_collect(child,frame,parts)
