extends SimTestCase

func test_protocol_five_and_capture_only_batching() -> void:
	assert_int_equal(HarnessProtocol.PROTOCOL_VERSION, 5, "deck-aware evidence protocol")
	var data := {"name": "batch", "logical_steps_per_present": 4}
	var parsed := HarnessScenario.parse(JSON.stringify(data))
	assert_true(parsed.error.is_empty(), "capture accepts four fixed steps")
	assert_int_equal(parsed.scenario.logical_steps_per_present, 4, "batch setting survives parsing")
	for mode: String in ["perf", "calibration"]:
		data.mode = mode
		assert_false(HarnessScenario.parse(JSON.stringify(data)).error.is_empty(), "noncapture rejects acceleration")
	data.mode = "capture"
	for invalid in [0, 5, 1.5, "4"]:
		data.logical_steps_per_present = invalid
		assert_false(HarnessScenario.parse(JSON.stringify(data)).error.is_empty(), "invalid batch rejected")
	var ordinary := HarnessScenario.parse('{"name":"ordinary"}')
	assert_int_equal(ordinary.scenario.logical_steps_per_present, 1, "old lanes retain one step")

class Replay:
	extends HarnessRoute
	var schedule: Array
	var index: int = 0
	var evidence := ConnectorEvidence.new()
	var events: Array = []
	var next_capture: int = 0
	var spec: HarnessScenario
	func next_step() -> void:
		var offered: Array = []
		while index < schedule.size() and int(schedule[index].tick) == tick:
			offered.append(schedule[index])
			index += 1
		step(offered)
		events.append_array(evidence.observe(player, tick, 0))
	func boundary() -> bool:
		return tick >= int(spec.connector.route_ticks) or (next_capture < spec.beats.size() and tick > int(spec.beats[next_capture].tick))

func _fixture(report: HarnessReport, spec: HarnessScenario) -> void:
	var layout := ShipLayout.authored().layout
	var pose := {"deck": 14, "body_state": PlayerMotion.BodyState.WALK, "mode": Locomotion.Mode.WALK, "eye": [33, 1.8, 0], "capsule": {"foot": [33, 0.385, 0], "head": [33, 1.8, 0]}}
	for beat: Dictionary in spec.beats:
		var sample: Dictionary = report.events[int(beat.tick)]
		for observed: Dictionary in report.events:
			if observed.kind == "logical_tick" and int(observed.tick) == int(beat.tick) + 1:
				sample = observed
				break
		var event := sample.duplicate(true)
		var doors: Dictionary = {}
		for id: StringName in layout.door_ids():
			if layout.door(id).deck_number() == int(sample.deck):
				doors[String(id)] = {"state": Doors.State.CLOSED, "attempt": 0, "work": 0, "wheel_angle": 0, "releases": 0}
		for observed: Dictionary in report.events:
			if observed.kind in ["door_attempt", "door_release", "door_opened"] and int(observed.tick) <= int(beat.tick) + 1 and doors.has(observed.id):
				doors[observed.id] = {"state": observed.state, "attempt": observed.attempt, "work": observed.work, "wheel_angle": observed.wheel_angle, "releases": observed.releases}
		event.doors = doors
		var rooms: Array[String] = []
		if int(sample.deck) != 14:
			for deck: int in range(maxi(1, int(sample.deck) - 2), mini(30, int(sample.deck) + 2) + 1):
				if deck != 14:
					rooms.append(String(ShipLayout.connector_id(deck, 1)))
		event.merge({"kind": "residency", "beat": beat.name, "tick": int(beat.tick) + 1, "frame": 0, "rooms": rooms, "pending_rooms": 0, "pending_labels": 0, "remote_lights": rooms.size() * 3, "build_usec": 0}, true)
		report.events.append(event)
	for name: String in spec.connector.labels:
		var expected: Dictionary = spec.connector.labels[name]
		var face := layout.face(StringName(expected.id))
		var deck := layout.door(face.door_id()).deck_number()
		var text := ShipText.hatch_label(deck, face.destination_section())
		var event := pose.duplicate(true)
		var beat: Dictionary = spec.beats.filter(func(value: Dictionary) -> bool: return value.name == name)[0]
		event.merge({"kind": "label", "beat": name, "id": expected.id, "deck": deck, "tick": int(beat.tick) + 1, "frame": 0, "section": face.destination_section(), "native": text.native, "spanish": text.perceived_es, "perceive": 0.0 if expected.stage == "native" else (1.0 if expected.stage == "resolved" else 0.5), "ready": true}, true)
		report.events.append(event)
	HarnessProtocol.sort_events(report.events)

