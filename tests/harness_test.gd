extends SimTestCase
## Engine-independent protocol tests for the harness port: chip
## encode/decode, scenario validation, the scripted-input adapter, the
## report roundtrip and canonical event order, beat accounting, and the
## sha256 identity contract.

const Protocol := preload("res://harness/protocol.gd")
const ScenarioModule := preload("res://harness/scenario.gd")
const ReportModule := preload("res://harness/report.gd")

func test_protocol_version_matches_the_rust_harness() -> void:
	assert_int_equal(Protocol.PROTOCOL_VERSION, 4, "protocol version")

func _paint_chip_image(tick: int, frame: int) -> Image:
	var size := Protocol.chip_size()
	var image := Image.create(size.x + 40, size.y + 30, false, Image.FORMAT_RGBA8)
	image.fill(Color.BLACK)
	for py: int in range(2 * Protocol.CELL_H):
		for px: int in range(Protocol.DIGITS * Protocol.CELL_W):
			var color := Protocol.chip_pixel(tick, frame, px, py)
			for block_y: int in range(Protocol.PIXEL_SCALE):
				for block_x: int in range(Protocol.PIXEL_SCALE):
					image.set_pixel(px * Protocol.PIXEL_SCALE + block_x,
						py * Protocol.PIXEL_SCALE + block_y, color)
	return image

func test_chip_encode_decode_roundtrip() -> void:
	for pair: Array in [[0, 0], [5, 42], [999999, 0], [42, 123456]]:
		var decoded := Protocol.decode_chip(_paint_chip_image(pair[0], pair[1]))
		assert_true(decoded.ok, "chip (%d,%d) decodes" % [pair[0], pair[1]])
		if decoded.ok:
			assert_int_equal(decoded.tick, pair[0], "chip (%d,%d) tick" % [pair[0], pair[1]])
			assert_int_equal(decoded.frame, pair[1], "chip (%d,%d) frame" % [pair[0], pair[1]])

func test_chip_decode_rejects_a_mutated_lattice() -> void:
	var image := _paint_chip_image(0, 0)
	# Pixel (0,0) is digit 0's on top-left lattice cell; paint it off.
	image.set_pixel(Protocol.PIXEL_SCALE / 2, Protocol.PIXEL_SCALE / 2, Protocol.OFF_COLOR)
	assert_false(Protocol.decode_chip(image).ok, "a flipped lattice cell must not decode")

func test_chip_decode_rejects_a_plain_dark_image() -> void:
	var image := Image.create(200, 100, false, Image.FORMAT_RGB8)
	image.fill(Color.BLACK)
	assert_false(Protocol.decode_chip(image).ok, "a dark image carries no chip")

func test_digit_cells_roundtrip() -> void:
	assert_int_equal(Protocol.number_from_cells(Protocol.digit_cells(0)), 0, "zero cells")
	assert_int_equal(Protocol.number_from_cells(Protocol.digit_cells(123456)), 123456, "padded cells")
	var cells := Protocol.digit_cells(987654)
	assert_int_equal(cells.size(), 6, "six cells")
	assert_int_equal(cells[0], 9, "most significant first")
	assert_int_equal(cells[5], 4, "least significant last")

func _minimal_scenario_json() -> String:
	return JSON.stringify({
		"name": "probe", "seed": 7, "ticks_per_second": 60,
		"actions": [
			{"tick": 0, "type": "press", "button": "activate"},
			{"tick": 1, "type": "release", "button": "activate"},
			{"tick": 2, "type": "look", "yaw_deg": -90.0, "pitch_deg": 0.0},
			{"tick": 3, "type": "move", "forward": 1.0, "strafe": 0.0},
		],
		"beats": [{"name": "b", "tick": 4}, {"name": "a", "tick": 2}],
	})

func test_scenario_parse_validates_and_sorts_beats() -> void:
	var parsed: Dictionary = ScenarioModule.parse(_minimal_scenario_json())
	assert_true(parsed.error.is_empty(), parsed.error)
	if parsed.error.is_empty():
		assert_int_equal(parsed.scenario.ticks_per_second, 60, "tick rate")
		assert_int_equal(parsed.scenario.beats.size(), 2, "beat count")
		assert_true(parsed.scenario.beats[0].name == "a", "beats sort by tick")
		assert_int_equal(parsed.scenario.actions.size(), 4, "action count")

