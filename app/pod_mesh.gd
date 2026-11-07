class_name PodMesh
extends RefCounted
## Shared clean-cage meshes in pod-local metres, with an articulated lid.

const POD_PATH: String = "res://assets/props/pod/pod-v4.glb"
const SURFACE_NAMES: Array[String] = ["ShellPlastic", "WindowTint", "CouchFabric", "PillowFabric", "Gasket"]
const SHELL_ALBEDO := Color(0.95, 0.95, 0.95)
const SHELL_ROUGHNESS: float = 0.12
const SHELL_METALLIC: float = 0.0
const SHELL_CLEARCOAT: float = 1.0
const SHELL_CLEARCOAT_ROUGHNESS: float = 0.08

static var _scene: PackedScene
static var _materials: Dictionary[String, Material] = {}
static var _shells: Dictionary[int, ArrayMesh] = {}

static func make_shell(state: int = Pods.PodState.PLAYER) -> Node3D:
	_ensure_scene()
	var root: Node3D = _scene.instantiate()
	root.name = "PodShell"
	var lid: Node3D = root.get_node("PodLid")
	lid.rotation.x = PodGeometry.lid_angle(state)
	return root

static func shell_transform() -> Transform3D:
	return Transform3D.IDENTITY

static func shell_material() -> StandardMaterial3D:
	_ensure_scene()
	return _materials["ShellPlastic"]

static func canopy_material() -> ShaderMaterial:
	_ensure_scene()
	return _materials["WindowTint"]

static func couch_material() -> StandardMaterial3D:
	_ensure_scene()
	return _materials["CouchFabric"]

## A pod-frame snapshot for geometric checks, not an extra rendered mesh.
static func shell_mesh(state: int = Pods.PodState.PLAYER) -> ArrayMesh:
	if not _shells.has(state):
		var root := make_shell(state)
		var mesh := ArrayMesh.new()
		for material_name: String in SURFACE_NAMES:
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			tool.set_material(_materials[material_name])
			_append_surfaces(root, Transform3D.IDENTITY, material_name, tool)
			tool.commit(mesh)
		_shells[state] = mesh
		root.free()
	return _shells[state]

static func _append_surfaces(node: Node3D, parent_frame: Transform3D, material_name: String, tool: SurfaceTool) -> void:
	var frame := parent_frame * node.transform
	if node is MeshInstance3D:
		for surface: int in range(node.mesh.get_surface_count()):
			if node.mesh.surface_get_material(surface).resource_name == material_name:
				tool.append_from(node.mesh, surface, frame)
	for child: Node3D in node.get_children():
		_append_surfaces(child, frame, material_name, tool)

static func _ensure_scene() -> void:
	if _scene != null:
		return
	var source: PackedScene = load(POD_PATH)
	assert(source != null and source.can_instantiate(), "pod-v4 must load")
	var root: Node3D = source.instantiate()
	_prepare(root)
	_scene = PackedScene.new()
	assert(_scene.pack(root) == OK, "pod hierarchy must pack")
	root.free()

static func _prepare(node: Node3D) -> void:
	if node is MeshInstance3D:
		var source: Mesh = node.mesh
		var importer := ImporterMesh.new()
		for surface: int in range(source.get_surface_count()):
			importer.add_surface(Mesh.PRIMITIVE_TRIANGLES, source.surface_get_arrays(surface))
		importer.generate_lods(60, 0, [])
		var mesh := ArrayMesh.new()
		for surface: int in range(source.get_surface_count()):
			var material: StandardMaterial3D = source.surface_get_material(surface)
			var material_name := material.resource_name
			assert(material_name in SURFACE_NAMES, "unexpected pod material")
			if not _materials.has(material_name):
				if material_name == "WindowTint":
					# #88: Godot ignores glTF transmission; own the thin-sheet contract here.
					var glass := ShaderMaterial.new()
					glass.resource_name = "WindowTint"
					glass.shader = preload("res://app/pod_glass.gdshader")
					_materials[material_name] = glass
				else:
					var shared: StandardMaterial3D = material.duplicate()
					if material_name == "ShellPlastic":
						# Godot drops KHR_materials_clearcoat on glTF import.
						shared.clearcoat_enabled = true
						shared.clearcoat = SHELL_CLEARCOAT
						shared.clearcoat_roughness = SHELL_CLEARCOAT_ROUGHNESS
					_materials[material_name] = shared
			var arrays := source.surface_get_arrays(surface)
			if material_name == "WindowTint":
				# #88: preserve the unsimplified single sheet's 0.5 mm polished edge.
				assert(arrays[Mesh.ARRAY_COLOR] != null, "glass requires explicit region colors")
				node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				node.sorting_use_aabb_center = true
				node.sorting_offset = 0.0
			elif material_name == "ShellPlastic":
				# #88: keep the glazing bevel and facet-matched seat unsimplified;
				# only the original shell surfaces use their bounded first LOD.
				assert(importer.get_surface_lod_count(surface) > 0, "smooth shell needs its first LOD")
				assert(importer.get_surface_lod_size(surface, 0) < 0.001, "pod LOD error exceeds 1 mm")
				arrays[Mesh.ARRAY_INDEX] = importer.get_surface_lod_indices(surface, 0)
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
			mesh.surface_set_material(surface, _materials[material_name])
		node.mesh = mesh
	for child: Node3D in node.get_children():
		_prepare(child)
