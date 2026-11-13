class_name BayCeilingMaterial
extends RefCounted
## Shared, finite StandardMaterial3D set for the fitted bay-ceiling variants.
## UV0 is normalized planar XY; see assets/props/bay-ceiling/materials/README.md.

const ALBEDO := {
	&"intact": preload("res://assets/props/bay-ceiling/materials/intact_albedo.png"),
	&"subtlewarp": preload("res://assets/props/bay-ceiling/materials/subtlewarp_albedo.png"),
	&"sag": preload("res://assets/props/bay-ceiling/materials/sag_albedo.png"),
	&"torncorner": preload("res://assets/props/bay-ceiling/materials/torncorner_albedo.png"),
	&"brokenedge": preload("res://assets/props/bay-ceiling/materials/brokenedge_albedo.png"),
}
const ROUGHNESS := {
	&"intact": preload("res://assets/props/bay-ceiling/materials/intact_roughness.png"),
	&"subtlewarp": preload("res://assets/props/bay-ceiling/materials/subtlewarp_roughness.png"),
	&"sag": preload("res://assets/props/bay-ceiling/materials/sag_roughness.png"),
	&"torncorner": preload("res://assets/props/bay-ceiling/materials/torncorner_roughness.png"),
	&"brokenedge": preload("res://assets/props/bay-ceiling/materials/brokenedge_roughness.png"),
}
const NORMAL := {
	&"intact": preload("res://assets/props/bay-ceiling/materials/intact_normal.png"),
	&"subtlewarp": preload("res://assets/props/bay-ceiling/materials/subtlewarp_normal.png"),
	&"sag": preload("res://assets/props/bay-ceiling/materials/sag_normal.png"),
	&"torncorner": preload("res://assets/props/bay-ceiling/materials/torncorner_normal.png"),
	&"brokenedge": preload("res://assets/props/bay-ceiling/materials/brokenedge_normal.png"),
}
static var _materials: Dictionary = {}

static func material_for_variant(variant: StringName) -> StandardMaterial3D:
	assert(ALBEDO.has(variant) and ROUGHNESS.has(variant) and NORMAL.has(variant), "unknown bay ceiling variant: %s" % variant)
	if not _materials.has(variant):
		var result := StandardMaterial3D.new()
		result.albedo_texture = ALBEDO[variant]
		result.metallic = 0.22
		result.roughness = 0.86
		result.roughness_texture = ROUGHNESS[variant]
		result.normal_enabled = true
		result.normal_texture = NORMAL[variant]
		result.normal_scale = 0.35
		result.emission_enabled = false
		_materials[variant] = result
	return _materials[variant]

static func cache_size() -> int:
	return _materials.size()
