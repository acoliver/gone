extends SimTestCase

func test_first_entry_requires_real_finite_open_deck_threshold_crossing() -> void:
	var memory := QuartersMemory.new()
	var previous := QuartersLayout.to_world(Vector3(4, 0.305, -0.1))
	var current := QuartersLayout.to_world(Vector3(4, 0.305, 0.1))
	memory.observe_entry(previous, current, 14, true, true)
	memory.observe_entry(previous, current, 16, false, true)
	memory.observe_entry(previous, current, 16, true, false)
	memory.observe_entry(previous + Vector3(2, 0, 0), current + Vector3(2, 0, 0), 16, true, true)
	assert_int_equal(memory.state, QuartersMemory.State.UNSEEN, "wrong deck, mode, closed door and wall do not trigger memory")
	assert_false(memory.press_console(), "cannot play before entering")
	memory.observe_entry(previous, current, 16, true, true)
	assert_int_equal(memory.state, QuartersMemory.State.REMEMBERED, "first accepted entry remembers")
	memory.observe_entry(current, previous, 16, true, true)
	memory.observe_entry(previous, current, 16, true, true)
	assert_int_equal(memory.state, QuartersMemory.State.REMEMBERED, "entry does not reset state")

func test_console_sequence_boundaries_and_persistent_present_state() -> void:
	var game := Game.new(0)
	_enter(game)
	assert_true(game.quarters.press_console(), "one accepted console press")
	assert_false(game.quarters.press_console(), "a repeat cannot restart playback")
	var stepper := GameStep.new(game)
	for tick: int in range(20): stepper.advance(true)
	assert_int_equal(game.quarters.elapsed, 0, "paused frames do not advance sequence")
	for tick: int in range(QuartersMemory.CORRUPT_TICKS - 1): stepper.advance()
	assert_true("CORRUPTED" in game.quarters.screen_text(), "corruption precedes message")
	stepper.advance()
	assert_true(QuartersMemory.MESSAGE in game.quarters.screen_text(), "message at exact tick")
	for tick: int in range(QuartersMemory.MESSAGE_TICKS): stepper.advance()
	assert_true(QuartersMemory.FAULT in game.quarters.screen_text(), "fault at exact tick")
	assert_true(game.quarters.remembered(), "fault still shows before final switch")
	for tick: int in range(QuartersMemory.FAULT_TICKS - 1): stepper.advance()
	assert_true(game.quarters.remembered(), "remembered through penultimate tick")
	stepper.advance()
	assert_int_equal(game.quarters.state, QuartersMemory.State.PRESENT, "switch at exact final tick")
	_enter(game)
	assert_int_equal(game.quarters.state, QuartersMemory.State.PRESENT, "re-entry stays present")
	assert_false(game.quarters.press_console(), "completed message cannot reset memory")
	assert_true(QuartersMemory.PLACEHOLDER in game.quarters.screen_text(), "ruling 16 remains explicit")

func test_state_roots_and_lights_change_together_and_console_stays_lit() -> void:
	var game := Game.new(0)
	game.press_console()
	var room := QuartersRoom.build(game)
	assert_true(room.present.visible and not room.remembered.visible, "unseen is physically present")
	_enter(game)
	room.process_frame()
	assert_true(room.remembered.visible and not room.present.visible, "entry switches geometry and descendant lights in one frame")
	assert_int_equal(room.present.find_children("BedsideLamp*", "OmniLight3D", true, false).size(), 0, "present bedside lamps are dead")
	game.quarters.press_console()
	for tick: int in range(QuartersMemory.TOTAL_TICKS): game.quarters.tick()
	room.process_frame()
	assert_true(room.present.visible and not room.remembered.visible, "completion switches geometry and descendant lights together")
	for lamp: OmniLight3D in room.white_lights:
		assert_float_equal(lamp.light_energy, Vector3(Lighting.regular_energy(), 0, 0).x, "secondary-power regular strips")
	for screen: MeshInstance3D in room.screens:
		assert_true(screen.material_override.emission_energy_multiplier > 0, "console screen remains lit")
	room.free()

func test_console_registered_with_existing_interaction_system_only_on_d16() -> void:
	var game := Game.new(0)
	var interactions := Interactions.new(game.layout)
	var target := interactions.target_for(QuartersLayout.CONSOLE, 16, Vector3.ZERO)
	assert_true(target != null and target.kind == Interactions.Kind.CONSOLE, "existing console interaction kind")
	var context := Interactions.Context.new()
	context.walking = true
	context.foot = QuartersLayout.to_world(Vector3(6.2, 0.305, 2))
	context.eye = context.foot + Vector3.UP * 1.35
	context.deck = 14
	assert_true(Interactions.hit_distance(target, context, []) < 0, "D14 cannot activate D16 console")
	context.deck = 16
	assert_true(Interactions.hit_distance(target, context, []) >= 0, "approved console approach is in reach")

func test_remembered_is_brighter_than_secondary_present_without_exposure_changes() -> void:
	var game := Game.new(114)
	game.press_console()
	var room := QuartersRoom.build(game)
	var energies: Array[float] = []
	var photopic: Array[float] = []
	for state: Node3D in [room.remembered, room.present]:
		var energy := 0.0
		var weighted := 0.0
		for light: OmniLight3D in state.find_children("*", "OmniLight3D", true, false):
			energy += light.light_energy
			weighted += light.light_energy * Vector3(light.light_color.r, light.light_color.g, light.light_color.b).dot(Vector3(0.2126, 0.7152, 0.0722))
		energies.append(energy)
		photopic.append(weighted)
	assert_float_in_range(energies[0], 13.49, 13.51, "four warm 3.2 keys plus two 0.35 bedside lamps")
	assert_float_in_range(energies[1], 7.87, 7.89, "four unchanged secondary regular strips")
	assert_true(photopic[0] > photopic[1] * 1.25, "warm memory remains brighter after accounting for warm light colour")
	var environment := Lighting._world_environment()
	assert_float_equal(environment.camera_attributes.exposure_multiplier, 2.0, "one unchanged world exposure for both room states and corridors")
	environment.free()
	room.free()

func _enter(game: Game) -> void:
	var context := Doors.Context.new()
	context.face_id = game.layout.door(QuartersLayout.DOOR).face_ids()[0]
	game.doors.press(QuartersLayout.DOOR, context)
	for tick: int in range(48): game.advance_doors()
	game.observe_bay_crossing(QuartersLayout.to_world(Vector3(4, 0.305, -0.1)), QuartersLayout.to_world(Vector3(4, 0.305, 0.1)), true, 16)
