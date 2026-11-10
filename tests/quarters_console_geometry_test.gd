extends SimTestCase

func test_taller_console_retains_desk_pose_and_cabinet_clearance_in_both_states() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var console := furnishings.get_node("Placement_console/console") as Node3D
		var screen := console.find_child("Display", true, false) as MeshInstance3D
		# #129: 16:10 replaces the 0.874 x 0.238 m strip, without scaling the deck.
		assert_close(screen.get_aabb().size, Vector3(.874, .54625, .004), "physical 16:10 display")
		assert_float_in_range(console.basis.y.length(), .999999, 1.000001, "layout must not shrink the refitted source height")
		var bounds := QuartersFurnishings._bounds(console)
		var cabinet := QuartersFurnishings._bounds(furnishings.get_node("Placement_lockers_over_bed/lockers_over_bed"))
		assert_float_in_range(cabinet.position.y - bounds.end.y, .2610, .2612, "trimmed upper cap increases measured cabinet clearance")
		assert_false(bounds.intersects(cabinet), "console clears upper cabinet mesh envelope")
		var key := console.find_child("Key_0_0", true, false) as MeshInstance3D
		assert_close(key.position, Vector3(-.425, .016, .0675), "keyboard remains at accepted deck-local position")
		assert_int_equal(console.find_children("Key_*", "MeshInstance3D", true, false).size(), 24, "24 keys retained")
		furnishings.free()

func test_entire_console_fits_unchanged_close_camera_with_margin() -> void:
	var output: Array = []
	var code := OS.execute(OS.get_executable_path(), ["--headless", "--path", ProjectSettings.globalize_path("res://"), "-s", "tests/quarters_console_frame_checks.gd"], output, true)
	assert_int_equal(code, 0, "console vertex projection: " + str(output))
	assert_true("CONSOLE FRAME PASS" in str(output), "projection check completed")

func test_baked_key_inventory_matches_production_native_stroke_expansion() -> void:
	var document: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tools/blender/quarters/console/legends.json"))
	assert_int_equal(document["keys"].size(), 24, "all key legends documented")
	assert_true(document.digits == Naleya.DIGITS, "production octal mapping")
	for key: Dictionary in document["keys"]:
		var layout := Naleya.layout(key.input, Naleya.ADVANCE)
		assert_true(layout != null and layout.units.size() == 1, "one production sign per cap")
		assert_true(layout.units[0].value == key.sign, "V/CV or octal digit resolves to maintained sign")
		var quads := Naleya.expand_strokes(layout.strokes)
		assert_int_equal(quads.size(), key.quads.size(), "production stroke count")
		for index: int in range(quads.size()):
			for corner: int in range(4):
				assert_true(quads[index][corner].is_equal_approx(Vector2(key.quads[index][corner][0], key.quads[index][corner][1])), "baked quad matches native renderer")

func test_all_playback_text_fits_taller_screen_with_margin() -> void:
	var game := Game.new(129)
	game.quarters.state = QuartersMemory.State.REMEMBERED
	var room := QuartersRoom.build(game)
	game.quarters.press_console()
	for elapsed: int in [0, QuartersMemory.CORRUPT_TICKS, QuartersMemory.CORRUPT_TICKS + QuartersMemory.MESSAGE_TICKS]:
		game.quarters.elapsed = elapsed
		room.process_frame()
		for index: int in range(room.screens.size()):
			var label := room.screen_labels[index]
			var size := room.screens[index].get_aabb().size
			var lines := label.text.split("\n")
			var height := label.font.get_height(label.font_size) * lines.size() * label.pixel_size
			assert_true(height <= size.y * .92, "all message lines fit physical height")
			for line: String in lines:
				var width := label.font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, label.font_size).x * label.pixel_size
				assert_true(width <= size.x * .92, "all message lines fit physical width")
	room.free()