func test_scenario_rejects_zero_tick_rate() -> void:
	var data: Dictionary = JSON.parse_string(_minimal_scenario_json())
	data.ticks_per_second = 0
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify(data))
	assert_false(parsed.error.is_empty(), "a zero rate fails")
	assert_true(parsed.error.contains("ticks_per_second"), parsed.error)

func test_scenario_rejects_a_negative_wait() -> void:
	var data: Dictionary = JSON.parse_string(_minimal_scenario_json())
	data.actions.append({"tick": 0, "type": "wait", "duration": -0.5})
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify(data))
	assert_false(parsed.error.is_empty(), "a negative wait fails")
	assert_true(parsed.error.contains("negative duration"), parsed.error)

func test_scenario_rejects_duplicate_beats() -> void:
	var data: Dictionary = JSON.parse_string(_minimal_scenario_json())
	data.beats.append({"name": "a", "tick": 9})
	var parsed: Dictionary = ScenarioModule.parse(JSON.stringify(data))
	assert_false(parsed.error.is_empty(), "a duplicate beat fails")
	assert_true(parsed.error.contains("duplicate"), parsed.error)

func test_scenario_rejects_unknown_buttons_and_types() -> void:
	var data: Dictionary = JSON.parse_string(_minimal_scenario_json())
	data.actions.append({"tick": 0, "type": "press", "button": "dance"})
	assert_false(ScenarioModule.parse(JSON.stringify(data)).error.is_empty(), "unknown button")
	data.actions.remove_at(data.actions.size() - 1)
	data.actions.append({"tick": 0, "type": "teleport"})
	assert_false(ScenarioModule.parse(JSON.stringify(data)).error.is_empty(), "unknown action type")

func test_adapter_delivers_each_edge_exactly_once() -> void:
	var adapter := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "press", "button": "activate"},
		{"tick": 1, "type": "release", "button": "activate"},
	], 60)
	var first: Dictionary = adapter.step()
	assert_int_equal(first.edges.size(), 1, "one edge on the press tick")
	assert_true(first.edges[0].button == "activate", "the edge names its button")
	assert_true(first.edges[0].edge == "press", "the edge names press")
	var second: Dictionary = adapter.step()
	assert_int_equal(second.edges.size(), 1, "the release delivers on its tick")
	assert_true(second.edges[0].edge == "release", "the edge names release")
	assert_int_equal(adapter.step().edges.size(), 0, "a drained tick delivers nothing")
	assert_true(adapter.is_complete(), "the schedule drains")

func test_adapter_separates_look_and_movement_channels() -> void:
	var adapter := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "look", "yaw_deg": 5.0, "pitch_deg": -2.0},
		{"tick": 0, "type": "move", "forward": 1.0, "strafe": 0.0},
	], 60)
	var step: Dictionary = adapter.step()
	assert_float_equal(step.look_deg.x, 5.0, "look yaw")
	assert_float_equal(step.look_deg.y, -2.0, "look pitch")
	assert_float_equal(step.movement.x, 1.0, "movement forward")
	assert_float_equal(step.movement.y, 0.0, "movement strafe")
	assert_int_equal(step.edges.size(), 0, "movement is not a button edge")

func test_adapter_wait_holds_later_actions_whole_ticks() -> void:
	var adapter := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "wait", "duration": 0.5},
		{"tick": 0, "type": "press", "button": "interact"},
	], 60)
	assert_int_equal(adapter.step().edges.size(), 0, "the wait itself delivers nothing")
	for floor_tick: int in range(1, 30):
		assert_int_equal(adapter.step().edges.size(), 0, "held at floor %d" % floor_tick)
	assert_int_equal(adapter.tick(), 30, "half a second at 60 tps is 30 ticks")
	assert_int_equal(adapter.step().edges.size(), 1, "the press lands after the hold")

func test_adapter_wait_until_tick_pins_the_floor() -> void:
	var adapter := ScenarioModule.InputAdapter.new([
		{"tick": 0, "type": "look", "yaw_deg": 5.0, "pitch_deg": 0.0},
		{"tick": 0, "type": "wait_until_tick", "tick_until": 5},
		{"tick": 0, "type": "look", "yaw_deg": 3.0, "pitch_deg": 0.0},
	], 60)
	assert_float_equal(adapter.step().look_deg.x, 5.0, "the pre-wait look delivers")
	for floor_tick: int in range(1, 5):
		assert_float_equal(adapter.step().look_deg.x, 0.0, "held at floor %d" % floor_tick)
	assert_float_equal(adapter.step().look_deg.x, 3.0, "the held look releases at the floor")

