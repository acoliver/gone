class_name Resolve
extends RefCounted
## Pure swept-capsule resolver, ported from gone_sim resolve.rs.
## Resolves one tick of first-person movement against the static
## ColliderSet with conservative advancement: the capsule only ever
## advances to its first contact minus the penetration tolerance and
## re-queries, so an oversized displacement can never tunnel. At a
## contact it slides along the struck face or steps up onto a low ledge.
## Units: meters, displacements per tick, up is positive Y. No clocks,
## no RNG, no scene types.

## Rounding slack for the grounding probe: a few ulps of error accumulate
## across the entry-fraction math, so the probe window widens slightly.
const GROUND_PROBE_SLACK: float = 1e-4

# Sentinels standing in for the Rust AxisSweep enum: NaN means the axis
# can never be struck (Miss), INF means the axis cannot gate the approach
# (Open); any finite value is a Hit entry fraction.
const AXIS_MISS: float = NAN
const AXIS_OPEN: float = INF

class Capsule:
	extends RefCounted
	var foot: Vector3 = Vector3.ZERO
	var head: Vector3 = Vector3.ZERO

class ResolvedMotion:
	extends RefCounted
	var displacement: Vector3 = Vector3.ZERO
	var grounded: bool = false
	var contact_normals: Array[Vector3] = []

