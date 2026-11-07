class_name ConnectorAssertions
extends RefCounted
## Typed wire validation and checks over observed production state.

const Evidence := preload("res://harness/connector_evidence.gd")
const CRANK_IDS: Array[String] = ["D14-C-000-H-AFT", "D14-C-000-H-FORE", "D14-C-001-H-AFT", "D14-C-001-H-FORE"]
const KINDS: Array[String] = ["logical_tick", "door_attempt", "door_release", "door_opened", "portal_crossed", "ladder_mount", "landing", "ladder_dismount", "label", "residency"]

static func _number(value) -> bool:
	return (value is int or value is float) and is_finite(float(value))

static func _integer(value) -> bool:
	return _number(value) and float(value) == int(value)

static func _vector(value) -> bool:
	return value is Array and value.size() == 3 and value.all(_number)

static func validate(event: Dictionary) -> String:
	if String(event.kind) not in KINDS:
		return ""
	for key: String in ["tick", "frame", "deck", "mode"]:
		if not event.has(key) or not _integer(event[key]):
			return "connector event %s needs integer %s" % [event.kind, key]
	if int(event.tick) < 1 or int(event.frame) < 0 or int(event.deck) < 1 or int(event.deck) > 30 or (int(event.mode) != -1 and int(event.mode) not in Locomotion.Mode.values()):
		return "connector event has invalid tick/deck/mode"
	var lying: bool = event.get("body_state") == PlayerMotion.BodyState.LYING and int(event.mode) == -1 and event.get("capsule") == null
	var capsule_ok: bool = event.get("capsule") is Dictionary and event.capsule.has_all(["foot", "head"]) and _vector(event.capsule.foot) and _vector(event.capsule.head)
	if not event.has("eye") or not _vector(event.eye) or not (lying or capsule_ok):
		return "connector event needs finite world eye/capsule"
	if event.kind in Evidence.LOGICAL_KINDS:
		for key: String in ["source_deck", "destination_deck"]:
			if not event.has(key) or not _integer(event[key]) or int(event[key]) < 1 or int(event[key]) > 30:
				return "connector movement needs source/destination deck"
	if event.kind in ["door_attempt", "door_release", "door_opened"]:
		if not event.has_all(["id", "face_id", "sequence", "attempt", "outcome", "angle_delta", "state", "work", "target_angle", "wheel_angle", "releases"]) or not event.id is String or not event.face_id is String:
			return "door evidence shape"
		for key: String in ["sequence", "attempt", "outcome", "state", "work", "releases"]:
			if not _integer(event[key]):
				return "door evidence integer %s" % key
		for key: String in ["angle_delta", "target_angle", "wheel_angle"]:
			if not _number(event[key]):
				return "door evidence finite %s" % key
	elif event.kind in ["portal_crossed", "ladder_mount", "landing", "ladder_dismount"]:
		if not event.get("id") is String or event.id.is_empty():
			return "movement evidence id"
		if event.kind == "portal_crossed" and (not event.get("open") is bool or not _vector(event.get("from")) or not _vector(event.get("to"))):
			return "portal evidence shape"
	elif event.kind == "label":
		if not event.has_all(["id", "beat", "section", "native", "spanish", "perceive", "ready"]) or not event.id is String or not event.beat is String or not event.native is String or not event.spanish is String or not _integer(event.section) or not _number(event.perceive) or not event.ready is bool:
			return "label evidence shape"
	elif event.kind == "residency":
		if not event.has_all(["beat", "doors", "rooms", "pending_rooms", "pending_labels", "remote_lights", "build_usec"]) or not event.rooms is Array or not event.doors is Dictionary or not event.beat is String:
			return "residency evidence shape"
		if not event.rooms.all(func(id) -> bool: return id is String or id is StringName):
			return "residency room ids"
		for id in event.doors:
			var state = event.doors[id]
			if not id is String or not state is Dictionary or not state.has_all(["state", "attempt", "work", "wheel_angle", "releases"]):
				return "residency door snapshot shape"
			for key: String in ["state", "attempt", "work", "releases"]:
				if not _integer(state[key]):
					return "residency door snapshot integer"
			if not _number(state.wheel_angle):
				return "residency door wheel angle"
		for key: String in ["pending_rooms", "pending_labels", "remote_lights", "build_usec"]:
			if not _integer(event[key]) or int(event[key]) < 0:
				return "residency evidence counters"
	elif event.kind == "logical_tick":
		if not event.has_all(["rod_carried", "bay_open", "power_open", "power_active", "console_presses"]):
			return "logical tick opening state"
		for key: String in ["rod_carried", "bay_open", "power_open", "power_active"]:
			if not event[key] is bool:
				return "logical tick opening boolean"
		if not _integer(event.console_presses):
			return "logical tick console presses"
	return ""

