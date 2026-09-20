class_name StasisPods
extends Node3D
## Seven stasis pods at their registry placements: each pod is a Node3D
## group at its pod_world_transform carrying the shared pod-v2 shell
## instance from PodMesh and the PodStrips flank tubes. The greybox box
## kit the shell replaced — body trays, lids, the standing canopy, the
## foot indicator plates, the hanging blankets — is retired from the
## render entirely; the round mesh is the rendered truth for every
## state. Colliders and placements stay authored in PodBody and
## Placement; positions and orientations derive from the sim registry,
## so this builder never hard-codes a pod placement.

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
	group.add_child(PodMesh.make_shell())
	group.add_child(PodStrips.make())
	return group
