class_name WakePass
extends CanvasLayer
## The eyelid post pass as a presentation node, ported from gone_app
## wake_pass.rs: a top CanvasLayer whose full-screen ColorRect runs the
## wake_eyelid shader over the finished frame (the Godot stock path for a
## post effect over the 3D view — no nested viewports). The uniform is
## the shader param triple mapped 1:1 from a WakeSample; the sample's
## sway offset is deliberately unmapped, it is camera motion for the
## presentation driver. The pass exists carrying the fully closed state,
## so no presented frame ever shows the un-liddered room, and it is
## deactivated at completion (the neutral hold is a passthrough, no
## full-screen draw is spent on it).

const SHADER_PATH: String = "res://app/wake_eyelid.gdshader"
## Above every game layer; the lids composite over the presented frame.
const LAYER_ORDER: int = 100

var _rect: ColorRect = null
var _material: ShaderMaterial = null

## The pass node wired for the main scene: the shader's uniform defaults
## are the neutral passthrough, then the closed sample is written, so the
## first frame an un-started wake presents is fully closed.
static func build() -> WakePass:
	var pass_layer := WakePass.new()
	pass_layer.name = "WakePass"
	pass_layer.layer = LAYER_ORDER
	pass_layer._material = ShaderMaterial.new()
	pass_layer._material.shader = load(SHADER_PATH) as Shader
	pass_layer._rect = ColorRect.new()
	pass_layer._rect.name = "Eyelid"
	pass_layer._rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	pass_layer._rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pass_layer._rect.material = pass_layer._material
	pass_layer.add_child(pass_layer._rect)
	pass_layer.apply_closed()
	return pass_layer

## The shader param triple of a sample, sway ignored. Pure; the driver
## writes it onto the material.
static func params_from_sample(sample: Wake.WakeSample) -> Dictionary:
	return {
		"lid_openness": sample.lid_openness,
		"blur": sample.blur,
		"exposure_ramp": sample.exposure_ramp,
	}

## Write one sample's params onto the material. A pure projection of the
## sim's sample: no state, no timing.
func apply_sample(sample: Wake.WakeSample) -> void:
	var params := params_from_sample(sample)
	for key: String in params:
		_material.set_shader_parameter(key, params[key])

## The fully closed rest state: what an un-started wake presents.
func apply_closed() -> void:
	apply_sample(Wake.WakeSample.closed())

## The material's current param triple, for wiring assertions.
func params() -> Dictionary:
	var current := {}
	for key: String in ["lid_openness", "blur", "exposure_ramp"]:
		current[key] = _material.get_shader_parameter(key)
	return current

## Deactivate the pass (completion): the rect stops drawing, so the
## neutral hold costs no full-screen composite.
func set_active(active: bool) -> void:
	_rect.visible = active

func is_active() -> bool:
	return _rect.visible
