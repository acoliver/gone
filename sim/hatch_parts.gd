class_name HatchParts
extends RefCounted
## Physical leaf geometry in pure leaf/group-local frames. Meshes belong to app.

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

static func leaf(door: ShipLayout.DoorSpec) -> Array[Group]:
	var aperture := door.leaf_aperture()
	var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
	var key := [aperture, into]
	if _leaves.has(key): return _leaves[key]
	var groups: Array[Group] = []
	for side: int in range(2):
		var prefix := "Fore" if side == 0 else "Aft"
		var face := Transform3D(Basis() if side == 0 else Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD), Vector3(0, 0, -0.05 if side == 0 else 0.05))
		var plate := Group.new(NodePath(prefix + "Steel"), face, side, true)
		plate.add("plate", &"rounded", Vector3(aperture.x - 0.025, aperture.y - ShipGeometry.SILL_HEIGHT - 0.025, 0.10), Transform3D(Basis(), Vector3(aperture.x / 2, (aperture.y + ShipGeometry.SILL_HEIGHT) / 2, 0)), 0.205)
		for index: int in range(2):
			var diagonal := -1.0 if index == 0 else 1.0
			_bar(plate, "brace-%d" % index, Vector3(aperture.x / 2 - diagonal * (aperture.x / 2 - 0.14), 0.28, -0.06), Vector3(aperture.x / 2 + diagonal * (aperture.x / 2 - 0.14), aperture.y - 0.15, -0.06), 0.075, 0.035)
		plate.add("label-plate", &"rounded", Vector3(ShipLayout.HATCH_LABEL_SIZE.x + 0.04, ShipLayout.HATCH_LABEL_SIZE.y + 0.04, 0.04), Transform3D(Basis(), Vector3(aperture.x / 2, ShipLayout.DOOR_LABEL_HEIGHT, -0.068)), 0.025)
		groups.append(plate)
		var straps := Group.new(NodePath("StrapHinges/" + prefix + "Steel"), face, side)
		var heights: Array[float] = [0.48, aperture.y - 0.40]
		for index: int in range(heights.size()):
			straps.add("strap-%d" % index, &"rounded", Vector3(0.43, 0.15, 0.08), Transform3D(Basis(), Vector3(0.215, heights[index], -0.075)), 0.04)
		groups.append(straps)
		var lugs := Group.new(NodePath("Lugs/" + prefix + "Steel"), face, side)
		heights = [0.40, 1.17, aperture.y - 0.33]
		for index: int in range(heights.size()):
			lugs.add("side-%d" % index, &"rounded", Vector3(0.19, 0.13, 0.075), Transform3D(Basis(), Vector3(aperture.x - 0.12, heights[index], -0.08)), 0.025)
		heights = [0.19, aperture.y - 0.13]
		for index: int in range(heights.size()):
			lugs.add("end-%d" % index, &"rounded", Vector3(0.14, 0.17, 0.075), Transform3D(Basis(), Vector3(aperture.x / 2, heights[index], -0.08)), 0.025)
		groups.append(lugs)
		var wheel_pose := Transform3D(Basis(Vector3.UP, 0 if side == 0 else PI), Vector3(aperture.x / 2, aperture.y / 2, -0.19 if side == 0 else 0.19))
		var wheel := Group.new(NodePath("Wheel" if side == 0 else "ReverseWheel"), wheel_pose, side)
		wheel.add("ring", &"torus", Vector3(0.61, 0.04, 0.61), Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3.ZERO), 0.305, 0.265)
		wheel.add("hub", &"cylinder", Vector3(0.164, 0.16, 0.164), Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(0, 0, 0.045)), 0.082)
		for index: int in range(6):
			var angle := index * TAU / 6
			_bar(wheel, "spoke-%d" % index, Vector3.ZERO, Vector3(cos(angle), sin(angle), 0) * 0.28, 0.035, 0.045)
		groups.append(wheel)
		var rivets := Group.new(NodePath(prefix + "Rivets"), face, side)
		for diagonal: float in [-1, 1]:
			for index: int in range(23):
				var t := float(index) / 22
				var position := Vector3(lerpf(aperture.x / 2 - diagonal * (aperture.x / 2 - 0.14), aperture.x / 2 + diagonal * (aperture.x / 2 - 0.14), t), lerpf(0.28, aperture.y - 0.15, t), -0.087)
				rivets.add("%03d" % rivets.parts.size(), &"cylinder", Vector3(0.036, 0.012, 0.036), Transform3D(Basis(Vector3.RIGHT, PI / 2), position), 0.018)
		groups.append(rivets)
	# A thin leaf lip laps the existing collar on its swing side. The hinge-side
	# return stays separate so its bounds do not fill the latch-side swing gap.
	for side: int in range(2):
		var prefix := "Fore" if side == 0 else "Aft"
		var pose := Transform3D(Basis(), Vector3(0, 0, into * SEAL_DEPTH / 2 + (-1 if side == 0 else 1) * SEAL_DEPTH / 4))
		var height := aperture.y - ShipGeometry.SILL_HEIGHT
		var center_y := ShipGeometry.SILL_HEIGHT + height / 2
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
