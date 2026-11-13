class_name QuartersSteelLibrary
extends RefCounted
## Whole-face images are baked once onto each fitted prop's original UVs.

const PROPS: Array[StringName] = [
	&"wardrobe", &"desk", &"console", &"bed", &"lockers_over_bed", &"bedside",
	&"media_cabinet", &"dining_table", &"dining_chair", &"desk_chair", &"view_screen",
]
const ACCEPTED: Array[StringName] = [
	&"desk", &"console", &"bed", &"lockers_over_bed", &"bedside",
	&"media_cabinet", &"dining_table", &"dining_chair", &"desk_chair", &"view_screen",
]
const SHADER := preload("res://app/shaders/quarters_library.gdshader")
const ROOT := "res://assets/props/quarters/steel/"
static var _materials: Dictionary = {}

static func material(prop: StringName, state: StringName) -> ShaderMaterial:
	assert(PROPS.has(prop), "unknown steel-library prop: %s" % prop)
	assert(state in [&"as_built", &"aged"], "unknown steel-library finish: %s" % state)
	var identity := StringName("%s/%s" % [prop, state])
	if _materials.has(identity): return _materials[identity]
	var finish := ShaderMaterial.new()
	finish.shader = SHADER
	for kind: String in ["albedo", "normal", "orm"]:
		var path := ROOT + "%s/%s_%s.png" % [prop, state, kind]
		assert(ResourceLoader.exists(path), "missing built library atlas: " + path)
		finish.set_shader_parameter("baked_" + kind, load(path))
	finish.set_shader_parameter(&"regions", load(ROOT + "%s/regions.png" % prop))
	finish.set_shader_parameter(&"paint_grain", Surfaces.HATCH_DETAIL_TEXTURES["albedo_b"])
	finish.set_shader_parameter(&"aged_finish", state == &"aged")
	finish.set_shader_parameter(&"diagnostic", 0)
	_materials[identity] = finish
	return finish

static func apply(root: Node3D, prop: StringName, state: StringName) -> void:
	var finish := material(prop, state)
	for piece: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		var overrides: Array[Material] = []
		var preserved := 0
		for surface: int in range(piece.mesh.get_surface_count()):
			var source := piece.mesh.surface_get_material(surface)
			assert(source != null, "library surfaces require imported material roles")
			var role := source.resource_name.to_lower()
			var keep := role.contains("display") or role.contains("glass") or role == "screen"
			if keep: preserved += 1
			overrides.append(piece.get_active_material(surface) if keep else finish)
		if preserved == overrides.size(): continue
		for surface: int in range(overrides.size()):
			piece.set_surface_override_material(surface, overrides[surface])
		# A mixed mesh must release its mesh-wide override before its per-surface
		# display material can remain effective alongside the steel finish.
		piece.material_override = null if preserved else finish

static func cache_size() -> int:
	return _materials.size()
