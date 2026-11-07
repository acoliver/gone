class_name ShipLabel
extends Node3D
## One independent blend material, backed by a shared immutable texture pair.

var face_id: StringName
var perception: DisplayPerception
var pair: ShipTextCache.Pair
var _cache: ShipTextCache
var _size: Vector2
var _quad: MeshInstance3D
var _material: ShaderMaterial
var _rendered_amount: float = -1.0

static func build(cache: ShipTextCache, text: ShipText.LabelText, id: StringName, frame: Transform3D, size: Vector2, state: DisplayPerception) -> ShipLabel:
	var label := ShipLabel.new()
	label.name = "NavigationLabel"
	label.face_id = id
	label.transform = frame
	label._size = size
	label.perception = state
	label._cache = cache
	label.pair = cache.acquire(text, &"door" if text.native.count("\n") > 1 else &"navigation")
	cache.pair_ready.connect(label._pair_ready)
	if label.pair.ready():
		label._attach()
	return label

func _pair_ready(key: String) -> void:
	if key == pair.key:
		_attach()

func _attach() -> void:
	assert(_quad == null, "label attaches once after raster completion")
	_material = ShaderMaterial.new()
	_material.shader = ShipDisplay.INK_SHADER
	_material.set_shader_parameter("native_ink", pair.native_texture())
	_material.set_shader_parameter("perceived_ink", pair.perceived_texture())
	_quad = MeshInstance3D.new()
	_quad.name = "TextSurface"
	var mesh := QuadMesh.new()
	mesh.size = _size
	_quad.mesh = mesh
	_quad.material_override = _material
	_quad.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_quad)
	present()

func present() -> void:
	if _material != null and perception.perceive != _rendered_amount:
		_rendered_amount = perception.perceive
		_material.set_shader_parameter("perceive", _rendered_amount)

func _exit_tree() -> void:
	_cache.release(pair.key)
