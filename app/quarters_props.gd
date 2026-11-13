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
const WARDROBE_ROOT := "res://tools/blender/quarters/wardrobe/"
const WARDROBE_TEXTURES := "res://assets/props/quarters/wardrobe_"
static var _wardrobe_layout: Dictionary = {}

const MEDAL_ROOT := "res://assets/props/quarters/dress_uniform/medal/"
const TUNIC_SCENES := {
	&"as_built": "res://assets/props/quarters/dress_uniform.glb",
	&"aged": "res://assets/props/quarters/dress_uniform_aged.glb",
}
static var _tunic_materials: Dictionary = {}
# Linear-light fit against the Tunic14 neutral chest, after grey-card light matching.
const TUNIC_AGED_WOOL_GAIN := Vector3(.813331, .860586, .899057)

static func prepare_geometry(root: Node3D) -> void:
	if _hinge_mesh == null:
		var scene: PackedScene = load(FACE_ROOT + "hinges.glb")
		var source := scene.instantiate()
		_hinge_mesh = (source.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
		source.free()
	for node: Node in root.find_children("Hinges", "MeshInstance3D", true, false):
		(node as MeshInstance3D).mesh = _hinge_mesh


static func material(prop: StringName, state: StringName, part: StringName = &"TunicBody", surface: int = 0) -> ShaderMaterial:
	if QuartersSteelLibrary.ACCEPTED.has(prop):
		return QuartersSteelLibrary.material(prop, state)
	if prop == &"wardrobe":
		assert(STATES.has(state), "unknown quarters finish: %s" % state)
		return _wardrobe_material(state)
	if prop == &"dress_uniform":
		assert(STATES.has(state), "unknown quarters finish: %s" % state)
		return _tunic_material(state, part, surface)
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
	if QuartersSteelLibrary.ACCEPTED.has(prop):
		QuartersSteelLibrary.apply(root, prop, state)
		return
	if prop == &"wardrobe":
		_apply_wardrobe(root, state)
		return
	if prop == &"dress_uniform":
		for node: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
			for surface: int in range(node.mesh.get_surface_count()):
				node.set_surface_override_material(surface, material(prop, state, node.name, surface))
		return
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


static func _tunic_material(state: StringName, part: StringName, surface: int) -> ShaderMaterial:
	if not _tunic_materials.has(state):
		var scene: PackedScene = load(TUNIC_SCENES[state])
		var source := scene.instantiate()
		var parts := {}
		var shared := {}
		for node: MeshInstance3D in source.find_children("*", "MeshInstance3D", true, false):
			var slots: Array[ShaderMaterial] = []
			for index: int in range(node.mesh.get_surface_count()):
				var imported := node.mesh.surface_get_material(index) as StandardMaterial3D
				assert(imported != null, "tunic requires imported PBR surfaces")
				if node.name == &"Medal" and index < 2:
					slots.append(_medal_finish(imported, state, index))
				elif node.name == &"Medal" and index == 2:
					slots.append(_ribbon_finish(imported, state))
				elif node.name == &"TunicBody":
					var finish := _tunic_finish(imported, state)
					_medal_contact(finish, state)
					slots.append(finish)
				else:
					if not shared.has(imported): shared[imported] = _tunic_finish(imported, state)
					slots.append(shared[imported])
			parts[node.name] = slots
		source.free()
		_tunic_materials[state] = parts
	assert(_tunic_materials[state].has(part), "unknown tunic part: %s" % part)
	assert(surface >= 0 and surface < _tunic_materials[state][part].size(), "unknown tunic surface")
	return _tunic_materials[state][part][surface]

static func _tunic_finish(imported: StandardMaterial3D, state: StringName) -> ShaderMaterial:
	var result := ShaderMaterial.new()
	var alpha := "opaque"
	if imported.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR: alpha = "mask"
	if imported.transparency in [BaseMaterial3D.TRANSPARENCY_ALPHA, BaseMaterial3D.TRANSPARENCY_ALPHA_DEPTH_PRE_PASS]: alpha = "blend"
	result.shader = load("res://app/shaders/quarters_tunic_%s.gdshader" % alpha)
	result.set_shader_parameter(&"base_colour", imported.albedo_color)
	result.set_shader_parameter(&"albedo_texture", imported.albedo_texture)
	result.set_shader_parameter(&"has_albedo", imported.albedo_texture != null)
	result.set_shader_parameter(&"normal_texture", imported.normal_texture)
	result.set_shader_parameter(&"has_normal", imported.normal_enabled)
	result.set_shader_parameter(&"normal_scale", imported.normal_scale)
	result.set_shader_parameter(&"metallic", imported.metallic)
	result.set_shader_parameter(&"roughness", imported.roughness)
	result.set_shader_parameter(&"alpha_cutoff", imported.alpha_scissor_threshold)
	result.set_shader_parameter(&"vertex_colour", imported.vertex_color_use_as_albedo)
	# Godot omits glTF specularFactor; aged Blender cloth/brass uses .12.
	var aged_pigment := state == &"aged" and imported.resource_name != "BareSteel" and imported.resource_name != "RibbonFabric"
	result.set_shader_parameter(&"specular", .12 if aged_pigment else imported.metallic_specular)
	var aged_wool := aged_pigment and is_zero_approx(imported.metallic) and not imported.resource_name.begins_with("MedalEnamel")
	result.set_shader_parameter(&"pigment_gain", TUNIC_AGED_WOOL_GAIN if aged_wool else Vector3.ONE)
	return result

static func _medal_finish(imported: StandardMaterial3D, state: StringName, role: int) -> ShaderMaterial:
	assert(role in [0, 1], "medal adapter only accepts brass and enamel")
	assert(imported.albedo_texture != null and imported.normal_enabled and imported.normal_texture != null, "medal PBR requires albedo and normal")
	assert(imported.roughness_texture != null and imported.metallic_texture != null and imported.ao_texture != null, "medal PBR requires packed ORM")
	assert(imported.roughness_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_GREEN and imported.metallic_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_BLUE and imported.ao_texture_channel == BaseMaterial3D.TEXTURE_CHANNEL_RED, "medal ORM layout must be R=AO, G=roughness, B=metallic")
	assert(imported.roughness_texture.get_image().get_data() == imported.metallic_texture.get_image().get_data() and imported.roughness_texture.get_image().get_data() == imported.ao_texture.get_image().get_data(), "medal ORM imports must retain identical packed pixels")
	assert(is_equal_approx(imported.roughness, 1.0) and is_equal_approx(imported.metallic, 1.0), "final-value ORM uses unit factors")
	var result := ShaderMaterial.new()
	result.shader = load("res://app/shaders/quarters_medal.gdshader")
	result.set_shader_parameter(&"base_colour", imported.albedo_color)
	result.set_shader_parameter(&"albedo_texture", imported.albedo_texture)
	result.set_shader_parameter(&"normal_texture", imported.normal_texture)
	result.set_shader_parameter(&"normal_scale", imported.normal_scale)
	result.set_shader_parameter(&"orm_texture", imported.roughness_texture)
	result.set_shader_parameter(&"has_normal", true)
	result.set_shader_parameter(&"roughness", imported.roughness)
	result.set_shader_parameter(&"metallic", imported.metallic)
	result.set_shader_parameter(&"specular", .5)
	result.set_shader_parameter(&"coat", 0.0)
	if role == 1:
		# Godot's native glTF import drops KHR_materials_clearcoat, so bind the saved master.
		var coat_texture := load(MEDAL_ROOT + String(state) + "_coat.png") as Texture2D
		assert(coat_texture != null, "enamel requires its generated coat-weight texture")
		result.set_shader_parameter(&"coat_texture", coat_texture)
		result.set_shader_parameter(&"has_coat_texture", true)
		result.set_shader_parameter(&"coat", 1.0)
		result.set_shader_parameter(&"coat_roughness", .30 if state == &"aged" else .09)
	return result

static func _ribbon_finish(imported: StandardMaterial3D, state: StringName) -> ShaderMaterial:
	assert(imported.albedo_texture != null and imported.normal_texture != null and imported.roughness_texture != null, "Ribbon master must export normal and roughness maps")
	var result := ShaderMaterial.new()
	result.shader = load("res://app/shaders/quarters_ribbon.gdshader")
	result.set_shader_parameter(&"base_colour", imported.albedo_color)
	result.set_shader_parameter(&"albedo_texture", imported.albedo_texture)
	result.set_shader_parameter(&"weave_normal", imported.normal_texture)
	result.set_shader_parameter(&"weave_roughness", imported.roughness_texture)
	result.set_shader_parameter(&"weave_scale", Vector2(imported.uv1_scale.x, imported.uv1_scale.y))
	result.set_shader_parameter(&"weave_offset", Vector2(imported.uv1_offset.x, imported.uv1_offset.y))
	result.set_shader_parameter(&"aged", state == &"aged")
	return result

static func _medal_contact(finish: ShaderMaterial, state: StringName) -> void:
	var frames: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MEDAL_ROOT + "contact-frames.json"))
	var frame: Dictionary = frames[state]
	finish.set_shader_parameter(&"contact_enabled", true)
	# #130: the wider remembered clearance needs more direct-light contact influence.
	finish.set_shader_parameter(&"contact_light_affect", .85 if state == &"as_built" else .35)
	finish.set_shader_parameter(&"contact_texture", load(MEDAL_ROOT + String(state) + "_contact.png"))
	for axis: String in ["x", "height", "depth"]:
		var values: Array = frame.axes[axis]
		finish.set_shader_parameter("contact_" + axis, Vector4(values[0], values[1], values[2], values[3]))

