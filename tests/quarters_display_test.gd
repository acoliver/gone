extends SimTestCase

func test_display_base_ignores_room_lights_and_text_has_high_contrast() -> void:
	var room := QuartersRoom.build(Game.new(114))
	for index: int in range(room.screens.size()):
		var finish := room.screens[index].material_override as StandardMaterial3D
		assert_int_equal(finish.shading_mode, BaseMaterial3D.SHADING_MODE_UNSHADED, "room lighting cannot wash out display")
		assert_true(finish.albedo_color.get_luminance() < .04, "dark display base")
		assert_true(finish.emission.get_luminance() * finish.emission_energy_multiplier < .08, "emission preserves dark base")
		var label := room.screen_labels[index]
		assert_false(label.shaded, "display text ignores room light")
		assert_true(label.modulate.get_luminance() > .9, "bright text")
		assert_true(label.pixel_size * 64 * 16 >= room.screens[index].get_aabb().size.x - .00001, "message uses readable display width")
	room.free()

func test_corruption_contains_bright_and_dark_blocks_and_changes_over_time() -> void:
	var game := Game.new(114)
	game.quarters.state = QuartersMemory.State.REMEMBERED
	var room := QuartersRoom.build(game)
	game.quarters.press_console()
	room.process_frame()
	assert_true(room.corruption.visible, "corruption phase active")
	var low := 1.0
	var high := 0.0
	var before: Array[Color] = []
	for block: MeshInstance3D in room.corruption.get_children():
		var finish := block.material_override as StandardMaterial3D
		assert_int_equal(finish.shading_mode, BaseMaterial3D.SHADING_MODE_UNSHADED, "corruption ignores lighting")
		low = minf(low, finish.albedo_color.get_luminance())
		high = maxf(high, finish.albedo_color.get_luminance())
		before.append(finish.albedo_color)
	assert_true(low < .03 and high > .7, "corruption includes near-black and bright signal blocks")
	for tick: int in range(4): game.quarters.tick()
	room.process_frame()
	var changed := false
	for index: int in range(before.size()):
		changed = changed or before[index] != room.corruption.get_child(index).material_override.albedo_color
	assert_true(changed, "corruption moves between frames")
	game.quarters.elapsed = QuartersMemory.CORRUPT_TICKS
	room.process_frame()
	assert_false(room.corruption.visible, "message phase clears corruption")
	assert_true("Hi honey." in room.screen_labels[0].text, "message text retained")
	game.quarters.elapsed += QuartersMemory.MESSAGE_TICKS
	room.process_frame()
	assert_true("MAIN SYSTEM FAULT" in room.screen_labels[0].text, "fault text retained")
	room.free()

func test_all_console_phases_wrap_to_actual_glyph_width() -> void:
	var room := QuartersRoom.build(Game.new(114))
	var label := room.screen_labels[0]
	var width := room.screens[0].get_aabb().size.x * .92 / label.pixel_size
	for text: String in [QuartersMemory.MESSAGE, QuartersMemory.FAULT, QuartersMemory.PLACEHOLDER, "PERSONAL MESSAGE / PRESS TO PLAY", "VIDEO DATA CORRUPTED"]:
		for line: String in QuartersRoom._wrapped(text).split("\n"):
			assert_true(ThemeDB.fallback_font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, label.font_size).x <= width, "console line fits display with margin: " + line)
	room.free()
