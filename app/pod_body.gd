class_name PodBody
extends RefCounted
## Pure stasis pod construction solids, ported from gone_app pod_body.rs.
## Every pod is an open-topped tray instead of a solid block: a base
## slab, a dark floor plate, a head wall between two side walls with a
## real cavity, and a fully open foot end (the exit aperture mouth). The
## state's top finishes the silhouette: sealed pods close with a flat
## lid, empty-open pods keep the angled open lid plus a hanging blanket,
## and the player pod stands its lid up as a canopy over the head end.
## The scene builders spawn these boxes verbatim and the collider set
## lifts the same data, so rendered geometry and guarantees cannot drift.
## All numbers are pod-local, in meters: local +Z is the pod's opening
## (its foot), local -Z the head, up is +Y. Pure data: no Node types.

## Cavity wall thickness, in meters.
const CAVITY_WALL: float = 0.06

## Base slab thickness, in meters: the cavity floor under the plate.
const CAVITY_BASE: float = 0.1

## Dark cavity floor plate thickness, in meters.
const CAVITY_PLATE_THICKNESS: float = 0.012

## The tray floor's top height in the pod-local frame: the plate top the
## lying capsule rests on. The pod group sits on the room floor, so this
## is also the world-frame height.
const TRAY_FLOOR_Y: float = CAVITY_BASE + CAVITY_PLATE_THICKNESS

## How far the side walls stop short of the foot face, in meters: the
## exit aperture mouth strip, held clear of standing geometry.
const EXIT_MOUTH_DEPTH: float = CAVITY_WALL

## The frozen exit aperture's clear width: the capsule diameter plus the
## frozen exit clearance on each side.
const EXIT_APERTURE_WIDTH: float = 2.0 * (Controller.CAPSULE_RADIUS + Controller.POD_EXIT_CLEARANCE)

## Pod lid slab thickness, in meters (closed lid, open lid, canopy alike).
const LID_THICKNESS: float = 0.06

## How much shorter than the body the open lid slab is.
const LID_SETBACK: float = 0.1

## The empty-open lid's tilt from horizontal, in radians.
const LID_OPEN_TILT: float = deg_to_rad(60.0)

## The player pod's canopy length along the pod, in meters.
const CANOPY_LENGTH: float = 1.3

## The occupancy blanket's silhouette, in meters.
const BLANKET_THICKNESS: float = 0.05
const BLANKET_DROP: float = 0.56
const BLANKET_WIDTH: float = 0.7

## How far above the pod top the blanket's upper edge sits.
const BLANKET_OVERHANG: float = 0.02

## Distance from the pod's foot end to the hanging blanket, in meters.
const BLANKET_FROM_FOOT: float = 0.15

enum SolidKind { BODY, CAVITY, LID, BLANKET }

class PodSolid:
	extends RefCounted
	## One solid cuboid of a pod's greybox, in the pod's local frame.

	var center: Vector3 = Vector3.ZERO
	var size: Vector3 = Vector3.ZERO
	var roll_radians: float = 0.0
	var kind: int = SolidKind.BODY

	func _init(p_center: Vector3, p_size: Vector3, p_roll_radians: float, p_kind: int) -> void:
		center = p_center
		size = p_size
		roll_radians = p_roll_radians
		kind = p_kind

## Build one pod's full solid set for `state`: the shared cavity tray plus
## the state's top (and the blanket for empty-open pods).
static func pod_solids(state: int) -> Array[PodBody.PodSolid]:
	var solids := cavity_solids()
	match state:
		Pods.PodState.SEALED:
			solids.append(sealed_lid())
		Pods.PodState.EMPTY_OPEN:
			solids.append(open_lid())
			solids.append(hanging_blanket())
		Pods.PodState.PLAYER:
			solids.append(player_canopy())
	return solids

## The open cavity's interior clear box as `[min, max]` corners: between
## the walls' inner faces and above the base slab.
static func cavity_interior() -> Array[Vector3]:
	var half_width := Pods.POD_WIDTH / 2.0 - CAVITY_WALL
	var half_length := Pods.POD_LENGTH / 2.0 - CAVITY_WALL
	return [
		Vector3(-half_width, CAVITY_BASE, -half_length),
		Vector3(half_width, Pods.POD_HEIGHT, half_length),
	]

static func _solid(center: Vector3, size: Vector3, kind: int) -> PodBody.PodSolid:
	return PodBody.PodSolid.new(center, size, 0.0, kind)