class ResolveError:
	extends RefCounted

	enum Kind { SWEEP_BOUND_EXCEEDED, START_PENETRATION, NON_FINITE_INPUT }
	enum NonFiniteInput { CAPSULE_FOOT, CAPSULE_HEAD, DISPLACEMENT }

	var kind: int = Kind.SWEEP_BOUND_EXCEEDED
	var bound: int = 0
	var index: int = 0
	var input: int = NonFiniteInput.CAPSULE_FOOT

	static func sweep_bound_exceeded(limit: int) -> Resolve.ResolveError:
		var error: Resolve.ResolveError = Resolve.ResolveError.new()
		error.kind = Kind.SWEEP_BOUND_EXCEEDED
		error.bound = limit
		return error

	static func start_penetration(collider_index: int) -> Resolve.ResolveError:
		var error: Resolve.ResolveError = Resolve.ResolveError.new()
		error.kind = Kind.START_PENETRATION
		error.index = collider_index
		return error

	static func non_finite_input(bad_input: int) -> Resolve.ResolveError:
		var error: Resolve.ResolveError = Resolve.ResolveError.new()
		error.kind = Kind.NON_FINITE_INPUT
		error.input = bad_input
		return error

	func equals(other: Resolve.ResolveError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.SWEEP_BOUND_EXCEEDED:
				return bound == other.bound
			Kind.START_PENETRATION:
				return index == other.index
			_:
				return input == other.input

	func _to_string() -> String:
		match kind:
			Kind.SWEEP_BOUND_EXCEEDED:
				return "sweep did not settle within the per-tick iteration bound SWEEP_ITERATION_BOUND = %d; leftover motion is an error, never a silent clamp" % bound
			Kind.START_PENETRATION:
				return "capsule starts embedded beyond PENETRATION_TOLERANCE in collider %d; fix the spawn position" % index
			_:
				return "sweep %s carried a non-finite component" % _input_name()

	func _input_name() -> String:
		match input:
			NonFiniteInput.CAPSULE_FOOT:
				return "capsule foot"
			NonFiniteInput.CAPSULE_HEAD:
				return "capsule head"
			_:
				return "displacement"

class Result:
	extends RefCounted
	var motion: Resolve.ResolvedMotion = null
	var error: Resolve.ResolveError = null

	static func with_motion(resolved: Resolve.ResolvedMotion) -> Resolve.Result:
		var result: Resolve.Result = Resolve.Result.new()
		result.motion = resolved
		return result

	static func with_error(failure: Resolve.ResolveError) -> Resolve.Result:
		var result: Resolve.Result = Resolve.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

class Contact:
	extends RefCounted
	var entry: float = 0.0
	var normal: Vector3 = Vector3.ZERO
	var box_top: float = 0.0

class SweepState:
	extends RefCounted
	var foot: Vector3 = Vector3.ZERO
	var head: Vector3 = Vector3.ZERO
	var remaining: Vector3 = Vector3.ZERO
	var contacts: Array[Vector3] = []

	func advance(colliders: ColliderSet) -> Resolve.ResolveError:
		var capsule_bounds := Resolve._capsule_aabb(foot, head)
		var query := Resolve._swept_query(capsule_bounds, remaining)
		var first: Resolve.Contact = null
		for index: int in colliders.overlapping(query):
			var collider: ColliderSet.Aabb = colliders.boxes()[index]
			if Resolve._embedded_beyond_tolerance(capsule_bounds, collider):
				return Resolve.ResolveError.start_penetration(index)
			var hit := Resolve._face_contact(capsule_bounds, collider, remaining)
			if hit == null:
				continue
			# An exact tie between colliders resolves to the later-inserted
			# one, matching the axis tie-break so first-hit order is fixed.
			if hit.entry > 1.0 or (first != null and hit.entry > first.entry):
				continue
			first = hit
		if first == null:
			move_by(remaining)
			remaining = Vector3.ZERO
			return null
		apply_contact(first, colliders)
		return null

	func apply_contact(contact: Resolve.Contact, colliders: ColliderSet) -> void:
		var path: float = remaining.length()
		# The tolerance is owed on the struck face's own axis, not along the
		# path, so the slack divides by the axial direction cosine.
		var axial: float = absf(remaining.dot(contact.normal))
		var stop: float = clampf(contact.entry * path - Controller.PENETRATION_TOLERANCE * path / axial, 0.0, path)
		var moved: Vector3 = remaining * (stop / path)
		move_by(moved)
		remaining -= moved
		if contact.normal.y == 0.0:
			# _try_step_up returns NAN when no step is possible.
			var raise_amount := Resolve._try_step_up(foot, head, contact.box_top, colliders)
			if not is_nan(raise_amount):
				foot.y += raise_amount
				head.y += raise_amount
				return
		record(contact.normal)
		var into: float = remaining.dot(contact.normal)
		if into < 0.0:
			remaining -= contact.normal * into

	func move_by(delta: Vector3) -> void:
		foot += delta
		head += delta

	func record(normal: Vector3) -> void:
		if not contacts.has(normal):
			contacts.append(normal)

static func resolve_motion(capsule: Capsule, displacement: Vector3, colliders: ColliderSet) -> Result:
	return sweep_with_bound(capsule, displacement, colliders, Controller.SWEEP_ITERATION_BOUND)

# The sweep with an explicit iteration bound so the bound-exceeded error
# path is testable without manufacturing an unsettleable scenario.
static func sweep_with_bound(capsule: Capsule, displacement: Vector3, colliders: ColliderSet, bound: int) -> Result:
	var input_failure := _input_error(capsule, displacement)
	if input_failure != null:
		return Result.with_error(input_failure)
	var state: SweepState = SweepState.new()
	state.foot = capsule.foot
	state.head = capsule.head
	state.remaining = displacement
	var residual: float = Controller.PENETRATION_TOLERANCE * Controller.PENETRATION_TOLERANCE
	for _iteration: int in range(bound):
		if state.remaining.length_squared() <= residual:
			break
		var advance_failure: ResolveError = state.advance(colliders)
		if advance_failure != null:
			return Result.with_error(advance_failure)
	if state.remaining.length_squared() > residual:
		return Result.with_error(ResolveError.sweep_bound_exceeded(bound))
	var motion: ResolvedMotion = ResolvedMotion.new()
	motion.displacement = state.foot - capsule.foot
	motion.grounded = _is_grounded(state.foot, colliders)
	motion.contact_normals = state.contacts
	return Result.with_motion(motion)

static func _input_error(capsule: Capsule, displacement: Vector3) -> ResolveError:
	if not capsule.foot.is_finite():
		return ResolveError.non_finite_input(ResolveError.NonFiniteInput.CAPSULE_FOOT)
	if not capsule.head.is_finite():
		return ResolveError.non_finite_input(ResolveError.NonFiniteInput.CAPSULE_HEAD)
	if not displacement.is_finite():
		return ResolveError.non_finite_input(ResolveError.NonFiniteInput.DISPLACEMENT)
	return null

static func _axis_sweep(motion: float, lo: float, hi: float, box_lo: float, box_hi: float) -> float:
	if motion == 0.0:
		var separated := box_lo - hi > 0.0 or lo - box_hi > 0.0
		return AXIS_MISS if separated else AXIS_OPEN
	var front_gap: float
	var back_gap: float
	if motion > 0.0:
		front_gap = box_lo - hi
		back_gap = box_hi - lo
	else:
		front_gap = lo - box_hi
		back_gap = hi - box_lo
	if back_gap <= 0.0:
		# At or past the far face and opening: this axis can never close.
		return AXIS_MISS
	if front_gap > Controller.PENETRATION_TOLERANCE:
		return front_gap / absf(motion)
	if front_gap >= -Controller.PENETRATION_TOLERANCE:
		# At the struck face within the tolerance band: immediate contact.
		return 0.0
	# Strictly inside the slab, moving through: the face is beside us.
	return AXIS_OPEN

static func _face_contact(capsule_bounds: ColliderSet.Aabb, collider: ColliderSet.Aabb, remaining: Vector3) -> Contact:
	var cmin := capsule_bounds.min_corner()
	var cmax := capsule_bounds.max_corner()
	var bmin := collider.min_corner()
	var bmax := collider.max_corner()
	var motion := PackedFloat64Array([remaining.x, remaining.y, remaining.z])
	var lo := PackedFloat64Array([cmin.x, cmin.y, cmin.z])
	var hi := PackedFloat64Array([cmax.x, cmax.y, cmax.z])
	var box_lo := PackedFloat64Array([bmin.x, bmin.y, bmin.z])
	var box_hi := PackedFloat64Array([bmax.x, bmax.y, bmax.z])
	var best := 0.0
	var struck := -1
	for axis: int in range(3):
		var sweep := _axis_sweep(motion[axis], lo[axis], hi[axis], box_lo[axis], box_hi[axis])
		if is_nan(sweep):
			return null
		if is_inf(sweep):
			continue
		# Entry is the slab maximum; an exact tie resolves to the later axis.
		if struck == -1 or sweep >= best:
			best = sweep
			struck = axis
	if struck == -1:
		return null
	var normal_sign := -1.0 if motion[struck] > 0.0 else 1.0
	var normal := Vector3.ZERO
	if struck == 0:
		normal = Vector3(normal_sign, 0.0, 0.0)
	elif struck == 1:
		normal = Vector3(0.0, normal_sign, 0.0)
	else:
		normal = Vector3(0.0, 0.0, normal_sign)
	var contact: Contact = Contact.new()
	contact.entry = best
	contact.normal = normal
	contact.box_top = bmax.y
	return contact

# Genuinely embedded (beyond the tolerance on every axis), not resting.
static func _embedded_beyond_tolerance(capsule_bounds: ColliderSet.Aabb, collider: ColliderSet.Aabb) -> bool:
	var cmin := capsule_bounds.min_corner()
	var cmax := capsule_bounds.max_corner()
	var bmin := collider.min_corner()
	var bmax := collider.max_corner()
	var tol := Controller.PENETRATION_TOLERANCE
	return cmin.x < bmax.x - tol and cmax.x > bmin.x + tol and cmin.y < bmax.y - tol and cmax.y > bmin.y + tol and cmin.z < bmax.z - tol and cmax.z > bmin.z + tol

static func _capsule_aabb(foot: Vector3, head: Vector3) -> ColliderSet.Aabb:
	var radius := Vector3.ONE * Controller.CAPSULE_RADIUS
	var lo := foot.min(head) - radius
	var hi := foot.max(head) + radius
	return ColliderSet.Aabb.from_parts((lo + hi) * 0.5, (hi - lo) * 0.5)

# Broad-phase: the hull of the capsule bounds at the start and end of the
# remaining motion; anything the motion can strike intersects this hull.
static func _swept_query(capsule_bounds: ColliderSet.Aabb, remaining: Vector3) -> ColliderSet.Aabb:
	var lo := capsule_bounds.min_corner()
	var hi := capsule_bounds.max_corner()
	var swept_lo := lo.min(lo + remaining)
	var swept_hi := hi.max(hi + remaining)
	return ColliderSet.Aabb.from_parts((swept_lo + swept_hi) * 0.5, (swept_hi - swept_lo) * 0.5)

# Attempt a step onto the struck ledge: the raise in meters, or NAN when
# the ledge is too high or the raised capsule is not free.
static func _try_step_up(foot: Vector3, head: Vector3, ledge_top: float, colliders: ColliderSet) -> float:
	var capsule_foot: float = foot.y - Controller.CAPSULE_RADIUS
	var ledge: float = ledge_top - capsule_foot
	if ledge <= 0.0 or ledge > Controller.STEP_UP_HEIGHT + Controller.PENETRATION_TOLERANCE:
		return NAN
	var raise_amount: float = ledge_top + Controller.PENETRATION_TOLERANCE - capsule_foot
	var up := Vector3.UP * raise_amount
	var raised := _capsule_aabb(foot + up, head + up)
	if colliders.overlapping(raised).is_empty():
		return raise_amount
	return NAN

# Whether a support face sits within the tolerance of the capsule foot
# height and underlaps the foot sphere.
static func _is_grounded(foot: Vector3, colliders: ColliderSet) -> bool:
	var foot_y: float = foot.y - Controller.CAPSULE_RADIUS
	var band: float = Controller.PENETRATION_TOLERANCE + GROUND_PROBE_SLACK
	var query := ColliderSet.Aabb.from_parts(Vector3(foot.x, foot_y, foot.z), Vector3(Controller.CAPSULE_RADIUS, band, Controller.CAPSULE_RADIUS))
	for index: int in colliders.overlapping(query):
		var collider: ColliderSet.Aabb = colliders.boxes()[index]
		var top: float = collider.max_corner().y
		if top < foot_y - band or top > foot_y + band:
			continue
		var bmin := collider.min_corner()
		var bmax := collider.max_corner()
		var radius := Controller.CAPSULE_RADIUS
		var over := bmin.x <= foot.x + radius and foot.x - radius <= bmax.x and bmin.z <= foot.z + radius and foot.z - radius <= bmax.z
		if over:
			return true
	return false
