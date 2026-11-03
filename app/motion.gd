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

var _controller: Exit.GetUpController = null
var locomotion: Locomotion
var ladder_events: Array[Ladder.Event] = []
var _failure: String = ""
var hallway_switch_flips: int = 0
var console_presses: int = 0
var rod_carried: bool = false
var objectives := ClickObjective.Follower.new()

func state() -> int:
	if _controller != null:
		return BodyState.GET_UP
	if locomotion != null:
		return BodyState.WALK
	return BodyState.LYING

func capsule() -> Resolve.Capsule:
	if _controller != null:
		return _controller.capsule()
	if locomotion != null:
		return locomotion.capsule()
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
func advance(plane: InputPlane, game: Game, yaw: float, dt: float, facing: Vector3 = Vector3.ZERO) -> void:
	ladder_events = []
	var previous := capsule()
	match state():
		BodyState.LYING:
			_begin_get_up_if_pressed(plane, game)
		BodyState.GET_UP:
			_advance_get_up(game)
		BodyState.WALK:
			_advance_walk(plane, game, yaw, dt, Vector3(-sin(yaw), 0, -cos(yaw)) if facing == Vector3.ZERO else facing)
	if previous != null and capsule() != null:
		game.observe_bay_crossing(previous.foot, capsule().foot, state() == BodyState.WALK)

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
			locomotion = Locomotion.start(game.layout, game.collision, 14, started.state).state
		else:
			record_failure("walk rejected: " + started.error._to_string())

## The Walk tick: the tick's movement intent, framed in the look yaw,
## sweeps the capsule through the resolver at the walk's current speed.
func _advance_walk(plane: InputPlane, game: Game, yaw: float, dt: float, facing: Vector3) -> void:
	if game.phase.current() != Phase.Wake.STANDING:
		record_failure("the walk state disagrees with the sim phase")
		return
	var movement := plane.take_movement()
	if plane.movement_pressed():
		objectives.cancel()
	if not mounted():
		movement = objectives.movement(capsule().foot, yaw, movement)
	var before := capsule().foot
	var intent := Walk.MoveIntent.try_new(yaw, movement.x, movement.y)
	if not intent.is_ok():
		record_failure("walk rejected: " + intent.error._to_string())
		return
	var input := Locomotion.Intent.new()
	input.walk = intent.intent
	var climb: Variant = plane.take_climb()
	input.has_climb = climb != null
	input.climb = 0.0 if climb == null else float(climb)
	if mounted():
		input.space = plane.take_press(InputPlane.Buttons.INTERACT)
	elif plane.has_press(InputPlane.Buttons.INTERACT):
		input.well_id = mount_target(game.layout, facing)
		if input.well_id != &"":
			input.space = plane.take_press(InputPlane.Buttons.INTERACT)
	input.facing = facing
	var result := locomotion.step(input, dt)
	locomotion.end_tick()
	if not result.is_ok():
		record_failure("locomotion rejected: %d" % result.error.kind)
		return
	ladder_events = result.events
	objectives.observe(before, capsule().foot)

func mounted() -> bool:
	return locomotion != null and locomotion.mode() != Locomotion.Mode.WALK

func deck() -> int:
	return locomotion.deck() if locomotion != null else 14

func mount_target(layout: ShipLayout, facing: Vector3) -> StringName:
	if locomotion == null or mounted() or capsule().foot.z > -1.5:
		return &""
	for id: StringName in layout.well_ids():
		if not Ladder.try_mount(layout, id, deck(), capsule(), facing).is_ok():
			continue
		var well := layout.well(id)
		var target := Interactions.Target.new()
		target.policy = Interactions.Selection.FACE_RAY
		target.deck = deck()
		target.center = well.climb_line().origin
		target.center.y = layout.floor_y(deck())
		target.frame = Transform3D(Basis(), target.center)
		target.size = well.doorway_size()
		var context := Interactions.Context.new()
		context.walking = true
		context.deck = deck()
		context.foot = capsule().foot
		context.eye = standing_eye(capsule())
		context.forward = facing
		if Interactions.hit_distance(target, context, []) >= 0:
			return id
	return &""

## The walk's current steadying speed, in meters per second.
func walk_speed() -> float:
	return locomotion.walk_speed() if locomotion != null else 0.0

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
