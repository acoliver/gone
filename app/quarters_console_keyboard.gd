class_name QuartersConsoleKeyboard
extends RefCounted
## The power-room mesh retains its PBR response, UVs and quarters-only finish sets.

const SCENE := "res://assets/props/quarters/console_keyboard.glb"
const TEXTURES := "res://assets/props/quarters/steel/console_keyboard/"
static var _materials: Dictionary = {}

static func build(state: StringName) -> Node3D:
	assert(state in QuartersProps.STATES, "known keyboard finish")
	var keyboard := (load(SCENE) as PackedScene).instantiate() as Node3D
	keyboard.name = "console_keyboard"
	if not _materials.has(state):
		var mesh := keyboard.find_child("Keyboard", true, false) as MeshInstance3D
		var finish := mesh.get_active_material(0).duplicate() as StandardMaterial3D
		finish.albedo_texture = load(TEXTURES + "%s_albedo.png" % state)
		finish.normal_texture = load(TEXTURES + "%s_normal.png" % state)
		var orm: Texture2D = load(TEXTURES + "%s_orm.png" % state)
		finish.ao_texture = orm
		finish.roughness_texture = orm
		finish.metallic_texture = orm
		_materials[state] = finish
	for piece: MeshInstance3D in keyboard.find_children("*", "MeshInstance3D", true, false):
		piece.material_override = _materials[state]
	return keyboard
