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
## interact press must land to act at the door.
const HATCH_INTERACT_REACH: float = 2.2

## How close to the rod's floor-plan center, in meters, an interact
## press must land to pick it up.
const ROD_PICKUP_REACH: float = 1.3

## How close to the hallway switch's plate, in meters on the floor
## plane, an interact press must land to flip it.
const SWITCH_ACT_REACH: float = 2.2

## The door's deterministic opening, in fixed ticks: the slab retracts
## flat into the doorway's wall band, then slides aside along -Z. The
## tick counts are the whole animation contract — no runtime
## randomness, no wall-clock term.
const DOOR_RETRACT_TICKS: int = 12
const DOOR_SLIDE_TICKS: int = 36

## How far, in meters, the slab travels in each phase: the retract
## tucks the slab inside the east wall's band, the slide clears the
## doorway's walkable width past its frame edge.
const DOOR_RETRACT_DISTANCE: float = 0.17
const DOOR_SLIDE_DISTANCE: float = 1.2

enum DoorState { CLOSED, OPENING, OPEN }

var _controller: Exit.GetUpController = null
var _walk: Walk.WalkState = null
var _failure: String = ""
var door_state: int = DoorState.CLOSED
var door_elapsed: int = 0
var door_openings: int = 0
var hallway_switch_flips: int = 0
var rod_carried: bool = false

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
	_tick_door(game)
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

## Consume an interact press at the stasis room door: while standing in
## reach, the first press starts the door's deterministic opening and
## every further in-reach press is eaten the same way — the door owns
## every press at the door, open or not, exactly as the old refusal
## did. A press out of the door's reach is left on the channel: the
## hallway switch, out at the far wall, shares the interact channel and
## needs the press the door cannot use. Returns true when the press was
## consumed at the door.
func interact_with_door(plane: InputPlane, game: Game) -> bool:
	if state() != BodyState.WALK:
		return false
	var foot: Vector3 = capsule().foot
	var hatch: Vector2 = game.registry.hatch().center
	var reach := Vector2(foot.x - hatch.x, foot.z - hatch.y)
	if reach.length() > HATCH_INTERACT_REACH:
		return false
	if not plane.take_press(InputPlane.Buttons.INTERACT):
		return false
	if door_state == DoorState.CLOSED:
		door_state = DoorState.OPENING
		door_openings += 1
	return true

## The door's opening tick, driven at the head of every advance so the
## animation runs whatever the body is doing. The doorway's colliders
## open only when the animation lands, so the capsule can never cut
## through the moving door.
func _tick_door(game: Game) -> void:
	if door_state != DoorState.OPENING:
		return
	door_elapsed += 1
	if door_elapsed >= DOOR_RETRACT_TICKS + DOOR_SLIDE_TICKS:
		door_state = DoorState.OPEN
		game.open_doorway()

## The door slab's animated offset from its authored ajar pose, in world
## space: the deterministic projection the hatch's door piece renders.
func door_slab_offset() -> Vector3:
	if door_state == DoorState.CLOSED:
		return Vector3.ZERO
	var retract: float = clampf(float(door_elapsed) / float(DOOR_RETRACT_TICKS), 0.0, 1.0)
	var slide: float = clampf(
		float(door_elapsed - DOOR_RETRACT_TICKS) / float(DOOR_SLIDE_TICKS),
		0.0, 1.0)
	return Vector3(DOOR_RETRACT_DISTANCE * retract, 0.0, -DOOR_SLIDE_DISTANCE * slide)

## Flip the hallway switch: while standing in reach of the far-wall
## plate, one interact press lights the hallway fixtures, exactly once.
## The press is consumed only when the flip lands, like the rod pickup:
## a press out of reach or before standing stays on the channel for the
## door to own.
func flip_hallway_switch(plane: InputPlane, game: Game) -> bool:
	if hallway_switch_flips >= 1:
		return false
	if state() != BodyState.WALK:
		return false
	var foot: Vector3 = capsule().foot
	var center: Vector3 = Hallway.switch_act_center()
	var reach := Vector2(foot.x - center.x, foot.z - center.z)
	if reach.length() > SWITCH_ACT_REACH:
		return false
	if not plane.take_press(InputPlane.Buttons.INTERACT):
		return false
	hallway_switch_flips += 1
	game.light_hallway()
	return true

## Pick up the dropped rod: while standing in reach, one interact press
## sets the carried flag, exactly once. The press is consumed only when
## the pickup lands, unlike the door, which eats every press: the rod
## and the door share the interact channel, and the door must still own
## every press at the door, so the rod takes only what it can use and
## leaves the edge to the door otherwise. A press after the pickup is a
## no-op.
func pickup_rod(plane: InputPlane) -> bool:
	if rod_carried:
		return false
	if state() != BodyState.WALK:
		return false
	var foot: Vector3 = capsule().foot
	var center := Rod.floor_center()
	var reach := Vector2(foot.x - center.x, foot.z - center.y)
	if reach.length() > ROD_PICKUP_REACH:
		return false
	if not plane.take_press(InputPlane.Buttons.INTERACT):
		return false
	rod_carried = true
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
