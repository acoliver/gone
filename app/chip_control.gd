class_name LaneChip
extends Control
## The frame-code chip shared by the harness lanes: a protocol-
## instrumentation Control painting the (tick, frame) lattice into the
## top-left of the captured view. Not scene lighting — it renders above
## the game layer only so captures are provably correlated to the
## timeline. Extracted from harness_mode.gd so the calibration lane
## paints the same chip.

const ChipProtocol := preload("res://harness/protocol.gd")

var code_tick: int = 0
var code_frame: int = 0

func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var size_px: Vector2i = ChipProtocol.chip_size()
	size = Vector2(size_px)

func set_code(p_tick: int, p_frame: int) -> void:
	if p_tick == code_tick and p_frame == code_frame:
		return
	code_tick = p_tick
	code_frame = p_frame
	queue_redraw()

func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), ChipProtocol.OFF_COLOR)
	for py: int in range(2 * ChipProtocol.CELL_H):
		for px: int in range(ChipProtocol.DIGITS * ChipProtocol.CELL_W):
			var color := ChipProtocol.chip_pixel(code_tick, code_frame, px, py)
			if color == ChipProtocol.ON_COLOR:
				var origin := Vector2(px, py) * ChipProtocol.PIXEL_SCALE
				draw_rect(Rect2(origin, Vector2(ChipProtocol.PIXEL_SCALE, ChipProtocol.PIXEL_SCALE)), color)
