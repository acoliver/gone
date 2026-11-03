class_name ClickObjective
extends RefCounted
## Typed fixed-tick input and straight-line following, independent of devices.

enum Kind { FLOOR, ACT }
const REACH: float = 0.25
const BLOCKED_TICKS: int = 30

var kind: int = Kind.FLOOR
var point := Vector3.ZERO
var target_id: StringName
var deck: int = 14

static func floor_point(position: Vector3, on_deck: int) -> ClickObjective:
	var objective := ClickObjective.new()
	objective.point = position
	objective.deck = on_deck
	return objective

static func act(id: StringName, on_deck: int) -> ClickObjective:
	var objective := ClickObjective.new()
	objective.kind = Kind.ACT
	objective.target_id = id
	objective.deck = on_deck
	return objective

func copy() -> ClickObjective:
	var objective := floor_point(point, deck)
	objective.kind = kind
	objective.target_id = target_id
	return objective

class Follower:
	extends RefCounted
	var current: ClickObjective
	var _blocked_ticks: int = 0

	func set_objective(objective: ClickObjective) -> void:
		current = objective.copy()
		_blocked_ticks = 0

	func cancel() -> void:
		current = null
		_blocked_ticks = 0

	func movement(foot: Vector3, yaw: float, keys: Vector2) -> Vector2:
		if keys != Vector2.ZERO:
			cancel()
			return keys
		if current == null:
			return Vector2.ZERO
		var delta := Vector3(current.point.x - foot.x, 0, current.point.z - foot.z)
		# Leave room for the ordinary walk's eased stop within the 25cm band.
		if delta.length() <= (0.18 if current.kind == ClickObjective.Kind.FLOOR else 0.05):
			if current.kind == ClickObjective.Kind.FLOOR:
				cancel()
			return Vector2.ZERO
		var direction := delta.normalized()
		return Vector2(direction.dot(Vector3(sin(yaw), 0, cos(yaw))), direction.dot(Vector3(cos(yaw), 0, -sin(yaw))))

	func observe(before: Vector3, after: Vector3) -> void:
		if current == null:
			return
		var from := Vector2(before.x - current.point.x, before.z - current.point.z).length()
		var to := Vector2(after.x - current.point.x, after.z - current.point.z).length()
		_blocked_ticks = 0 if from - to > 0.0001 else _blocked_ticks + 1
		if _blocked_ticks >= ClickObjective.BLOCKED_TICKS:
			cancel()
