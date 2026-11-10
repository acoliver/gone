class_name StatusBoard
extends MeshInstance3D

const PERCEPTION_SHADER := preload("res://app/status_board.gdshader")
const SCREEN_SIZE := Vector2(2.4, 1.02)

var perception: DisplayPerception
var _material: ShaderMaterial
var _amount: float = -1.0

static func build(memory: DisplayPerception.Memory) -> StatusBoard:
	var board := StatusBoard.new()
	board.name = "StatusBoard"
	board.perception = DisplayPerception.new(memory)
	var quad := QuadMesh.new()
	quad.size = SCREEN_SIZE
	board.mesh = quad
	board.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	board._material = ShaderMaterial.new()
	board._material.shader = PERCEPTION_SHADER
	board._material.set_shader_parameter("native_board", load("res://assets/props/status_panel/board-native.png"))
	board._material.set_shader_parameter("perceived_board", load("res://assets/props/status_panel/board-perceived.png"))
	board.material_override = board._material
	return board

func tick_attention(eye: Vector3, forward: Vector3) -> void:
	perception.tick(DisplayPerception.attends(eye, forward, global_position,
		global_basis.x * SCREEN_SIZE.x * 0.5, global_basis.y * SCREEN_SIZE.y * 0.5,
		global_basis.z))
	if not is_equal_approx(_amount, perception.perceive):
		_amount = perception.perceive
		_material.set_shader_parameter("perceive", _amount)
