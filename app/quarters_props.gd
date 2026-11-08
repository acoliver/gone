class_name QuartersProps
extends RefCounted
## Rigid quarters props keep one mesh; the transition swaps shared atlas sets.

const STEEL := preload("res://app/shaders/quarters_steel.gdshader")
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
		&"runoff_colour": preload("res://assets/props/quarters/storage_locker_module/aged_rust.png"),
		&"weather_masks": preload("res://assets/props/quarters/storage_locker_module/weather_masks.png"),
		&"region_masks": preload("res://assets/props/quarters/storage_locker_module/region_masks.png"),
		&"streak_sources": preload("res://assets/props/quarters/storage_locker_module/streak_sources.tres"),
	},
}
static var _materials: Dictionary = {}

static func material(prop: StringName, state: StringName) -> ShaderMaterial:
	assert(PROPS.has(prop), "unknown quarters prop: %s" % prop)
	assert(STATES.has(state), "unknown quarters finish: %s" % state)
	var identity := StringName("%s/%s" % [prop, state])
	if _materials.has(identity): return _materials[identity]
	var result := ShaderMaterial.new()
	result.shader = STEEL
	for kind: String in ["albedo", "normal", "orm"]:
		result.set_shader_parameter("baked_" + kind, PROPS[prop][state][kind])
	result.set_shader_parameter(&"baked_dust", PROPS[prop][&"baked_dust"])
	result.set_shader_parameter(&"runoff_colour", PROPS[prop][&"runoff_colour"])
	result.set_shader_parameter(&"weather_masks", PROPS[prop][&"weather_masks"])
	result.set_shader_parameter(&"region_masks", PROPS[prop][&"region_masks"])
	result.set_shader_parameter(&"streak_sources", PROPS[prop][&"streak_sources"])
	result.set_shader_parameter(&"aged_finish", state == &"aged")
	result.set_shader_parameter(&"dust_enabled", true)
	result.set_shader_parameter(&"diagnostic", 0)
	result.set_shader_parameter(&"diagnostic_door", false)
	for parameter: String in Surfaces.HATCH_DETAIL_TEXTURES:
		result.set_shader_parameter(parameter, Surfaces.HATCH_DETAIL_TEXTURES[parameter])
	_materials[identity] = result
	return result

static func apply(root: Node3D, prop: StringName, state: StringName) -> void:
	_apply(root, Transform3D.IDENTITY, material(prop, state))

static func _apply(node: Node3D, prop_from_node: Transform3D, finish: ShaderMaterial) -> void:
	if node is MeshInstance3D:
		node.material_override = finish
		node.set_instance_shader_parameter(&"prop_x", Vector4(prop_from_node.basis.x.x, prop_from_node.basis.y.x, prop_from_node.basis.z.x, prop_from_node.origin.x))
		node.set_instance_shader_parameter(&"prop_y", Vector4(prop_from_node.basis.x.y, prop_from_node.basis.y.y, prop_from_node.basis.z.y, prop_from_node.origin.y))
		node.set_instance_shader_parameter(&"prop_z", Vector4(prop_from_node.basis.x.z, prop_from_node.basis.y.z, prop_from_node.basis.z.z, prop_from_node.origin.z))
	for child: Node in node.get_children():
		if child is Node3D:
			_apply(child, prop_from_node * child.transform, finish)

static func cache_size() -> int:
	return _materials.size()