# Shared slot finishes remain for storage stand-ins and demo display/glass
# optics. Rigid batch-1 surfaces use the routed per-prop materials above.
static var _interim_materials: Dictionary = {}

static func interim_material(slot: StringName, state: StringName) -> Material:
	assert(STATES.has(state), "known interim finish state")
	assert(slot in [&"PaintedSteel", &"BareSteel", &"DarkSteel", &"Fabric", &"Wood", &"Display", &"Glass"], "unknown furniture material slot: " + String(slot))
	var identity := StringName("%s/%s" % [slot, state])
	if _interim_materials.has(identity): return _interim_materials[identity]
	var result: Material
	if state == &"aged" and slot in [&"PaintedSteel", &"BareSteel", &"DarkSteel"]:
		var steel := Surfaces.material(&"pipe").duplicate() as ShaderMaterial
		steel.set_shader_parameter(&"seam_strength", 0.0)
		steel.set_shader_parameter(&"colour_gain", Vector3.ONE * (0.45 if slot == &"DarkSteel" else 1.0))
		result = steel
	else:
		var simple := StandardMaterial3D.new()
		# Same hero ROI median used by bake_finishes.design_paint for the locker.
		simple.albedo_color = {
			&"PaintedSteel": Color(97.0 / 255, 118.0 / 255, 115.0 / 255),
			&"BareSteel": Color(0.72, 0.75, 0.77), &"DarkSteel": Color(0.23, 0.265, 0.26),
			&"Fabric": Color(0.18, 0.19, 0.20) if state == &"as_built" else Color(0.27, 0.25, 0.22),
			&"Wood": Color(0.35, 0.22, 0.12) if state == &"as_built" else Color(0.20, 0.15, 0.10),
			&"Display": Color(0.025, 0.055, 0.065),
			&"Glass": Color(0.10, 0.12, 0.13, 0.10),
		}[slot]
		simple.roughness = 0.9 if state == &"aged" or slot in [&"Fabric", &"Wood"] else (0.35 if slot == &"BareSteel" else 0.45)
		simple.metallic = 0.45 if slot in [&"BareSteel", &"DarkSteel"] else 0.02
		if slot == &"Glass":
			# The pod shader needs a mesh-specific vertex edge mask.
			simple.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			simple.roughness = 0.07
		result = simple
	_interim_materials[identity] = result
	return result

