extends SceneTree

const Data = preload("res://app/status_board_data.gd")
const Naleya = preload("res://app/naleya.gd")
const FONT_PATH := "/System/Library/Fonts/SFCompact.ttf"
const SIZE := Vector2i(2560, 1080)
const MARGIN := 40.0
const ROW_CELL_PX := float(Data.MINIMUM_ROW_CELL_PX)
const COLUMN_SYSTEMS := [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13]]
const COLUMNS := ["ENERGÍA Y RED", "COMPUTACIÓN Y SENSORES", "SEGURIDAD Y SOPORTE"]
const NATIVE_COLUMNS := ["nawa chena", "kimela shoketa", "tewe talu"]

class Canvas extends Node2D:
	var perceived := false
	var font: Font
	var boxes: Array[Rect2] = []
	var ink_boxes: Array[Rect2] = []
	var ship_geometry := ""

	func _draw() -> void:
		font = FontFile.new()
		assert(font.load_dynamic_font(FONT_PATH) == OK)
		draw_rect(Rect2(Vector2.ZERO, SIZE), Color("050b10"), true)
		_header()
		_ship_elevation()
		_systems()
		_validate()

	func _header() -> void:
		draw_rect(Rect2(40, 28, 2480, 108), Color("09141c"), true)
		_draw_label({"native":"malu mishela", "es":"MAPA DE LA NAVE"}, Rect2(72, 52, 950, 72), 60, Color("d7f2f7"))
		_draw_label({"native":"te mu nawa lina shenu", "es":"SISTEMA SECUNDARIO ACTIVO"}, Rect2(1540, 46, 940, 54), 38, Color("41f1a2"))
		_draw_label({"native":"mo lokemi malu", "es":"SIN DAÑOS EN LA NAVE"}, Rect2(1540, 110, 940, 24), 22, Color("9fc4d0"))

	func _ship_elevation() -> void:
		var band := Rect2(40, 150, 2480, 400)
		boxes.append(band)
		draw_rect(band, Color("0a151d"), true)
		draw_rect(band, Color("294251"), false, 2)
		_draw_label({"native":Data.DECK_COUNT.native, "es":Data.DECK_COUNT.perceived_es}, Rect2(62, 162, 1200, 42), 34, Color("9fc4d0"))
		var drawing := Data.side_elevation(Rect2(470, 214, 1510, 300))
		ship_geometry = str(drawing)
		var hull: PackedVector2Array = drawing.hull
		draw_colored_polygon(hull, Color("10232c"))
		for deck: Dictionary in drawing.decks:
			var color := Color("41f1a2") if deck.highlighted else Color("688996")
			var line: PackedVector2Array = deck.line
			draw_line(line[0], line[1], color, 4 if deck.highlighted else 2)
			boxes.append(Rect2(line[0], line[1] - line[0]))
		hull.append(hull[0])
		draw_polyline(hull, Color("9fc4d0"), 3)
		var marker: Vector2 = drawing.marker
		draw_circle(marker, 13, Color("41f1a2"))
		draw_circle(marker, 5, Color("050b10"))
		_draw_label({"native":Data.HERE.native, "es":Data.HERE.perceived_es}, Rect2(1992, 332, 500, 44), 28, Color("41f1a2"))
		_draw_label({"native":"shulu", "es":"POPA"}, Rect2(62, 430, 300, 48), 36, Color("d7f2f7"))
		_draw_label({"native":"shulu", "es":"PROA"}, Rect2(2170, 430, 300, 48), 36, Color("d7f2f7"))
		assert(drawing.decks.size() == 30, "board elevation draws all 30 deck levels")

	func _systems() -> void:
		var area := Rect2(40, 574, 2480, 466)
		var gutter := 20.0
		var width := (area.size.x - gutter * 2) / 3.0
		for col in range(3):
			var tile := Rect2(area.position.x + col * (width + gutter), area.position.y, width, area.size.y)
			boxes.append(tile)
			draw_rect(tile, Color("0a151d"), true)
			draw_rect(tile, Color("294251"), false, 2)
			_draw_label({"native":NATIVE_COLUMNS[col], "es":COLUMNS[col]}, Rect2(tile.position.x + 18, tile.position.y + 14, tile.size.x - 36, 62), 48, Color("9fc4d0"))
			var cursor := tile.position.y + 90
			for index: int in COLUMN_SYSTEMS[col]:
				var row := Rect2(tile.position.x + 16, cursor, tile.size.x - 32, ROW_CELL_PX)
				assert(tile.encloses(row), "System row outside board column")
				var running: bool = Data.SYSTEMS[index].state == "shenu"
				draw_circle(Vector2(row.position.x + 22, row.get_center().y), 15, Color("41f1a2") if running else Color("ee5a61"))
				var item := {"native":Data.SYSTEMS[index].native, "es":Data.SYSTEMS[index].perceived_es}
				_draw_label(item, Rect2(row.position.x + 54, row.position.y + 2, row.size.x - 68, row.size.y - 4), 54, Color("d7f2f7"))
				cursor += ROW_CELL_PX + 12
		assert(ROW_CELL_PX >= 60.0, "Minimum system row cell is 60 px")

	func _draw_label(item: Dictionary, box: Rect2, size: int, color: Color) -> void:
		boxes.append(box)
		var text := str(item.es) if perceived else str(item.native)
		var baseline := box.position.y + box.size.y * 0.76
		if perceived:
			var fitted := size
			while fitted > 1 and font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fitted).x > box.size.x:
				fitted -= 1
			var measured := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fitted)
			draw_string(font, Vector2(box.position.x, baseline), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fitted, color)
			ink_boxes.append(Rect2(box.position.x, baseline - font.get_ascent(fitted), measured.x, font.get_ascent(fitted) + font.get_descent(fitted)))
		else:
			var layout := Naleya.layout(text, box.size.x * Naleya.CELL / float(size))
			assert(layout != null, "Could not arrange native board label: " + text)
			var scale := float(size) / Naleya.CELL
			var ink_min := Vector2(INF, INF)
			var ink_max := Vector2(-INF, -INF)
			for path: PackedVector2Array in layout.strokes:
				var points := PackedVector2Array()
				for point: Vector2 in path:
					var mapped := box.position + Vector2(point.x, Naleya.CELL - point.y) * scale
					points.append(mapped)
					ink_min.x = minf(ink_min.x, mapped.x)
					ink_min.y = minf(ink_min.y, mapped.y)
					ink_max.x = maxf(ink_max.x, mapped.x)
					ink_max.y = maxf(ink_max.y, mapped.y)
				draw_polyline(points, color, maxf(2.0, Naleya.STROKE_WIDTH * scale), true)
			var half_stroke := maxf(2.0, Naleya.STROKE_WIDTH * scale) * 0.5
			ink_boxes.append(Rect2(ink_min - Vector2(half_stroke, half_stroke), ink_max - ink_min + Vector2(half_stroke * 2, half_stroke * 2)))

	func _validate() -> void:
		for box in ink_boxes:
			assert(box.position.x >= MARGIN and box.position.y >= MARGIN and box.end.x <= SIZE.x - MARGIN and box.end.y <= SIZE.y - MARGIN, "Rendered text ink violates 40 px margin: " + str(box))
			for other in ink_boxes:
				if box != other:
					assert(not box.intersects(other, true), "Rendered text ink overlaps: %s / %s" % [box, other])

var geometry := ""

func _initialize() -> void:
	call_deferred("_render")

func _render() -> void:
	for perceived in [false, true]:
		var viewport := SubViewport.new()
		viewport.size = SIZE
		viewport.disable_3d = true
		viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		root.add_child(viewport)
		var canvas := Canvas.new()
		canvas.perceived = perceived
		viewport.add_child(canvas)
		await process_frame
		await RenderingServer.frame_post_draw
		var signature := str(canvas.boxes) + canvas.ship_geometry
		if geometry.is_empty():
			geometry = signature
		else:
			assert(signature == geometry, "Native and perceived board geometry differs")
		var suffix := "perceived" if perceived else "native"
		var output := "res://assets/props/status_panel/board-%s.png" % suffix
		assert(viewport.get_texture().get_image().save_png(output) == OK, "Failed to write " + output)
		viewport.queue_free()
		await process_frame
	quit()
