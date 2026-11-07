extends RefCounted

## Separating-axis test for the new fixed hinge details. Rotated whole-slab
## AABBs contain empty space around the pivot, unlike the oriented slab.
static func penetrates(a: Transform3D, a_size: Vector3, b: Transform3D, b_size: Vector3, tolerance: float = 0.001) -> bool:
	var axes: Array[Vector3] = [a.basis.x, a.basis.y, a.basis.z, b.basis.x, b.basis.y, b.basis.z]
	for i: int in range(3):
		for j: int in range(3):
			var axis := a.basis[i].cross(b.basis[j])
			if axis.length_squared() > 0.00000001: axes.append(axis.normalized())
	for axis: Vector3 in axes:
		var ra := 0.0
		var rb := 0.0
		for i: int in range(3):
			ra += absf(axis.dot(a.basis[i])) * a_size[i] / 2
			rb += absf(axis.dot(b.basis[i])) * b_size[i] / 2
		if ra + rb - absf(axis.dot(b.origin - a.origin)) <= tolerance: return false
	return true