func test_report_roundtrip_and_canonical_order() -> void:
	var identity := {"app_hash": "a", "scenario_hash": "s", "config_hash": "c"}
	var run_a := ReportModule.new(4, "probe", 1, identity)
	run_a.add_event({"kind": "ready", "frame": 0})
	run_a.add_event({"kind": "beat", "name": "beat-a", "tick": 2, "frame": 2, "request_id": 1})
	run_a.add_event({"kind": "input", "tick": 0, "frame": 0, "what": "look 15 0"})
	run_a.add_event({"kind": "input", "tick": 5, "frame": 5, "what": "activate press"})
	run_a.add_event({"kind": "complete", "frame": 11})
	run_a.beats["beat-a"] = {"file": "beats/beat-a.png", "tick": 2, "frame": 2, "request_id": 1}
	var run_b := ReportModule.new(4, "probe", 1, identity)
	run_b.add_event({"kind": "complete", "frame": 11})
	run_b.add_event({"kind": "input", "tick": 5, "frame": 5, "what": "activate press"})
	run_b.add_event({"kind": "beat", "name": "beat-a", "tick": 2, "frame": 2, "request_id": 1})
	run_b.add_event({"kind": "input", "tick": 0, "frame": 0, "what": "look 15 0"})
	run_b.add_event({"kind": "ready", "frame": 0})
	run_b.beats["beat-a"] = {"file": "beats/beat-a.png", "tick": 2, "frame": 2, "request_id": 1}
	var json_a := run_a.to_json()
	var json_b := run_b.to_json()
	assert_true(json_a == json_b, "both append orders serialize to the same report")
	var parsed: Dictionary = ReportModule.parse(json_a)
	assert_true(parsed.error.is_empty(), parsed.error)
	if parsed.error.is_empty():
		var report = parsed.report
		assert_int_equal(report.protocol_version, 4, "version survives")
		assert_int_equal(report.ready_frame(), 0, "ready frame")
		assert_true(report.first_failure() == "", "no failure on a clean report")
		assert_true(report.events[0].kind == "ready", "ready first")
		assert_true(report.events[report.events.size() - 1].kind == "complete", "terminal last")
		assert_int_equal(report.beats["beat-a"].tick, 2, "beat entry tick")

func test_report_parse_rejects_malformed_input() -> void:
	assert_false(ReportModule.parse("{ nope").error.is_empty(), "invalid JSON")
	assert_false(ReportModule.parse("{}").error.is_empty(), "empty object")

func test_verify_beats_names_the_first_missing_beat() -> void:
	var happened := [{"name": "b1", "tick": 3}]
	var expected := [{"name": "b2", "tick": 9}, {"name": "b1", "tick": 3}]
	var error := Protocol.verify_beats(happened, expected)
	assert_false(error.is_empty(), "a missing beat fails")
	assert_true(error.contains("b2"), error)
	assert_true(error.contains("9"), error)
	assert_true(Protocol.verify_beats(happened, [{"name": "b1", "tick": 3}]) == "",
		"all expected present passes")

func test_sha256_known_vector_and_file() -> void:
	assert_true(Protocol.sha256_hex("abc".to_ascii_buffer())
		== "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
		"the sha256 implementation matches the known vector")
	var path := "res://scenarios/gameplay-full.json"
	var via_bytes := Protocol.sha256_hex(FileAccess.get_file_as_bytes(path))
	assert_true(Protocol.sha256_file(path) == via_bytes, "file hash matches the bytes hash")
	assert_int_equal(Protocol.sha256_file(path).length(), 64, "hash is 64 hex chars")

func test_app_hash_is_stable_and_covers_the_scripts() -> void:
	var root := ProjectSettings.globalize_path("res://")
	assert_int_equal(Protocol.app_hash(root).length(), 64, "app hash is 64 hex chars")
	assert_true(Protocol.app_hash(root) == Protocol.app_hash(root), "app hash is stable")
	assert_true(Protocol.app_hash("/nonexistent-root")
		== Protocol.sha256_hex(PackedByteArray()), "an empty tree hashes to the bare digest")