## The cavity tray every pod is built from: base slab, dark floor plate,
## the head wall between the side walls, and no foot wall at all. The side
## walls stop short of the foot face by EXIT_MOUTH_DEPTH.
static func cavity_solids() -> Array[PodBody.PodSolid]:
	var bounds := cavity_interior()
	var interior_min: Vector3 = bounds[0]
	var interior_max: Vector3 = bounds[1]
	var wall_height := Pods.POD_HEIGHT - CAVITY_BASE
	var wall_mid := CAVITY_BASE + wall_height / 2.0
	var head_z := -(Pods.POD_LENGTH - CAVITY_WALL) / 2.0
	var wall_length := Pods.POD_LENGTH - EXIT_MOUTH_DEPTH
	var wall_mid_z := -EXIT_MOUTH_DEPTH / 2.0
	var solids: Array[PodBody.PodSolid] = [
		_solid(
			Vector3(0.0, CAVITY_BASE / 2.0, 0.0),
			Vector3(Pods.POD_WIDTH, CAVITY_BASE, Pods.POD_LENGTH),
			SolidKind.BODY
		),
		_solid(
			Vector3(0.0, CAVITY_BASE + CAVITY_PLATE_THICKNESS / 2.0, 0.0),
			Vector3(
				interior_max.x - interior_min.x,
				CAVITY_PLATE_THICKNESS,
				interior_max.z - interior_min.z
			),
			SolidKind.CAVITY
		),
		_solid(
			Vector3(0.0, wall_mid, head_z),
			Vector3(interior_max.x - interior_min.x, wall_height, CAVITY_WALL),
			SolidKind.BODY
		),
	]
	for side: float in [-1.0, 1.0]:
		solids.append(
			_solid(
				Vector3(side * (interior_max.x + CAVITY_WALL / 2.0), wall_mid, wall_mid_z),
				Vector3(CAVITY_WALL, wall_height, wall_length),
				SolidKind.BODY
			)
		)
	return solids

## The sealed pod's closed lid: one flat slab over the whole footprint.
static func sealed_lid() -> PodBody.PodSolid:
	return _solid(
		Vector3(0.0, Pods.POD_HEIGHT + LID_THICKNESS / 2.0, 0.0),
		Vector3(Pods.POD_WIDTH, LID_THICKNESS, Pods.POD_LENGTH),
		SolidKind.LID
	)

## The empty-open pod's lid: hinged at the head end top edge and swung up
## LID_OPEN_TILT, propped over the head.
static func open_lid() -> PodBody.PodSolid:
	var length := Pods.POD_LENGTH - LID_SETBACK
	var hinge := Vector3(0.0, Pods.POD_HEIGHT, -Pods.POD_LENGTH / 2.0)
	var center := hinge + Vector3(
		0.0,
		sin(LID_OPEN_TILT) * length / 2.0,
		cos(LID_OPEN_TILT) * length / 2.0
	)
	return PodBody.PodSolid.new(
		center,
		Vector3(Pods.POD_WIDTH, LID_THICKNESS, length),
		-LID_OPEN_TILT,
		SolidKind.LID
	)

## The player pod's raised canopy: the lid stood fully upright over the
## head wall, inside the footprint.
static func player_canopy() -> PodBody.PodSolid:
	return _solid(
		Vector3(
			0.0,
			Pods.POD_HEIGHT + CANOPY_LENGTH / 2.0,
			-(Pods.POD_LENGTH - LID_THICKNESS) / 2.0
		),
		Vector3(Pods.POD_WIDTH, CANOPY_LENGTH, LID_THICKNESS),
		SolidKind.LID
	)

## The empty-open pod's occupancy blanket: a thin slab draped over one
## rim, hanging down the outside wall.
static func hanging_blanket() -> PodBody.PodSolid:
	var over_rim := Pods.POD_WIDTH / 2.0 + BLANKET_THICKNESS / 2.0
	var top := Pods.POD_HEIGHT - BLANKET_DROP / 2.0 + BLANKET_OVERHANG
	var along := -Pods.POD_LENGTH / 2.0 + BLANKET_FROM_FOOT + BLANKET_WIDTH / 2.0
	return _solid(
		Vector3(over_rim, top, along),
		Vector3(BLANKET_THICKNESS, BLANKET_DROP, BLANKET_WIDTH),
		SolidKind.BLANKET
	)
