class_name ShipDisplay
extends Node3D
## The console keeps semantic canvases; only the shared cache owns raster views.

const TextCanvas = preload("res://app/ship_text_canvas.gd")
const INK_SHADER = preload("res://app/ship_text.gdshader")

var perception: DisplayPerception
var native_canvas: ShipTextCanvas
var perceived_canvas: ShipTextCanvas
var physical_only: bool = false:
	set(value):
		physical_only = value
		_apply_perception()
var _cache: ShipTextCache
var _pair: ShipTextCache.Pair
var _prefetched: Array[ShipTextCache.Pair] = []
var _quad: MeshInstance3D
var _material: ShaderMaterial
var _rendered_amount: float = -1.0

static func build(memory: DisplayPerception.Memory, cache: ShipTextCache = null) -> ShipDisplay:
	var display := ShipDisplay.new()
	display.name = "ShipDisplay"
	display.perception = DisplayPerception.new(memory)
	display._cache = cache
	if cache == null:
		display._cache = ShipTextCache.new()
		display.add_child(display._cache)
	display._cache.pair_ready.connect(display._pair_ready)
	display.native_canvas = TextCanvas.new()
	display.perceived_canvas = TextCanvas.new()
	display.perceived_canvas.native = false
	for canvas: ShipTextCanvas in [display.native_canvas, display.perceived_canvas]:
		canvas.visible = false
		display.add_child(canvas)
	display._material = ShaderMaterial.new()
	display._material.shader = INK_SHADER
	display._quad = MeshInstance3D.new()
	display._quad.name = "TextSurface"
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.92, TextCanvas.SCREEN_HEIGHT)
	display._quad.mesh = mesh
	display._quad.material_override = display._material
	display._quad.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	display.add_child(display._quad)
	return display

func prefetch(heading_id: String, state_ids: Array[String]) -> void:
	if not _prefetched.is_empty():
		return
	for state_id: String in state_ids:
		_prefetched.append(_cache.acquire(_text(heading_id, state_id), &"console"))

static func _text(heading_id: String, state_id: String) -> ShipText.LabelText:
	var head := ShipText.message(heading_id)
	var state := ShipText.message(state_id)
	return ShipText.LabelText.new(head.native + "\n" + state.native, head.perceived_es + "\n" + state.perceived_es)

func set_messages(heading_id: String, state_id: String) -> void:
	perception.text_changed()
	if _pair != null:
		_cache.release(_pair.key)
		_pair = null
	var head := ShipText.message(heading_id) if not state_id.is_empty() else {}
	var state := ShipText.message(state_id) if not state_id.is_empty() else {}
	native_canvas.set_text(head.get("native", ""), state.get("native", ""))
	perceived_canvas.set_text(head.get("perceived_es", ""), state.get("perceived_es", ""))
	_quad.visible = not state_id.is_empty()
	if not state_id.is_empty():
		_pair = _cache.acquire(_text(heading_id, state_id), &"console")
		if _pair.ready():
			_pair_ready(_pair.key)
		else:
			# No stale message while a standalone display is being prepared.
			_material.set_shader_parameter("native_ink", null)
			_material.set_shader_parameter("perceived_ink", null)
	_apply_perception()

func _pair_ready(key: String) -> void:
	if _pair != null and key == _pair.key:
		_material.set_shader_parameter("native_ink", _pair.native_texture())
		_material.set_shader_parameter("perceived_ink", _pair.perceived_texture())

func tick_attention(eye: Vector3, camera_forward: Vector3) -> void:
	var screen_size := (_quad.mesh as QuadMesh).size
	var attend := not native_canvas.state_word.is_empty() \
		and DisplayPerception.attends(eye, camera_forward, global_position,
			global_basis.x * screen_size.x * 0.5, global_basis.y * screen_size.y * 0.5,
			global_basis.z)
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

func _exit_tree() -> void:
	if _pair != null:
		_cache.release(_pair.key)
	for pair: ShipTextCache.Pair in _prefetched:
		_cache.release(pair.key)
