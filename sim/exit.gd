class_name Exit
extends RefCounted
## The authored get-up path out of the stasis pod and its tick-driven
## controller, ported from gone_sim exit/mod.rs. ExitPath authors the exit
## as five key capsule poses (lying, sitting up, standing in the tray,
## through the aperture mouth, standing on the room floor) with every
## number derived from the frozen controller and pods constants; the pod
## placement and the tray floor height are inputs. GetUpController drives
## the phase machine from AwakeInPod through ExitingPod to Standing while
## walking the capsule along the path, one authored segment per tick,
## every motion swept through the caller's ColliderSet by the landed
## resolver. A sweep stopped short of the target pose is a hard
## PathBlocked error, never a silent clamp and never a pass through
## geometry. Units: meters, up is positive Y. Pure logic: no Node, scene,
## rendering, or input types.

## Arrival tolerance for one authored pose: twice the resolver's
## penetration tolerance. A tick that stops within this distance of the
## authored pose counts as reaching it; anything farther is a blocked
## path, never a near miss to shrug off.
const POSE_TOLERANCE: float = 2.0 * Controller.PENETRATION_TOLERANCE

## The clear width the exit aperture mouth must hold for the path to be
## walkable: the capsule diameter plus the frozen POD_EXIT_CLEARANCE on
## each jamb.
const EXIT_MOUTH_WIDTH: float = 2.0 * (Controller.CAPSULE_RADIUS + Controller.POD_EXIT_CLEARANCE)

## How many key poses the authored path holds.
const EXIT_POSE_COUNT: int = 5

## How many authored segments connect the key poses.
const _EXIT_SEGMENT_COUNT: int = EXIT_POSE_COUNT - 1

## Slack for classifying an authored segment as rigid. The pose table's
## rigid deltas are formed per sphere through independent adds, so
## equal-by-construction deltas can disagree in the last ulp. The band
## sits orders of magnitude above that rounding noise and below the pose
## tolerance.
const _RIGID_SLACK: float = 1e-5

## Slack for authored-pivot geometry checks: axis-aligned radius vectors
## formed through the placement transform can carry cross-axis terms of a
## few ulps, which this band absorbs while staying far below any authored
## pivot dimension.
const _PIVOT_SLACK: float = 1e-4

