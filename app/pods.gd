class_name StasisPods
extends Node3D
## Seven stasis pods at their registry placements: each pod is a Node3D
## group at its pod_world_transform carrying the shared pod-v2 shell
## instance from PodMesh, the state's retained dressing (sealed pods
## their authored flat lid, empty-open pods the tilted lid and the
## hanging blanket, the player pod nothing beyond the shell's own
## raised canopy), and the foot-mounted indicator plate, which stays
## its own instance at its authored placement. Colliders and
## placements stay authored in PodBody and Placement; positions and
## orientations derive from the sim registry, so this builder never
## hard-codes a pod placement.

const INDICATOR_SHADE: float = 0.08

## The retained dressing palette, carried from the superseded greybox
## dressing pass: the lid slabs' painted steel and the occupancy
## blanket's worn fabric. One shared material each per process.
const LID_ALBEDO: Color = Color(0.21, 0.23, 0.2)
const LID_ROUGHNESS: float = 0.42
const LID_METALLIC: float = 0.7
const BLANKET_ALBEDO: Color = Color(0.38, 0.34, 0.27)
const BLANKET_ROUGHNESS: float = 1.0

static var _plate_mesh: BoxMesh = null
static var _plate_material: StandardMaterial3D = null
static var _lid_steel: StandardMaterial3D = null
static var _blanket_fabric: StandardMaterial3D = null
static var _box_meshes: Dictionary = {}

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
	group.add_child(PodMesh.make_shell())
	group.add_child(PodStrips.make())
	for solid: PodBody.PodSolid in _dressing_solids(pod.state()):
		group.add_child(_dressing_instance(solid))
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var plate_instance := MeshInstance3D.new()
	plate_instance.mesh = plate_mesh
	plate_instance.material_override = indicator
	plate_instance.position = plate.center
	plate_instance.quaternion = plate.rotation
	group.add_child(plate_instance)
	return group

## The state's retained dressing solids: the authored lid and blanket
## boxes the mesh shell does not replace, at their authored placements.
## The player pod's standing canopy slab is deliberately absent: the
## shell's own raised canopy is the rendered truth there, while its
## collider stays authored in PodBody.
static func _dressing_solids(state: int) -> Array[PodBody.PodSolid]:
	if state == Pods.PodState.PLAYER:
		return []
	var solids: Array[PodBody.PodSolid] = []
	for solid: PodBody.PodSolid in PodBody.pod_solids(state):
		if solid.kind == PodBody.SolidKind.BODY or solid.kind == PodBody.SolidKind.CAVITY:
			continue
		solids.append(solid)
	return solids

static func _dressing_instance(solid: PodBody.PodSolid) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = _box_mesh(solid.size)
	if solid.kind == PodBody.SolidKind.LID:
		instance.name = "PodLid"
		instance.material_override = _lid_material()
	else:
		instance.name = "PodBlanket"
		instance.material_override = _blanket_material()
	instance.position = solid.center
	instance.quaternion = Quaternion(Vector3.RIGHT, solid.roll_radians)
	return instance

## One shared BoxMesh per distinct size: the seven pods reuse three
## dressing boxes and the indicator plate, so nothing allocates per pod.
static func _box_mesh(size: Vector3) -> BoxMesh:
	if not _box_meshes.has(size):
		var box := BoxMesh.new()
		box.size = size
		_box_meshes[size] = box
	return _box_meshes[size]

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

static func _lid_material() -> StandardMaterial3D:
	if _lid_steel != null:
		return _lid_steel
	var material := StandardMaterial3D.new()
	material.albedo_color = LID_ALBEDO
	material.roughness = LID_ROUGHNESS
	material.metallic = LID_METALLIC
	material.emission_enabled = false
	_lid_steel = material
	return material

static func _blanket_material() -> StandardMaterial3D:
	if _blanket_fabric != null:
		return _blanket_fabric
	var material := StandardMaterial3D.new()
	material.albedo_color = BLANKET_ALBEDO
	material.roughness = BLANKET_ROUGHNESS
	material.emission_enabled = false
	_blanket_fabric = material
	return material
