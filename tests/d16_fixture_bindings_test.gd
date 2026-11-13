extends SimTestCase

const Inventory := preload("res://tools/light_inventory.gd")

func test_finished_d16_fixture_sources_retain_physical_bodies_and_positions() -> void:
	var game := Game.new(114)
	game.light_hallway()
	var spec := game.layout.section(QuartersLayout.SECTION)
	var section := ShipSection.build(game.layout, spec)
	var circuit := SectionPowerLighting.build(game, spec, section)
	section.add_child(circuit)
	var inventory := Inventory.new()
	var keys := _red_keys(section)
	assert_int_equal(keys.size(), 8, "finished D16 emergency key sources")
	assert_int_equal(circuit._white_lights.size(), spec.regular_light_frames().size(), "finished D16 regular strip sources")
	assert_true(not keys.is_empty() and not circuit._white_lights.is_empty(), "physical source checks have actual fixture nodes")
	for source: Light3D in keys + circuit._white_lights:
		_assert_physical_source(inventory, source)
	var emergency_end := section.get_node("PowerLighting/EmergencyFillEnd") as OmniLight3D
	var regular_end := circuit._white_end_fill as OmniLight3D
	assert_true(emergency_end != null and regular_end != null, "both physical corridor end sources exist")
	if emergency_end != null and regular_end != null:
		_assert_physical_source(inventory, emergency_end)
		_assert_physical_source(inventory, regular_end)
		assert_true(emergency_end.position.is_equal_approx(spec.emergency_end_fill_position()), "emergency end source uses the authored emergency position")
		assert_true(regular_end.position.is_equal_approx(spec.emergency_end_fill_position() - Vector3(0, 0, 2.6)), "regular end source uses the separated opposite-wall position")
	section.free()

func test_emergency_lenses_are_registered_and_dark_at_both_unlit_build_states() -> void:
	var dark_game := Game.new(114)
	var dark := _build_lit_fixture(dark_game, false)
	_assert_lenses_match_visible_cages(dark.section, dark.circuit)
	_assert_lens_emission(dark.circuit, 0.0, "immediately dark hallway-off build")
	dark.section.free()

	var secondary_game := Game.new(114)
	secondary_game.light_hallway()
	secondary_game.press_console()
	var secondary := _build_fixture(secondary_game)
	_assert_lenses_match_visible_cages(secondary.section, secondary.circuit)
	_assert_lens_emission(secondary.circuit, 0.0, "immediately dark secondary-active build")
	secondary.section.free()

func test_actual_emergency_lens_materials_follow_both_power_handoffs() -> void:
	var game := Game.new(114)
	game.light_hallway()
	var fixture := _build_fixture(game)
	_assert_lenses_match_visible_cages(fixture.section, fixture.circuit)
	_assert_lens_emission(fixture.circuit, 1.0, "initial emergency-lit build")
	for active: bool in [true, false]:
		game.power_active = active
		for tick: int in range(Lighting.FIXTURE_SETTLE_TICKS + 1):
			fixture.circuit.process_frame()
			var level: float = fixture.circuit.red_level()
			assert_true(level >= 0.0 and level <= 1.0, "main emergency fade level remains within 0-1")
			_assert_lens_emission(fixture.circuit, level, "lens emission during power handoff")
	_assert_lens_emission(fixture.circuit, 1.0, "emergency-lit settled state")
	fixture.section.free()

func _build_lit_fixture(game: Game, hallway_lit: bool) -> Dictionary:
	if hallway_lit:
		game.light_hallway()
	return _build_fixture(game)

func _build_fixture(game: Game) -> Dictionary:
	var spec := game.layout.section(QuartersLayout.SECTION)
	var section := ShipSection.build(game.layout, spec)
	var circuit := SectionPowerLighting.build(game, spec, section)
	section.add_child(circuit)
	return {"section": section, "circuit": circuit}