static func bedside_lens(state: StringName) -> StandardMaterial3D:
	var identity := StringName("bedside_lens/%s" % state)
	if not _interim_materials.has(identity):
		var finish := (interim_material(&"Display", state) as StandardMaterial3D).duplicate() as StandardMaterial3D
		if state == &"as_built":
			finish.albedo_color = Color(1.0, 0.69, 0.38)
			finish.emission_enabled = true
			finish.emission = finish.albedo_color
			finish.emission_energy_multiplier = Lighting.REGULAR_EMISSIVE
		_interim_materials[identity] = finish
	return _interim_materials[identity]

static func _wardrobe_material(state: StringName) -> ShaderMaterial:
	var identity := StringName("wardrobe/%s" % state)
	if _materials.has(identity): return _materials[identity]
	var result := ShaderMaterial.new()
	result.shader = load(WARDROBE_ROOT + "material.gdshader")
	result.set_shader_parameter(&"face_albedo", load(WARDROBE_TEXTURES + "aged_albedo.png"))
	result.set_shader_parameter(&"face_orm", load(WARDROBE_TEXTURES + "aged_orm.png"))
	result.set_shader_parameter(&"clean_paint", load(WARDROBE_TEXTURES + "as_built_paint.png"))
	result.set_shader_parameter(&"albedo_b", Surfaces.HATCH_DETAIL_TEXTURES["albedo_b"])
	result.set_shader_parameter(&"aged_finish", state == &"aged")
	result.set_shader_parameter(&"diagnostic", 0)
	_materials[identity] = result
	return result


