class_name SmokeVision
extends CanvasLayer

const EFFECT: Shader = preload("res://app/smoke_vision.gdshader")
var symptoms: SmokeSymptoms
var wake_pass: WakePass
var _material: ShaderMaterial

static func build(state: SmokeSymptoms, wake: WakePass) -> SmokeVision:
	var layer := SmokeVision.new()
	layer.name = "SmokeVision"
	layer.layer = 99
	layer.symptoms = state
	layer.wake_pass = wake
	return layer

func _ready() -> void:
	var rect := ColorRect.new()
	rect.name = "PeripheralSymptoms"
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_material = ShaderMaterial.new()
	_material.shader = EFFECT
	rect.material = _material
	add_child(rect)

func _process(_delta: float) -> void:
	var state := symptoms.sample()
	_material.set_shader_parameter("dose", state.dose)
	_material.set_shader_parameter("cough_pulse", state.cough_pulse)
	_material.set_shader_parameter("breath_pulse", state.breath_pulse)
	_material.set_shader_parameter("viewport_size", get_viewport().get_visible_rect().size)
	visible = not wake_pass.is_active()
