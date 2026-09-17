class_name HarnessCalibration
extends RefCounted
## The calibration-evidence lane's scenario parameters and setup evidence,
## ported from Rust harness/calibration.rs. The scenario predeclares one
## luminance step, an equal-area bright-patch placement plan, a
## metering-mask selection, and the auto-exposure arm; the app renders the
## scene through exposure settings it controls and records the run's setup
## identity as a tick-stamped report event before any sample is pinned.
## The runner measures the capture PNGs against that setup.

const LEVEL_MAX: float = 100.0
const PATCH_AREA_FRACTION_MAX: float = 0.03
const MASK_CENTER_PATH: String = "res://harness/metering-mask-center.png"
const MASK_UNIFORM_PATH: String = "res://harness/metering-mask-uniform.png"
const VALID_MASKS: Array[String] = ["center_weighted", "uniform"]
const VALID_CELLS: Array[String] = ["A", "B", "C", "D"]

static func mask_path(mask: String) -> String:
	return MASK_CENTER_PATH if mask == "center_weighted" else MASK_UNIFORM_PATH

static func parse_params(data: Dictionary) -> Dictionary:
	var params := {}
	for key: String in ["initial_level", "patch_area_fraction"]:
		if not data.has(key):
			return {"params": null, "error": "calibration parse error: missing `%s`" % key}
		params[key] = float(data[key])
	var step: Dictionary = data.get("step", {})
	if not (step is Dictionary) or not step.has("tick") or not step.has("level"):
		return {"params": null, "error": "calibration parse error: missing `step` {tick, level}"}
	params.step = {"tick": int(step.tick), "level": float(step.level)}
	var patch: Dictionary = data.get("patch", {})
	if not (patch is Dictionary) or not patch.has("type"):
		return {"params": null, "error": "calibration parse error: missing `patch`"}
	var patch_type := String(patch.type)
	match patch_type:
		"fixed_center", "fixed_edge":
			params.patch = {"type": patch_type}
		"center_then_edge":
			if not patch.has("at_tick"):
				return {"params": null,
					"error": "calibration parse error: center_then_edge needs `at_tick`"}
			params.patch = {"type": patch_type, "at_tick": int(patch.at_tick)}
		_:
			return {"params": null,
				"error": "calibration parse error: unknown patch plan `%s`" % patch_type}
	params.mask = String(data.get("mask", "center_weighted"))
	if not VALID_MASKS.has(params.mask):
		return {"params": null,
			"error": "calibration parse error: unknown mask `%s`" % params.mask}
	params.auto_exposure = bool(data.get("auto_exposure", true))
	params.cell = String(data.get("cell", "A"))
	if not VALID_CELLS.has(params.cell):
		return {"params": null,
			"error": "calibration parse error: unknown cell `%s`" % params.cell}
	var error := validate(params)
	if not error.is_empty():
		return {"params": null, "error": error}
	return {"params": params, "error": ""}

static func validate(params: Dictionary) -> String:
	var level_error := _validate_level("initial_level", float(params.initial_level))
	if not level_error.is_empty():
		return level_error
	level_error = _validate_level("step level", float(params.step.level))
	if not level_error.is_empty():
		return level_error
	if int(params.step.tick) < 1:
		return "calibration step tick must be at least 1 (the initial level is sampled first)"
	var area: float = float(params.patch_area_fraction)
	if not is_finite(area) or area <= 0.0:
		return "calibration patch_area_fraction must be finite and positive, got %s" % str(area)
	if area >= PATCH_AREA_FRACTION_MAX:
		return "calibration patch_area_fraction must stay below %s (the patch must fit fully on screen in the edge slot), got %s" % [str(PATCH_AREA_FRACTION_MAX), str(area)]
	if move_tick(params.patch) != null and int(move_tick(params.patch)) < 1:
		return "calibration patch move tick must be at least 1 (the initial placement is sampled first)"
	return ""

static func _validate_level(name: String, level: float) -> String:
	if not is_finite(level) or level <= 0.0:
		return "calibration %s must be finite and positive, got %s" % [name, str(level)]
	if level > LEVEL_MAX:
		return "calibration %s must not exceed %s, got %s" % [name, str(LEVEL_MAX), str(level)]
	return ""

static func move_tick(plan: Dictionary):
	if plan.type == "center_then_edge":
		return int(plan.at_tick)
	return null

static func patch_slot_at(plan: Dictionary, tick: int) -> String:
	if plan.type == "fixed_edge":
		return "edge"
	if plan.type == "center_then_edge" and tick >= int(plan.at_tick):
		return "edge"
	return "center"

## The placements a plan produces, in tick order: the initial slot at
## tick 0, then the move slot at its pinned tick when the plan moves.
static func patch_placements(plan: Dictionary) -> Array:
	if plan.type == "fixed_edge":
		return [{"tick": 0, "slot": "edge"}]
	if plan.type == "center_then_edge":
		return [{"tick": 0, "slot": "center"},
			{"tick": int(plan.at_tick), "slot": "edge"}]
	return [{"tick": 0, "slot": "center"}]

## The wall level on tick: the initial level until the step tick, the
## step level from it on.
static func wall_level(params: Dictionary, tick: int) -> float:
	if tick >= int(params.step.tick):
		return float(params.step.level)
	return float(params.initial_level)

## The auto-exposure settings in force when the arm is on (the port's
## authored constants, mirroring the Rust AutoExposure component's
## range/filter/speeds as bound).
const AE_RANGE_MIN: float = -8.0
const AE_RANGE_MAX: float = 8.0
const AE_FILTER_MIN: float = 0.0
const AE_FILTER_MAX: float = 1.0
const AE_SPEED_BRIGHTEN: float = 3.0
const AE_SPEED_DARKEN: float = 1.0

static func auto_exposure_evidence(enabled: bool) -> Dictionary:
	if not enabled:
		return {"enabled": false, "settings": null}
	return {"enabled": true, "settings": {
		"range_min": AE_RANGE_MIN, "range_max": AE_RANGE_MAX,
		"filter_min": AE_FILTER_MIN, "filter_max": AE_FILTER_MAX,
		"speed_brighten": AE_SPEED_BRIGHTEN, "speed_darken": AE_SPEED_DARKEN,
	}}
