class_name SmokeSymptoms
extends RefCounted
## Deterministic, reversible presyncope exposure trial. Render and audio
## consumers read sample/events; only tick owns dose and event timing.

const TICK_RATE := 60.0
const BAY_END := 5.5
const HALL_START := 6.0
const DOSE_UP_SECS := 18.0
const DOSE_DOWN_SECS := 8.0
const MAX_DOSE := 1.0
const MIN_GAP := 0.2
const PULSE_DURATION := 0.95
const COUGH_DURATION := 1.01
const MILD_DURATION := 0.75
const COUGH_ACTIVE_OFFSET := 0.57
const BREATH_MILD := "breath_mild"
const BREATH_PULSE := "breath_pulse"
const COUGH := "cough"

class Sample:
	extends RefCounted
	var dose: float
	var cough_pulse: float
	var breath_pulse: float
	var tick: int
	func _init(p_dose: float, p_cough: float, p_breath: float, p_tick: int) -> void:
		dose = p_dose
		cough_pulse = p_cough
		breath_pulse = p_breath
		tick = p_tick

class Event:
	extends RefCounted
	var id: int
	var kind: String
	var gain_db: float
	var onset_tick: int
	func _init(p_id: int, p_kind: String, p_gain: float, p_tick: int) -> void:
		id = p_id
		kind = p_kind
		gain_db = p_gain
		onset_tick = p_tick

var _dose := 0.0
var _tick := 0
var _event_id := 0
var _started := false
var _events: Array[Event] = []
var _until_event := 0
var _next_cough := 0
var _breath_count := 0
var _last_end_tick := -100000
var _cough_age := -1
var _cough_cue_delay := -1
var _breath_age := -1

static func exposure_at(position: Vector3) -> float:
	if position.y < 0.0 or position.y > 3.2 or absf(position.z) > 4.0 or position.x >= HALL_START:
		return 0.0
	if position.x <= BAY_END:
		return 1.0
	return 1.0 - (position.x - BAY_END) / (HALL_START - BAY_END)

func tick(phase_ready: bool, position: Vector3) -> void:
	_tick += 1
	if _cough_age >= 0:
		_cough_age += 1
	if _breath_age >= 0:
		_breath_age += 1
	if _cough_cue_delay >= 0:
		_cough_cue_delay -= 1
		if _cough_cue_delay == 0:
			_cough_age = 1
			_cough_cue_delay = -1
	if not phase_ready:
		return
	var exposure := exposure_at(position)
	_dose = clampf(_dose + (exposure / (DOSE_UP_SECS * TICK_RATE)) - ((1.0 - exposure) / (DOSE_DOWN_SECS * TICK_RATE)), 0.0, MAX_DOSE)
	if _dose <= 0.0:
		_until_event = 0
		_next_cough = 0
		_events.clear()
		_started = false
		return
	if not _started:
		_started = true
		_until_event = 21
		_next_cough = 86
	if _until_event > 0:
		_until_event -= 1
	if _next_cough > 0:
		_next_cough -= 1
	if _next_cough == 0 and _cue_available():
		_schedule(COUGH, 1.0, COUGH_DURATION)
		var active_period := lerpf(7.0, 3.5, _dose)
		_next_cough = roundi(active_period * TICK_RATE) + _variance(_event_id, 17)
		_until_event = maxi(_until_event, ceili(COUGH_DURATION * TICK_RATE) + ceili(MIN_GAP * TICK_RATE))
	elif _next_cough > 0 and _until_event == 0:
		var interval := lerpf(2.4, 1.2, _dose)
		var breath_kind := BREATH_MILD
		if _dose >= 0.45 and _breath_count % (3 if _dose < 0.7 else 2) == 1:
			breath_kind = BREATH_PULSE
		var gain := minf(5.0, _dose * 5.0) if breath_kind == BREATH_PULSE else minf(1.0, _dose)
		if _cue_available():
			var duration := PULSE_DURATION if breath_kind == BREATH_PULSE else MILD_DURATION
			_schedule(breath_kind, gain, duration)
			_breath_count += 1
		_until_event = roundi(interval * TICK_RATE) + _variance(_event_id, 7)

func _schedule(kind: String, gain_db: float, duration: float) -> void:
	assert(_cue_available(), "smoke stem must have full duration and silence available")
	var support_ticks := ceili(duration * TICK_RATE)
	_event_id += 1
	var event := Event.new(_event_id, kind, gain_db, _tick)
	_events.append(event)
	_last_end_tick = _tick + support_ticks
	if kind == COUGH:
		_cough_cue_delay = roundi(COUGH_ACTIVE_OFFSET * TICK_RATE)
	else:
		_breath_age = 1

func _cue_available() -> bool:
	return _tick >= _last_end_tick + ceili(MIN_GAP * TICK_RATE)

static func _variance(counter: int, span: int) -> int:
	return posmod(counter * 17 + 11, span * 2 + 1) - span

func drain_events() -> Array[Event]:
	var result := _events
	_events = []
	return result

static func _visual_envelope(age: int, attack_ticks: int, decay_ticks: int) -> float:
	if age <= 0 or age >= attack_ticks + decay_ticks:
		return 0.0
	if age <= attack_ticks:
		return smoothstep(0.0, float(attack_ticks), float(age))
	return 1.0 - smoothstep(0.0, float(decay_ticks), float(age - attack_ticks))

func sample() -> Sample:
	return Sample.new(_dose, _visual_envelope(_cough_age, 6, 30), _visual_envelope(_breath_age, 12, 36) * 0.45, _tick)

func dose() -> float:
	return _dose
