extends SimTestCase

const Inventory := preload("res://tools/light_inventory.gd")
const BASELINE := "res://tests/fixtures/illuminance-217355c.json"
static var _inventory: Dictionary

func _ship() -> Dictionary:
	if _inventory.is_empty(): _inventory = Inventory.new().collect_ship()
	return _inventory

func test_every_ship_light_has_a_visible_housed_emitter_within_one_centimetre() -> void:
	var inventory := _ship()
	var checked := 0
	var failures: Array[String] = []
	for record: Dictionary in inventory.lights_and_emissives:
		if record.kind != "light": continue
		checked += 1
		if not record.get("fixture_valid", false):
			failures.append("%s %s %s: %s" % [record.owner, record.circuit_state, record.path, record.get("fixture_error", "no housed emitter")])
	assert_int_equal(checked, 572, "all 286 lights, including inactive circuits and spark strobes, in both circuit states")
	assert_true(failures.is_empty(), "%d unhoused or misplaced lights: %s" % [failures.size(), "; ".join(failures)])

func test_every_space_keeps_its_recorded_floor_wall_ceiling_illuminance() -> void:
	var expected: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BASELINE)).illuminance
	var actual: Dictionary = _ship().illuminance
	assert_int_equal(actual.size(), expected.size(), "all spaces and circuit states retain measurements")
	for id: String in expected:
		assert_true(actual.has(id), "space still exists: " + id)
		if not actual.has(id): continue
		for panel: String in ["total", "floor", "ceiling", "walls"]:
			# Flush recessed beams cannot illuminate the ceiling above their glass.
			# The approved exception is limited to these three white-circuit ceiling subtotals.
			if panel == "ceiling" and id in ["secondary-white/D14-BAY", "secondary-white/D14-POWER", "secondary-white/D14-S-041"]: continue
			var before: float = expected[id][panel]
			var after: float = actual[id][panel]
			assert_true(absf(after - before) <= before * 0.10 + 0.000001, "%s %s illumination %.6f -> %.6f exceeds 10%%" % [id, panel, before, after])

func test_illuminance_uses_the_renderer_range_cutoff_and_power_falloff() -> void:
	var probe := Inventory.new()
	var light := OmniLight3D.new()
	light.position = Vector3(0, 2, 0)
	light.light_energy = 1
	light.light_cull_mask = 1
	light.light_color = Color.WHITE
	light.omni_range = 4
	light.omni_attenuation = 2
	var expected := pow(1.0 - pow(2.0 / 4.0, 4), 2) / 4.0
	assert_float_equal(probe.incident(light, Vector3.ZERO, Vector3.UP, 1), expected, "matches shader get_omni_attenuation and incidence")
	assert_float_equal(probe.incident(light, Vector3(0, -2, 0), Vector3.UP, 1), 0, "range cutoff")
	assert_float_equal(probe.incident(light, Vector3.ZERO, Vector3.DOWN, 1), 0, "back face")
	assert_float_equal(probe.incident(light, Vector3.ZERO, Vector3.UP, 2), 0, "receiver layer")
	light.light_energy = 1.2
	assert_true(probe.incident(light, Vector3.ZERO, Vector3.UP, 1) > expected * 1.1, "regression detects a 20 percent energy change")
	light.free()

func test_fixture_gate_rejects_missing_hidden_bare_and_displaced_emitters() -> void:
	var inventory := Inventory.new()
	var layout := ShipLayout.authored().layout
	var fixture := Lighting.steady_fixture(Vector3(0, 2.65, 0), 1, 3, Surfaces.surface_frame(layout, &"D14-S-041", &"CEILING"))
	var light := fixture.get_child(0) as OmniLight3D
	var lens: MeshInstance3D = fixture.get_node("Lens")
	assert_true(inventory._fixture_error(light).is_empty(), "real cage passes")
	light.position.x = 0.02
	assert_false(inventory._fixture_error(light).is_empty(), "two centimetres misses the emitter")
	light.position.x = 0.0
	lens.hide()
	assert_false(inventory._fixture_error(light).is_empty(), "hidden glass cannot authorize a source")
	lens.show()
	var rounded := lens.mesh
	lens.mesh = BoxMesh.new()
	assert_false(inventory._fixture_error(light).is_empty(), "bare rectangle fails even with a binding")
	lens.mesh = rounded
	fixture.get_node("Steel").hide()
	assert_false(inventory._fixture_error(light).is_empty(), "hidden housing fails")
	light.remove_meta(&"fixture_emitter")
	assert_false(inventory._fixture_error(light).is_empty(), "missing emitter fails")
	fixture.free()
