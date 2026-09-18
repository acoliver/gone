class_name StasisPods
extends Node3D
## Seven stasis pod bodies at their registry placements, issue #37's
## realistic pod meshes: each pod is a Node3D group at its
## pod_world_transform carrying one MeshInstance3D of the merged,
## multi-surface per-state ArrayMesh from PodMesh (shared across every
## pod in the same state) plus the foot-mounted indicator plate, which
## stays its own instance at its authored placement. Positions and
## orientations derive from the sim registry; this builder never
## hard-codes a pod placement.

const INDICATOR_SHADE: float = 0.08

static var _plate_mesh: BoxMesh = null
static var _plate_material: StandardMaterial3D = null

static func build(registry: Pods.PodRegistry) -> StasisPods:
	var pods := StasisPods.new()
	pods.name = "StasisPods"
	var plate_mesh := _plate_box_mesh()
	var indicator := _indicator_material()
	for pod: Pods.Pod in registry.pods():
		pods.add_child(_pod_group(pod, plate_mesh, indicator))
	return pods

static func _pod_group(
	pod: Pods.Pod, plate_mesh: BoxMesh, indicator: StandardMaterial3D
) -> Node3D:
	var frame := Placement.pod_world_transform(pod.placement())
	var group := Node3D.new()
	group.name = "Pod%d" % pod.id().index()
	group.position = frame[1]
	group.quaternion = frame[0]
	var body := MeshInstance3D.new()
	body.name = "PodBody"
	body.mesh = PodMesh.for_state(pod.state())
	group.add_child(body)
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var plate_instance := MeshInstance3D.new()
	plate_instance.mesh = plate_mesh
	plate_instance.material_override = indicator
	plate_instance.position = plate.center
	plate_instance.quaternion = plate.rotation
	group.add_child(plate_instance)
	return group

## Pod systems are unpowered throughout the opening beat, including the
## player pod: dead plate, no emission.
static func _indicator_material() -> StandardMaterial3D:
	if _plate_material != null:
		return _plate_material
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(INDICATOR_SHADE, INDICATOR_SHADE, INDICATOR_SHADE)
	material.roughness = 0.6
	_plate_material = material
	return material

static func _plate_box_mesh() -> BoxMesh:
	if _plate_mesh != null:
		return _plate_mesh
	_plate_mesh = BoxMesh.new()
	_plate_mesh.size = Placement.indicator_plate().size
	return _plate_mesh
