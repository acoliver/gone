class_name ShipTextCanvas
extends Node2D
## A static text texture. Native ink only comes from Naleya's expanded paths.

const Writing = preload("res://app/naleya.gd")
const TEXTURE_SIZE := Vector2i(1024, 640)
const SCREEN_HEIGHT: float = 0.58
const HEAD_Y: float = 0.12
const STATE_Y: float = -0.10
const HEAD_COLOR := Color(0.75, 0.85, 0.95)
const STATE_COLOR := Color(0.85, 0.95, 1.0)

var native: bool = true
var heading: String = ""
var state_word: String = ""
var stroke_quads: Array[PackedVector2Array] = []
var _head_quad_count: int = 0

func set_text(head: String, state: String) -> void:
	heading = head
	state_word = state
	stroke_quads.clear()
	if native and not state.is_empty():
		_append_native(head, 6.0, HEAD_Y)
		_head_quad_count = stroke_quads.size()
		_append_native(state, 12.0, STATE_Y)
	queue_redraw()

func _append_native(text: String, scale_pixels: float, screen_y: float) -> void:
	var layout := Writing.layout(text, 150.0)
	assert(layout != null, "authored native text must lay out")
	var quads := Writing.expand_strokes(layout.strokes)
	var bounds := Rect2(quads[0][0], Vector2.ZERO)
	for quad: PackedVector2Array in quads:
		for point: Vector2 in quad:
			bounds = bounds.expand(point)
	var center := bounds.get_center()
	for quad: PackedVector2Array in quads:
		var pixels := PackedVector2Array()
		for point: Vector2 in quad:
			pixels.append(Vector2(
				TEXTURE_SIZE.x * 0.5 + (point.x - center.x) * scale_pixels,
				_pixel_y(screen_y) - (point.y - center.y) * scale_pixels))
		stroke_quads.append(pixels)

static func _pixel_y(screen_y: float) -> float:
	return TEXTURE_SIZE.y * (0.5 - screen_y / SCREEN_HEIGHT)

func _draw() -> void:
	if state_word.is_empty():
		return
	if native:
		for index: int in range(stroke_quads.size()):
			draw_colored_polygon(stroke_quads[index], HEAD_COLOR if index < _head_quad_count else STATE_COLOR)
	else:
		_draw_spanish(heading, 52, HEAD_Y, HEAD_COLOR)
		_draw_spanish(state_word, 104, STATE_Y, STATE_COLOR)

func _draw_spanish(text: String, size_pixels: int, screen_y: float, color: Color) -> void:
	var font := ThemeDB.fallback_font
	var font_size := size_pixels
	var max_width := TEXTURE_SIZE.x * 0.91
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	if width > max_width:
		font_size = floori(font_size * max_width / width)
		width = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	var baseline := _pixel_y(screen_y) + (font.get_ascent(font_size) - font.get_descent(font_size)) * 0.5
	draw_string(font, Vector2((TEXTURE_SIZE.x - width) * 0.5, baseline), text,
		HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)
