class_name InputPlane
extends RefCounted
## The shared gameplay input plane, ported from gone_app player/mod.rs.
## Device input (mouse motion, held InputMap actions) and scripted input
## (the harness adapter) converge here, and the gameplay consumers take
## from it, so the body cannot tell a human from the runner. Whatever no
## consumer takes by the end of the fixed tick is dropped by end_frame,
## never buffered. Pure data: no Node or engine input types inside.

## Look rotation per mouse pixel, in radians.
const LOOK_SENSITIVITY: float = 0.0022

## Pitch hard stop just short of the vertical.
const PITCH_LIMIT: float = deg_to_rad(89.0)

enum Buttons { ACTIVATE, INTERACT, EXIT }

var _look: Vector2 = Vector2.ZERO
var _forward: float = 0.0
var _strafe: float = 0.0
var _edges: Array[int] = []

func offer_look(yaw_delta: float, pitch_delta: float) -> void:
	_look += Vector2(yaw_delta, pitch_delta)

## Mouse pixels into the plane's radians: mouse right turns right (yaw
## decreases), mouse up looks up (pitch increases).
func offer_look_pixels(pixels: Vector2) -> void:
	offer_look(-pixels.x * LOOK_SENSITIVITY, -pixels.y * LOOK_SENSITIVITY)

func offer_movement(forward: float, strafe: float) -> void:
	_forward += forward
	_strafe += strafe

func offer_press(button: int) -> void:
	_edges.append(button)

## Take the accumulated look delta, zeroing the channel: exactly one
## consumer sees each tick's motion.
func take_look() -> Vector2:
	var taken := _look
	_look = Vector2.ZERO
	return taken

## Take the movement intent, zeroing the channel.
func take_movement() -> Vector2:
	var taken := Vector2(_forward, _strafe)
	_forward = 0.0
	_strafe = 0.0
	return taken

## Consume one queued press of this button, exactly once.
func take_press(button: int) -> bool:
	if _edges.has(button):
		_edges.erase(button)
		return true
	return false

func pending_edges() -> int:
	return _edges.size()

## Drop everything unconsumed: input not consumed in its tick is lost.
func end_frame() -> void:
	_look = Vector2.ZERO
	_forward = 0.0
	_strafe = 0.0
	_edges.clear()

## Pure look integration over a plane delta in radians: pitch clamps to
## the vertical stop, yaw wraps into (-PI, PI].
static func integrate_look(yaw: float, pitch: float, delta: Vector2) -> Vector2:
	return Vector2(wrap_angle(yaw + delta.x), clampf(pitch + delta.y, -PITCH_LIMIT, PITCH_LIMIT))

static func wrap_angle(angle: float) -> float:
	if absf(angle) <= PI:
		return angle
	var wrapped := fposmod(angle, TAU)
	if wrapped > PI:
		wrapped -= TAU
	return wrapped

## The scripted input adapter: the harness lane's stand-in for the device
## producer. Press edges and look deltas queue for the next tick; held
## movement is offered on every tick until released. offer_tick drains
## exactly one tick's queue onto the plane, so an edge offered once is
## consumed by exactly one fixed tick.
class ScriptedAdapter:
	extends RefCounted

	var _pending_edges: Array[int] = []
	var _pending_look: Vector2 = Vector2.ZERO
	var _held: Vector2 = Vector2.ZERO

	func press(button: int) -> void:
		_pending_edges.append(button)

	func look(yaw_delta: float, pitch_delta: float) -> void:
		_pending_look += Vector2(yaw_delta, pitch_delta)

	func hold(forward: float, strafe: float) -> void:
		_held = Vector2(forward, strafe)

	func release() -> void:
		_held = Vector2.ZERO

	func has_pending_edges() -> bool:
		return not _pending_edges.is_empty()

	## Offer this fixed tick's scripted input onto the shared plane,
	## draining the tick's queue.
	func offer_tick(plane: InputPlane) -> void:
		for button: int in _pending_edges:
			plane.offer_press(button)
		_pending_edges.clear()
		plane.offer_look(_pending_look.x, _pending_look.y)
		_pending_look = Vector2.ZERO
		if _held != Vector2.ZERO:
			plane.offer_movement(_held.x, _held.y)
