class_name SpineServices
extends RefCounted
## Each room owns its runs up to the bulkhead centre, with a collar on its face.

const PIPE_OFFSETS: Array[float] = [-0.91, -0.63, 0.73]
const PIPE_DROP := 0.225
const SUPPORT_PITCH := 2.0
const DUCT_PITCH := 0.8
const DUCT_SIZE := Vector2(0.35, 0.44)
const DUCT_RISE := 0.05
const DUCT_BODY := Vector2(0.30, 0.40)
const DUCT_LIP := 0.05
const DUCT_FLANGE_DEPTH := 0.018
const COLLAR_DEPTH := 0.035
const SIDE_DROP := 0.627
const SIDE_INSET := 0.05

var pipes: Array[Transform3D] = []
var pipe_collars: Array[Transform3D] = []
var side_conduits: Array[Transform3D] = []
var service_collars: Array[Transform3D] = []
var bolts: Array[Transform3D] = []
var brackets: Array[Transform3D] = []
var ducts: Array[Transform3D] = []
var duct_collars: Array[Transform3D] = []
var duct_flanges: Array[Transform3D] = []
var fittings: Array[Dictionary] = []

static func fixture_offset(space: ShipLayout.Spec, light_position: Vector3) -> Vector3:
	# Move the visible housing only; the circuit's light anchor stays authored.
	var side := signf(light_position.z - space.bounds().get_center().z)
	if space is ShipLayout.SectionSpec: return Vector3(0, 0, -side * 0.10)
	return Vector3(0, 0, -0.80) if side > 0 else Vector3.ZERO

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
		for index: int in range(2):
			result.pipe_collars.append(result._collar(Vector3(faces[index], y, z), diameter, index))
		var x := floorf(start / SUPPORT_PITCH) * SUPPORT_PITCH + SUPPORT_PITCH / 2
		if x < start: x += SUPPORT_PITCH
		while x < end:
			var bottom := y + diameter / 2 - 0.01
			result.brackets.append(_pose(Vector3(x, (bounds.end.y + bottom) / 2, z), Vector3(0.06, bounds.end.y - bottom, diameter)))
			x += SUPPORT_PITCH
	for side: int in [-1, 1]:
		var center := Vector3((start + end) / 2, bounds.end.y - SIDE_DROP, bounds.get_center().z + side * (bounds.size.z / 2 - SIDE_INSET))
		result.side_conduits.append(_pipe(center, end - start, 0.036))
		for index: int in range(2):
			result.service_collars.append(result._collar(Vector3(faces[index], center.y, center.z), 0.036, index))
	for index: int in range(2):
		result.service_collars.append(result._collar(Vector3(faces[index], bounds.end.y - 0.28, bounds.position.z + 0.10), CeilingServices.PIPE_RADIUS * 2, index))
	# Keep the same tile grid through short hatch bays; only wall-end tiles are cut.
	var datum := ShipLayout.WALL / 2
	var x := floorf((start - datum) / DUCT_PITCH) * DUCT_PITCH + datum
	while x < end - 0.0001:
		var left := maxf(x, start)
		var right := minf(x + DUCT_PITCH, end)
		if right - left > 0.0001:
			result.ducts.append(_pose(Vector3((left + right) / 2, bounds.end.y - DUCT_SIZE.x / 2 + DUCT_RISE, bounds.end.z - 0.45), Vector3(right - left, DUCT_SIZE.x, DUCT_SIZE.y)))
		x += DUCT_PITCH
	for index: int in range(2):
		var face := faces[index]
		var z := bounds.end.z - 0.45
		var body_bottom := bounds.end.y - DUCT_SIZE.x + DUCT_RISE
		var center := Vector3(face, body_bottom + DUCT_BODY.x / 2, z)
		var height := DUCT_BODY.x + DUCT_LIP
		var width := DUCT_BODY.y + DUCT_LIP * 2
		var frame_center := center - Vector3(0, DUCT_LIP / 2, 0)
		result.duct_collars.append_array(_duct_ring(center, COLLAR_DEPTH, DUCT_BODY, DUCT_LIP))
		var into := 1 if index == 0 else -1
		var flange_center := center + Vector3(into * (COLLAR_DEPTH + DUCT_FLANGE_DEPTH) / 2, 0, 0)
		result.duct_flanges.append_array(_duct_ring(flange_center, DUCT_FLANGE_DEPTH, DUCT_BODY, 0.015))
		var ring: Array[Transform3D] = []
		for side: int in [-1, 1]:
			for y: float in [-1, 1]:
				ring.append(_pose(frame_center + Vector3(into * COLLAR_DEPTH / 2, y * (height / 2 - DUCT_LIP / 2), side * (width / 2 - DUCT_LIP / 2)), Vector3(0.012, 0.022, 0.022)))
		result.bolts.append_array(ring)
		result.fittings.append({"kind": &"duct", "body": _pose(frame_center, Vector3(COLLAR_DEPTH, height, width)), "bolts": ring})
	return result

static func _duct_ring(center: Vector3, depth: float, body: Vector2, lip: float) -> Array[Transform3D]:
	var result: Array[Transform3D] = []
	result.append(_pose(center - Vector3(0, (body.x + lip) / 2, 0), Vector3(depth, lip, body.y + lip * 2)))
	# The top bar occupies the body's upper edge, entirely below the slab.
	result.append(_pose(center + Vector3(0, (body.x - lip) / 2, 0), Vector3(depth, lip, body.y + lip * 2)))
	for side: int in [-1, 1]:
		result.append(_pose(center + Vector3(0, -lip / 2, side * (body.y + lip) / 2), Vector3(depth, body.x - lip, lip)))
	return result

func _collar(center: Vector3, diameter: float, face: int) -> Transform3D:
	var outer := diameter * 1.7
	var body := _pipe(center, COLLAR_DEPTH, outer)
	var ring: Array[Transform3D] = []
	for index: int in range(6):
		var angle := TAU * index / 6
		var position := center + Vector3((1 if face == 0 else -1) * COLLAR_DEPTH / 2, sin(angle) * diameter * 0.68, cos(angle) * diameter * 0.68)
		var size := minf(0.016, diameter * 0.18)
		ring.append(_pose(position, Vector3(0.012, size, size)))
	bolts.append_array(ring)
	fittings.append({"kind": &"pipe", "body": body, "diameter": diameter, "bolts": ring})
	return body

static func _pose(center: Vector3, size: Vector3) -> Transform3D:
	return Transform3D(Basis.from_scale(size), center)

static func _pipe(center: Vector3, length: float, diameter: float) -> Transform3D:
	return Transform3D(Basis(Vector3.BACK, -PI / 2).scaled_local(Vector3(diameter, length, diameter)), center)

func reservations() -> Array[ShipLayout.DressingClearance]:
	var result: Array[ShipLayout.DressingClearance] = []
	for pose: Transform3D in pipes + pipe_collars + side_conduits + service_collars + bolts + brackets + ducts + duct_collars + duct_flanges:
		result.append(ShipLayout.DressingClearance.new(&"SPINE_SERVICE", (pose * ShipDressing.UNIT).grow(0.002)))
	return result
