class_name PodMesh
extends RefCounted
## The rendered pod shell: the authored pod-v2.glb asset, loaded once
## per process, its single textured mesh instanced by all seven pods
## under one frozen mesh-to-pod transform (probe-verified against the
## authored pod numbers: envelope parity 0.00% on all three axes, the
## authored sit-up corridor clear with its worst clearance at the lying
## eye). The authored solids in PodBody stay the single source for
## colliders and placement parity; the shell is dressing. All numbers
## are pod-local meters: local +Z is the foot (the opening), local -Z
## the head, up is +Y.

const POD_PATH: String = "res://assets/props/pod/pod-v2.glb"

## The dome skin's near-vertical edge along the model's open strip, in
## mesh-frame z: the strip runs from here to the slot's outer wall, and
## its centering offset derives from this edge.
const SKIRT_Z: float = 0.25

static var _shell: Mesh = null

## The shared shell mesh: the GLB's one MeshInstance3D surface,
## extracted with its own imported material (the painted pod texture),
## so every pod draws from exactly one mesh and one material.
static func shell_mesh() -> Mesh:
	if _shell == null:
		_shell = _extract_shell()
	return _shell

## One shell instance configured with the frozen mesh-to-pod transform:
## the mesh's long X onto the pod's long Z with both open ends kept
## clear, mesh Y up off the skid line, mesh Z flipped onto pod X so the
## raised canopy rides +X, and the open strip centered on the pod
## centerline.
static func make_shell() -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = "PodShell"
	instance.mesh = shell_mesh()
	instance.transform = shell_transform()
	return instance

## The frozen mesh-to-pod transform, derived from the mesh's own AABB
## exactly as the verified probe derived it: per-axis envelope scales
## onto the authored pod footprint, height off the mesh's skid line, and
## the strip centering offset from the dome edge. The basis only
## permutes axes with a positive determinant, so triangle winding
## survives the transform unchanged. Deterministic: the loaded AABB
## never changes, so every derivation lands on the same transform.
static func shell_transform() -> Transform3D:
	var bounds: AABB = shell_mesh().get_aabb()
	var mesh_min: Vector3 = bounds.position
	var mesh_max: Vector3 = bounds.end
	var s_len: float = Pods.POD_LENGTH / (mesh_max.x - mesh_min.x)
	var s_height: float = Pods.POD_HEIGHT / (mesh_max.y - mesh_min.y)
	var s_width: float = Pods.POD_WIDTH / (mesh_max.z - mesh_min.z)
	var strip_center: float = 0.5 * (SKIRT_Z + mesh_max.z)
	var x_offset: float = strip_center * s_width
	return Transform3D(
		Basis(
			Vector3(0.0, 0.0, s_len),
			Vector3(0.0, s_height, 0.0),
			Vector3(-s_width, 0.0, 0.0)
		),
		Vector3(x_offset, -mesh_min.y * s_height, 0.0)
	)

static func _extract_shell() -> Mesh:
	var scene: PackedScene = load(POD_PATH)
	assert(scene != null and scene.can_instantiate(), "the pod shell asset must load: %s" % POD_PATH)
	var root_node: Node3D = scene.instantiate()
	var carrier := _find_mesh_instance(root_node)
	assert(carrier != null and carrier.mesh != null, "the pod shell asset carries a mesh")
	var mesh: Mesh = carrier.mesh
	root_node.free()
	return mesh

static func _find_mesh_instance(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node
	for child: Node in node.get_children():
		var found := _find_mesh_instance(child)
		if found != null:
			return found
	return null
