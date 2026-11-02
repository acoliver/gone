class_name DisplayPerception
extends RefCounted
## One display's reading, advanced once per fixed 60 Hz tick.

const FIRST_HOLD: int = 72
const FIRST_RAMP: int = 96
const LATER_HOLD: int = 21
const LATER_RAMP: int = 36
const DECAY: int = 21
const ATTENTION_RANGE: float = 4.0
const ATTENTION_MARGIN: float = 0.20

class Memory:
	extends RefCounted
	## Owned by the protagonist's Game, shared by every display.
	var has_resolved: bool = false

var perceive: float = 0.0
var _memory: Memory
var _attending: bool = false
var _elapsed: int = 0
var _hold: int = FIRST_HOLD
var _ramp: int = FIRST_RAMP
var _ramp_start: float = 0.0

func _init(memory: Memory) -> void:
	_memory = memory

func text_changed() -> void:
	perceive = 0.0
	_attending = false
	_elapsed = 0

func tick(attend: bool) -> void:
	if not attend:
		_attending = false
		_elapsed = 0
		perceive = maxf(0.0, perceive - 1.0 / DECAY)
		if perceive < 1e-8:
			perceive = 0.0
		return
	if not _attending:
		_attending = true
		# Keep slow timing through text resets until he realizes he can read the
		# ship's writing by completing a resolution; an early press must not skip it.
		_hold = LATER_HOLD if _memory.has_resolved else FIRST_HOLD
		_ramp = LATER_RAMP if _memory.has_resolved else FIRST_RAMP
		_ramp_start = perceive
	_elapsed += 1
	if _elapsed > _hold:
		var fraction := minf(1.0, float(_elapsed - _hold) / _ramp)
		perceive = lerpf(_ramp_start, 1.0, fraction)
		if perceive == 1.0:
			_memory.has_resolved = true
			_elapsed = _hold + _ramp

static func attends(eye: Vector3, camera_forward: Vector3, center: Vector3,
		right_half_extent: Vector3, up_half_extent: Vector3, screen_front: Vector3) -> bool:
	var to_screen := center - eye
	if to_screen.length_squared() > ATTENTION_RANGE * ATTENTION_RANGE:
		return false
	var front_distance := screen_front.dot(-to_screen)
	if front_distance <= 0.0:
		return false
	var approach := camera_forward.dot(screen_front)
	if approach >= 0.0:
		return false
	var hit_offset := eye + camera_forward * (-front_distance / approach) - center
	var half_size := Vector2(right_half_extent.length(), up_half_extent.length()) \
		+ Vector2(ATTENTION_MARGIN, ATTENTION_MARGIN)
	var hit_position := Vector2(hit_offset.dot(right_half_extent.normalized()),
		hit_offset.dot(up_half_extent.normalized()))
	return absf(hit_position.x) <= half_size.x and absf(hit_position.y) <= half_size.y