static func evaluate(report, scenario) -> Array[Dictionary]:
	var outcomes: Array[Dictionary] = []
	var errors: Array[String] = []
	var layout := ShipLayout.authored().layout
	var attempts: Dictionary = {}
	var opened: Array[String] = []
	var released: Array[String] = []
	var crossed: Dictionary = {}
	var ticks := 0
	var last_sequence := 0
	var last_event_tick := 0
	var mounted := false
	var landing_deck := 14
	var journey_landings: Array[int] = []
	var dismounts: Array[int] = []
	var labels: Dictionary = {}
	var residency: Dictionary = {}
	var final: Dictionary = {}
	for event: Dictionary in report.events:
		if String(event.kind) not in KINDS:
			continue
		var malformed := validate(event)
		if not malformed.is_empty():
			errors.append(malformed)
			continue
		if int(event.tick) < last_event_tick:
			errors.append("transition evidence reordered")
		last_event_tick = int(event.tick)
		if event.kind == "logical_tick":
			ticks += 1
			if int(event.tick) != ticks:
				errors.append("missing/reordered logical tick")
			final = event
		elif event.kind in ["door_attempt", "door_release", "door_opened"]:
			if StringName(event.id) not in layout.door_ids():
				errors.append("unknown door id")
				continue
			var door := layout.door(StringName(event.id))
			if int(event.deck) != door.deck_number() or StringName(event.face_id) not in door.face_ids() or int(event.sequence) != last_sequence + 1:
				errors.append("door id/deck/sequence mismatch")
			last_sequence = int(event.sequence)
			if event.kind == "door_attempt":
				var count := int(attempts.get(event.id, 0)) + 1
				attempts[event.id] = count
				if int(event.attempt) != count:
					errors.append("attempt count mismatch")
				if door.policy() == ShipLayout.Policy.CRANK:
					var schedule := HatchResistance.schedule(scenario.seed, door.id())
					if count > schedule.weights.size():
						errors.append("too many seeded attempts")
						continue
					var expected := schedule.angle_after(count)
					var previous := schedule.angle_after(count - 1)
					var stalled := schedule.weights[count - 1] == 0
					if absf(float(event.target_angle) - expected) > 1e-6 or absf(float(event.angle_delta) - (expected - previous)) > 1e-6 or int(event.outcome) != (Doors.Outcome.STALLED if stalled else Doors.Outcome.MOVED):
						errors.append("seeded work/stall/angle mismatch")
				elif door.policy() == ShipLayout.Policy.NEVER_OPENS:
					if int(event.outcome) != Doors.Outcome.REFUSED or int(event.work) != 0 or float(event.target_angle) != 0:
						errors.append("locked door progressed")
			elif event.kind == "door_release":
				if event.id in released or int(event.releases) != 1:
					errors.append("duplicate release")
				released.append(event.id)
			else:
				if event.id not in released or event.id in opened:
					errors.append("open before release or duplicate open")
				opened.append(event.id)
		elif event.kind == "portal_crossed":
			if not event.open or event.id not in opened or int(event.source_deck) != int(event.destination_deck):
				errors.append("illegal portal traversal")
			crossed[event.id] = true
		elif event.kind == "ladder_mount":
			if mounted or event.id != "C-001-LADDER" or int(event.source_deck) != landing_deck or int(event.mode) != Locomotion.Mode.MOUNTING:
				errors.append("mount transition order/id/mode")
			mounted = true
		elif event.kind == "landing":
			var dest := int(event.destination_deck)
			if not mounted or event.id != "C-001-LADDER" or int(event.source_deck) != landing_deck or absi(dest - landing_deck) != 1 or int(event.mode) != Locomotion.Mode.CLIMBING:
				errors.append("landing transition order/id/mode")
			if absf(float(event.capsule.foot[1]) - layout.floor_y(dest) - 0.385) > 0.02502:
				errors.append("landing capsule height")
			landing_deck = dest
			journey_landings.append(dest)
		elif event.kind == "ladder_dismount":
			if not mounted or int(event.destination_deck) != landing_deck or int(event.mode) != Locomotion.Mode.WALK:
				errors.append("dismount transition order/mode")
			mounted = false
			dismounts.append(landing_deck)
		elif event.kind == "label":
			labels[event.beat] = event
		elif event.kind == "residency":
			residency[event.beat] = event
	_add(outcomes, "typed ordered transitions, seeded attempts/stalls and legal traversal", errors.is_empty(), "; ".join(errors))
	var expected_open := CRANK_IDS.duplicate()
	expected_open.append_array([String(ShipLayout.BAY_DOOR_ID), String(ShipLayout.POWER_DOOR_ID)])
	expected_open.sort()
	opened.sort()
	var doors_ok := opened == expected_open and released.size() == expected_open.size()
	for id: String in CRANK_IDS:
		doors_ok = doors_ok and int(attempts.get(id, 0)) == HatchResistance.schedule(scenario.seed, StringName(id)).weights.size() and crossed.has(id)
	_add(outcomes, "exact four D14 crank hatches, one release/open each and four traversals", doors_ok)
	var expected_landings: Array[int] = []
	for deck: int in range(13, 0, -1):
		expected_landings.append(deck)
	for deck: int in range(2, 31):
		expected_landings.append(deck)
	for deck: int in range(29, 13, -1):
		expected_landings.append(deck)
	_add(outcomes, "all 58 ordered landing crossings and D01/D30/D14 dismounts", journey_landings == expected_landings and dismounts == [1, 30, 14] and not mounted)
	var refusal_ok := true
	for deck: int in [1, 30]:
		var spec := layout.connector(ShipLayout.connector_id(deck, 1))
		for id: StringName in spec.hatch_ids() + [layout.lift(spec.lift_id()).door_id()]:
			refusal_ok = refusal_ok and int(attempts.get(String(id), 0)) == 1
	refusal_ok = refusal_ok and int(attempts.get(String(layout.section(&"D14-S-042").side_door_ids()[0]), 0)) == 1
	_add(outcomes, "section42 and endpoint hatch/lift refusals", refusal_ok)
	var label_ok: bool = labels.size() == scenario.connector.labels.size()
	for name: String in scenario.connector.labels:
		if not labels.has(name):
			label_ok = false
			continue
		var event: Dictionary = labels[name]
		var expected: Dictionary = scenario.connector.labels[name]
		var face := layout.face(StringName(expected.id))
		var deck := layout.door(face.door_id()).deck_number()
		var text := ShipText.hatch_label(deck, face.destination_section())
		label_ok = label_ok and event.id == expected.id and int(event.deck) == deck and int(event.section) == face.destination_section() and event.native == text.native and event.spanish == text.perceived_es and event.ready
		# Independently decode the native boxed octal quantities.
		var boxes := RegEx.new()
		boxes.compile("\\[([0-7]+)\\]")
		var matches := boxes.search_all(event.native)
		label_ok = label_ok and matches.size() == 2
		if matches.size() == 2:
			label_ok = label_ok and _octal(matches[0].get_string(1)) == deck and _octal(matches[1].get_string(1)) == face.destination_section()
		var amount := float(event.perceive)
		label_ok = label_ok and (amount == 0 if expected.stage == "native" else (amount == 1 if expected.stage == "resolved" else amount > 0 and amount < 1))
	_add(outcomes, "native/partial/resolved labels and octal/Spanish quantity equality", label_ok)
	var resident_ok: bool = residency.size() == scenario.beats.size()
	for event: Dictionary in residency.values():
		resident_ok = resident_ok and int(event.pending_rooms) == 0 and int(event.pending_labels) == 0 and event.rooms.size() <= 5 and int(event.remote_lights) == event.rooms.size() * 3
		if int(event.deck) != 14:
			resident_ok = resident_ok and ShipLayout.connector_id(int(event.deck), 1) in event.rooms
	for prefix: String in ["fore-inner", "fore-outer", "x30", "x36"]:
		var id: String = {"fore-inner": "D14-C-000-H-AFT", "fore-outer": "D14-C-000-H-FORE", "x30": "D14-C-001-H-FORE", "x36": "D14-C-001-H-AFT"}[prefix]
		for suffix: String in ["closed", "mid-crank", "open"]:
			var sample: Dictionary = residency.get(prefix + "-" + suffix, {})
			var door: Dictionary = sample.get("doors", {}).get(id, {})
			var expected_state := Doors.State.CLOSED if suffix == "closed" else (Doors.State.CRANKING if suffix == "mid-crank" else Doors.State.OPEN)
			resident_ok = resident_ok and int(door.get("state", -1)) == expected_state
	_add(outcomes, "capture residency, bounded queues and closed/cranking/open hatch snapshots", resident_ok)
	var returned: bool = not final.is_empty() and int(final.deck) == 14 and int(final.mode) == Locomotion.Mode.WALK and final.rod_carried and final.bay_open and final.power_open and final.power_active and int(final.console_presses) == 1 and absf(float(final.capsule.foot[1]) - 0.385) < 0.00002
	_add(outcomes, "D14 return preserves opening state", returned)
	var persisted_digest := Evidence.digest(report.events)
	_add(outcomes, "every logical tick and compiled replay digest", ticks == int(scenario.connector.route_ticks) and report.logical_ticks == ticks and report.logical_steps_per_present == scenario.logical_steps_per_present and report.logical_digest == persisted_digest and report.logical_digest == scenario.connector.digest, "ticks=%d reported=%d compiled=%d; digest reported=%s persisted=%s compiled=%s" % [ticks, report.logical_ticks, int(scenario.connector.route_ticks), report.logical_digest, persisted_digest, scenario.connector.digest])
	return outcomes

static func _octal(text: String) -> int:
	var value := 0
	for digit: String in text:
		value = value * 8 + digit.to_int()
	return value

static func _add(outcomes: Array[Dictionary], name: String, passed: bool, detail: String = "") -> void:
	outcomes.append({"name": name, "passed": passed, "detail": detail})
