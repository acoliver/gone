class_name ShipTextCanvas
extends Node2D
## Static raster input. Native ink only comes from Naleya's expanded paths.

const Writing = preload("res://app/naleya.gd")
const TEXTURE_SIZE := Vector2i(1024, 640)
const NAVIGATION_SIZE := Vector2i(1024, 512)
const DOOR_SIZE := Vector2i(1024, 768)
const SCREEN_HEIGHT: float = 0.58
const HEAD_Y: float = 0.12
const STATE_Y: float = -0.10
const HEAD_COLOR := Color(0.75, 0.85, 0.95)
const STATE_COLOR := Color(0.85, 0.95, 1.0)
const LAYOUT_VERSION: int = 2

var native: bool = true
var heading: String = ""
var state_word: String = ""
var lines: PackedStringArray = []
var stroke_quads: Array[PackedVector2Array] = []
var _colors: Array[Color] = []
var _centers: Array[float] = []
var _font_sizes: Array[int] = []
var texture_size := TEXTURE_SIZE
var _vertical_scale: float = 1.0

static func size_for(style: StringName) -> Vector2i:
	assert(style in [&"console", &"navigation", &"door"], "known text style")
	if style == &"door": return DOOR_SIZE
	return TEXTURE_SIZE if style == &"console" else NAVIGATION_SIZE

func set_text(head: String, state: String) -> void:
	heading = head
	state_word = state
	set_lines("" if state.is_empty() else head + "\n" + state, &"console")

func set_lines(text: String, style: StringName) -> void:
	texture_size = size_for(style)
	lines = PackedStringArray() if text.is_empty() else text.split("\n")
	# The lift quad is half as high; preserve the glyphs' physical aspect ratio.
	_vertical_scale = 2.0 if style == &"navigation" and lines.size() == 1 else 1.0
	stroke_quads.clear()
	_colors.clear()
	_centers.clear()
	_font_sizes.clear()
	assert(lines.size() <= (4 if style == &"door" else 2), "text fits its authored sign style")
	for index: int in range(lines.size()):
		var console := style == &"console"
		var center := TEXTURE_SIZE.y * (0.5 - (HEAD_Y if index == 0 else STATE_Y) / SCREEN_HEIGHT) if console else NAVIGATION_SIZE.y * (0.5 if lines.size() == 1 else 0.27 + 0.46 * index)
		if style == &"door": center = DOOR_SIZE.y * (index + 0.5) / lines.size()
		var color := HEAD_COLOR if console and index == 0 else STATE_COLOR
		_centers.append(center)
		_font_sizes.append((52 if index == 0 else 104) if console else 82)
		if native:
			_append_native(lines[index], (6.0 if index == 0 else 12.0) if console else 8.0, center, color)
	queue_redraw()

func _append_native(text: String, scale_pixels: float, center_y: float, color: Color) -> void:
	var layout := Writing.layout(text, 150.0)
	assert(layout != null and layout.rows == 1, "authored line must fit")
	var quads := Writing.expand_strokes(layout.strokes)
	assert(not quads.is_empty(), "authored line has ink")
	var bounds := Rect2(quads[0][0], Vector2.ZERO)
	for quad: PackedVector2Array in quads:
		for point: Vector2 in quad:
			bounds = bounds.expand(point)
	scale_pixels = minf(scale_pixels, texture_size.x * 0.91 / bounds.size.x)
	var center := bounds.get_center()
	for quad: PackedVector2Array in quads:
		var pixels := PackedVector2Array()
		for point: Vector2 in quad:
			pixels.append(Vector2(texture_size.x * 0.5 + (point.x - center.x) * scale_pixels, center_y - (point.y - center.y) * scale_pixels * _vertical_scale))
		stroke_quads.append(pixels)
		_colors.append(color)

func _draw() -> void:
	if native:
		for index: int in range(stroke_quads.size()):
			draw_colored_polygon(stroke_quads[index], _colors[index])
	else:
		for index: int in range(lines.size()):
			_draw_spanish(lines[index], _font_sizes[index], _centers[index], HEAD_COLOR if texture_size == TEXTURE_SIZE and index == 0 else STATE_COLOR)

func _draw_spanish(text: String, size_pixels: int, center_y: float, color: Color) -> void:
	var font := ThemeDB.fallback_font
	var font_size := size_pixels
	var max_width := texture_size.x * 0.91
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	if width > max_width:
		font_size = floori(font_size * max_width / width)
		width = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	var baseline := (font.get_ascent(font_size) - font.get_descent(font_size)) * 0.5
	draw_set_transform(Vector2(0, center_y), 0, Vector2(1, _vertical_scale))
	draw_string(font, Vector2((texture_size.x - width) * 0.5, baseline), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)
	draw_set_transform(Vector2.ZERO)
