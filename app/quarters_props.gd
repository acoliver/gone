class_name QuartersProps
extends RefCounted
## Rigid quarters props keep one mesh; the transition swaps shared atlas sets.

const STEEL := preload("res://app/shaders/quarters_steel.gdshader")
const SOFA := preload("res://app/shaders/quarters_sofa.gdshader")
const SOFA_POWDER := preload("res://app/shaders/quarters_sofa_powder.gdshader")
const SOFA_ROOT := "res://assets/props/quarters/sofa/"
const SOFA_WEAVE := preload(SOFA_ROOT + "weave.png")
const SOFA_SETS := {
	&"as_built": {
		"albedo": preload(SOFA_ROOT + "as_built_albedo.png"),
		"nodust": preload(SOFA_ROOT + "as_built_nodust.png"),
		"normal": preload(SOFA_ROOT + "as_built_normal.png"),
		"orm": preload(SOFA_ROOT + "as_built_orm.png"),
		"masks": preload(SOFA_ROOT + "as_built_masks.png"),
	},
	&"aged": {
		"albedo": preload(SOFA_ROOT + "aged_albedo.png"),
		"nodust": preload(SOFA_ROOT + "aged_nodust.png"),
		"normal": preload(SOFA_ROOT + "aged_normal.png"),
		"orm": preload(SOFA_ROOT + "aged_orm.png"),
		"masks": preload(SOFA_ROOT + "aged_masks.png"),
	},
}
const STATES: Array[StringName] = [&"as_built", &"aged"]
const PROPS := {
	&"storage_locker_module": {
		&"as_built": {
			"albedo": preload("res://assets/props/quarters/storage_locker_module/as_built_albedo.png"),
			"normal": preload("res://assets/props/quarters/storage_locker_module/as_built_normal.png"),
			"orm": preload("res://assets/props/quarters/storage_locker_module/as_built_orm.png"),
		},
		&"aged": {
			"albedo": preload("res://assets/props/quarters/storage_locker_module/aged_albedo.png"),
			"normal": preload("res://assets/props/quarters/storage_locker_module/aged_normal.png"),
			"orm": preload("res://assets/props/quarters/storage_locker_module/aged_orm.png"),
		},
		&"baked_dust": preload("res://assets/props/quarters/storage_locker_module/aged_dust.png"),
		&"weather_masks": preload("res://assets/props/quarters/storage_locker_module/weather_masks.png"),
		&"region_masks": preload("res://assets/props/quarters/storage_locker_module/region_masks.png"),
	},
}
const FACE_ROOT := "res://tools/quarters_aging/locker_material/"
const FACE_ALBEDO := preload(FACE_ROOT + "aged-face-albedo.png")
const FACE_ORM := preload(FACE_ROOT + "aged-face-orm.png")
const TOP_NODUST := preload(FACE_ROOT + "top-nodust.png")
static var _materials: Dictionary = {}
static var _face_layout: Dictionary = {}
static var _hinge_mesh: Mesh

