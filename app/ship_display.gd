class_name ShipDisplay
extends Node3D
## The physical texture remains native. Only the player's presentation blends.

const TextCanvas = preload("res://app/ship_text_canvas.gd")
const INK_SHADER = preload("res://app/ship_text.gdshader")

var perception: DisplayPerception
var native_canvas: ShipTextCanvas
var perceived_canvas: ShipTextCanvas
var physical_only: bool = false:
	set(value):
		physical_only = value
		_apply_perception()
var _native_view: SubViewport
var _perceived_view: SubViewport
var _quad: MeshInstance3D
var _material: ShaderMaterial
var _rendered_amount: float = -1.0

static func build(memory: DisplayPerception.Memory) -> ShipDisplay:
	var display := ShipDisplay.new()
	display.name = "ShipDisplay"
	display.perception = DisplayPerception.new(memory)
	display._native_view = display._text_view("NativeInk")
	display.native_canvas = TextCanvas.new()
	display._native_view.add_child(display.native_canvas)
	display._perceived_view = display._text_view("PerceivedInk")
	display.perceived_canvas = TextCanvas.new()
	display.perceived_canvas.native = false
	display._perceived_view.add_child(display.perceived_canvas)
	display._material = ShaderMaterial.new()
	display._material.shader = INK_SHADER
	display._material.set_shader_parameter("native_ink", display._native_view.get_texture())
	display._material.set_shader_parameter("perceived_ink", display._perceived_view.get_texture())
	display._quad = MeshInstance3D.new()
	display._quad.name = "TextSurface"
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.92, TextCanvas.SCREEN_HEIGHT)
	display._quad.mesh = mesh
	display._quad.material_override = display._material
	display._quad.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	display.add_child(display._quad)
	return display

func _text_view(view_name: String) -> SubViewport:
	var view := SubViewport.new()
	view.name = view_name
	view.size = TextCanvas.TEXTURE_SIZE
	view.transparent_bg = true
	view.disable_3d = true
	view.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(view)
	return view

func set_messages(heading_id: String, state_id: String) -> void:
	perception.text_changed()
	var head := ShipText.message(heading_id) if not state_id.is_empty() else {}
	var state := ShipText.message(state_id) if not state_id.is_empty() else {}
	native_canvas.set_text(head.get("native", ""), state.get("native", ""))
	perceived_canvas.set_text(head.get("perceived_es", ""), state.get("perceived_es", ""))
	_quad.visible = not state_id.is_empty()
	_native_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	_perceived_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	_apply_perception()

func tick_attention(eye: Vector3, camera_forward: Vector3) -> void:
	var attend := not native_canvas.state_word.is_empty() \
		and DisplayPerception.attends(eye, camera_forward, global_position, global_basis.z)
	perception.tick(attend)
	_apply_perception()

func perception_amount() -> float:
	return 0.0 if physical_only else perception.perceive

func _apply_perception() -> void:
	var amount := perception_amount()
	if amount == _rendered_amount:
		return
	_rendered_amount = amount
	_material.set_shader_parameter("perceive", amount)
