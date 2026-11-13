extends SimTestCase

const ASSETS := {
	"desk": "desk", "console": "console", "bedside_l": "bedside", "bedside_r": "bedside",
	"view_screen": "view_screen", "media_cabinet": "media_cabinet", "lockers_over_bed": "lockers_over_bed",
}

func test_remaining_batch_assets_replace_all_their_standins_in_both_states() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		for id: String in ASSETS:
			var placement := furnishings.get_node("Placement_" + id)
			assert_true(placement.find_children("Standin_*", "", true, false).is_empty(), "no replaced stand-ins at " + id)
			var asset := placement.get_node_or_null(ASSETS[id]) as Node3D
			assert_true(asset != null, "real furniture at " + id)
			if asset != null:
				assert_true(asset.scene_file_path == QuartersFurnishings.ROOT + ASSETS[id] + ".glb", "imported asset " + id)
		assert_true(furnishings.has_node("Placement_bed/bed_soft"), "real soft bed parts remain")
		furnishings.free()

func test_console_base_contacts_actual_worktop_without_clipping() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var desk := furnishings.get_node_or_null("Placement_desk/desk") as Node3D
		var console := furnishings.get_node_or_null("Placement_console/console") as Node3D
		assert_true(desk != null and console != null, "real desk and console")
		if desk != null and console != null:
			var top := desk.find_child("Worktop", true, false) as MeshInstance3D
			var worktop := ShipScene._world_frame(top) * top.get_aabb()
			var base := QuartersFurnishings._bounds(console)
			assert_float_in_range(base.position.y - worktop.end.y, -0.00001, 0.002, "console rests within 2 mm of desk")
			assert_true(base.position.x >= worktop.position.x and base.end.x <= worktop.end.x, "console fits worktop depth")
			assert_true(base.position.z >= worktop.position.z and base.end.z <= worktop.end.z, "console fits worktop width")
			for upper: MeshInstance3D in console.find_children("*", "MeshInstance3D", true, false):
				var upper_bounds := (ShipScene._world_frame(upper) * upper.get_aabb()).grow(-0.00001)
				for lower: MeshInstance3D in desk.find_children("*", "MeshInstance3D", true, false):
					assert_false(upper_bounds.intersects(ShipScene._world_frame(lower) * lower.get_aabb()), "console part %s clears desk part %s" % [upper.name, lower.name])
		furnishings.free()

func test_wall_mounted_assets_clear_shell_bed_and_each_other() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var mounted: Array[AABB] = []
		for id: String in ["view_screen", "lockers_over_bed"]:
			var asset := furnishings.get_node_or_null("Placement_%s/%s" % [id, id]) as Node3D
			assert_true(asset != null, "real mounted " + id)
			if asset == null: continue
			var bounds := QuartersFurnishings._bounds(asset)
			for solid: ShipGeometry.SolidSpec in QuartersGeometry.shell():
				assert_false(bounds.grow(-0.00001).intersects(AABB(solid.center - solid.size / 2, solid.size)), "mount clears shell " + id)
			assert_false(bounds.intersects(QuartersFurnishings._bounds(furnishings.get_node("Placement_bed"))), "mount clears bed " + id)
			for other: AABB in mounted: assert_false(bounds.intersects(other), "mounts clear each other")
			mounted.append(bounds)
			var base := 1.0 if id == "view_screen" else 1.9
			assert_float_in_range(bounds.position.y - QuartersLayout.FLOOR_Y, base - 0.00001, base + 0.00001, "layout mounting height " + id)
		furnishings.free()

func test_console_sequence_uses_imported_display_and_seated_text() -> void:
	var game := Game.new(114)
	game.quarters.observe_entry(QuartersLayout.to_world(Vector3(4, .305, -.1)), QuartersLayout.to_world(Vector3(4, .305, .1)), 16, true, true)
	var room := QuartersRoom.build(game)
	for index: int in range(2):
		var state := room.remembered if index == 0 else room.present
		var console := state.get_node_or_null("Placement_console/console")
		assert_true(console != null, "real console")
		if console == null: continue
		assert_true(room.screens[index] == console.find_child("Display", true, false), "sequence uses real display mesh")
		assert_true(room.screen_labels[index].get_parent() == room.screens[index], "text mounted on imported display")
		assert_true(room.screens[index].material_override.emission_enabled, "display emits in both states")
		assert_true(room.screens[index].material_override.emission_energy_multiplier > 0, "display has nonzero emission")
	game.quarters.press_console()
	room.process_frame()
	assert_true(room.corruption.visible, "corruption visible before message")
	for tick: int in range(QuartersMemory.CORRUPT_TICKS): game.quarters.tick()
	room.process_frame()
	assert_false(room.corruption.visible, "corruption ends at message")
	for label: Label3D in room.screen_labels: assert_true("Hi honey." in label.text, "message on both real displays")
	for tick: int in range(QuartersMemory.MESSAGE_TICKS): game.quarters.tick()
	room.process_frame()
	for label: Label3D in room.screen_labels: assert_true("MAIN SYSTEM FAULT" in label.text, "fault on both displays")
	for tick: int in range(QuartersMemory.FAULT_TICKS): game.quarters.tick()
	room.process_frame()
	assert_true(room.present.visible and not room.remembered.visible, "300 ticks selects Present")
	room.free()

func test_bedside_lenses_and_lights_follow_actual_lamp_positions_and_state() -> void:
	var room := QuartersRoom.build(Game.new(114))
	for state: Node3D in [room.remembered, room.present]:
		assert_true(state.find_children("Standin_bedside_lamp*", "", true, false).is_empty(), "no separate lamp stand-ins")
		for id: String in ["bedside_l", "bedside_r"]:
			var asset := state.get_node_or_null("Placement_" + id + "/bedside")
			assert_true(asset != null, "real bedside")
			if asset == null: continue
			var lens := asset.find_child("LampLens", true, false) as MeshInstance3D
			var finish := lens.material_override as StandardMaterial3D
			assert_true(finish != null, "lamp lens finish")
			if finish != null: assert_true(finish.emission_enabled == (state == room.remembered), "lamp lens follows room state")
			var light := asset.find_child("BedsideLamp", true, false) as OmniLight3D
			if state == room.remembered:
				assert_true(light != null, "remembered real lamp light")
				if light != null:
					var centre := (ShipScene._world_frame(lens) * lens.get_aabb()).get_center()
					assert_true(ShipScene._world_frame(light).origin.distance_to(centre) <= .012, "light seated at lamp lens")
					assert_float_in_range(light.light_energy, .349999, .350001, "existing bedside energy")
			else: assert_true(light == null, "Present lamp is dead")
	room.free()

func test_view_screen_is_off_in_both_states_with_glossy_transparent_glass() -> void:
	for state: StringName in QuartersProps.STATES:
		var furnishings := QuartersFurnishings.build(state)
		var asset := furnishings.get_node_or_null("Placement_view_screen/view_screen")
		assert_true(asset != null, "real view screen")
		if asset != null:
			var display := asset.find_child("Display", true, false) as MeshInstance3D
			var finish := display.get_surface_override_material(0) as StandardMaterial3D
			assert_false(finish.emission_enabled, "wall display off")
			var glass := asset.find_child("Glass", true, false) as MeshInstance3D
			var pane := glass.get_surface_override_material(0) as StandardMaterial3D
			assert_true(pane.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA, "simple transparent glass")
			assert_true(pane.roughness <= .1, "glossy glass")
		furnishings.free()
