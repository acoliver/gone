class_name HatchParts
extends RefCounted
## Physical leaf geometry in pure leaf/group-local frames. Meshes belong to app.

const WHEEL_HEIGHT: float = 1.15
const SEAL_DEPTH: float = 0.02
const SEAL_LAP: float = 0.02
const HINGE_RETURN_WIDTH: float = 0.02
# Andrew's 2026-11-05 heavy, flush slab. The offset hinge stays behind the
# wall for its 130-degree swing; solid steel now reaches the raised front bead.
const HINGE_OUTSET: float = 0.03
const APPROACH_SLAB_DEPTH: float = 0.22
const REVERSE_SLAB_DEPTH: float = 0.04
const HARDWARE_FACE_DEPTH: float = 0.10
const SLAB_EDGE_BEVEL: float = 0.004
const PAINT_LAYER_DEPTH: float = 0.002
# Round 11: real pivot knuckles and upper fittings clear the level-gaze label.
const HINGE_HEIGHTS: Array[float] = [0.48, 2.24]
const DOG_HEIGHTS: Array[float] = [0.40, 1.17, 1.496046]
const KEEPER_HEIGHTS: Array[float] = [0.40, 1.17, 2.24]
const DOG_INSET: float = 0.193619
const WHEEL_SCALE: float = 0.643 / 0.888
const BARREL_RADIUS: float = 0.028
const BARREL_LENGTH: float = 0.06

static var _leaves: Dictionary = {}

class Part:
	extends RefCounted
	var id: StringName
	var shape: StringName
	var size: Vector3
	var transform: Transform3D
	var radius: float
	var inner_radius: float
	var contour := PackedVector2Array()
	var edge_bevel: float = 0.0
	var paint_layer_depth: float = 0.0
	func _init(p_id: StringName, p_shape: StringName, p_size: Vector3, p_transform: Transform3D, p_radius: float = 0.0, p_inner_radius: float = 0.0) -> void:
		id = p_id
		shape = p_shape
		size = p_size
		transform = p_transform
		radius = p_radius
		inner_radius = p_inner_radius

class Group:
	extends RefCounted
	var path: NodePath
	var transform: Transform3D
	var side: int
	var steel: bool
	var parts: Array[Part] = []
	func _init(p_path: NodePath, p_transform: Transform3D, p_side: int, p_steel: bool = false) -> void:
		path = p_path
		transform = p_transform
		side = p_side
		steel = p_steel
	func add(id: String, shape: StringName, size: Vector3, pose: Transform3D, radius: float = 0.0, inner_radius: float = 0.0) -> void:
		parts.append(Part.new(StringName("%s/%s" % [path, id]), shape, size, pose, radius, inner_radius))

static func _bar(group: Group, id: String, a: Vector3, b: Vector3, width: float, depth: float) -> void:
	var delta := b - a
	group.add(id, &"box", Vector3(width, delta.length(), depth), Transform3D(Basis(Vector3.BACK, -atan2(delta.x, delta.y)), (a + b) / 2))

static func _pin(group: Group, id: String, radius: float, length: float, center: Vector3, axis: Vector3 = Vector3.BACK) -> void:
	group.add(id, &"cylinder", Vector3(radius * 2, length, radius * 2), Transform3D(Basis(Quaternion(Vector3.UP, axis)), center), radius)

static func outline(size: Vector2, radius: float) -> PackedVector2Array:
	var points := PackedVector2Array()
	for corner: int in range(4):
		var center := Vector2((size.x / 2 - radius) * (1 if corner in [0, 3] else -1), (size.y / 2 - radius) * (1 if corner < 2 else -1))
		for segment: int in range(9):
			var angle := (corner + segment / 8.0) * PI / 2
			points.append(center + Vector2(cos(angle), sin(angle)) * radius)
	return points

static func loop_length(loop: PackedVector2Array) -> float:
	var length := 0.0
	for index: int in range(loop.size()):
		length += loop[index].distance_to(loop[(index + 1) % loop.size()])
	return length

