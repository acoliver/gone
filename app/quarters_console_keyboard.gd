class_name QuartersConsoleKeyboard
extends RefCounted
## The power-room mesh retains its own UVs and quarters-only finish sets.

const SCENE := "res://assets/props/quarters/console_keyboard.glb"
const TEXTURES := "res://assets/props/quarters/steel/console_keyboard/"
static var _materials: Dictionary = {}

static func build(state: StringName) -> Node3D:
	assert(state in QuartersProps.STATES, "known keyboard finish")
	if not _materials.has(state):
		var finish := ShaderMaterial.new()
		finish.shader = QuartersSteelLibrary.SHADER
		for kind: String in ["albedo", "normal", "orm"]:
			finish.set_shader_parameter("baked_" + kind, load(TEXTURES + "%s_%s.png" % [state, kind]))
		finish.set_shader_parameter(&"regions", load(TEXTURES + "regions.png"))
		finish.set_shader_parameter(&"paint_grain", Surfaces.HATCH_DETAIL_TEXTURES["albedo_b"])
		finish.set_shader_parameter(&"aged_finish", state == &"aged")
		_materials[state] = finish
	var keyboard := (load(SCENE) as PackedScene).instantiate() as Node3D
	keyboard.name = "console_keyboard"
	for piece: MeshInstance3D in keyboard.find_children("*", "MeshInstance3D", true, false):
		piece.material_override = _materials[state]
	return keyboard
