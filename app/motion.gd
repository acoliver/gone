class_name PlayerMotion
extends RefCounted
## Player body motion, ported from gone_app player/motion.rs: the mirror
## that follows the sim's phase machine through the authored get-up and
## the steadying walk. The sim owns every motion decision (the phase
## machine, the authored exit path, the walk ramp, the swept capsule);
## this class only wires the shared input plane, the machine, the
## collider set, and the exit path together, records the first typed
## rejection fail-fast, and never invents motion. Pure logic: testable
## headless with a plain Game container.

enum BodyState { LYING, GET_UP, WALK }

## How close to the hatch center, in meters on the floor plane, an
## interact press must land to be a refusal.
const HATCH_INTERACT_REACH: float = 2.2

var _controller: Exit.GetUpController = null
var _walk: Walk.WalkState = null
var _failure: String = ""
var refusals: int = 0
var refusal_events: Array[String] = []

func state() -> int:
	if _controller != null:
		return BodyState.GET_UP
	if _walk != null:
		return BodyState.WALK
	return BodyState.LYING

func capsule() -> Resolve.Capsule:
	if _controller != null:
		return _controller.capsule()
	if _walk != null:
		return _walk.capsule()
	return null

func failure() -> String:
	return _failure

## The rig's eye point for the mirror's current state; the lying eye is
## the authored path's first pose head, matching the spawn.
func eye(game: Game) -> Vector3:
	match state():
		BodyState.GET_UP:
			return get_up_eye(capsule())
		BodyState.WALK:
			return standing_eye(capsule())
		_:
			return game.exit_path.poses()[0].head()

func record_failure(message: String) -> void:
	if _failure.is_empty():
		_failure = message

## Advance the body one fixed tick: consume the tick's activate press or
## movement intent from the shared plane and drive the sim controller
## the mirror currently holds. dt is the fixed tick's sim seconds.
func advance(plane: InputPlane, game: Game, yaw: float, dt: float) -> void:
	match state():
		BodyState.LYING:
			_begin_get_up_if_pressed(plane, game)
		BodyState.GET_UP:
			_advance_get_up(game)
		BodyState.WALK:
			_advance_walk(plane, game, yaw, dt)

## The Lying tick: a fresh activate press starts the get-up, but only in
## AwakeInPod; every other phase drops the edge, never buffers it.
func _begin_get_up_if_pressed(plane: InputPlane, game: Game) -> void:
	if not plane.take_press(InputPlane.Buttons.ACTIVATE):
		return
	if game.phase.current() != Phase.Wake.AWAKE_IN_POD:
		return
	var result := Exit.GetUpController.start(game.phase, game.exit_path)
	if result.is_ok():
		_controller = result.controller
	else:
		record_failure("get-up rejected: " + result.error._to_string())

## The GetUp tick: drive the authored path exactly one segment through
## the machine and the collider set; reaching the waypoint hands the
## standing capsule to the walk.
func _advance_get_up(game: Game) -> void:
	var tick := _controller.tick(game.phase, game.colliders)
	if not tick.is_ok():
		record_failure("get-up rejected: " + tick.error._to_string())
		return
	if tick.progress.at_waypoint:
		var started := Walk.WalkState.start(game.phase, _controller.capsule())
		if started.is_ok():
			_controller = null
			_walk = started.state
		else:
			record_failure("walk rejected: " + started.error._to_string())

## The Walk tick: the tick's movement intent, framed in the look yaw,
## sweeps the capsule through the resolver at the walk's current speed.
func _advance_walk(plane: InputPlane, game: Game, yaw: float, dt: float) -> void:
	if game.phase.current() != Phase.Wake.STANDING:
		record_failure("the walk state disagrees with the sim phase")
		return
	var movement := plane.take_movement()
	var intent := Walk.MoveIntent.try_new(yaw, movement.x, movement.y)
	if not intent.is_ok():
		record_failure("walk rejected: " + intent.error._to_string())
		return
	var step := _walk.step(intent.intent, dt, game.colliders)
	_walk.end_tick()
	if not step.is_ok():
		record_failure("walk rejected: " + step.error._to_string())

## Consume an interact press at the jammed hatch: while standing in
## reach, the door refuses (there is no opening transition; the hatch
## solids stay exactly as authored) and the refusal is recorded. Returns
## true when the interaction was refused.
func interact_with_hatch(plane: InputPlane, game: Game) -> bool:
	if not plane.take_press(InputPlane.Buttons.INTERACT):
		return false
	if state() != BodyState.WALK:
		return false
	var foot: Vector3 = capsule().foot
	var hatch: Vector2 = game.registry.hatch().center
	var reach := Vector2(foot.x - hatch.x, foot.z - hatch.y)
	if reach.length() > HATCH_INTERACT_REACH:
		return false
	refusals += 1
	refusal_events.append("refused")
	return true

## The walk's current steadying speed, in meters per second.
func walk_speed() -> float:
	return _walk.speed() if _walk != null else 0.0

## The standing rig's eye point: above the foot's ground contact at the
## placement truth's standing eye height.
static func standing_eye(capsule: Resolve.Capsule) -> Vector3:
	return Vector3(
		capsule.foot.x,
		capsule.foot.y - Controller.CAPSULE_RADIUS + PlacementTruth.STANDING_EYE_HEIGHT,
		capsule.foot.z
	)

## The get-up rig's eye point: the capsule's head sphere.
static func get_up_eye(capsule: Resolve.Capsule) -> Vector3:
	return capsule.head
