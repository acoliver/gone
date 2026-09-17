class_name HarnessScenario
extends RefCounted
## Scenario JSON parsing/validation and the pure scripted-input adapter,
## ported from the Rust harness scenario.rs + input.rs. Engine
## independent: actions carry button names as strings ("activate",
## "interact", "exit"); the app lane maps them onto InputPlane.Buttons.
##
## Scenario JSON:
##   {"name": String, "seed": int,
##    "ticks_per_second": int (>= 1, default 60),
##    "mode": "capture", "content": "gameplay",
##    "max_frames": int (deadline after the readiness boundary),
##    "actions": [{"tick": int, "type": "press"|"release",
##                 "button": "activate"|"interact"|"exit"}
##                | {"tick": int, "type": "look",
##                 "yaw_deg": float, "pitch_deg": float}
##                | {"tick": int, "type": "key_turn",
##                 "dir": "left"|"right"}
##                | {"tick": int, "type": "move",
##                 "forward": float, "strafe": float}
##                | {"tick": int, "type": "wait", "duration": float}
##                | {"tick": int, "type": "wait_until_tick", "tick_until": int}],
##    "beats": [{"name": String, "tick": int}]}
##
## The adapter is the port of Rust's InputAdapter: actions dispatch when
## the clock reaches their tick; a wait holds later actions for whole
## ticks (ceil(duration * tps)); a wait_until_tick pins the dispatch
## floor. Each step() returns exactly one tick's edges, look delta
## (degrees), turn-key axis, and movement, each consumed exactly once.

const VALID_BUTTONS: Array[String] = ["activate", "interact", "exit"]
const VALID_TURN_DIRS: Array[String] = ["left", "right"]
const VALID_MODES: Array[String] = ["capture", "perf", "calibration"]
const VALID_CONTENTS: Array[String] = ["calibration", "gameplay"]
const DEFAULT_TICKS_PER_SECOND: int = 60
const DEFAULT_MAX_FRAMES: int = 2000

var scenario_name: String = ""
var seed: int = 0
var ticks_per_second: int = DEFAULT_TICKS_PER_SECOND
var mode: String = "capture"
var content: String = "gameplay"
var max_frames: int = DEFAULT_MAX_FRAMES
var actions: Array = []
var beats: Array = []
var calibration: Dictionary = {}

const CalibrationModule := preload("res://harness/calibration.gd")

static func parse(text: String) -> Dictionary:
	var parsed = JSON.parse_string(text)
	if parsed == null or not (parsed is Dictionary):
		return {"scenario": null, "error": "scenario parse error: not a JSON object"}
	var data: Dictionary = parsed
	var scenario := new()
	if not data.has("name") or not (data.name is String) or data.name.is_empty():
		return {"scenario": null, "error": "scenario parse error: missing name"}
	scenario.scenario_name = data.name
	scenario.seed = int(data.get("seed", 0))
	scenario.ticks_per_second = int(data.get("ticks_per_second", DEFAULT_TICKS_PER_SECOND))
	if scenario.ticks_per_second < 1:
		return {"scenario": null,
			"error": "scenario `%s` has ticks_per_second 0: the fixed clock needs a rate of at least 1 tick per second" % scenario.scenario_name}
	scenario.mode = String(data.get("mode", "capture"))
	if not VALID_MODES.has(scenario.mode):
		return {"scenario": null, "error": "scenario `%s` has unknown mode `%s`" % [scenario.scenario_name, scenario.mode]}
	scenario.content = String(data.get("content", "gameplay"))
	if not VALID_CONTENTS.has(scenario.content):
		return {"scenario": null, "error": "scenario `%s` has unknown content `%s`" % [scenario.scenario_name, scenario.content]}
	scenario.max_frames = int(data.get("max_frames", DEFAULT_MAX_FRAMES))
	for entry: Dictionary in data.get("actions", []):
		var action := _parse_action(scenario.scenario_name, entry)
		if action.is_empty():
			return {"scenario": null, "error": "scenario `%s` has a malformed action" % scenario.scenario_name}
		scenario.actions.append(action)
	var beat_names := {}
	for entry: Dictionary in data.get("beats", []):
		if not entry.has("name") or not entry.has("tick") or String(entry.name).is_empty():
			return {"scenario": null, "error": "scenario `%s` has a malformed beat" % scenario.scenario_name}
		if beat_names.has(entry.name):
			return {"scenario": null, "error": "scenario `%s` has duplicate beat `%s`" % [scenario.scenario_name, entry.name]}
		beat_names[entry.name] = true
		scenario.beats.append({"name": String(entry.name), "tick": int(entry.tick)})
	scenario.beats.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return a.tick < b.tick)
	for action: Dictionary in scenario.actions:
		if action.type == "wait" and action.duration < 0.0:
			return {"scenario": null,
				"error": "scenario `%s` has a wait action with negative duration %f: a wait consumes scenario time, never rewinds it" % [scenario.scenario_name, action.duration]}
	if scenario.mode == "calibration":
		if not (data.has("calibration") and data.calibration is Dictionary):
			return {"scenario": null,
				"error": "scenario `%s` in calibration mode needs a `calibration` section" % scenario.scenario_name}
		var parsed_calibration: Dictionary = CalibrationModule.parse_params(data.calibration)
		if parsed_calibration.error != "":
			return {"scenario": null, "error": "scenario `%s`: %s" % [scenario.scenario_name, parsed_calibration.error]}
		scenario.calibration = parsed_calibration.params
	return {"scenario": scenario, "error": ""}

