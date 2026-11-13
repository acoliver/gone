extends SimTestCase

const Inventory := preload("res://tools/light_inventory.gd")
const Rows := preload("res://tools/fixture_rows.gd")
static var _rows: Array[Dictionary] = []

func _fixtures() -> Array[Dictionary]:
	if _rows.is_empty(): _rows = Rows.rows(Inventory.new().collect_ship())
	return _rows

func test_no_wall_has_two_fixtures_within_one_and_a_half_metres_on_any_deck() -> void:
	var failures := Rows.close_pairs(_fixtures())
	assert_true(failures.is_empty(), "wall fixture centres require more than 1.5 m: " + "; ".join(failures))

func test_every_live_lamp_has_at_least_one_third_of_its_room_circuit_median_share() -> void:
	var failures := Rows.dim_lamps(_fixtures())
	assert_true(failures.is_empty(), "live lamps must visibly glow beside their neighbours: " + "; ".join(failures))

func test_spacing_and_glow_gates_reject_boundary_and_dim_lamps() -> void:
	var fixtures: Array[Dictionary] = []
	for index: int in range(3):
		fixtures.append({"owner": "D01-S-041", "state": "emergency", "fixture": str(index), "position": [index * 1.5, 2.5, -1.3], "wall": "PORT", "share": 0.01 if index == 0 else 1.0, "live": true})
	assert_int_equal(Rows.close_pairs(fixtures).size(), 2, "exactly 1.5 m is rejected")
	assert_int_equal(Rows.dim_lamps(fixtures).size(), 1, "near-dark lamp fails")
	fixtures[0].share = 1.0 / 3.0
	assert_true(Rows.dim_lamps(fixtures).is_empty(), "one third of median is accepted")
	fixtures[0].share = 0.0
	assert_int_equal(Rows.dim_lamps(fixtures).size(), 1, "a dark lamp on a live circuit also fails")
	fixtures[0].live = false
	assert_true(Rows.dim_lamps(fixtures).is_empty(), "an off circuit is not a live near-dark decoration")
	fixtures[1].wall = "STARBOARD"
	assert_true(Rows.close_pairs(fixtures).is_empty(), "opposite walls are independent rows")
	fixtures[1].share = 0.0
	fixtures[2].share = 0.0
	assert_int_equal(Rows.dim_lamps(fixtures).size(), 2, "a zero median cannot authorize dark lamps on a live circuit")

func test_every_standalone_fixture_has_exactly_one_light_source() -> void:
	var counts: Dictionary = {}
	for row: Dictionary in _fixtures():
		assert_int_equal(row.sources.size(), 1, "one cage or beam, one source: " + row.fixture)
		counts[row.state] = counts.get(row.state, 0) + 1
	assert_int_equal(counts.emergency, 240, "whole ship fixture inventory")
	assert_int_equal(counts["secondary-white"], 240, "same fixtures survive handoff")

func test_zero_output_cannot_make_an_independent_always_on_circuit_appear_off() -> void:
	var sources: Array[Dictionary] = []
	for index: int in range(2):
		sources.append({"kind": "light", "fixture": "Fixture%d/Lens" % index, "circuit_state": "emergency", "owner": "D14-S-040", "position": [0, 2.65, -1.3], "energy": 0.0 if index == 0 else Lighting.FIXTURE_ENERGY})
	var rows := Rows.rows({"lights_and_emissives": sources})
	assert_int_equal(Rows.dim_lamps(rows).size(), 1, "a dark source on an independent always-on circuit must fail")

func test_bay_long_wall_cages_are_mirrored_even_rows_with_symmetric_profiles() -> void:
	for state: String in ["emergency", "secondary-white"]:
		var west: Array[Dictionary] = []
		var east: Array[Dictionary] = []
		for row: Dictionary in _fixtures():
			if row.owner != "D14-BAY" or row.state != state: continue
			if row.wall == "WEST": west.append(row)
			if row.wall == "EAST": east.append(row)
		assert_int_equal(west.size(), east.size(), "bay long walls have the same cage count")
		assert_true(west.size() >= 3, "each row covers the usable wall")
		if west.size() != east.size() or west.size() < 3: continue
		west.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.position[2] < b.position[2])
		east.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.position[2] < b.position[2])
		var pitch: float = west[1].position[2] - west[0].position[2]
		var profiles: Array[Vector3] = []
		for index: int in range(west.size()):
			var a := west[index]
			var b := east[index]
			assert_true(absf(a.position[0] + b.position[0] - 30.0) <= 0.03, "opposite cages mirror across the bay centreline")
			assert_true(absf(a.position[2] - b.position[2]) <= 0.03, "opposite cages share a station")
			assert_true(absf(a.position[1] - west[0].position[1]) <= 0.03 and absf(b.position[1] - west[0].position[1]) <= 0.03, "one mounting height on both walls")
			if index > 0:
				assert_true(absf(a.position[2] - west[index - 1].position[2] - pitch) <= 0.03, "west row has uniform pitch")
				assert_true(absf(b.position[2] - east[index - 1].position[2] - pitch) <= 0.03, "east row has the same uniform pitch")
			var profile := Vector3(a.share, a.sources[0].range, a.sources[0].attenuation)
			var opposite := Vector3(b.share, b.sources[0].range, b.sources[0].attenuation)
			assert_true(profile.is_equal_approx(opposite), "opposite cages share output, throw and falloff")
			if not profiles.has(profile): profiles.append(profile)
		assert_true(profiles.size() <= 2, "bay cages use at most two symmetric profiles")