static func prepare_geometry(root: Node3D) -> void:
	if _hinge_mesh == null:
		var scene: PackedScene = load(FACE_ROOT + "hinges.glb")
		var source := scene.instantiate()
		_hinge_mesh = (source.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
		source.free()
	for node: Node in root.find_children("Hinges", "MeshInstance3D", true, false):
		(node as MeshInstance3D).mesh = _hinge_mesh


static func material(prop: StringName, state: StringName) -> ShaderMaterial:
	assert(prop == &"sofa" or PROPS.has(prop), "unknown quarters prop: %s" % prop)
	assert(STATES.has(state), "unknown quarters finish: %s" % state)
	var identity := StringName("%s/%s" % [prop, state])
	if _materials.has(identity): return _materials[identity]
	var result := ShaderMaterial.new()
	if prop == &"sofa":
		result.shader = SOFA
		for kind: String in SOFA_SETS[state]:
			result.set_shader_parameter("baked_" + kind, SOFA_SETS[state][kind])
		result.set_shader_parameter(&"weave", SOFA_WEAVE)
		result.set_shader_parameter(&"aged_finish", state == &"aged")
		for parameter: String in ["albedo_a", "albedo_b", "albedo_c"]:
			result.set_shader_parameter(parameter, Surfaces.HATCH_DETAIL_TEXTURES[parameter])
		result.set_shader_parameter(&"dust_enabled", true)
		result.set_shader_parameter(&"diagnostic", 0)
		_materials[identity] = result
		return result
	result.shader = STEEL
	for kind: String in ["albedo", "normal", "orm"]:
		result.set_shader_parameter("baked_" + kind, PROPS[prop][state][kind])
	result.set_shader_parameter(&"baked_dust", PROPS[prop][&"baked_dust"])
	result.set_shader_parameter(&"weather_masks", PROPS[prop][&"weather_masks"])
	result.set_shader_parameter(&"region_masks", PROPS[prop][&"region_masks"])
	result.set_shader_parameter(&"face_albedo", FACE_ALBEDO)
	result.set_shader_parameter(&"face_orm", FACE_ORM)
	result.set_shader_parameter(&"top_nodust", TOP_NODUST)
	result.set_shader_parameter(&"aged_finish", state == &"aged")
	result.set_shader_parameter(&"dust_enabled", true)
	result.set_shader_parameter(&"diagnostic", 0)
	result.set_shader_parameter(&"diagnostic_door", false)
	for parameter: String in Surfaces.HATCH_DETAIL_TEXTURES:
		result.set_shader_parameter(parameter, Surfaces.HATCH_DETAIL_TEXTURES[parameter])
	_materials[identity] = result
	return result

static func _sofa_powder_material(state: StringName) -> ShaderMaterial:
	var identity := StringName("sofa/%s/powder" % state)
	if _materials.has(identity): return _materials[identity]
	var result := ShaderMaterial.new()
	result.shader = SOFA_POWDER
	for kind: String in SOFA_SETS[state]:
		result.set_shader_parameter("baked_" + kind, SOFA_SETS[state][kind])
	_materials[identity] = result
	return result

static func apply(root: Node3D, prop: StringName, state: StringName) -> void:
	if prop == &"sofa":
		var finish := material(prop, state)
		for node: Node in root.find_children("*", "MeshInstance3D", true, false):
			(node as MeshInstance3D).material_override = _sofa_powder_material(state) if String(node.name).contains("Powder") else finish
		return
	prepare_geometry(root)
	if _face_layout.is_empty():
		_face_layout = JSON.parse_string(FileAccess.get_file_as_string(FACE_ROOT + "face-layout.json"))["faces"]
	_apply(root, Transform3D.IDENTITY, material(prop, state))

static func _apply(node: Node3D, prop_from_node: Transform3D, finish: ShaderMaterial) -> void:
	if node is MeshInstance3D:
		node.material_override = finish
		_set_face(node, prop_from_node)
		node.set_instance_shader_parameter(&"prop_x", Vector4(prop_from_node.basis.x.x, prop_from_node.basis.y.x, prop_from_node.basis.z.x, prop_from_node.origin.x))
		node.set_instance_shader_parameter(&"prop_y", Vector4(prop_from_node.basis.x.y, prop_from_node.basis.y.y, prop_from_node.basis.z.y, prop_from_node.origin.y))
		node.set_instance_shader_parameter(&"prop_z", Vector4(prop_from_node.basis.x.z, prop_from_node.basis.y.z, prop_from_node.basis.z.z, prop_from_node.origin.z))
	for child: Node in node.get_children():
		if child is Node3D:
			_apply(child, prop_from_node * child.transform, finish)

static func cache_size() -> int:
	return _materials.size()

static func _set_face(node: MeshInstance3D, prop_from_node: Transform3D) -> void:
	var identity := ""
	for key: String in _face_layout:
		if _face_layout[key]["part"] == String(node.name): identity = key
	var hardware := node.name in [&"Hinges", &"Handle", &"DoorVents", &"Rivets", &"HandlePocket"]
	if hardware: identity = "hardware"
	if String(node.name).begins_with("DoorReturn"): identity = "door"
	if node.name in [&"BackPanel", &"BottomPanel"]: identity = "left"
	if node.name == &"SurroundSill": identity = "kick"
	assert(identity != "", "every locker mesh has an explicit image mapping: %s" % node.name)
	var face: Dictionary = _face_layout[identity]
	var rectangle: Array = face["uv_rectangle"]
	var axes: Array = face["axes"]
	var low: Array = face["low"]
	var size: Array = face["size"]
	if hardware and node.name != &"Hinges":
		var bounds := prop_from_node * node.get_aabb()
		axes = [0, 1]
		low = [bounds.position.x - .1, bounds.position.y - .1]
		size = [.2, .2]
	if node.name in [&"BackPanel", &"BottomPanel", &"SurroundSill"]:
		var bounds := prop_from_node * node.get_aabb()
		axes = [0, 2] if node.name == &"BottomPanel" else [0, 1]
		low = [bounds.position.x, bounds.position.z if node.name == &"BottomPanel" else bounds.position.y]
		size = [bounds.size.x, bounds.size.z if node.name == &"BottomPanel" else bounds.size.y]
	node.set_instance_shader_parameter(&"face_rectangle", Vector4(rectangle[0], rectangle[1], rectangle[2], rectangle[3]))
	node.set_instance_shader_parameter(&"face_projection", Vector4(axes[0], axes[1], low[0], low[1]))
	node.set_instance_shader_parameter(&"face_size", Vector4(size[0], size[1], 1.0 if node.name == &"Hinges" else 0.0, 2.0 if node.name == &"Handle" else (1.0 if hardware else (-1.0 if identity == "top" else 0.0))))