static func storage_material(state: StringName) -> Material:
	assert(STATES.has(state), "unknown storage finish: %s" % state)
	if state == &"as_built": return interim_material(&"PaintedSteel", state)
	var identity := StringName("storage/%s" % state)
	if not _materials.has(identity):
		var finish := _wardrobe_material(state).duplicate() as ShaderMaterial
		finish.set_shader_parameter(&"face_albedo", FACE_ALBEDO)
		finish.set_shader_parameter(&"face_orm", FACE_ORM)
		_materials[identity] = finish
	return _materials[identity]


static func prepare_storage(piece: MeshInstance3D) -> void:
	if _face_layout.is_empty():
		_face_layout = JSON.parse_string(FileAccess.get_file_as_string(FACE_ROOT + "face-layout.json"))["faces"]
	var front: Array = _face_layout["door"]["uv_rectangle"]
	var top: Array = _face_layout["top"]["uv_rectangle"]
	var bounds := piece.get_aabb()
	piece.set_instance_shader_parameter(&"face_front", Vector4(front[0], front[1], front[2], front[3]))
	piece.set_instance_shader_parameter(&"face_back", Vector4(front[0], front[1], front[2], front[3]))
	piece.set_instance_shader_parameter(&"face_dust", Vector4(top[0], top[1], top[2], top[3]))
	piece.set_instance_shader_parameter(&"local_low", Vector4(bounds.position.x, bounds.position.y, bounds.position.z, 0))
	piece.set_instance_shader_parameter(&"local_size", Vector4(bounds.size.x, bounds.size.y, bounds.size.z, 0))
	piece.set_instance_shader_parameter(&"projection", Vector4(2, 0, 1, 0))

static func _wardrobe_rectangle(face: String) -> Vector4:
	var rectangle: Array = _wardrobe_layout[face]["uv_rectangle"]
	return Vector4(rectangle[0], rectangle[1], rectangle[2], rectangle[3])


static func _apply_wardrobe(root: Node3D, state: StringName) -> void:
	var finish := _wardrobe_material(state)
	if _wardrobe_layout.is_empty():
		_wardrobe_layout = JSON.parse_string(FileAccess.get_file_as_string(WARDROBE_ROOT + "material-layout.json"))["faces"]
	var panels := {&"Door": "door-outer", &"SidePanel_L": "left-inner", &"SidePanel_R": "right", &"BackPanel": "back", &"TopPanel": "top", &"BottomPanel": "bottom", &"SurroundHead": "header", &"DoorReturn_T": "header", &"DoorReturn_B": "header"}
	var reverse := {&"Door": "door-inner", &"SidePanel_L": "left", &"SidePanel_R": "right-inner", &"TopPanel": "ceiling"}
	for piece: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		assert(piece.mesh.get_surface_count() == 1, "wardrobe parts have one material class")
		var imported := piece.mesh.surface_get_material(0) as StandardMaterial3D
		assert(imported != null, "wardrobe requires imported material classes")
		var kind := [&"PaintedSteel", &"BareSteel", &"DarkSteel"].find(StringName(imported.resource_name)) + 1
		assert(kind > 0, "unknown wardrobe material: %s" % imported.resource_name)
		var bounds := piece.get_aabb()
		var size := bounds.size
		var thickness := 0 if size.x < minf(size.y, size.z) else (1 if size.y < size.z else 2)
		var horizontal := 2 if thickness == 0 else 0
		var vertical := 2 if thickness == 1 else 1
		var face: String = panels.get(piece.name, "frame") if kind == 1 else "hardware"
		if face == "frame" and size[horizontal] > size[vertical]:
			var swap := horizontal
			horizontal = vertical
			vertical = swap
		piece.material_override = finish
		piece.set_instance_shader_parameter(&"face_front", _wardrobe_rectangle(face))
		piece.set_instance_shader_parameter(&"face_back", _wardrobe_rectangle(reverse.get(piece.name, face) if kind == 1 else face))
		piece.set_instance_shader_parameter(&"face_edge", _wardrobe_rectangle("frame"))
		piece.set_instance_shader_parameter(&"face_dust", _wardrobe_rectangle("top"))
		piece.set_instance_shader_parameter(&"local_low", Vector4(bounds.position.x, bounds.position.y, bounds.position.z, 0))
		piece.set_instance_shader_parameter(&"local_size", Vector4(size.x, size.y, size.z, 0))
		piece.set_instance_shader_parameter(&"projection", Vector4(thickness, horizontal, vertical, kind))
