extends SceneTree
## Read back production support and service envelopes for the offline installation.

func _initialize() -> void:
	assert(DisplayServer.get_name()!="headless", "native renderer required for MultiMesh support transforms")
	var output := OS.get_cmdline_user_args()[0]
	var ceiling := BayCeiling.build()
	var boxes: Array = []
	_collect(ceiling, Transform3D.IDENTITY, "", boxes)
	var obstacles: Array = []
	for box: AABB in BayCeiling.service_bounds(): obstacles.append(_box(box))
	var pods: Array = []
	for pod: Pods.Pod in Pods.PodRegistry.frozen().pods():
		var pose := Placement.pod_world_transform(pod.placement())
		pods.append({"id":pod.id().index(), "position":_v(pose[1]), "yaw":pod.placement().yaw_radians})
	var path := PlacementTruth.player_exit_path()
	var get_up_top := 0.0
	var poses: Array = []
	for pose: Exit.ExitPose in path.poses():
		get_up_top = maxf(get_up_top,maxf(pose.head().y,pose.foot().y)+Controller.CAPSULE_RADIUS)
		poses.append({"foot":_v(pose.foot()),"head":_v(pose.head())})
	var player := {"standing_capsule_top_m":Controller.CAPSULE_STANDING_HEIGHT+Controller.PENETRATION_TOLERANCE,
		"get_up_envelope_top_m":get_up_top,"capsule_radius_m":Controller.CAPSULE_RADIUS,
		"exit_poses":poses,"method":"rigid/pivot continuous extrema enclosed by maximum pose Y plus capsule radius"}
	var file := FileAccess.open(output, FileAccess.WRITE)
	file.store_string(JSON.stringify({"supports":boxes,"services":obstacles,"pods":pods,"player":player})+"\n")
	ceiling.free()
	quit()

func _v(p: Vector3) -> Array:
	return [p.x,p.y,p.z]

func _box(box: AABB) -> Array:
	return [_v(box.position),_v(box.end)]

func _collect(node: Node, parent: Transform3D, path: String, boxes: Array) -> void:
	var pose := parent
	path += "/"+String(node.name)
	if node is Node3D: pose *= (node as Node3D).transform
	if node is MultiMeshInstance3D:
		var batch := (node as MultiMeshInstance3D).multimesh
		for i in range(batch.instance_count):
			boxes.append({"path":path,"bounds":_box(pose*batch.get_instance_transform(i)*batch.mesh.get_aabb())})
	for child: Node in node.get_children(): _collect(child,pose,path,boxes)
