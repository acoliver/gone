class_name PodMesh
extends RefCounted
## One authored smooth pod mesh shared by all seven pods. Geometry is
## already pod-local meters: +Z foot, -Z head, +Y up, deck at zero.
## Its three surfaces use process-wide plastic, glass and fabric materials.
## PodGeometry and Placement remain the collision and placement owners.

const POD_PATH: String = "res://assets/props/pod/pod-v3.glb"
const SURFACE_NAMES: Array[String] = ["ShellPlastic", "CanopyGlass", "CouchFabric"]
const SHELL_ALBEDO: Color = Color(0.96, 0.96, 0.96)
const SHELL_ROUGHNESS: float = 0.12
const SHELL_METALLIC: float = 0.0
const SHELL_CLEARCOAT: float = 1.0
const SHELL_CLEARCOAT_ROUGHNESS: float = 0.08

static var _shell: ArrayMesh = null
static var _shell_material: StandardMaterial3D = null
static var _canopy_material: StandardMaterial3D = null
static var _couch_material: StandardMaterial3D = null

static func shell_mesh() -> Mesh:
	if _shell == null:
		_shell = _extract_shell()
	return _shell

static func shell_material() -> StandardMaterial3D:
	if _shell_material == null:
		var material := StandardMaterial3D.new()
		material.resource_name = SURFACE_NAMES[0]
		material.albedo_color = SHELL_ALBEDO
		material.roughness = SHELL_ROUGHNESS
		material.metallic = SHELL_METALLIC
		material.clearcoat_enabled = true
		material.clearcoat = SHELL_CLEARCOAT
		material.clearcoat_roughness = SHELL_CLEARCOAT_ROUGHNESS
		_shell_material = material
	return _shell_material

static func canopy_material() -> StandardMaterial3D:
	if _canopy_material == null:
		var material := StandardMaterial3D.new()
		material.resource_name = SURFACE_NAMES[1]
		# Opaque tint avoids sorting artifacts between the inner/outer glass
		# skins. The raised lid leaves the couch visible without transparency.
		material.albedo_color = Color(0.025, 0.035, 0.045)
		material.roughness = 0.06
		material.metallic = 0.0
		_canopy_material = material
	return _canopy_material

static func couch_material() -> StandardMaterial3D:
	if _couch_material == null:
		var material := StandardMaterial3D.new()
		material.resource_name = SURFACE_NAMES[2]
		material.albedo_color = Color(0.09, 0.12, 0.14)
		material.roughness = 0.9
		material.metallic = 0.0
		_couch_material = material
	return _couch_material

static func make_shell() -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = "PodShell"
	instance.mesh = shell_mesh()
	instance.transform = shell_transform()
	return instance

static func shell_transform() -> Transform3D:
	return Transform3D.IDENTITY

static func _extract_shell() -> ArrayMesh:
	var scene: PackedScene = load(POD_PATH)
	assert(scene != null and scene.can_instantiate(), "the pod asset must load: %s" % POD_PATH)
	var root_node: Node3D = scene.instantiate()
	var carrier := _find_mesh_instance(root_node)
	assert(carrier != null and carrier.mesh != null, "the pod asset carries a mesh")
	assert(carrier.transform == Transform3D.IDENTITY, "pod geometry is baked in pod-local meters")
	var source: Mesh = carrier.mesh
	assert(source.get_surface_count() == 3, "pod has plastic, glass and fabric surfaces")
	var materials: Array[Material] = [shell_material(), canopy_material(), couch_material()]
	var mesh := ArrayMesh.new()
	# Select by authored material name, not importer-dependent surface order.
	for index: int in range(SURFACE_NAMES.size()):
		var matched := false
		for surface: int in range(source.get_surface_count()):
			if source.surface_get_material(surface).resource_name == SURFACE_NAMES[index]:
				mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, source.surface_get_arrays(surface))
				mesh.surface_set_material(index, materials[index])
				matched = true
				break
		assert(matched, "pod is missing authored surface %s" % SURFACE_NAMES[index])
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
