class_name ConnectorEvidence
extends RefCounted
## Logical evidence is independent of rendered frames and raster completion.

const LOGICAL_KINDS: Array[String] = ["logical_tick", "door_attempt", "door_release", "door_opened", "portal_crossed", "ladder_mount", "landing", "ladder_dismount"]
var _previous: Vector3
var _deck: int = 14
var _landing: int = 14
var _started: bool = false
var _digest := HashingContext.new()
var ticks: int = 0

func _init() -> void:
	_digest.start(HashingContext.HASH_SHA256)

static func vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

static func pose(player: Player) -> Dictionary:
	var motion := player.motion
	var deck := motion.locomotion.ladder_state().nearest_landing() if motion.mounted() else motion.deck()
	var capsule := motion.capsule()
	return {"deck": deck, "body_state": motion.state(), "mode": motion.locomotion.mode() if motion.locomotion != null else -1, "eye": vector(motion.eye(player.game)), "capsule": {"foot": vector(capsule.foot), "head": vector(capsule.head)} if capsule != null else null}

func observe(player: Player, tick: int, frame: int) -> Array:
	var game := player.game
	var current := pose(player)
	var out: Array = []
	var base := current.duplicate(true)
	base.tick = tick
	base.frame = frame
	base.source_deck = _deck
	base.destination_deck = current.deck
	var sample := base.duplicate(true)
	sample.kind = "logical_tick"
	sample.rod_carried = player.motion.rod_carried
	sample.bay_open = game.door_open
	sample.power_open = game.power_door_open
	sample.power_active = game.power_active
	sample.console_presses = player.motion.console_presses
	out.append(sample)
	for event: Doors.Event in game.doors.events():
		var entry := base.duplicate(true)
		entry.kind = "door_opened" if event.kind() == Doors.EventKind.OPENED else ("door_release" if event.kind() == Doors.EventKind.RELEASED else "door_attempt")
		entry.id = String(event.door_id())
		entry.face_id = String(event.face_id())
		entry.sequence = event.sequence()
		entry.attempt = event.attempt()
		entry.outcome = event.outcome()
		entry.angle_delta = event.angle_delta()
		var state := game.doors.snapshot(event.door_id())
		entry.state = state.state
		entry.work = state.work
		entry.target_angle = state.target_angle
		entry.wheel_angle = state.wheel_angle
		entry.releases = state.releases
		out.append(entry)
	for event: Ladder.Event in player.motion.ladder_events:
		if event.kind not in [Ladder.EventKind.MOUNT, Ladder.EventKind.LANDING, Ladder.EventKind.LANDED]:
			continue
		var entry := base.duplicate(true)
		entry.kind = "ladder_mount" if event.kind == Ladder.EventKind.MOUNT else ("landing" if event.kind == Ladder.EventKind.LANDING else "ladder_dismount")
		entry.id = String(event.well_id)
		entry.source_deck = _landing
		entry.destination_deck = event.deck
		if event.kind != Ladder.EventKind.MOUNT:
			_landing = event.deck
		out.append(entry)
	var capsule := player.motion.capsule()
	var foot := capsule.foot if capsule != null else player.motion.eye(game)
	if _started and not player.motion.mounted() and _deck == current.deck:
		for id: StringName in game.layout.door_ids():
			var door := game.layout.door(id)
			if door.deck_number() != current.deck or door.kind() not in [ShipLayout.DoorKind.HATCH, ShipLayout.DoorKind.BAY, ShipLayout.DoorKind.POWER]:
				continue
			var inverse := door.frame().affine_inverse()
			var before := inverse * _previous
			var after := inverse * foot
			if (before.z > 0 and after.z <= 0) or (before.z < 0 and after.z >= 0):
				var hit := before.lerp(after, before.z / (before.z - after.z))
				if absf(hit.x) <= door.aperture().x / 2 and hit.y >= 0 and hit.y <= door.aperture().y:
					var entry := base.duplicate(true)
					entry.kind = "portal_crossed"
					entry.id = String(id)
					entry.open = game.doors.snapshot(id).state == Doors.State.OPEN
					entry.from = vector(_previous)
					entry.to = vector(foot)
					out.append(entry)
	_previous = foot
	_deck = current.deck
	_started = capsule != null
	ticks += 1
	for entry: Dictionary in out:
		_digest.update(digest_line(entry).to_utf8_buffer())
	return out

static func digest_line(event: Dictionary) -> String:
	var copy := event.duplicate(true)
	copy.erase("frame")
	return JSON.stringify(_wire_numbers(copy), "", true, true) + "\n"

static func _wire_numbers(value):
	# Godot's JSON numeric parser can shift the last double bit. Digest a fixed
	# nine-decimal wire form while retaining full precision in the raw report.
	if value is int or value is float:
		return "%.9f" % float(value)
	if value is Array:
		return value.map(_wire_numbers)
	if value is Dictionary:
		var normalized: Dictionary = {}
		for key in value:
			normalized[key] = _wire_numbers(value[key])
		return normalized
	return value

func finish_digest() -> String:
	return _digest.finish().hex_encode()

static func digest(events: Array) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	for event: Dictionary in events:
		if String(event.kind) in LOGICAL_KINDS:
			context.update(digest_line(event).to_utf8_buffer())
	return context.finish().hex_encode()

static func label(label_node: ShipLabel, layout: ShipLayout, beat: String, tick: int, frame: int, player: Player) -> Dictionary:
	var face := layout.face(label_node.face_id)
	var door := layout.door(face.door_id())
	var entry := pose(player)
	entry.merge({"kind": "label", "tick": tick, "frame": frame, "beat": beat, "id": String(label_node.face_id), "deck": door.deck_number(), "section": face.destination_section(), "native": label_node.pair.native, "spanish": label_node.pair.perceived_es, "perceive": label_node.perception.perceive, "ready": label_node.pair.ready()})
	return entry