## Equal arc-length spacing around a closed loop. Restarting at every edge crowds
## the short tangent segments of a rounded corner against the straight runs.
static func evenly_spaced(loop: PackedVector2Array, count: int) -> PackedVector2Array:
	var spacing := loop_length(loop) / count
	var points := PackedVector2Array()
	var edge := 0
	var edge_start := 0.0
	for step: int in range(count):
		var distance := step * spacing
		var edge_length := loop[edge].distance_to(loop[(edge + 1) % loop.size()])
		while distance > edge_start + edge_length:
			edge_start += edge_length
			edge += 1
			edge_length = loop[edge].distance_to(loop[(edge + 1) % loop.size()])
		points.append(loop[edge].lerp(loop[(edge + 1) % loop.size()], (distance - edge_start) / edge_length))
	return points

static func _hinge_return(group: Group, size: Vector3, center: Vector3) -> void:
	var bottom := center.y - size.y / 2
	for top: float in [HINGE_HEIGHTS[0] + BARREL_LENGTH / 2, HINGE_HEIGHTS[1] + BARREL_LENGTH / 2, center.y + size.y / 2]:
		var segment := size
		segment.y = top - bottom
		var point := center
		point.y = (bottom + top) / 2
		group.add("return-%d" % group.parts.size(), &"box", segment, Transform3D(Basis(), point))
		bottom = top + 0.04

