extends SimTestCase

func _fill_mask(room: Node3D) -> int:
	if room is Lighting or room.name == "BayRoot":
		return 1 << 17
	return 1 << 18 if room is Hallway else 1 << 19

func test_fills_never_cast_shadows() -> void:
	for room: Node3D in _rooms(Game.new(91)):
		for fill: OmniLight3D in _fills(room):
			assert_false(fill.shadow_enabled, "dim fill must not render shadow passes")
		room.free()

func test_real_scene_fills_only_reach_their_own_room_layers() -> void:
	var root := Node3D.new()
	var game := Game.new(91)
	var scene := ShipScene.build_into(root, game, false)
	var rooms: Array[Node3D] = [scene.bay_root, scene.hallway, scene.power_room]
	var surfaces: Array[Node3D] = [scene.room, scene.hallway, scene.power_room]
	for source: int in range(rooms.size()):
		var fills := _fills(rooms[source])
		assert_int_equal(fills.size(), [6, 4, 6][source], "production fills survive scene assembly")
		for fill: OmniLight3D in fills:
			assert_int_equal(fill.light_cull_mask, _fill_mask(rooms[source]), "scene assembly preserves fill mask")
			for target: int in range(surfaces.size()):
				var meshes := surfaces[target].find_children("*", "GeometryInstance3D", true, false)
				assert_true(not meshes.is_empty(), "real room geometry is tested")
				for mesh: GeometryInstance3D in meshes:
					assert_true(((mesh.layers & fill.light_cull_mask) != 0) == (source == target), "fill lights its own room and cannot light either other room: %s" % mesh.name)
	var hatch := scene.hatch.view
	for side: String in ["ForeSteel", "AftSteel"]:
		var mesh: GeometryInstance3D = hatch.get_node("Frame/" + side)
		var expected := (1 << 18) if side == "ForeSteel" else (1 << 17)
		assert_int_equal(mesh.layers, 1 | expected, "bay hatch faces keep key layer and only their visible room's fill")
	root.free()

func test_fill_layers_do_not_overlap_any_independent_circuit() -> void:
	var layout := ShipLayout.authored().layout
	var reserved := (1 << 17) | (1 << 18) | (1 << 19)
	for deck: int in range(1, 31):
		for id: StringName in layout.deck(deck).connector_ids():
			assert_int_equal(Lighting.space_mask(layout, id) & reserved, 0, "connector circuit excludes fill layers")
		for number: int in [40, 41, 42]:
			var id := ShipLayout.section_id(deck, number)
			assert_int_equal(Lighting.space_mask(layout, id) & reserved, 0, "section circuit excludes fill layers")

func _rooms(game: Game) -> Array[Node3D]:
	return [Lighting.build(game), Hallway.build(game), PowerRoom.build(game)]

func _fills(room: Node3D) -> Array[Node]:
	return room.find_children("EmergencyFill*", "OmniLight3D", true, false)

func _assert_fills(room: Node3D, count: int, level: float) -> void:
	var fills := _fills(room)
	assert_int_equal(fills.size(), count, "explicit switched-room fill inventory")
	for fill: OmniLight3D in fills:
		assert_true(fill.get_parent() == room, "room owns fill beside its key fixtures")
		assert_true(fill.light_color == Color(1.0, 0.94, 0.84), "localized warm fill")
		assert_true(is_equal_approx(fill.light_energy, Lighting.FIXTURE_ENERGY * 0.1 * level), "fill follows the emergency fade")
		assert_int_equal(fill.light_cull_mask, _fill_mask(room), "fill uses only its room's reserved layer")

func test_fills_start_on_their_circuit_and_fade_without_restarting() -> void:
	var game := Game.new(91)
	var rooms := _rooms(game)
	var counts := [6, 4, 6]
	for index: int in range(rooms.size()):
		_assert_fills(rooms[index], counts[index], 1.0 if index == 0 else 0.0)
	game.light_hallway()
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		game.light_hallway()
		for index: int in range(rooms.size()):
			rooms[index].process_frame(Sim.LOGICAL_TICK_SECS)
			_assert_fills(rooms[index], counts[index], rooms[index].level())
	for room: Node3D in rooms:
		assert_true(room.is_settled(), "repeated targets do not restart the 30-tick fade")
		assert_float_equal(room.level(), 1.0, "emergency keys settle lit")
		room.free()

