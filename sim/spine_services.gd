class_name SpineServices
extends RefCounted
## Each room owns its runs up to the bulkhead centre, with a collar on its face.

const PIPE_OFFSETS: Array[float] = [-0.91, -0.63, 0.73]
# Raise the old runs 40 mm so collars clear the top conduit without hanging lower.
const PIPE_DROP := 0.25
const SUPPORT_PITCH := 2.0
const DUCT_PITCH := 0.8
const DUCT_SIZE := Vector2(0.35, 0.44)
const COLLAR_DEPTH := 0.03

var pipes: Array[Transform3D] = []
var pipe_collars: Array[Transform3D] = []
var brackets: Array[Transform3D] = []
var ducts: Array[Transform3D] = []
var duct_collars: Array[Transform3D] = []

static func build(bounds: AABB) -> SpineServices:
	var result := SpineServices.new()
	var start := bounds.position.x + ShipLayout.WALL / 2
	var end := bounds.end.x + ShipLayout.WALL / 2
	var faces: Array[float] = [bounds.position.x + ShipLayout.WALL + COLLAR_DEPTH / 2, bounds.end.x - COLLAR_DEPTH / 2]
	for offset: float in PIPE_OFFSETS:
		var diameter := 0.15 if offset < -0.8 else 0.09
		var y := bounds.end.y - PIPE_DROP
		var z := bounds.get_center().z + offset
		result.pipes.append(_pipe(Vector3((start + end) / 2, y, z), end - start, diameter))
		for x: float in faces:
			result.pipe_collars.append(_pipe(Vector3(x, y, z), COLLAR_DEPTH, diameter + 0.06))
		var x := floorf(start / SUPPORT_PITCH) * SUPPORT_PITCH + SUPPORT_PITCH / 2
		if x < start: x += SUPPORT_PITCH
		while x < end:
			var bottom := y + diameter / 2 - 0.01
			result.brackets.append(_pose(Vector3(x, (bounds.end.y + bottom) / 2, z), Vector3(0.06, bounds.end.y - bottom, diameter)))
			x += SUPPORT_PITCH
	# Keep the same tile grid through short hatch bays; only wall-end tiles are cut.
	var datum := ShipLayout.WALL / 2
	var x := floorf((start - datum) / DUCT_PITCH) * DUCT_PITCH + datum
	while x < end - 0.0001:
		var left := maxf(x, start)
		var right := minf(x + DUCT_PITCH, end)
		if right - left > 0.0001:
			result.ducts.append(_pose(Vector3((left + right) / 2, bounds.end.y - DUCT_SIZE.x / 2, bounds.end.z - 0.45), Vector3(right - left, DUCT_SIZE.x, DUCT_SIZE.y)))
		x += DUCT_PITCH
	for face: float in faces:
		var z := bounds.end.z - 0.45
		var bottom := bounds.end.y - DUCT_SIZE.x
		for y: float in [bottom + 0.012, bounds.end.y - 0.012]:
			result.duct_collars.append(_pose(Vector3(face, y, z), Vector3(COLLAR_DEPTH, 0.024, DUCT_SIZE.y + 0.06)))
		for side: int in [-1, 1]:
			result.duct_collars.append(_pose(Vector3(face, (bottom + bounds.end.y) / 2, z + side * (DUCT_SIZE.y / 2 + 0.015)), Vector3(COLLAR_DEPTH, DUCT_SIZE.x, 0.03)))
	return result

static func _pose(center: Vector3, size: Vector3) -> Transform3D:
	return Transform3D(Basis.from_scale(size), center)

static func _pipe(center: Vector3, length: float, diameter: float) -> Transform3D:
	return Transform3D(Basis(Vector3.BACK, -PI / 2).scaled_local(Vector3(diameter, length, diameter)), center)

func reservations() -> Array[ShipLayout.DressingClearance]:
	var result: Array[ShipLayout.DressingClearance] = []
	for pose: Transform3D in pipes + pipe_collars + brackets + ducts + duct_collars:
		result.append(ShipLayout.DressingClearance.new(&"SPINE_SERVICE", (pose * ShipDressing.UNIT).grow(0.002)))
	return result