func _assert_physical_source(inventory: Inventory, source: Light3D) -> void:
	assert_true(source.has_meta(&"fixture_emitter") and source.has_meta(&"fixture_housing"), "source retains emitter and housing bindings")
	if not source.has_meta(&"fixture_emitter") or not source.has_meta(&"fixture_housing"): return
	var emitter := source.get_meta(&"fixture_emitter") as MeshInstance3D
	var housing := source.get_meta(&"fixture_housing") as MeshInstance3D
	assert_true(emitter != null and housing != null, "bound emitter and housing are actual meshes")
	if emitter == null or housing == null: return
	assert_true(inventory._visible(emitter) and inventory._visible(housing), "bound emitter and housing remain visible")
	assert_true(inventory._fixture_error(source).is_empty(), "existing light inventory physical-source validator accepts finished D16 source")

func _assert_lenses_match_visible_cages(section: Node3D, circuit: SectionPowerLighting) -> void:
	var visible_key_lenses: Array[MeshInstance3D] = []
	var actual_key_materials: Array[StandardMaterial3D] = []
	var visible_end_lenses: Array[MeshInstance3D] = []
	for mesh: MeshInstance3D in section.find_children("*", "MeshInstance3D", true, false):
		if mesh.get_meta(&"lamp_circuit", "") != "emergency" or not inventory_visible(mesh): continue
		var material := mesh.get_active_material(0) as StandardMaterial3D
		assert_true(material != null, "visible emergency cage lens has its active StandardMaterial3D")
		if mesh.get_parent() is Lighting.EmergencyFill:
			var owner := mesh.get_parent() as Lighting.EmergencyFill
			assert_true(owner.name == "EmergencyFillEnd", "the ninth visible emergency lens belongs to the physical emergency end source")
			assert_true(owner.get_parent() == circuit and owner == section.get_node("PowerLighting/EmergencyFillEnd"), "emergency end lens belongs to the D16 circuit end-source node")
			assert_true(material == owner.lens_material, "emergency end lens uses its owner's active fill material")
			visible_end_lenses.append(mesh)
		else:
			var key_fixture := false
			for source: Node in mesh.get_parent().get_children():
				if source is OmniLight3D and source.has_meta(&"energy_share"): key_fixture = true
			assert_true(key_fixture, "each corridor key lens belongs to an energy-share emergency fixture")
			visible_key_lenses.append(mesh)
			if material != null and not actual_key_materials.has(material): actual_key_materials.append(material)
	assert_int_equal(visible_key_lenses.size(), 8, "exact eight visible corridor-key emergency cage lenses")
	assert_int_equal(visible_end_lenses.size(), 1, "exact one visible physical emergency end-source lens")
	assert_int_equal(visible_key_lenses.size() + visible_end_lenses.size(), 9, "exact visible emergency lens composition")
	assert_int_equal(actual_key_materials.size(), 8, "eight distinct active materials cover the corridor-key lenses")
	assert_int_equal(circuit._red_lenses.size(), 8, "the emergency fade registry contains exactly the eight corridor-key materials")
	for material: StandardMaterial3D in actual_key_materials:
		assert_true(circuit._red_lenses.has(material), "each corridor key's active material is registered for the emergency fade")
	assert_true(not visible_end_lenses.is_empty(), "physical emergency end-source lens is present before fade checks")

func _assert_lens_emission(circuit: SectionPowerLighting, level: float, context: String) -> void:
	assert_int_equal(circuit._red_lenses.size(), 8, context + " checks all eight corridor-key lens materials")
	var expected := Lighting.emergency_emission(level)
	for material: StandardMaterial3D in circuit._red_lenses:
		assert_true(material.emission.is_equal_approx(expected), context + " corridor-key emission follows emergency fade")
	var end_source := circuit.get_node("EmergencyFillEnd") as Lighting.EmergencyFill
	assert_true(end_source != null, context + " retains the physical emergency end source")
	if end_source != null:
		var end_emission := end_source.light_color * Lighting.REGULAR_EMISSIVE * level
		assert_true(end_source.lens_material.emission.is_equal_approx(end_emission), context + " physical emergency end-source lens follows its owner-specific fill emission")

func inventory_visible(node: Node3D) -> bool:
	var current: Node = node
	while current is Node3D:
		if not current.visible: return false
		current = current.get_parent()
	return true

func _red_keys(section: Node3D) -> Array[OmniLight3D]:
	var result: Array[OmniLight3D] = []
	for fixture: Node in section.get_children():
		for child: Node in fixture.get_children():
			if child is OmniLight3D and child.has_meta(&"energy_share"): result.append(child)
	return result
