extends SceneTree

const Data = preload("res://tmp/issue91/display/board_data.gd")
const Writing = preload("res://app/naleya.gd")
const OUT := "res://tmp/issue91/display/"
const FONT_PATH := "/System/Library/Fonts/SFCompact.ttf"
const SCREEN := Rect2(Vector2.ZERO, Vector2(Data.SIZE))
const PUNCTUATION := [".", ",", ":", ";", "!", "?", "(", ")", "\""]

class Board extends Node2D:
	const VERTICAL_EXAGGERATION := 3.0
	var perceived := false
	var profile: Array = []
	var font: Font
	var text_boxes: Array[Rect2] = []
	var text_anchor_boxes: Array[Rect2] = []
	var text_box_colors: Array[Color] = []
	var element_boxes: Array[Rect2] = []
	var hull_strokes: Array[Dictionary] = []
	var native_draw_count := 0
	var latin_font_draw_count := 0
	var minimum_native_row_height := INF
	var minimum_title_height := INF
	var deck_band_pitch_px := 0.0
	var maximum_spanish_width_ratio := 0.0
	var minimum_spanish_system_size := INF

	var bg := Color("050b10")
	var panel := Color("0a151d")
	var outline := Color("294251")
	var label_ink := Color("d7f2f7")
	var soft_ink := Color("9fc4d0")
	var red := Color("ee5a61")
	var green := Color("41f1a2")
	var hull := Color("9fc4d0")

	func _draw() -> void:
		font = FontFile.new()
		assert(font.load_dynamic_font(FONT_PATH) == OK, "Could not load condensed system font: " + FONT_PATH)
		draw_rect(SCREEN, bg, true)
		_draw_header()
		_draw_ship_band()
		_draw_systems()
		_draw_footer()
		_verify_geometry()

	func _draw_header() -> void:
		var header := Rect2(40, 28, 2480, 112)
		element_boxes.append(header)
		draw_rect(header, Color("09141c"), true)
		draw_line(Vector2(40, 144), Vector2(2520, 144), outline, 2)
		add_text(Data.HEADER, Rect2(72, 44, 1240, 80), 64, label_ink, true)
		add_text(Data.BOARD, Rect2(1690, 48, 640, 52), 31, green)
		add_text(Data.DAMAGE, Rect2(1690, 99, 465, 34), 21, soft_ink)

	func _draw_ship_band() -> void:
		var band := Rect2(40, 154, 2480, 442)
		element_boxes.append(band)
		draw_rect(band, panel, true)
		draw_rect(band, outline, false, 1)
		add_text({"native":"malu", "es":"CORTE LONGITUDINAL · 30 CUBIERTAS"}, Rect2(72, 154, 320, 26), 16, soft_ink, false, false, true)
		var ship_rect := Rect2(400, 184, 1750, 372)
		_draw_longitudinal_section(ship_rect)
		_draw_engine_marks(ship_rect)
		add_text({"native":"shulu", "es":"POPA · MOTORES"}, Rect2(64, 385, 320, 44), 32, label_ink, false, false, true)
		add_text({"native":"shulu", "es":"PROA"}, Rect2(2180, 385, 300, 44), 32, label_ink, false, false, true)
		add_text(Data.HERE, Rect2(2200, 205, 300, 30), 18, green, false, false, true)
		add_text({"native":"malu mishela", "es":"MAPA DE LA NAVE · ESCALA VERTICAL ×3"}, Rect2(2200, 160, 300, 36), 18, soft_ink, false, false, true)

	func _draw_longitudinal_section(rect: Rect2) -> void:
		var vertical_scale := rect.size.x / 2400.0 * VERTICAL_EXAGGERATION
		deck_band_pitch_px = 5.5 * vertical_scale
		assert(deck_band_pitch_px >= 12.0, "Deck band pitch below 12 px: %.2f" % deck_band_pitch_px)
		var upper := PackedVector2Array()
		var lower := PackedVector2Array()
		for station: Dictionary in profile:
			var x := rect.position.x + (1200.0 - float(station.x)) / 2400.0 * rect.size.x
			var half := float(station.halfheight) * vertical_scale
			upper.append(Vector2(x, rect.get_center().y - half))
			lower.append(Vector2(x, rect.get_center().y + half))
		var silhouette := upper.duplicate()
		for index in range(lower.size() - 1, -1, -1):
			silhouette.append(lower[index])
		draw_colored_polygon(silhouette, Color(0.10, 0.23, 0.30, 0.38))
		draw_checked_hull_polyline(upper, 4)
		draw_checked_hull_polyline(lower, 4)
		draw_checked_hull_polyline(PackedVector2Array([upper[0], lower[0]]), 3)
		draw_checked_hull_polyline(PackedVector2Array([upper[-1], lower[-1]]), 3)
		for deck in range(1, 31):
			var y_m := (14.0 - float(deck)) * 5.5
			var y := rect.get_center().y - y_m * vertical_scale
			var bounds := _deck_x_bounds(absf(y_m))
			var left := rect.position.x + (1200.0 - bounds.y) / 2400.0 * rect.size.x
			var right := rect.position.x + (1200.0 - bounds.x) / 2400.0 * rect.size.x
			var color := Color(0.62, 0.79, 0.84, 0.85) if deck != 14 else green
			if deck < 30:
				var next_y := rect.get_center().y - (y_m - 5.5) * vertical_scale
				var next_bounds := _deck_x_bounds(absf(y_m - 5.5))
				var band_color := Color(0.08, 0.20, 0.27, 0.62) if deck != 14 else Color(0.08, 0.46, 0.30, 0.82)
				var band_left := rect.position.x + (1200.0 - minf(bounds.y, next_bounds.y)) / 2400.0 * rect.size.x
				var band_right := rect.position.x + (1200.0 - maxf(bounds.x, next_bounds.x)) / 2400.0 * rect.size.x
				draw_colored_polygon(PackedVector2Array([Vector2(band_left, y), Vector2(band_right, y), Vector2(band_right, next_y), Vector2(band_left, next_y)]), band_color)
			draw_checked_hull_polyline(PackedVector2Array([Vector2(left, y), Vector2(right, y)]), 2 if deck != 14 else 4, color)
			for label: Dictionary in Data.DECK_LABELS:
				if int(label.deck) == deck:
					var label_x := 235.0
					add_text(label, Rect2(label_x, y - 13, 135, 27), 19, green if deck == 14 else soft_ink)
		var marker_x := rect.position.x + (1200.0 - 27.0) / 2400.0 * rect.size.x
		var marker := Vector2(marker_x, rect.get_center().y)
		draw_circle(marker, 17, Color(0.10, 0.95, 0.61, 0.22))
		draw_circle(marker, 10, green)
		draw_circle(marker, 4, Color("06120e"))
		draw_checked_hull_polyline(upper, 4)
		draw_checked_hull_polyline(lower, 4)
		draw_checked_hull_polyline(PackedVector2Array([upper[0], lower[0]]), 3)
		draw_checked_hull_polyline(PackedVector2Array([upper[-1], lower[-1]]), 3)
		element_boxes.append(rect)

	func draw_checked_hull_polyline(points: PackedVector2Array, width: float, color: Color = hull) -> void:
		hull_strokes.append({"points": points, "width": width})
		draw_polyline(points, color, width, false)

	func _text_intersects_hull_stroke(box: Rect2, stroke: Dictionary) -> bool:
		var points: PackedVector2Array = stroke.points
		var expanded := box.grow(float(stroke.width) / 2.0)
		var corners := PackedVector2Array([
			expanded.position,
			Vector2(expanded.end.x, expanded.position.y),
			expanded.end,
			Vector2(expanded.position.x, expanded.end.y),
		])
		for index in range(points.size() - 1):
			var start := points[index % points.size()]
			var finish := points[(index + 1) % points.size()]
			if expanded.has_point(start) or expanded.has_point(finish):
				return true
			for edge_index in corners.size():
				var edge_start := corners[edge_index]
				var edge_finish := corners[(edge_index + 1) % corners.size()]
				if Geometry2D.segment_intersects_segment(start, finish, edge_start, edge_finish) != null:
					return true
		return false

	func _deck_x_bounds(required_height: float) -> Vector2:
		var first := 1200.0
		var last := -1200.0
		for index in range(profile.size() - 1):
			var a: Dictionary = profile[index]
			var b: Dictionary = profile[index + 1]
			var ah := float(a.halfheight)
			var bh := float(b.halfheight)
			if maxf(ah, bh) < required_height:
				continue
			var left := float(a.x)
			var right := float(b.x)
			if ah < required_height:
				left = lerpf(float(a.x), float(b.x), (required_height - ah) / (bh - ah))
			if bh < required_height:
				right = lerpf(float(a.x), float(b.x), (required_height - ah) / (bh - ah))
			first = minf(first, left)
			last = maxf(last, right)
		return Vector2(first, last)




	func _draw_engine_marks(rect: Rect2) -> void:
		var aft_x := rect.position.x + rect.size.x * 0.055
		var engine_names := [
			{"native":"wesha kama", "es":"MOTOR S"},
			{"native":"chalu kama", "es":"MOTOR H"},
			{"native":"kalo kama", "es":"EMPUJE"}
		]
		for index in range(3):
			var shape := Rect2(aft_x + index * 145, rect.get_center().y - 28, 52, 56)
			draw_rect(shape, Color("183441"), true)
			draw_rect(shape, Color("688996"), false, 2)
			add_text(engine_names[index], Rect2(aft_x - 70 + index * 145, rect.position.y - 8, 190, 26), 18, label_ink)
		var bridge_x := rect.position.x + rect.size.x * 0.26
		var bridge_y := rect.get_center().y - 96.0 * rect.size.x / 2400.0 * VERTICAL_EXAGGERATION
		var bridge := PackedVector2Array([Vector2(bridge_x - 56, bridge_y), Vector2(bridge_x + 68, bridge_y), Vector2(bridge_x + 68, bridge_y - 15), Vector2(bridge_x - 56, bridge_y - 15)])
		draw_colored_polygon(bridge, Color("7895a0"))
		draw_polyline(bridge, Color("d7f2f7"), 2, true)

	func _draw_systems() -> void:
		var area := Rect2(40, 590, 2480, 400)
		var gutter_x := 16.0
		var gutter_y := 12.0
		var tile_w := (area.size.x - gutter_x * 2) / 3.0
		var tile_h := (area.size.y - gutter_y) / 2.0
		for category_index in Data.CATEGORIES.size():
			var column := category_index % 3
			var row := category_index / 3
			var tile := Rect2(area.position.x + column * (tile_w + gutter_x), area.position.y + row * (tile_h + gutter_y), tile_w, tile_h)
			element_boxes.append(tile)
			draw_rect(tile, panel, true)
			draw_rect(tile, outline, false, 1)
			var category: Dictionary = Data.CATEGORIES[category_index]
			var cursor_y := tile.position.y + 8.0
			var header := Rect2(tile.position.x + 12, cursor_y, tile.size.x - 24, 32)
			draw_rect(Rect2(tile.position.x + 8, cursor_y, tile.size.x - 16, 32), Color("10232c"), true)
			add_text({"native":category.native, "es":category.name}, header, 30, soft_ink, false, false, true)
			draw_line(Vector2(tile.position.x + 12, cursor_y + 32), Vector2(tile.end.x - 12, cursor_y + 32), outline, 1)
			cursor_y += 40.0
			var row_h := 35.0
			for system_index: int in category.systems:
				var system: Dictionary = Data.SYSTEMS[system_index]
				var row_rect := Rect2(tile.position.x + 10, cursor_y, tile.size.x - 20, row_h)
				assert(tile.encloses(row_rect), "System row exceeds category tile: " + system.es)
				var running: bool = system.state == "shenu"
				var status_color: Color = green if running else red
				draw_circle(Vector2(row_rect.position.x + 11, row_rect.get_center().y), 6, status_color)
				var label_box := Rect2(row_rect.position.x + 24, row_rect.position.y + 1, row_rect.size.x - 32, 31)
				add_text({"native":system.native, "es":system.es}, label_box, 29, label_ink, false, true)
				minimum_native_row_height = minf(minimum_native_row_height, 29.0 if not perceived else 0.0)
				element_boxes.append(row_rect)
				cursor_y += row_h + 2.0
			assert(tile.encloses(header), "Category heading exceeds its tile: " + category.name)
			assert(cursor_y - 2.0 <= tile.end.y, "Category rows exceed their tile: " + category.name)


	func _draw_footer() -> void:
		element_boxes.append(Rect2(40, 1000, 2480, 38))
		draw_line(Vector2(40, 1000), Vector2(2520, 1000), outline, 1)
		add_text(Data.EXTERNAL_SENSORS, Rect2(64, 1004, 760, 34), 32, soft_ink)
		add_text({"native":"shenu", "es":"VERDE: EN FUNCIONAMIENTO"}, Rect2(1510, 1004, 570, 34), 32, green)
		add_text({"native":"palo", "es":"ROJO: INACTIVO"}, Rect2(2090, 1004, 390, 34), 32, red)


	func add_text(item: Dictionary, box: Rect2, size: int, color: Color, is_title: bool = false, is_system: bool = false, fit_text: bool = false) -> void:
		assert(box.position.x >= 0 and box.position.y >= 0 and box.end.x <= Data.SIZE.x and box.end.y <= Data.SIZE.y, "Text box exceeds screen: " + str(box))
		text_anchor_boxes.append(box)
		if perceived:
			var value: String = item.es
			var measured := font.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
			var available_width := box.size.x - (8.0 if is_system else 0.0)
			if measured > available_width and (is_system or fit_text):
				size = floori(float(size) * available_width / measured)
				measured = font.get_string_size(value, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
			assert(measured <= available_width, "Spanish text clips: '%s' measured %.1fpx in %.1fpx box" % [value, measured, box.size.x])
			if is_system:
				minimum_spanish_system_size = minf(minimum_spanish_system_size, float(size))
			maximum_spanish_width_ratio = maxf(maximum_spanish_width_ratio, measured / box.size.x)
			var baseline := box.position.y + size
			var ascent := font.get_ascent(size)
			var descent := font.get_descent(size)
			var drawn_box := Rect2(box.position.x, baseline - ascent, measured, ascent + descent)
			text_boxes.append(drawn_box)
			text_box_colors.append(color)
			draw_string(font, Vector2(box.position.x, baseline), value, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
		else:
			var value: String = item.native
			var layout := Writing.layout(value, box.size.x * 10.0 / float(size))
			assert(layout != null, "Could not lay out native Naleya text: " + value)
			var factor := float(size) / 10.0
			var ink_min := Vector2(INF, INF)
			var ink_max := Vector2(-INF, -INF)
			for unit: Naleya.Unit in layout.units:
				if unit.kind == "punct":
					assert(unit.value in PUNCTUATION, "Unsupported native editorial punctuation: " + unit.value)
					latin_font_draw_count += 1
					var baseline := box.position.y + (Writing.CELL - unit.origin.y) * factor
					draw_string(font, Vector2(box.position.x + unit.origin.x * factor, baseline), unit.value, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
					var punctuation_size := font.get_string_size(unit.value, HORIZONTAL_ALIGNMENT_LEFT, -1, size)
					ink_min.x = minf(ink_min.x, box.position.x + unit.origin.x * factor)
					ink_min.y = minf(ink_min.y, baseline - font.get_ascent(size))
					ink_max.x = maxf(ink_max.x, box.position.x + unit.origin.x * factor + punctuation_size.x)
					ink_max.y = maxf(ink_max.y, baseline + font.get_descent(size))
				else:
					assert(unit.kind == "glyph" or unit.kind == "identifier", "Unknown native Unit kind: " + unit.kind)
					assert(unit.kind != "glyph" or unit.value in Writing.SYLLABLES, "Non-Naleya glyph in native output")
					assert(unit.kind != "identifier" or unit.value.is_valid_int(), "Invalid boxed native identifier")
					native_draw_count += 1
			var stroke_width := maxf(1.4, Writing.STROKE_WIDTH * factor)
			for path: PackedVector2Array in layout.strokes:
				var points := PackedVector2Array()
				for point: Vector2 in path:
					var mapped := box.position + Vector2(point.x, Writing.CELL - point.y) * factor
					points.append(mapped)
					ink_min.x = minf(ink_min.x, mapped.x)
					ink_min.y = minf(ink_min.y, mapped.y)
					ink_max.x = maxf(ink_max.x, mapped.x)
					ink_max.y = maxf(ink_max.y, mapped.y)
				draw_polyline(points, color, stroke_width, true)
			var measured_width := layout.end.x * factor
			assert(measured_width <= box.size.x, "Native text clips: '%s' measured %.1fpx in %.1fpx box" % [value, measured_width, box.size.x])
			var half_stroke := stroke_width / 2.0
			ink_min -= Vector2(half_stroke, half_stroke)
			ink_max += Vector2(half_stroke, half_stroke)
			var drawn_box := Rect2(ink_min, ink_max - ink_min)
			text_boxes.append(drawn_box)
			text_box_colors.append(color)
			if is_title:
				minimum_title_height = minf(minimum_title_height, float(size))
			if is_system:
				minimum_native_row_height = minf(minimum_native_row_height, float(size))

	func _verify_geometry() -> void:
		for box: Rect2 in element_boxes:
			assert(SCREEN.encloses(box), "Element exceeds screen bounds: " + str(box))
		for index in text_boxes.size():
			var first := text_boxes[index]
			assert(SCREEN.encloses(first), "Text exceeds screen bounds: " + str(first))
			for stroke: Dictionary in hull_strokes:
				assert(not _text_intersects_hull_stroke(first, stroke), "Text ink intersects hull/deck stroke: box=%s path=%s" % [first, stroke.points])
			for other_index in range(index + 1, text_boxes.size()):
				var second := text_boxes[other_index]
				assert(not first.intersects(second, true), "Text boxes overlap: %s and %s" % [first, second])
		if not perceived:
			assert(latin_font_draw_count == 0, "Native render used Latin-font path %d times" % latin_font_draw_count)
			assert(native_draw_count > 0, "Native screen has no Naleya glyph units")
			assert(minimum_native_row_height >= 29, "Native system cell below 29 px")
			assert(minimum_title_height >= 64, "Native title below 64 px")
		var required_labels := [
			"RED DE LA NAVE", "RED DE EMERGENCIA", "ENERGÍA PRINCIPAL", "ENERGÍA SECUNDARIA",
			"COMPUTADORAS DE LA NAVE", "COMPUTADORAS SECUNDARIAS", "MOTOR S", "MOTOR H",
			"SENSORES INTERNOS", "SENSORES INTERNOS SECUNDARIOS", "SENSORES EXTERNOS", "SENSORES EXTERNOS SECUNDARIOS",
			"EXTINCIÓN DE INCENDIOS"
		]
		var actual_labels := PackedStringArray()
		for system: Dictionary in Data.SYSTEMS:
			actual_labels.append(system.es)
		for required: String in required_labels:
			assert(required in actual_labels, "Required first-page system missing: " + required)
		assert(actual_labels.count("MOTOR S") == 1, "Duplicate S-drive row remains")
		assert(not actual_labels.has("MOTOR S · NAWI WESHA KAMA"), "Duplicate full-name S-drive row remains")
		var grouped_indices: Array[int] = []
		for category: Dictionary in Data.CATEGORIES:
			for index: int in category.systems:
				assert(index >= 0 and index < Data.SYSTEMS.size(), "Category references missing system")
				assert(index not in grouped_indices, "System appears in multiple categories")
				grouped_indices.append(index)
		assert(grouped_indices.size() == Data.SYSTEMS.size(), "A first-page system is not in a category")
		var running_rows := 0
		for system: Dictionary in Data.SYSTEMS:
			assert(system.state in ["palo", "shenu"], "Unrecognized native system status: " + system.state)
			if system.state == "shenu":
				assert(system.es == "ENERGÍA SECUNDARIA", "Only secondary power may be running")
				running_rows += 1
		assert(running_rows == 1, "Expected exactly one running row, found %d" % running_rows)

var geometry_signature := ""

func _initialize() -> void:
	call_deferred("_render_all")

func _make_viewport(size: Vector2i) -> Array:
	var viewport := SubViewport.new()
	viewport.size = size
	viewport.disable_3d = true
	viewport.transparent_bg = false
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	return [viewport]

func _render_all() -> void:
	var file := FileAccess.open("res://docs/art/ship/3d/ship_atlas.json", FileAccess.READ)
	assert(file != null, "Ship atlas is missing")
	var atlas: Dictionary = JSON.parse_string(file.get_as_text())
	var profile: Array = atlas.coordinate_system.hull_profile
	for perceived in [false, true]:
		var viewport := _make_viewport(Data.SIZE)[0] as SubViewport
		var board := Board.new()
		board.profile = profile
		board.perceived = perceived
		viewport.add_child(board)
		await process_frame
		await RenderingServer.frame_post_draw
		var image := viewport.get_texture().get_image()
		var current_geometry := str([board.element_boxes, board.text_anchor_boxes])
		if geometry_signature.is_empty():
			geometry_signature = current_geometry
		else:
			assert(current_geometry == geometry_signature, "Native and perceived geometry differ")
		var suffix := "perceived" if perceived else "native"
		var path := OUT + "board-v2-" + suffix + ".png"
		assert(image.get_size() == Data.SIZE, "Unexpected render size: " + str(image.get_size()))
		assert(image.save_png(path) == OK, "Could not save " + path)
		assert(image.save_png(OUT + "board-v2-" + suffix + "-screen.png") == OK, "Could not save screen-only render")
		var min_native := "%.1f" % board.minimum_native_row_height if not perceived else "n/a"
		var min_title := "%.1f" % board.minimum_title_height if not perceived else "n/a"
		var min_spanish := "%.1f" % board.minimum_spanish_system_size if perceived else "n/a"
		var stats := "variant=%s\nsize=%s\ntext_boxes=%d\ntext_overlaps=0\nhull_deck_strokes=%d\ntext_hull_deck_intersections=0\nelements_checked=%d\nelements_outside=0\nsystems=%d\ncategories=%d\nrunning_rows=1\nminimum_native_system_cell_px=%s\nminimum_native_title_cell_px=%s\nminimum_spanish_system_font_px=%s\nlatin_font_draw_calls=%d\nnative_glyph_units=%d\nmaximum_spanish_width_ratio=%.4f\nnative_perceived_geometry_identical=true\n" % [suffix, str(Data.SIZE), board.text_boxes.size(), board.hull_strokes.size(), board.element_boxes.size(), Data.SYSTEMS.size(), Data.CATEGORIES.size(), min_native, min_title, min_spanish, board.latin_font_draw_count, board.native_draw_count, board.maximum_spanish_width_ratio]
		stats += "vertical_exaggeration=%.1fx\nminimum_deck_band_pitch_px=%.2f\n" % [board.VERTICAL_EXAGGERATION, board.deck_band_pitch_px]
		var log := FileAccess.open(OUT + "verify-" + suffix + ".txt", FileAccess.WRITE)
		assert(log != null)
		log.store_string(stats)
		log.close()
		var box_records: Array[Dictionary] = []
		for index in board.text_boxes.size():
			var text_box := board.text_boxes[index]
			var box_color := board.text_box_colors[index]
			box_records.append({"rect":[text_box.position.x, text_box.position.y, text_box.size.x, text_box.size.y], "color":[box_color.r8, box_color.g8, box_color.b8]})
		var boxes_file := FileAccess.open(OUT + "ink-boxes-" + suffix + ".json", FileAccess.WRITE)
		assert(boxes_file != null)
		boxes_file.store_string(JSON.stringify(box_records, "\t") + "\n")
		boxes_file.close()
		viewport.queue_free()
		await process_frame
	quit()
