class_name ColliderSet
extends RefCounted
## Static-world collider set, ported from gone_sim colliders.rs.
## A small list of validated AABBs with a linear broad-phase; at the
## scene's scale (tens of boxes) the linear scan is the whole broad-phase.
## Every Aabb is validated at construction so nothing downstream can
## observe a degenerate or non-finite box. Units: meters, up is positive
## Y. Pure simulation data: no Node, scene, rendering, or input types.

class ColliderError:
	extends RefCounted

	enum Kind { NON_FINITE, NEGATIVE_HALF_EXTENT, MIN_ABOVE_MAX }

	var kind: int = Kind.NON_FINITE
	var value: Vector3 = Vector3.ZERO
	var half_extents: Vector3 = Vector3.ZERO
	var min_corner: Vector3 = Vector3.ZERO
	var max_corner: Vector3 = Vector3.ZERO

	static func non_finite(payload: Vector3) -> ColliderSet.ColliderError:
		var error: ColliderSet.ColliderError = ColliderSet.ColliderError.new()
		error.kind = Kind.NON_FINITE
		error.value = payload
		return error

	static func negative_half_extent(payload: Vector3) -> ColliderSet.ColliderError:
		var error: ColliderSet.ColliderError = ColliderSet.ColliderError.new()
		error.kind = Kind.NEGATIVE_HALF_EXTENT
		error.half_extents = payload
		return error

	static func min_above_max(corner_min: Vector3, corner_max: Vector3) -> ColliderSet.ColliderError:
		var error: ColliderSet.ColliderError = ColliderSet.ColliderError.new()
		error.kind = Kind.MIN_ABOVE_MAX
		error.min_corner = corner_min
		error.max_corner = corner_max
		return error

	func equals(other: ColliderSet.ColliderError) -> bool:
		if other == null or kind != other.kind:
			return false
		match kind:
			Kind.NON_FINITE:
				return _same_vector(value, other.value)
			Kind.NEGATIVE_HALF_EXTENT:
				return _same_vector(half_extents, other.half_extents)
			_:
				return _same_vector(min_corner, other.min_corner) and _same_vector(max_corner, other.max_corner)

	func _to_string() -> String:
		match kind:
			Kind.NON_FINITE:
				return "collider coordinates must be finite, got %s" % str(value)
			Kind.NEGATIVE_HALF_EXTENT:
				return "collider half extents must be non-negative, got %s" % str(half_extents)
			_:
				return "collider min corner %s exceeds max corner %s on some axis" % [str(min_corner), str(max_corner)]

	static func _same_vector(a: Vector3, b: Vector3) -> bool:
		# Component-wise equality where a NaN payload still matches itself,
		# mirroring the Rust total-order payload comparison.
		return _same_component(a.x, b.x) and _same_component(a.y, b.y) and _same_component(a.z, b.z)

	static func _same_component(a: float, b: float) -> bool:
		return a == b or (is_nan(a) and is_nan(b))

class Aabb:
	extends RefCounted

	var _center: Vector3 = Vector3.ZERO
	var _half_extents: Vector3 = Vector3.ZERO

	static func try_new(p_center: Vector3, p_half_extents: Vector3) -> ColliderSet.Result:
		if not p_center.is_finite():
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.non_finite(p_center))
		if not p_half_extents.is_finite():
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.non_finite(p_half_extents))
		if p_half_extents.x < 0.0 or p_half_extents.y < 0.0 or p_half_extents.z < 0.0:
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.negative_half_extent(p_half_extents))
		return ColliderSet.Result.with_box(from_parts(p_center, p_half_extents))

	static func from_min_max(corner_min: Vector3, corner_max: Vector3) -> ColliderSet.Result:
		if not corner_min.is_finite():
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.non_finite(corner_min))
		if not corner_max.is_finite():
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.non_finite(corner_max))
		if corner_min.x > corner_max.x or corner_min.y > corner_max.y or corner_min.z > corner_max.z:
			return ColliderSet.Result.with_error(ColliderSet.ColliderError.min_above_max(corner_min, corner_max))
		return ColliderSet.Result.with_box(from_parts((corner_min + corner_max) * 0.5, (corner_max - corner_min) * 0.5))

	# Assemble from already-valid parts; the public constructors validate.
	static func from_parts(p_center: Vector3, p_half_extents: Vector3) -> ColliderSet.Aabb:
		var box: ColliderSet.Aabb = ColliderSet.Aabb.new()
		box._center = p_center
		box._half_extents = p_half_extents
		return box

	func center() -> Vector3:
		return _center

	func half_extents() -> Vector3:
		return _half_extents

	func min_corner() -> Vector3:
		return _center - _half_extents

	func max_corner() -> Vector3:
		return _center + _half_extents

	# Inclusive: two boxes sharing exactly one face plane count as overlapping.
	func overlaps(other: ColliderSet.Aabb) -> bool:
		var a_min := min_corner()
		var a_max := max_corner()
		var b_min := other.min_corner()
		var b_max := other.max_corner()
		return a_min.x <= b_max.x and b_min.x <= a_max.x and a_min.y <= b_max.y and b_min.y <= a_max.y and a_min.z <= b_max.z and b_min.z <= a_max.z

	func equals(other: ColliderSet.Aabb) -> bool:
		return other != null and _center == other._center and _half_extents == other._half_extents

class Result:
	extends RefCounted

	var box: ColliderSet.Aabb = null
	var error: ColliderSet.ColliderError = null

	static func with_box(valid: ColliderSet.Aabb) -> ColliderSet.Result:
		var result: ColliderSet.Result = ColliderSet.Result.new()
		result.box = valid
		return result

	static func with_error(failure: ColliderSet.ColliderError) -> ColliderSet.Result:
		var result: ColliderSet.Result = ColliderSet.Result.new()
		result.error = failure
		return result

	func is_ok() -> bool:
		return error == null

var _boxes: Array[ColliderSet.Aabb] = []

func insert(aabb: ColliderSet.Aabb) -> int:
	_boxes.append(aabb)
	return _boxes.size() - 1

func size() -> int:
	return _boxes.size()

func is_empty() -> bool:
	return _boxes.is_empty()

func boxes() -> Array[ColliderSet.Aabb]:
	return _boxes

# Broad-phase: insertion indices of every box whose bounds overlap the query.
func overlapping(query: ColliderSet.Aabb) -> PackedInt32Array:
	var indices := PackedInt32Array()
	for index: int in range(_boxes.size()):
		if _boxes[index].overlaps(query):
			indices.append(index)
	return indices