static func leaf(door: ShipLayout.DoorSpec) -> Array[Group]:
	var aperture := door.leaf_aperture()
	var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
	var key := [aperture, into]
	if _leaves.has(key): return _leaves[key]
	var groups: Array[Group] = []
	var center_y := (aperture.y + ShipGeometry.SILL_HEIGHT) / 2
	for side: int in range(2):
		var prefix := "Fore" if side == 0 else "Aft"
		var face := Transform3D(Basis() if side == 0 else Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD), Vector3.ZERO)
		var plate := Group.new(NodePath(prefix + "Steel"), face, side, true)
		var approach := (side == 0) == (into > 0)
		var depth := APPROACH_SLAB_DEPTH if approach else REVERSE_SLAB_DEPTH
		plate.add("plate", &"rounded", Vector3(aperture.x, aperture.y - ShipGeometry.SILL_HEIGHT, depth), Transform3D(Basis(), Vector3(aperture.x / 2, center_y, -depth / 2)), ShipGeometry.HATCH_CORNER_RADIUS)
		# Slab thickness must not scale the existing paint relief or widen its face bevel.
		plate.parts[0].edge_bevel = SLAB_EDGE_BEVEL
		plate.parts[0].paint_layer_depth = PAINT_LAYER_DEPTH
		var lower := outline(Vector2(aperture.x, aperture.y - ShipGeometry.SILL_HEIGHT), (aperture.x - ShipGeometry.SILL_WALK_WIDTH) / 2 - 0.005)
		plate.parts[0].contour = outline(Vector2(aperture.x, aperture.y - ShipGeometry.SILL_HEIGHT), plate.parts[0].radius)
		for index: int in range(lower.size() / 2, lower.size()): plate.parts[0].contour[index] = lower[index]
		groups.append(plate)
		var hardware_face := face
		hardware_face.origin.z = (-1 if side == 0 else 1) * (depth - HARDWARE_FACE_DEPTH)
		var straps := Group.new(NodePath("StrapHinges/" + prefix + "Steel"), hardware_face, side)
		for index: int in range(2):
			var y := HINGE_HEIGHTS[index]
			var strap_x := 0.230 if index == 0 else 0.40
			straps.add("strap-%d" % index, &"rounded", Vector3(0.40, 0.21, 0.055), Transform3D(Basis(), Vector3(strap_x, y, -0.125)), 0.035)
			var axis := hardware_face.affine_inverse() * Vector3(-HINGE_OUTSET, y, 0)
			var elbow := axis + Vector3.RIGHT * (0.15 if index == 0 else 0.30)
			var join := Vector3(elbow.x, y, -0.125)
			_pin(straps, "neck-axis-%d" % index, 0.018, axis.distance_to(elbow), (axis + elbow) / 2, Vector3.RIGHT)
			_pin(straps, "neck-face-%d" % index, 0.018, elbow.distance_to(join), (elbow + join) / 2, (join - elbow).normalized())
			if approach:
				_pin(straps, "barrel-%d" % index, BARREL_RADIUS, BARREL_LENGTH, axis, Vector3.UP)
				_pin(straps, "cap-%d" % index, BARREL_RADIUS, 0.01, axis - Vector3.UP * 0.035, Vector3.UP)
			for x: float in [strap_x - 0.08, strap_x + 0.08]:
				_pin(straps, "bolt-%d-%s" % [index, x], 0.021, 0.014, Vector3(x, y, -0.159))
		groups.append(straps)
		var lugs := Group.new(NodePath("Lugs/" + prefix + "Steel"), hardware_face, side)
		for index: int in range(3):
			var pivot := Vector3(aperture.x - DOG_INSET, DOG_HEIGHTS[index], -HARDWARE_FACE_DEPTH)
			lugs.add("whole-%d" % index, &"generated_latch", HatchGeneratedParts.LATCH_SIZE, Transform3D(Basis(), pivot + HatchGeneratedParts.LATCH_CENTER))
		groups.append(lugs)
		var wheel_pose := Transform3D(Basis() if side == 0 else Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3(aperture.x / 2, WHEEL_HEIGHT, -0.190 if side == 0 else 0.190))
		wheel_pose.origin += hardware_face.origin
		var wheel := Group.new(NodePath("Wheel" if side == 0 else "ReverseWheel"), wheel_pose, side)
		wheel.add("hub", &"generated_wheel", HatchGeneratedParts.WHEEL_SIZE, Transform3D(Basis(), HatchGeneratedParts.WHEEL_CENTER), 0.3215)
		_pin(wheel, "cap", 0.085 * WHEEL_SCALE, 0.010 * WHEEL_SCALE, Vector3(0, 0, -HatchGeneratedParts.NUT_SEAT - 0.005 * WHEEL_SCALE))
		var wheel_diameter := 0.888
		wheel.add("hazard-band", &"band", Vector3(0.75, wheel_diameter * 0.10, 0.012), Transform3D(Basis(Vector3.BACK, 0.060), Vector3(0, -0.150, -0.026)))
		var band := wheel.parts[-1]
		var rng := RandomNumberGenerator.new()
		rng.seed = 7308
		var bottom := PackedVector2Array()
		for index: int in range(25):
			var x := -band.size.x / 2 + index * band.size.x / 24
			band.contour.append(Vector2(x, band.size.y / 2 - rng.randf_range(0, band.size.y * 0.075)))
			bottom.append(Vector2(x, -band.size.y / 2 + rng.randf_range(0, band.size.y * 0.08)))
		band.contour[12].y = band.size.y / 2
		bottom[12].y = -band.size.y / 2
		bottom.reverse()
		band.contour.append_array(bottom)
		for x: float in [-0.32, 0.32]:
			var pin_pose := band.transform * Transform3D(Basis(Quaternion(Vector3.UP, Vector3.BACK)), Vector3(x, 0, -0.004))
			wheel.add("band-bolt-%s" % x, &"cylinder", Vector3(0.028, 0.003, 0.028), pin_pose, 0.014)
		for part: Part in wheel.parts:
			if not ("/hazard-band" in String(part.id) or "/band-bolt" in String(part.id)): continue
			part.size *= WHEEL_SCALE
			part.transform.origin *= WHEEL_SCALE
			part.radius *= WHEEL_SCALE
			part.inner_radius *= WHEEL_SCALE
			for index: int in range(part.contour.size()): part.contour[index] *= WHEEL_SCALE
		groups.append(wheel)
		var rivets := Group.new(NodePath(prefix + "Rivets"), hardware_face, side)
		var border := outline(Vector2(aperture.x - 0.105, aperture.y - 0.19), 0.22)
		var contour := Group.new(NodePath(prefix + "Contour"), hardware_face, side)
		var border_centre := Vector2(aperture.x / 2, center_y)
		for index: int in range(border.size()):
			var a := border[index] + border_centre
			var b := border[(index + 1) % border.size()] + border_centre
			var delta := b - a
			_pin(contour, "edge-%02d" % index, 0.009, delta.length(), Vector3((a.x + b.x) / 2, (a.y + b.y) / 2, -0.103), Vector3(delta.x, delta.y, 0).normalized())
		var rivet_loop := PackedVector2Array()
		for point: Vector2 in border: rivet_loop.append(point + border_centre)
		for point: Vector2 in evenly_spaced(rivet_loop, ceili(loop_length(rivet_loop) / ShipGeometry.HATCH_RIVET_PITCH)):
			_pin(rivets, "%03d" % rivets.parts.size(), 0.012, 0.010, Vector3(point.x, point.y, -0.111))
		groups.append(contour)
		groups.append(rivets)
	for entry: Array in [["Body", Vector3(1.10, 2.32, 0.03), Vector3(0.55, center_y, into * 0.035), 0.235], ["Hinge", Vector3(0.03, 2.32, 0.01), Vector3(-0.015, center_y, into * 0.025), 0.01], ["Latch", Vector3(0.05, 2.32, 0.03), Vector3(1.125, center_y, into * 0.035), 0.024]]:
		var lap := Group.new(NodePath("BackingLap" + entry[0]), Transform3D.IDENTITY, 0, true)
		if entry[0] == "Hinge":
			# Interrupt only the rear return at the fixed knuckles' axial stations.
			_hinge_return(lap, entry[1], entry[2])
		else:
			lap.add("lap", &"rounded", entry[1], Transform3D(Basis(), entry[2]), entry[3])
		groups.append(lap)
	# A thin leaf lip laps the existing collar on its swing side. The hinge-side
	# return stays separate so its bounds do not fill the latch-side swing gap.
	for side: int in range(2):
		var prefix := "Fore" if side == 0 else "Aft"
		var pose := Transform3D(Basis(), Vector3(0, 0, into * SEAL_DEPTH / 2 + (-1 if side == 0 else 1) * SEAL_DEPTH / 4))
		var height := aperture.y - ShipGeometry.SILL_HEIGHT
		var face_depth := SEAL_DEPTH / 2
		var face_z := (-1 if side == 0 else 1) * (door.leaf_face_depth(side) - SEAL_DEPTH / 40 - face_depth / 2)
		var face_seal := Group.new(NodePath(prefix + "FaceSealSteel"), Transform3D(Basis(), Vector3(0, 0, face_z)), side, true)
		# Carry the latch-side lap to the flush face, so oblique aperture rays
		# cannot pass the rounded lower edge before reaching the old rear lip.
		var face_width := aperture.x + SEAL_LAP
		face_seal.add("face-return", &"box", Vector3(face_width, height, face_depth), Transform3D(Basis(), Vector3(face_width / 2, center_y, 0)))
		groups.append(face_seal)
		var pivot_seal := Group.new(NodePath(prefix + "PivotSealSteel"), Transform3D(Basis(), Vector3(0, 0, face_z)), side, true)
		_hinge_return(pivot_seal, Vector3(HINGE_RETURN_WIDTH, height, face_depth), Vector3(-HINGE_RETURN_WIDTH / 2, center_y, 0))
		groups.append(pivot_seal)
		var width := aperture.x + SEAL_LAP
		var seal := Group.new(NodePath(prefix + "SealSteel"), pose, side, true)
		seal.add("lip", &"box", Vector3(width, height, SEAL_DEPTH / 2), Transform3D(Basis(), Vector3(width / 2, center_y, 0)))
		groups.append(seal)
		var hinge_seal := Group.new(NodePath(prefix + "HingeSealSteel"), pose, side, true)
		_hinge_return(hinge_seal, Vector3(HINGE_RETURN_WIDTH, height, SEAL_DEPTH / 2), Vector3(-HINGE_RETURN_WIDTH / 2, center_y, 0))
		groups.append(hinge_seal)
	var rib_side := 0 if into > 0 else 1
	var rib_face := Basis() if rib_side == 0 else Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD)
	var rib := Group.new(NodePath("Rib/ForeSteel" if rib_side == 0 else "Rib/AftSteel"), Transform3D(rib_face, Vector3.ZERO), rib_side)
	for index: int in range(2):
		var interval := HatchGeneratedParts.RIB_INTERVALS[index]
		var size := Vector3(HatchGeneratedParts.RIB_WIDTH, interval.y - interval.x, HatchGeneratedParts.RIB_DEPTH)
		rib.add("segment-%d" % index, &"generated_rib", size, Transform3D(Basis(), Vector3(aperture.x / 2, (interval.x + interval.y) / 2, -APPROACH_SLAB_DEPTH - size.z / 2)))
	groups.append(rib)
	for group: Group in groups: group.transform.origin.x += HINGE_OUTSET
	_leaves[key] = groups
	return groups

static func part_bounds(part: Part, pose: Transform3D) -> AABB:
	if part.shape == &"generated_wheel": return HatchGeneratedParts.bounds(pose)
	return pose * AABB(-part.size / 2, part.size)
