class_name PodGeometry
extends RefCounted
## Pod-local collision recipes for the clean-cage pod (#88).
## The five-piece tub has no foot wall. Three stepped lid slabs follow
## the dome envelope and rotate about the same hidden pivot as PodLid.

const CAVITY_WALL: float = 0.04
const CAVITY_BASE: float = 0.228
const CAVITY_PLATE_THICKNESS: float = 0.012
const TRAY_FLOOR_Y: float = 0.240
const TUB_TOP_Y: float = 0.419
const EXIT_MOUTH_DEPTH: float = 0.2965
const EXIT_APERTURE_WIDTH: float = 2.0 * (Controller.CAPSULE_RADIUS + Controller.POD_EXIT_CLEARANCE)
const LID_THICKNESS: float = 0.10
const LID_OPEN_TILT: float = deg_to_rad(70.0)
const LID_PIVOT := Vector3(0.0, 0.976, -1.15330785124)

# Retained only as a clearance reference for the retired blanket dressing.
const BLANKET_THICKNESS: float = 0.05
const BLANKET_DROP: float = 0.56
const BLANKET_WIDTH: float = 0.7
const BLANKET_OVERHANG: float = 0.02
const BLANKET_FROM_FOOT: float = 0.15

enum SolidKind { BODY, CAVITY, LID, BLANKET }

class PodSolid:
	extends RefCounted
	var center: Vector3
	var size: Vector3
	var roll_radians: float
	var kind: int

	func _init(p_center: Vector3, p_size: Vector3, p_roll_radians: float, p_kind: int) -> void:
		center = p_center
		size = p_size
		roll_radians = p_roll_radians
		kind = p_kind

static func lid_angle(state: int) -> float:
	match state:
		Pods.PodState.SEALED:
			return 0.0
		Pods.PodState.EMPTY_OPEN:
			return -LID_OPEN_TILT
		Pods.PodState.PLAYER:
			return -PI / 2.0
	assert(false, "unknown pod state")
	return 0.0

static func pod_solids(state: int) -> Array[PodGeometry.PodSolid]:
	var solids := cavity_solids()
	solids.append_array(lid_solids(state))
	return solids

static func cavity_interior() -> Array[Vector3]:
	return [Vector3(-0.33, CAVITY_BASE, -1.01), Vector3(0.33, TUB_TOP_Y, 1.01)]

static func _solid(center: Vector3, size: Vector3, kind: int) -> PodGeometry.PodSolid:
	return PodGeometry.PodSolid.new(center, size, 0.0, kind)

static func cavity_solids() -> Array[PodGeometry.PodSolid]:
	# The 550 x 1900 mm contact slab fits the measured flat underside;
	# the narrower couch plate and stopped-short rails fit the curved tub.
	return [
		_solid(Vector3(0, 0.114, 0), Vector3(0.55, 0.228, 1.9), SolidKind.BODY),
		_solid(Vector3(0, 0.234, 0), Vector3(0.62, 0.012, 1.8), SolidKind.CAVITY),
		_solid(Vector3(0, 0.275, -1.03), Vector3(0.42, 0.26, 0.04), SolidKind.BODY),
		_solid(Vector3(-0.35, 0.275, 0), Vector3(0.04, 0.26, 1.3), SolidKind.BODY),
		_solid(Vector3(0.35, 0.275, 0), Vector3(0.04, 0.26, 1.3), SolidKind.BODY),
	]

static func lid_solids(state: int) -> Array[PodGeometry.PodSolid]:
	var angle := lid_angle(state)
	var rotation := Basis(Vector3.RIGHT, angle)
	var solids: Array[PodGeometry.PodSolid] = []
	# Sections fit under the 896 mm crown and the lower rounded ends.
	for center: Vector3 in [Vector3(0, 0.73, -0.79), Vector3(0, 0.84, 0), Vector3(0, 0.73, 0.79)]:
		var length := 1.2 if center.z == 0.0 else 0.38
		solids.append(PodGeometry.PodSolid.new(
			LID_PIVOT + rotation * (center - LID_PIVOT),
			Vector3(0.64 if center.z == 0.0 else 0.40, LID_THICKNESS if center.z == 0.0 else 0.04, length), angle, SolidKind.LID))
	return solids

# Single central slabs remain available to dressing-clearance callers.
static func sealed_lid() -> PodGeometry.PodSolid:
	return lid_solids(Pods.PodState.SEALED)[1]

static func open_lid() -> PodGeometry.PodSolid:
	return lid_solids(Pods.PodState.EMPTY_OPEN)[1]

static func player_canopy() -> PodGeometry.PodSolid:
	return lid_solids(Pods.PodState.PLAYER)[1]

static func hanging_blanket() -> PodGeometry.PodSolid:
	return _solid(
		Vector3(Pods.POD_WIDTH / 2.0 + BLANKET_THICKNESS / 2.0,
			Pods.POD_HEIGHT - BLANKET_DROP / 2.0 + BLANKET_OVERHANG,
			-Pods.POD_LENGTH / 2.0 + BLANKET_FROM_FOOT + BLANKET_WIDTH / 2.0),
		Vector3(BLANKET_THICKNESS, BLANKET_DROP, BLANKET_WIDTH), SolidKind.BLANKET)