static func _parse_action(scenario_name: String, entry: Dictionary) -> Dictionary:
	if not entry.has("tick") or not entry.has("type"):
		return {}
	var action := {"tick": int(entry.tick), "type": String(entry.type)}
	match action.type:
		"press", "release":
			var button := String(entry.get("button", ""))
			if not VALID_BUTTONS.has(button):
				return {}
			action.button = button
		"look":
			action.yaw_deg = float(entry.get("yaw_deg", 0.0))
			action.pitch_deg = float(entry.get("pitch_deg", 0.0))
		"key_turn":
			var dir := String(entry.get("dir", ""))
			if not VALID_TURN_DIRS.has(dir):
				return {}
			action.dir = dir
		"move":
			action.forward = float(entry.get("forward", 0.0))
			action.strafe = float(entry.get("strafe", 0.0))
		"wait":
			action.duration = float(entry.get("duration", 0.0))
		"wait_until_tick":
			action.tick_until = int(entry.get("tick_until", 0))
		_:
			return {}
	return action

## The pure scripted-input state machine (Rust InputAdapter). Buttons
## stay strings here; the app lane maps them to the input plane's enum.
class InputAdapter:
	extends RefCounted

	var _actions: Array = []
	var _edges: Array = []
	var _pending_look: Vector2 = Vector2.ZERO
	var _pending_key_turn: float = 0.0
	var _pending_movement: Vector2 = Vector2.ZERO
	var _tick_floor: int = 0
	var _ticks_per_second: int = 60
	var _hold_until_tick: int = 0
	var _hold_remaining_ticks: float = 0.0

	func _init(p_actions: Array = [], p_ticks_per_second: int = 60) -> void:
		assert(p_ticks_per_second > 0, "the input adapter needs a tick rate of at least 1")
		_actions = p_actions.duplicate()
		_actions.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
			return a.tick < b.tick)
		_ticks_per_second = p_ticks_per_second

	func tick() -> int:
		return _tick_floor

	func is_complete() -> bool:
		return _actions.is_empty() and _edges.is_empty()

	## Advance one fixed update: exactly this tick's button edges, look
	## delta (degrees), turn-key axis (+1 right, -1 left; same-tick key
	## turns sum), and movement intent. Held actions stay queued
	## until their wait lifts, whatever their own ticks say.
	func step() -> Dictionary:
		var out := {"edges": [], "look_deg": Vector2.ZERO, "key_turn": 0.0, "movement": Vector2.ZERO}
		if _hold_remaining_ticks > 0.0:
			_hold_remaining_ticks -= 1.0
		while not _actions.is_empty():
			var front: Dictionary = _actions[0]
			if front.tick > _tick_floor or _tick_floor < _hold_until_tick or _hold_remaining_ticks > 0.0:
				break
			_actions.pop_front()
			_apply(front, out)
		out.look_deg = _pending_look
		_pending_look = Vector2.ZERO
		out.key_turn = _pending_key_turn
		_pending_key_turn = 0.0
		out.movement = _pending_movement
		_pending_movement = Vector2.ZERO
		_tick_floor += 1
		return out

	func _apply(action: Dictionary, out: Dictionary) -> void:
		match action.type:
			"press":
				out.edges.append({"button": action.button, "edge": "press"})
			"release":
				out.edges.append({"button": action.button, "edge": "release"})
			"look":
				_pending_look += Vector2(action.yaw_deg, action.pitch_deg)
			"key_turn":
				_pending_key_turn += 1.0 if action.dir == "right" else -1.0
			"move":
				_pending_movement += Vector2(action.forward, action.strafe)
			"wait":
				_hold_remaining_ticks = ceil(maxf(action.duration, 0.0) * float(_ticks_per_second))
			"wait_until_tick":
				_hold_until_tick = maxi(action.tick_until, _tick_floor)
