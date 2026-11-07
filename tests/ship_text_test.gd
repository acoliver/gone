extends SimTestCase

const Catalog = preload("res://app/ship_text.gd")
const Writing = preload("res://app/naleya.gd")

func test_single_line_lift_raster_compensates_for_half_height_quad() -> void:
	var hatch := ShipTextCanvas.new()
	var lift := ShipTextCanvas.new()
	hatch.set_lines("lometa [16]\nshelani paki [51]", &"navigation")
	lift.set_lines("lometa [16]", &"navigation")
	for index: int in range(lift.stroke_quads.size()):
		for point: int in range(4):
			assert_float_equal(lift.stroke_quads[index][point].x, hatch.stroke_quads[index][point].x, "same physical horizontal metric")
		var hatch_height := absf(hatch.stroke_quads[index][0].y - hatch.stroke_quads[index][2].y)
		var lift_height := absf(lift.stroke_quads[index][0].y - lift.stroke_quads[index][2].y)
		assert_true(absf(lift_height * 0.23 - hatch_height * 0.46) < 0.00002, "same physical vertical metric after projection")
	hatch.free()
	lift.free()

func test_navigation_factories_preserve_identifier_quantities() -> void:
	var label := Catalog.hatch_label(14, 41)
	assert_true(label.native == "lometa [16]\nshelani paki [51]", "native octal identifiers")
	assert_true(label.perceived_es == "CUBIERTA 14\nSECCIÓN 41", "decimal perceived quantities")
	assert_true(Catalog.deck_label(30).native == "lometa [36]", "deck thirty in octal")
	assert_true(Catalog.deck_label(30).perceived_es == "CUBIERTA 30", "single deck line for lifts")
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.kind() not in [ShipLayout.DoorKind.HATCH, ShipLayout.DoorKind.BAY]:
			continue
		for face_id: StringName in door.face_ids():
			var face := layout.face(face_id)
			var generated := Catalog.hatch_label(door.deck_number(), face.destination_section())
			assert_true(Writing.layout(generated.native, 150) != null, "every authored face has native text " + String(face_id))
			assert_true(generated.perceived_es == "CUBIERTA %d\nSECCIÓN %d" % [door.deck_number(), face.destination_section()], "every face preserves quantity")

func test_navigation_terms_are_authored_and_canvas_lines_have_equal_scale() -> void:
	for pair: Array in [["deck", "lometa", "CUBIERTA"], ["section", "shelani paki", "SECCIÓN"], ["lift", "kotewa", "ASCENSOR"], ["hatch", "pana", "ESCOTILLA"]]:
		assert_true(Catalog.message("navigation." + pair[0]) == {"native": pair[1], "perceived_es": pair[2]}, "navigation term " + pair[0])
	var canvas := ShipTextCanvas.new()
	canvas.set_lines("lometa [16]\nshelani paki [51]", &"navigation")
	assert_int_equal(canvas.lines.size(), 2, "two explicit sign lines")
	assert_false(canvas.stroke_quads.is_empty(), "native sign draws")
	for quad: PackedVector2Array in canvas.stroke_quads:
		for pixel: Vector2 in quad:
			assert_float_in_range(pixel.x, 0, 1024, "navigation width")
			assert_float_in_range(pixel.y, 0, 512, "navigation height")
	canvas.free()

func test_catalog_validates_every_native_word_on_load() -> void:
	assert_true(Catalog.VALID, "the loaded catalog is valid")
	assert_int_equal(Catalog.MESSAGES.size(), 10, "console and navigation terms plus level, bay and short room name")
	for id: String in Catalog.MESSAGES:
		var message: Dictionary = Catalog.message(id)
		assert_false(message.native.is_empty(), "native text required for " + id)
		assert_false(message.perceived_es.is_empty(), "Spanish text required for " + id)
		for word: String in message.native.split(" "):
			assert_false(Writing.syllabify(word).is_empty(), "valid native word " + word)

func test_console_catalog_preserves_authored_meanings() -> void:
	assert_true(Catalog.message("secondary_power.heading") == {"native": "te mu nawa lina", "perceived_es": "SISTEMA DE ENERGÍA SECUNDARIO"}, "heading pair")
	assert_true(Catalog.message("secondary_power.inactive") == {"native": "palo", "perceived_es": "INACTIVO"}, "off without a defect")
	assert_true(Catalog.message("secondary_power.active") == {"native": "shenu", "perceived_es": "EN FUNCIONAMIENTO"}, "running")
