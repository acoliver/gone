class_name StasisPods
extends Node3D
## Seven registry-placed clean-cage pods with shared meshes/materials.
## PodLid and its pane rotate together about the authored hidden pivot.

static func build(registry: Pods.PodRegistry) -> StasisPods:
	var pods := StasisPods.new()
	pods.name = "StasisPods"
	for pod: Pods.Pod in registry.pods():
		pods.add_child(_pod_group(pod))
	return pods

static func _pod_group(pod: Pods.Pod) -> Node3D:
	var frame := Placement.pod_world_transform(pod.placement())
	var group := Node3D.new()
	group.name = "Pod%d" % pod.id().index()
	group.position = frame[1]
	group.quaternion = frame[0]
	group.add_child(PodMesh.make_shell(pod.state()))
	group.add_child(PodStrips.make())
	return group