func test_fills_hold_then_extinguish_with_keys_at_secondary_handoff() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var rooms := _rooms(game)
	var counts := [6, 4, 6]
	game.press_console()
	for hold: int in range(10):
		for index: int in range(rooms.size()):
			rooms[index].process_frame(0.0)
			_assert_fills(rooms[index], counts[index], 1.0)
	var mirror := Intensity.FixtureFade.try_new(1.0, 0.0, Lighting.FIXTURE_SETTLE_TICKS).fade
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		game.press_console()
		var level := mirror.tick()
		for index: int in range(rooms.size()):
			rooms[index].process_frame(Sim.LOGICAL_TICK_SECS)
			_assert_fills(rooms[index], counts[index], level)
			assert_float_equal(rooms[index].level(), level, "fill and keys share the existing clock")
	for index: int in range(rooms.size()):
		_assert_fills(rooms[index], counts[index], 0.0)
		assert_true(rooms[index].is_settled(), "handoff settles on tick 30")
		rooms[index].free()
	var rebuilt := _rooms(game)
	for index: int in range(rebuilt.size()):
		_assert_fills(rebuilt[index], counts[index], 0.0)
		assert_float_equal(rebuilt[index].level(), 0.0, "rebuilt powered room starts with emergency keys off")
		assert_float_equal(rebuilt[index].white_level(), 1.0, "rebuilt powered room retains regular white")
		rebuilt[index].free()

func test_bay_fill_extinguishes_on_emergency_power_cut() -> void:
	var game := Game.new(91)
	var bay := Lighting.build(game)
	game.power.cut_emergency_power()
	for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		bay.process_frame(Sim.LOGICAL_TICK_SECS)
		_assert_fills(bay, 6, bay.level())
	_assert_fills(bay, 6, 0.0)
	bay.free()
	bay = Lighting.build(game)
	_assert_fills(bay, 6, 0.0)
	bay.free()

func test_every_emergency_circuit_uses_one_red_orange_palette_and_lens() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var rooms := _rooms(game)
	var palette := Color(1.0, 0.28, 0.12)
	for room: Node3D in rooms:
		for light: OmniLight3D in room.lights():
			assert_true(light.light_color == palette, "switched emergency palette")
		assert_true(room.lens_material().emission.is_equal_approx(Color(2.6, 2.6 * 0.28, 2.6 * 0.12)), "switched lens matches key palette")
		room.free()
	for deck: int in range(1, 31):
		for id: StringName in game.layout.deck(deck).connector_ids():
			var room := ShipConnector.build(game.layout, game.layout.connector(id))
			_assert_steady_palette(room, palette)
			assert_int_equal(_fills(room).size(), 0, "remote connectors get no fill")
			assert_int_equal(room.find_children("*", "OmniLight3D", true, false).size(), 3, "three lights per connector remains the budget")
			room.free()
	for number: int in [40, 42]:
		var room := ShipSection.build(game.layout, game.layout.section(ShipLayout.section_id(14, number)))
		_assert_steady_palette(room, palette)
		assert_int_equal(_fills(room).size(), 0, "outer sections get no fill")
		room.free()

func test_only_independent_no_fill_keys_use_the_readability_multiplier() -> void:
	var game := Game.new(91)
	game.light_hallway()
	var switched := _rooms(game)
	for room: Node3D in switched:
		for light: OmniLight3D in room.lights():
			assert_true(is_equal_approx(light.light_energy, Lighting.FIXTURE_ENERGY), "D14 switched keys retain their unboosted energy")
		room.free()
	var independent: Array[Node3D] = []
	for deck: int in range(1, 31):
		for id: StringName in game.layout.deck(deck).connector_ids():
			independent.append(ShipConnector.build(game.layout, game.layout.connector(id)))
	for number: int in [40, 42]:
		independent.append(ShipSection.build(game.layout, game.layout.section(ShipLayout.section_id(14, number))))
	var expected := Lighting.FIXTURE_ENERGY * Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER
	assert_true(expected > Lighting.FIXTURE_ENERGY, "no-fill keys restore readability with stronger energy")
	for room: Node3D in independent:
		for light: OmniLight3D in room.find_children("*", "OmniLight3D", true, false):
			assert_true(is_equal_approx(light.light_energy, expected), "all independent keys, including landings, use the shared no-fill multiplier")
		room.free()

func _assert_steady_palette(room: Node3D, palette: Color) -> void:
	for light: OmniLight3D in room.find_children("*", "OmniLight3D", true, false):
		assert_true(light.light_color == palette, "independent emergency palette")
		var lens: MeshInstance3D = light.get_parent().get_node("Lens")
		var material: StandardMaterial3D = lens.material_override
		assert_true(material.emission.is_equal_approx(Color(2.6, 2.6 * 0.28, 2.6 * 0.12)), "independent lens matches key palette")
