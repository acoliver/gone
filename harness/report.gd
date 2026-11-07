class_name HarnessReport
extends RefCounted
## The run report, ported from the Rust harness report.rs: event
## timeline, checkpoints, beat manifest, frame stats, and identity.
## Serialized as JSON in the canonical event order (HarnessProtocol.
## sort_events); parsing validates the shape the runner asserts on.

const Protocol := preload("res://harness/protocol.gd")

var protocol_version: int
var scenario: String
var seed: int
var events: Array = []
var checkpoints: Array[String] = []
var frame_stats: Dictionary = {"frames": 0, "mean_us": 0.0, "p95_us": 0.0, "median_us": 0.0}
var perf: Dictionary = {}
var beats: Dictionary = {}
var logical_steps_per_present: int = 1
var logical_ticks: int = 0
var logical_digest: String = ""
var identity: Dictionary = {"app_hash": "", "scenario_hash": "", "config_hash": ""}

func _init(p_protocol_version: int = 0, p_scenario: String = "", p_seed: int = 0, p_identity: Dictionary = {}) -> void:
	protocol_version = p_protocol_version
	scenario = p_scenario
	seed = p_seed
	if not p_identity.is_empty():
		identity = p_identity.duplicate()

static func parse(text: String) -> Dictionary:
	var parsed = JSON.parse_string(text)
	if parsed == null or not (parsed is Dictionary):
		return {"report": null, "error": "report parse error: not a JSON object"}
	var data: Dictionary = parsed
	for key: String in ["protocol_version", "scenario", "seed", "events", "checkpoints", "beats", "identity"]:
		if not data.has(key):
			return {"report": null, "error": "report parse error: missing `%s`" % key}
	var report := new()
	report.protocol_version = int(data.protocol_version)
	report.scenario = String(data.scenario)
	report.seed = int(data.seed)
	if not data.events is Array:
		return {"report": null, "error": "report parse error: events must be an array"}
	for value in data.events:
		if not value is Dictionary:
			return {"report": null, "error": "report parse error: event must be an object"}
		var event: Dictionary = value
		if not event.has("kind") or not event.kind is String:
			return {"report": null, "error": "report parse error: event without a kind"}
		var event_error := ConnectorAssertions.validate(event)
		if not event_error.is_empty():
			return {"report": null, "error": event_error}
		report.events.append(event)
	report.logical_steps_per_present = int(data.get("logical_steps_per_present", 1))
	report.logical_ticks = int(data.get("logical_ticks", 0))
	report.logical_digest = String(data.get("logical_digest", ""))
	for checkpoint: String in data.checkpoints:
		report.checkpoints.append(checkpoint)
	if data.has("frame_stats") and data.frame_stats is Dictionary:
		report.frame_stats = data.frame_stats
	if data.has("perf") and data.perf is Dictionary:
		report.perf = data.perf
	for name: String in data.beats:
		var entry: Dictionary = data.beats[name]
		for key: String in ["file", "tick", "frame", "request_id"]:
			if not entry.has(key):
				return {"report": null,
					"error": "report parse error: beat `%s` entry missing `%s`" % [name, key]}
		report.beats[name] = {"file": String(entry.file), "tick": int(entry.tick),
			"frame": int(entry.frame), "request_id": int(entry.request_id)}
		if entry.has("lamps"):
			var lamp_error: String = preload("res://harness/lamp_samples.gd").validate(entry.lamps)
			if not lamp_error.is_empty():
				return {"report": null, "error": "report parse error: beat `%s`: %s" % [name, lamp_error]}
			report.beats[name].lamps = entry.lamps
	var identity: Dictionary = data.identity
	for key: String in ["app_hash", "scenario_hash", "config_hash"]:
		if not identity.has(key):
			return {"report": null, "error": "report parse error: identity missing `%s`" % key}
	report.identity = {"app_hash": String(identity.app_hash),
		"scenario_hash": String(identity.scenario_hash),
		"config_hash": String(identity.config_hash)}
	return {"report": report, "error": ""}

func add_event(event: Dictionary) -> void:
	events.append(event)

func ready_frame() -> int:
	for event: Dictionary in events:
		if event.kind == "ready":
			return int(event.frame)
	return -1

func first_failure() -> String:
	for event: Dictionary in events:
		if event.kind == "failure":
			return String(event.what)
	return ""

func has_checkpoint(snippet: String) -> bool:
	for checkpoint: String in checkpoints:
		if checkpoint.contains(snippet):
			return true
	return false

func to_json() -> String:
	var sorted := events.duplicate()
	Protocol.sort_events(sorted)
	var data := {
		"protocol_version": protocol_version,
		"scenario": scenario,
		"seed": seed,
		"events": sorted,
		"checkpoints": checkpoints,
		"frame_stats": frame_stats,
		"beats": beats,
		"identity": identity,
		"logical_steps_per_present": logical_steps_per_present,
		"logical_ticks": logical_ticks,
		"logical_digest": logical_digest,
	}
	if not perf.is_empty():
		data.perf = perf
	return JSON.stringify(data, "\t", true, true)
