class_name HatchParts
extends RefCounted
## Physical leaf geometry in pure leaf/group-local frames. Meshes belong to app.

const WHEEL_HEIGHT: float = 1.15
const SEAL_DEPTH: float = 0.02
const SEAL_LAP: float = 0.02
const HINGE_RETURN_WIDTH: float = 0.10

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
		plate.add("plate", &"rounded", Vector3(aperture.x, aperture.y - ShipGeometry.SILL_HEIGHT, 0.10), Transform3D(Basis(), Vector3(aperture.x / 2, center_y, -0.05)), 0.255)
		groups.append(plate)
		var straps := Group.new(NodePath("StrapHinges/" + prefix + "Steel"), face, side)
		for index: int in range(2):
			var y := 0.48 if index == 0 else aperture.y - 0.40
			straps.add("strap-%d" % index, &"rounded", Vector3(0.40, 0.21, 0.055), Transform3D(Basis(), Vector3(0.215, y, -0.125)), 0.035)
			_pin(straps, "barrel-%d" % index, 0.074, 0.32, Vector3(0.09, y, -0.125), Vector3.UP)
			for cap: int in [-1, 1]:
				_pin(straps, "cap-%d-%d" % [index, cap], 0.080, 0.030, Vector3(0.09, y + cap * 0.15, -0.125), Vector3.UP)
			for x: float in [0.19, 0.35]:
				_pin(straps, "bolt-%d-%s" % [index, x], 0.021, 0.014, Vector3(x, y, -0.159))
		groups.append(straps)
		var lugs := Group.new(NodePath("Lugs/" + prefix + "Steel"), face, side)
		for index: int in range(3):
			var y: float = [0.40, 1.17, aperture.y - 0.33][index]
			lugs.add("plate-%d" % index, &"rounded", Vector3(0.11, 0.23, 0.055), Transform3D(Basis(), Vector3(0.87, y, -0.125)), 0.025)
			var a := Vector3(0.87, y, -0.170)
			var b := Vector3(1.01, y + 0.035, -0.170)
			_pin(lugs, "arm-%d" % index, 0.028, a.distance_to(b), (a + b) / 2, (b - a).normalized())
			lugs.add("grip-%d" % index, &"rounded", Vector3(0.050, 0.14, 0.050), Transform3D(Basis(), Vector3(1.01, y + 0.090, -0.170)), 0.018)
			_pin(lugs, "pivot-%d" % index, 0.047, 0.035, Vector3(0.87, y, -0.200))
			for dy: float in [-0.085, 0.085]:
				_pin(lugs, "bolt-%d-%s" % [index, dy], 0.018, 0.015, Vector3(0.87, y + dy, -0.153))
		groups.append(lugs)
		var wheel_pose := Transform3D(Basis() if side == 0 else Basis(Vector3.LEFT, Vector3.UP, Vector3.FORWARD), Vector3(aperture.x / 2, WHEEL_HEIGHT, -0.198 if side == 0 else 0.198))
		var wheel := Group.new(NodePath("Wheel" if side == 0 else "ReverseWheel"), wheel_pose, side)
		wheel.add("ring", &"torus", Vector3(0.888, 0.064, 0.888), Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3.ZERO), 0.444, 0.380)
		wheel.add("flange", &"torus", Vector3(0.864, 0.011, 0.864), Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(0, 0, -0.026)), 0.432, 0.322)
		_pin(wheel, "hub", 0.150, 0.110, Vector3(0, 0, 0.030))
		_pin(wheel, "shaft", 0.062, 0.050, Vector3(0, 0, 0.095))
		_pin(wheel, "cap", 0.085, 0.010, Vector3(0, 0, -0.027))
		for index: int in range(6):
			var angle := PI / 6 + index * TAU / 6
			var direction := Vector3(cos(angle), sin(angle), 0)
			_bar(wheel, "spoke-%d" % index, direction * 0.075 + Vector3(0, 0, 0.006), direction * 0.413 + Vector3(0, 0, 0.006), 0.090, 0.064)
		wheel.add("hazard-band", &"band", Vector3(0.75, 0.24, 0.012), Transform3D(Basis(Vector3.BACK, 0.060), Vector3(0, -0.150, -0.026)))
		var band := wheel.parts[-1]
		var rng := RandomNumberGenerator.new()
		rng.seed = 7308
		var bottom := PackedVector2Array()
		for index: int in range(25):
			var x := -0.375 + index * 0.75 / 24
			band.contour.append(Vector2(x, 0.120 - rng.randf_range(0, 0.018)))
			bottom.append(Vector2(x, maxf(-0.120 + rng.randf_range(0, 0.019), 0.15 - sqrt(0.43 * 0.43 - x * x))))
		band.contour[12].y = 0.120
		bottom[12].y = -0.120
		bottom.reverse()
		band.contour.append_array(bottom)
		for x: float in [-0.32, 0.32]:
			var pin_pose := band.transform * Transform3D(Basis(Quaternion(Vector3.UP, Vector3.BACK)), Vector3(x, 0, -0.004))
			wheel.add("band-bolt-%s" % x, &"cylinder", Vector3(0.028, 0.003, 0.028), pin_pose, 0.014)
		groups.append(wheel)
		var rivets := Group.new(NodePath(prefix + "Rivets"), face, side)
		var border := outline(Vector2(aperture.x - 0.105, aperture.y - 0.19), 0.22)
		var contour := Group.new(NodePath(prefix + "Contour"), face, side)
		for index: int in range(border.size()):
			var a := border[index] + Vector2(aperture.x / 2, center_y)
			var b := border[(index + 1) % border.size()] + Vector2(aperture.x / 2, center_y)
			var delta := b - a
			_pin(contour, "edge-%02d" % index, 0.009, delta.length(), Vector3((a.x + b.x) / 2, (a.y + b.y) / 2, -0.103), Vector3(delta.x, delta.y, 0).normalized())
			var count := maxi(1, int(ceil(a.distance_to(b) / 0.16)))
			for step: int in range(count):
				var point := a.lerp(b, float(step) / count)
				_pin(rivets, "%03d" % rivets.parts.size(), 0.012, 0.010, Vector3(point.x, point.y, -0.111))
		groups.append(contour)
		groups.append(rivets)
	for entry: Array in [["Body", Vector3(1.10, 2.32, 0.03), Vector3(0.55, center_y, into * 0.035), 0.235], ["Hinge", Vector3(0.09, 2.32, 0.03), Vector3(-0.045, center_y, into * 0.035), 0.04], ["Latch", Vector3(0.05, 2.32, 0.03), Vector3(1.125, center_y, into * 0.035), 0.024]]:
		var lap := Group.new(NodePath("BackingLap" + entry[0]), Transform3D.IDENTITY, 0, true)
		lap.add("lap", &"rounded", entry[1], Transform3D(Basis(), entry[2]), entry[3])
		groups.append(lap)
	# A thin leaf lip laps the existing collar on its swing side. The hinge-side
	# return stays separate so its bounds do not fill the latch-side swing gap.
	for side: int in range(2):
		var prefix := "Fore" if side == 0 else "Aft"
		var pose := Transform3D(Basis(), Vector3(0, 0, into * SEAL_DEPTH / 2 + (-1 if side == 0 else 1) * SEAL_DEPTH / 4))
		var height := aperture.y - ShipGeometry.SILL_HEIGHT
		var face_depth := SEAL_DEPTH / 2
		var face_z := (-1 if side == 0 else 1) * (ShipLayout.WALL / 2 - SEAL_DEPTH / 40 - face_depth / 2)
		var face_seal := Group.new(NodePath(prefix + "FaceSealSteel"), Transform3D(Basis(), Vector3(0, 0, face_z)), side, true)
		face_seal.add("face-return", &"box", Vector3(aperture.x, height, face_depth), Transform3D(Basis(), Vector3(aperture.x / 2, center_y, 0)))
		groups.append(face_seal)
		var pivot_seal := Group.new(NodePath(prefix + "PivotSealSteel"), face_seal.transform, side, true)
		pivot_seal.add("pivot-return", &"box", Vector3(HINGE_RETURN_WIDTH, height, face_depth), Transform3D(Basis(), Vector3(-HINGE_RETURN_WIDTH / 2, center_y, 0)))
		groups.append(pivot_seal)
		var width := aperture.x + SEAL_LAP
		var seal := Group.new(NodePath(prefix + "SealSteel"), pose, side, true)
		seal.add("lip", &"box", Vector3(width, height, SEAL_DEPTH / 2), Transform3D(Basis(), Vector3(width / 2, center_y, 0)))
		groups.append(seal)
		var hinge_seal := Group.new(NodePath(prefix + "HingeSealSteel"), pose, side, true)
		hinge_seal.add("return", &"box", Vector3(HINGE_RETURN_WIDTH, height, SEAL_DEPTH / 2), Transform3D(Basis(), Vector3(-HINGE_RETURN_WIDTH / 2, center_y, 0)))
		groups.append(hinge_seal)
	_leaves[key] = groups
	return groups