func test_connector_real_input_replay_batches_capture_stops_and_assertion_failures() -> void:
	var spec: HarnessScenario = HarnessScenario.parse(FileAccess.get_file_as_string("res://scenarios/connector-route.json")).scenario
	assert_true(spec.connector.digest == "d10b0792e4dcf0717aa0c09cdca7bcafbc81c0135287a2a14dc0ffbe853e638a", "pinned connector capture schedule")
	var digests: Array[String] = []
	for batch: int in [1, 4]:
		var game := Game.new(spec.seed)
		var player := Player.build(game, null)
		player.scripted = true
		player.adapter = InputPlane.ScriptedAdapter.new()
		player._ready()
		game.wake_state.mark_ready()
		var replay := Replay.new(player, spec.max_frames)
		replay.spec = spec
		replay.schedule = spec.actions
		while replay.tick < int(spec.connector.route_ticks):
			CaptureBatch.advance(batch, replay.next_step, replay.boundary)
			if replay.next_capture < spec.beats.size() and replay.tick > int(spec.beats[replay.next_capture].tick):
				assert_int_equal(replay.tick, int(spec.beats[replay.next_capture].tick) + 1, "batch stops at exact capture tick")
				var before := JSON.stringify(ConnectorEvidence.pose(player))
				var clock := replay.stepper.logical_tick
				for _present: int in range(9):
					replay.stepper.advance(true)
				assert_true(JSON.stringify(ConnectorEvidence.pose(player)) == before and replay.stepper.logical_tick == clock, "delayed capture freezes simulation")
				replay.next_capture += 1
		var digest := replay.evidence.finish_digest()
		digests.append(digest)
		assert_true(digest == spec.connector.digest, "full logical journey matches compiled schedule")
		var report := HarnessReport.new(5, spec.scenario_name, spec.seed)
		report.events = replay.events
		report.logical_digest = digest
		report.logical_ticks = replay.tick
		report.logical_steps_per_present = spec.logical_steps_per_present
		_fixture(report, spec)
		var persisted := HarnessReport.parse(report.to_json())
		assert_true(persisted.error.is_empty(), "full typed report survives serialization")
		if ConnectorEvidence.digest(persisted.report.events) != digest:
			var before_events: Array = report.events.filter(func(event: Dictionary) -> bool: return event.kind in ConnectorEvidence.LOGICAL_KINDS)
			var after_events: Array = persisted.report.events.filter(func(event: Dictionary) -> bool: return event.kind in ConnectorEvidence.LOGICAL_KINDS)
			for index: int in range(before_events.size()):
				if ConnectorEvidence.digest_line(before_events[index]) != ConnectorEvidence.digest_line(after_events[index]):
					print("digest roundtrip first difference before: ", ConnectorEvidence.digest_line(before_events[index]))
					print("digest roundtrip first difference after: ", ConnectorEvidence.digest_line(after_events[index]))
					break
		assert_true(ConnectorEvidence.digest(persisted.report.events) == digest, "JSON numeric roundtrip preserves logical digest")
		for outcome: Dictionary in ConnectorAssertions.evaluate(report, spec):
			assert_true(outcome.passed, "%s: %s" % [outcome.name, outcome.detail])
		if batch == 4:
			var landing_indices: Array[int] = []
			for index: int in range(report.events.size()):
				if report.events[index].kind == "landing":
					landing_indices.append(index)
			var first := landing_indices[0]
			var second := landing_indices[1]
			var saved: Dictionary = report.events[first]
			report.events[first] = report.events[second]
			report.events[second] = saved
			assert_false(ConnectorAssertions.evaluate(report, spec)[0].passed, "reordered landings fail")
			report.events[second] = report.events[first]
			report.events[first] = saved
			report.events.remove_at(first)
			assert_false(ConnectorAssertions.evaluate(report, spec)[0].passed, "missing landing fails")
			report.events.insert(first, saved)
			var label: Dictionary = report.events.filter(func(event: Dictionary) -> bool: return event.kind == "label")[0]
			label.native = "lometa [17]\nshelani paki [51]"
			assert_false(ConnectorAssertions.evaluate(report, spec)[4].passed, "corrupt boxed quantity fails")
		player.free()
	assert_true(digests[0] == digests[1], "batch one/four logical digests equal")
	print("connector capture replay digest: ", digests[0])

func test_typed_report_rejects_missing_nonfinite_and_wrong_shape_evidence() -> void:
	var player := Player.build(Game.new(0), null)
	player.scripted = true
	player._ready()
	var event := ConnectorEvidence.pose(player)
	event.merge({"kind": "door_attempt", "id": "D14-C-001-H-FORE", "face_id": "face", "tick": 1, "frame": 0, "source_deck": 14, "destination_deck": 14, "sequence": 1, "attempt": 1, "outcome": Doors.Outcome.STALLED, "angle_delta": 0, "state": Doors.State.CRANKING, "work": 0, "target_angle": 0, "wheel_angle": 0, "releases": 0})
	var report := HarnessReport.new(5, "probe", 0)
	report.add_event(event)
	assert_true(HarnessReport.parse(report.to_json()).error.is_empty(), "typed event roundtrip")
	event.erase("source_deck")
	assert_false(HarnessReport.parse(report.to_json()).error.is_empty(), "missing movement deck rejected")
	event.source_deck = 14
	event.eye = [0, 0]
	assert_false(HarnessReport.parse(report.to_json()).error.is_empty(), "malformed eye rejected")
	event.eye = [0, NAN, 0]
	assert_false(ConnectorAssertions.validate(event).is_empty(), "nonfinite eye rejected")
	player.free()