class ExitPathError:
	extends RefCounted

	enum Kind { NON_FINITE_PLACEMENT, NON_FINITE_TRAY_FLOOR, TRAY_FLOOR_BELOW_ROOM, TRAY_FLOOR_TOO_HIGH, AUTHORED_PATH_DISCONNECTED }

	var kind: int = Kind.NON_FINITE_PLACEMENT
	var max_floor: float = 0.0
	var got: float = 0.0
	var index: int = 0

	static func non_finite_placement() -> Exit.ExitPathError:
		var error: Exit.ExitPathError = Exit.ExitPathError.new()
		error.kind = Kind.NON_FINITE_PLACEMENT
		return error

	static func non_finite_tray_floor() -> Exit.ExitPathError:
		var error: Exit.ExitPathError = Exit.ExitPathError.new()
		error.kind = Kind.NON_FINITE_TRAY_FLOOR
		return error

	static func tray_floor_below_room(p_got: float) -> Exit.ExitPathError:
		var error: Exit.ExitPathError = Exit.ExitPathError.new()
		error.kind = Kind.TRAY_FLOOR_BELOW_ROOM
		error.got = p_got
		return error

	static func tray_floor_too_high(p_max_floor: float, p_got: float) -> Exit.ExitPathError:
		var error: Exit.ExitPathError = Exit.ExitPathError.new()
		error.kind = Kind.TRAY_FLOOR_TOO_HIGH
		error.max_floor = p_max_floor
		error.got = p_got
		return error

	static func authored_path_disconnected(p_index: int) -> Exit.ExitPathError:
		var error: Exit.ExitPathError = Exit.ExitPathError.new()
		error.kind = Kind.AUTHORED_PATH_DISCONNECTED
		error.index = p_index
		return error

	func equals(other: Exit.ExitPathError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.TRAY_FLOOR_BELOW_ROOM:
				return Exit._same_float(got, other.got)
			Kind.TRAY_FLOOR_TOO_HIGH:
				return Exit._same_float(max_floor, other.max_floor) and Exit._same_float(got, other.got)
			Kind.AUTHORED_PATH_DISCONNECTED:
				return index == other.index
			_:
				return true

	func _to_string() -> String:
		match kind:
			Kind.NON_FINITE_PLACEMENT:
				return "pod placement carried a non-finite coordinate or yaw"
			Kind.NON_FINITE_TRAY_FLOOR:
				return "tray floor height was non-finite"
			Kind.TRAY_FLOOR_BELOW_ROOM:
				return "tray floor %s m sits below the room floor" % str(got)
			Kind.TRAY_FLOOR_TOO_HIGH:
				return "tray floor %s m exceeds the %s m ceiling the lying capsule fits under" % [str(got), str(max_floor)]
			_:
				return "authored exit pose %d is not connected to the previous pose by a rigid move or a pivot" % index

class ExitError:
	extends RefCounted

	enum Kind { WRONG_PHASE, PATH_BLOCKED, RESOLVER, GET_UP_ALREADY_COMPLETE }

	var kind: int = Kind.WRONG_PHASE
	var expected: int = Phase.Wake.WAKING
	var current: int = Phase.Wake.WAKING
	var pose_index: int = 0
	var shortfall: float = 0.0
	var resolver: Resolve.ResolveError = null

	static func wrong_phase(p_expected: int, p_current: int) -> Exit.ExitError:
		var error: Exit.ExitError = Exit.ExitError.new()
		error.kind = Kind.WRONG_PHASE
		error.expected = p_expected
		error.current = p_current
		return error

	static func path_blocked(p_pose_index: int, p_shortfall: float) -> Exit.ExitError:
		var error: Exit.ExitError = Exit.ExitError.new()
		error.kind = Kind.PATH_BLOCKED
		error.pose_index = p_pose_index
		error.shortfall = p_shortfall
		return error

	static func resolver_error(failure: Resolve.ResolveError) -> Exit.ExitError:
		var error: Exit.ExitError = Exit.ExitError.new()
		error.kind = Kind.RESOLVER
		error.resolver = failure
		return error

	static func get_up_already_complete() -> Exit.ExitError:
		var error: Exit.ExitError = Exit.ExitError.new()
		error.kind = Kind.GET_UP_ALREADY_COMPLETE
		return error

	func equals(other: Exit.ExitError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.WRONG_PHASE:
				return expected == other.expected and current == other.current
			Kind.PATH_BLOCKED:
				return pose_index == other.pose_index and Exit._same_float(shortfall, other.shortfall)
			Kind.RESOLVER:
				return resolver != null and resolver.equals(other.resolver)
			_:
				return true

	func _to_string() -> String:
		match kind:
			Kind.WRONG_PHASE:
				return "get-up expected phase %s, found %s: the call is rejected and nothing moved" % [Phase.phase_name(expected), Phase.phase_name(current)]
			Kind.PATH_BLOCKED:
				return "get-up sweep toward pose %d was stopped %s m short: the authored path is blocked" % [pose_index, str(shortfall)]
			Kind.RESOLVER:
				return "get-up sweep rejected by the resolver: %s" % resolver._to_string()
			_:
				return "the get-up already reached the waypoint"

## One authored key pose: a capsule segment position plus the arrival
## tolerance, in room coordinates.
class ExitPose:
	extends RefCounted

	var _foot: Vector3 = Vector3.ZERO
	var _head: Vector3 = Vector3.ZERO
	var _tolerance: float = 0.0

	func _init(p_foot: Vector3, p_head: Vector3, p_tolerance: float) -> void:
		_foot = p_foot
		_head = p_head
		_tolerance = p_tolerance

	func foot() -> Vector3:
		return _foot

	func head() -> Vector3:
		return _head

	func tolerance() -> float:
		return _tolerance

	func capsule() -> Resolve.Capsule:
		var copy: Resolve.Capsule = Resolve.Capsule.new()
		copy.foot = _foot
		copy.head = _head
		return copy

## How one authored segment moves the capsule, and the single resolver
## displacement whose sweep conservatively covers it. A rigid segment
## sweeps its own translation. A pivot is a quarter turn of the free
## sphere about the fixed sphere between axis-aligned radius directions,
## and sweeps the whole capsule by the free sphere's reached radius
## vector: the true swept quarter sector stays inside that straight
## sweep.
class SegmentMove:
	extends RefCounted

	enum Kind { RIGID, PIVOT_ABOUT_FOOT, PIVOT_ABOUT_HEAD }

	var kind: int = Kind.RIGID
	var _vector: Vector3 = Vector3.ZERO

	static func rigid(displacement: Vector3) -> Exit.SegmentMove:
		var movement: Exit.SegmentMove = Exit.SegmentMove.new()
		movement.kind = Kind.RIGID
		movement._vector = displacement
		return movement

	static func pivot_about_foot(radius: Vector3) -> Exit.SegmentMove:
		var movement: Exit.SegmentMove = Exit.SegmentMove.new()
		movement.kind = Kind.PIVOT_ABOUT_FOOT
		movement._vector = radius
		return movement

	static func pivot_about_head(radius: Vector3) -> Exit.SegmentMove:
		var movement: Exit.SegmentMove = Exit.SegmentMove.new()
		movement.kind = Kind.PIVOT_ABOUT_HEAD
		movement._vector = radius
		return movement

	func vector() -> Vector3:
		return _vector

	## The capsule state once the segment is reached. A rigid segment
	## applies the resolver's own displacement, so a stop inside the
	## tolerance band leaves the capsule where the sweep put it. A pivot
	## keeps its fixed sphere put and places the free sphere at its
	## reached radius: the sweep proved the quarter sector free.
	func visited(current: Resolve.Capsule, swept: Vector3) -> Resolve.Capsule:
		var capsule: Resolve.Capsule = Resolve.Capsule.new()
		match kind:
			Kind.RIGID:
				capsule.foot = current.foot + swept
				capsule.head = current.head + swept
			Kind.PIVOT_ABOUT_FOOT:
				capsule.foot = current.foot
				capsule.head = current.foot + _vector
			_:
				capsule.foot = current.head + _vector
				capsule.head = current.head
		return capsule

	func equals(other: Exit.SegmentMove) -> bool:
		return other != null and kind == other.kind and _vector == other._vector

class GetUpProgress:
	extends RefCounted

	var pose_index: int = 0
	var at_waypoint: bool = false

class PathResult:
	extends RefCounted

	var path: Exit.ExitPath = null
	var error: Exit.ExitPathError = null

	static func with_path(valid: Exit.ExitPath) -> Exit.PathResult:
		var result: Exit.PathResult = Exit.PathResult.new()
		result.path = valid
		return result

	static func with_error(failure: Exit.ExitPathError) -> Exit.PathResult:
		var result: Exit.PathResult = Exit.PathResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class StartResult:
	extends RefCounted

	var controller: Exit.GetUpController = null
	var error: Exit.ExitError = null

	static func with_controller(started: Exit.GetUpController) -> Exit.StartResult:
		var result: Exit.StartResult = Exit.StartResult.new()
		result.controller = started
		return result

	static func with_error(failure: Exit.ExitError) -> Exit.StartResult:
		var result: Exit.StartResult = Exit.StartResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class TickResult:
	extends RefCounted

	var progress: Exit.GetUpProgress = null
	var error: Exit.ExitError = null

	static func with_progress(made: Exit.GetUpProgress) -> Exit.TickResult:
		var result: Exit.TickResult = Exit.TickResult.new()
		result.progress = made
		return result

	static func with_error(failure: Exit.ExitError) -> Exit.TickResult:
		var result: Exit.TickResult = Exit.TickResult.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

## The authored exit from the pod: five key capsule poses in room
## coordinates plus the per-segment movement table. Built only through
## try_new, which validates the inputs and the authored table's
## connectivity.
class ExitPath:
	extends RefCounted

	var _poses: Array[Exit.ExitPose] = []
	var _moves: Array[Exit.SegmentMove] = []

	static func try_new(placement: Pods.PodPlacement, tray_floor_y: float) -> Exit.PathResult:
		if not (is_finite(placement.center.x) and is_finite(placement.center.y) and is_finite(placement.yaw_radians)):
			return Exit.PathResult.with_error(Exit.ExitPathError.non_finite_placement())
		if not is_finite(tray_floor_y):
			return Exit.PathResult.with_error(Exit.ExitPathError.non_finite_tray_floor())
		if tray_floor_y < 0.0:
			return Exit.PathResult.with_error(Exit.ExitPathError.tray_floor_below_room(tray_floor_y))
		var max_floor: float = Pods.POD_HEIGHT - 2.0 * Controller.CAPSULE_RADIUS
		if tray_floor_y > max_floor:
			return Exit.PathResult.with_error(Exit.ExitPathError.tray_floor_too_high(max_floor, tray_floor_y))
		var poses: Array[Exit.ExitPose] = Exit._authored_poses(placement, tray_floor_y)
		var moves: Array[Exit.SegmentMove] = []
		for index: int in range(Exit._EXIT_SEGMENT_COUNT):
			var movement: Exit.SegmentMove = Exit.segment_move(poses[index], poses[index + 1])
			if movement == null:
				return Exit.PathResult.with_error(Exit.ExitPathError.authored_path_disconnected(index))
			moves.append(movement)
		var path: Exit.ExitPath = Exit.ExitPath.new()
		path._poses = poses
		path._moves = moves
		return Exit.PathResult.with_path(path)

	func poses() -> Array[Exit.ExitPose]:
		return _poses

	func moves() -> Array[Exit.SegmentMove]:
		return _moves

	## The final pose: standing on the room floor at the exit waypoint.
	func waypoint() -> Exit.ExitPose:
		return _poses[Exit.EXIT_POSE_COUNT - 1]

## The tick-driven get-up controller: one authored segment per tick, every
## motion swept through the caller's colliders by the landed resolver.
## Built only through start, which consumes the explicit exit command in
## AwakeInPod and advances the machine to ExitingPod.
class GetUpController:
	extends RefCounted

	var _path: Exit.ExitPath = null
	var _capsule: Resolve.Capsule = null
	var _segment: int = 1

	## Begin the authored get-up: consume the explicit exit command in
	## AwakeInPod and start the capsule on the path's first pose. A machine
	## in any other phase rejects the start and is left unchanged.
	static func start(phase: Phase.Machine, path: Exit.ExitPath) -> Exit.StartResult:
		var transition: Phase.Transition = phase.request_pod_exit(Phase.InputEdge.RISING)
		var advanced: bool = transition.kind == Phase.Transition.Kind.ADVANCED and transition.from == Phase.Wake.AWAKE_IN_POD and transition.to == Phase.Wake.EXITING_POD
		if not advanced:
			return Exit.StartResult.with_error(Exit.ExitError.wrong_phase(Phase.Wake.AWAKE_IN_POD, phase.current()))
		var controller: Exit.GetUpController = Exit.GetUpController.new()
		controller._path = path
		controller._capsule = path.poses()[0].capsule()
		controller._segment = 1
		return Exit.StartResult.with_controller(controller)

	func capsule() -> Resolve.Capsule:
		return Exit._copy_capsule(_capsule)

	## Advance the authored get-up by exactly one segment: sweep the
	## segment's conservative displacement through the colliders and move
	## the capsule to the resolved stop. A stop short of the target pose
	## beyond its tolerance is a hard PathBlocked error; reaching the final
	## pose delivers the get-up-complete signal, advancing the machine to
	## Standing.
	func tick(phase: Phase.Machine, colliders: ColliderSet) -> Exit.TickResult:
		if _segment == Exit.EXIT_POSE_COUNT:
			return Exit.TickResult.with_error(Exit.ExitError.get_up_already_complete())
		if not phase.in_phase(Phase.Wake.EXITING_POD):
			return Exit.TickResult.with_error(Exit.ExitError.wrong_phase(Phase.Wake.EXITING_POD, phase.current()))
		var pose_index: int = _segment
		var pose: Exit.ExitPose = _path.poses()[pose_index]
		var movement: Exit.SegmentMove = _path.moves()[pose_index - 1]
		var resolved: Resolve.Result = Resolve.resolve_motion(_capsule, movement.vector(), colliders)
		if not resolved.is_ok():
			return Exit.TickResult.with_error(Exit.ExitError.resolver_error(resolved.error))
		var swept: Vector3 = resolved.motion.displacement
		var shortfall: float = (movement.vector() - swept).length()
		if shortfall > pose.tolerance():
			# A stopped rigid segment keeps the resolver's partial motion;
			# a stopped pivot keeps the previous pose, because the
			# conservative sweep stopped, not the authored swing.
			if movement.kind == Exit.SegmentMove.Kind.RIGID:
				_capsule = Exit._translate_capsule(_capsule, swept)
			return Exit.TickResult.with_error(Exit.ExitError.path_blocked(pose_index, shortfall))
		_capsule = movement.visited(_capsule, swept)
		_segment += 1
		var at_waypoint: bool = pose_index + 1 == Exit.EXIT_POSE_COUNT
		if at_waypoint:
			var failure: Exit.ExitError = _finish_get_up(phase)
			if failure != null:
				return Exit.TickResult.with_error(failure)
		var progress: Exit.GetUpProgress = Exit.GetUpProgress.new()
		progress.pose_index = pose_index
		progress.at_waypoint = at_waypoint
		return Exit.TickResult.with_progress(progress)

	## Deliver the get-up-complete boundary signal at the waypoint. The
	## tick entry check already pinned the machine to ExitingPod, where the
	## signal cannot be a rejected skip.
	func _finish_get_up(phase: Phase.Machine) -> Exit.ExitError:
		var result: Phase.Result = phase.get_up_complete()
		if result.is_ok():
			return null
		return Exit.ExitError.wrong_phase(Phase.Wake.EXITING_POD, result.error.current)

## Classify one authored segment, or null when the conservative sweep
## cannot cover it: both spheres moving by different displacements, or a
## pivot that is not a quarter turn between axis-aligned radius
## directions.
static func segment_move(from_pose: Exit.ExitPose, to_pose: Exit.ExitPose) -> Exit.SegmentMove:
	var by_foot: Vector3 = to_pose.foot() - from_pose.foot()
	var by_head: Vector3 = to_pose.head() - from_pose.head()
	if (by_head - by_foot).length() <= _RIGID_SLACK:
		return SegmentMove.rigid(by_foot)
	if by_foot == Vector3.ZERO:
		var foot_radius: Variant = _pivot_radius(from_pose.foot(), from_pose.head(), to_pose.head())
		if foot_radius == null:
			return null
		return SegmentMove.pivot_about_foot(foot_radius)
	if by_head == Vector3.ZERO:
		var head_radius: Variant = _pivot_radius(from_pose.head(), from_pose.foot(), to_pose.foot())
		if head_radius == null:
			return null
		return SegmentMove.pivot_about_head(head_radius)
	return null

## The free sphere's reached radius about the fixed sphere, when the
## authored pivot is a quarter turn between axis-aligned radius directions
## of one length; null otherwise.
static func _pivot_radius(fixed: Vector3, free_start: Vector3, free_end: Vector3) -> Variant:
	var start: Vector3 = free_start - fixed
	var end: Vector3 = free_end - fixed
	var length: float = start.length()
	if absf(end.length() - length) > _PIVOT_SLACK:
		return null
	var start_axis: int = _radius_axis(start, length)
	if start_axis == -1:
		return null
	var end_axis: int = _radius_axis(end, length)
	if end_axis == -1:
		return null
	if start_axis == end_axis:
		return null
	return end

## Which axis an authored radius runs along, when it runs along exactly
## one: the axis index, or -1 for a radius with off-axis components.
static func _radius_axis(radius: Vector3, length: float) -> int:
	var absolute: Vector3 = radius.abs()
	if absf(absolute.x - length) <= _PIVOT_SLACK and absolute.y <= _PIVOT_SLACK and absolute.z <= _PIVOT_SLACK:
		return 0
	if absolute.x <= _PIVOT_SLACK and absf(absolute.y - length) <= _PIVOT_SLACK and absolute.z <= _PIVOT_SLACK:
		return 1
	if absolute.x <= _PIVOT_SLACK and absolute.y <= _PIVOT_SLACK and absf(absolute.z - length) <= _PIVOT_SLACK:
		return 2
	return -1

## The authored pose table for one placement and tray floor. Pod-local
## numbers per pose; _to_world maps them through the placement.
static func _authored_poses(placement: Pods.PodPlacement, tray_floor_y: float) -> Array[Exit.ExitPose]:
	var tolerance: float = POSE_TOLERANCE
	var segment: float = Controller.CAPSULE_STANDING_HEIGHT - 2.0 * Controller.CAPSULE_RADIUS
	var lying_y: float = tray_floor_y + Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
	var half_segment: float = segment / 2.0
	var inside_face: float = Pods.POD_LENGTH / 2.0 - Controller.CAPSULE_RADIUS - 2.0 * Controller.PENETRATION_TOLERANCE
	var past_face: float = Pods.POD_LENGTH / 2.0 + Controller.CAPSULE_RADIUS + 2.0 * Controller.PENETRATION_TOLERANCE
	var standing_y: float = Controller.CAPSULE_RADIUS + Controller.PENETRATION_TOLERANCE
	var local_foots: Array[Vector3] = [
		Vector3(0.0, lying_y, half_segment),
		Vector3(0.0, lying_y, half_segment),
		Vector3(0.0, lying_y, inside_face),
		Vector3(0.0, lying_y, past_face),
		Vector3(0.0, standing_y, past_face),
	]
	var local_heads: Array[Vector3] = [
		Vector3(0.0, lying_y, -half_segment),
		Vector3(0.0, lying_y + segment, half_segment),
		Vector3(0.0, lying_y + segment, inside_face),
		Vector3(0.0, lying_y + segment, past_face),
		Vector3(0.0, standing_y + segment, past_face),
	]
	var poses: Array[Exit.ExitPose] = []
	for index: int in range(EXIT_POSE_COUNT):
		poses.append(ExitPose.new(_to_world(placement, local_foots[index]), _to_world(placement, local_heads[index]), tolerance))
	return poses

## Map a pod-local point into the room frame through the placement: the
## yaw about +Y rotates local +Z onto the opening's world direction,
## matching pods.
static func _to_world(placement: Pods.PodPlacement, local: Vector3) -> Vector3:
	var sin_yaw: float = sin(placement.yaw_radians)
	var cos_yaw: float = cos(placement.yaw_radians)
	return Vector3(
		placement.center.x + local.x * cos_yaw + local.z * sin_yaw,
		local.y,
		placement.center.y - local.x * sin_yaw + local.z * cos_yaw
	)

static func _translate_capsule(capsule: Resolve.Capsule, by: Vector3) -> Resolve.Capsule:
	var translated: Resolve.Capsule = Resolve.Capsule.new()
	translated.foot = capsule.foot + by
	translated.head = capsule.head + by
	return translated

static func _copy_capsule(capsule: Resolve.Capsule) -> Resolve.Capsule:
	var copy: Resolve.Capsule = Resolve.Capsule.new()
	copy.foot = capsule.foot
	copy.head = capsule.head
	return copy

static func _same_float(a: float, b: float) -> bool:
	return a == b or (is_nan(a) and is_nan(b))
