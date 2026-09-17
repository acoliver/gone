class_name StasisPods
extends Node3D
## Seven stasis pod bodies at their registry placements, ported from
## gone_app geometry.rs (spawn_pods, fill_pod). Each pod is a Node3D
## group at its pod_world_transform carrying one MeshInstance3D per pure
## construction solid (PodBody.pod_solids, spawned verbatim) plus the
## foot-mounted indicator plate. Positions and orientations derive from
## the sim registry; this builder never hard-codes a pod placement.

const POD_BODY_SHADE: float = 0.45
const POD_LID_SHADE: float = 0.42
const POD_CAVITY_SHADE: float = 0.05
const BLANKET_SHADE: float = 0.55
const INDICATOR_SHADE: float = 0.08

static var _box_cache: Dictionary = {}
static var _kind_materials: Dictionary = {}

static func build(registry: Pods.PodRegistry) -> StasisPods:
	var pods := StasisPods.new()
	var indicator := _indicator_material()
	for pod: Pods.Pod in registry.pods():
		pods.add_child(_pod_group(pod, indicator))
	return pods

static func _pod_group(pod: Pods.Pod, indicator: StandardMaterial3D) -> Node3D:
	var frame := Placement.pod_world_transform(pod.placement())
	var group := Node3D.new()
	group.name = "Pod%d" % pod.id().index()
	group.position = frame[1]
	group.quaternion = frame[0]
	for solid: PodBody.PodSolid in PodBody.pod_solids(pod.state()):
		var body := MeshInstance3D.new()
		body.mesh = _box_mesh(solid.size)
		body.material_override = _kind_material(solid.kind)
		body.position = solid.center
		body.quaternion = Quaternion(Vector3.RIGHT, solid.roll_radians)
		group.add_child(body)
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var plate_instance := MeshInstance3D.new()
	plate_instance.mesh = _box_mesh(plate.size)
	plate_instance.material_override = indicator
	plate_instance.position = plate.center
	plate_instance.quaternion = plate.rotation
	group.add_child(plate_instance)
	return group

## The grey shade for one construction solid kind; materials are shared
## per kind, never per instance.
static func _kind_material(kind: int) -> StandardMaterial3D:
	if _kind_materials.has(kind):
		return _kind_materials[kind]
	var shade := POD_BODY_SHADE
	match kind:
		PodBody.SolidKind.CAVITY:
			shade = POD_CAVITY_SHADE
		PodBody.SolidKind.LID:
			shade = POD_LID_SHADE
		PodBody.SolidKind.BLANKET:
			shade = BLANKET_SHADE
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(shade, shade, shade)
	material.roughness = 0.95
	_kind_materials[kind] = material
	return material

## Pod systems are unpowered throughout the opening beat, including the
## player pod: dead plate, no emission.
static func _indicator_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(INDICATOR_SHADE, INDICATOR_SHADE, INDICATOR_SHADE)
	material.roughness = 0.6
	return material

static func _box_mesh(size: Vector3) -> BoxMesh:
	if _box_cache.has(size):
		return _box_cache[size]
	var mesh := BoxMesh.new()
	mesh.size = size
	_box_cache[size] = mesh
	return mesh
