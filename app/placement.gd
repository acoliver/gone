class_name Placement
extends RefCounted
## Pure world-space placements for every non-pod scene solid, plus the
## static collider-set derivation, ported from gone_app placement.rs and
## colliders.rs. One construction path: the scene builders spawn these
## placements verbatim and the collider set derives from the same data,
## so the rendered world and the swept-collision world cannot drift
## apart. All values are world space, in meters, up is +Y, with one
## exception: the status indicator plate is pod-local because the scene
## spawns it under each pod group. Pure data: no Node types.

## Shell wall and floor slab thickness, in meters.
const WALL_THICKNESS: float = 0.2

## The hatch opening's size, in meters, and the frame pieces around it.
const HATCH_WIDTH: float = 1.2
const HATCH_HEIGHT: float = 2.4
const FRAME_DEPTH: float = 0.18
const FRAME_POST_WIDTH: float = 0.16
const SILL_HEIGHT: float = 0.08

## The hatch door slab: smaller than the opening, recessed behind the
## frame front, ajar about its hinge edge, leaning into the room.
const DOOR_WIDTH: float = 1.12
const DOOR_HEIGHT: float = 2.2
const DOOR_THICKNESS: float = 0.06
const DOOR_RECESS: float = 0.1
const DOOR_HINGE_INSET: float = 0.04
const HATCH_DOOR_AJAR: float = deg_to_rad(8.0)

## X of the hatch frame's center plane: protruding FRAME_DEPTH from the
## wall's inner face.
const HATCH_FRAME_X: float = Pods.ROOM_LENGTH / 2.0 - FRAME_DEPTH / 2.0

## X of the hatch door slab's center plane: recessed behind the frame's
## front face.
const HATCH_DOOR_X: float = Pods.ROOM_LENGTH / 2.0 - DOOR_RECESS

## Cable tray cross-section, in meters, and the drop of the tray center
## line below the ceiling.
const TRAY_WIDTH: float = 0.3
const TRAY_HEIGHT: float = 0.08
const TRAY_CEILING_DROP: float = 0.15

## Hanging wire loop torus mesh radii, in meters: the inner ring radius
## and the outer extent.
const WIRE_INNER_RADIUS: float = 0.035
const WIRE_OUTER_RADIUS: float = 0.11

## The status indicator plate, in meters: mounted on the pod's foot face.
const PLATE_WIDTH: float = 0.2
const PLATE_HEIGHT: float = 0.1
const PLATE_THICKNESS: float = 0.04
const PLATE_STANDOFF: float = 0.02
const PLATE_MOUNT_HEIGHT: float = 0.55

class SolidPlacement:
	extends RefCounted
	## One placed solid box: world center, full size, and the world
	## rotation applied at spawn. Most pieces are axis-aligned; the ajar
	## hatch door and the torn cable trays carry real rotations.

	var center: Vector3 = Vector3.ZERO
	var size: Vector3 = Vector3.ZERO
	var rotation: Quaternion = Quaternion.IDENTITY

	func _init(p_center: Vector3, p_size: Vector3, p_rotation: Quaternion = Quaternion.IDENTITY) -> void:
		center = p_center
		size = p_size
		rotation = p_rotation

class WireLoop:
	extends RefCounted
	## One hanging wire loop: a torus hanging under the torn ceiling,
	## tipped from face-up to vertical, with a per-loop swing yaw.

	var center: Vector3 = Vector3.ZERO
	var rotation: Quaternion = Quaternion.IDENTITY

	func _init(p_center: Vector3, p_rotation: Quaternion) -> void:
		center = p_center
		rotation = p_rotation

## The room shell's six boxes in fixed order: floor, ceiling, then the
## -Z, +Z, -X, and +X walls. The playable interior is exactly
## ROOM_LENGTH by ROOM_WIDTH with its ceiling at ROOM_CEILING_HEIGHT.
static func room_shell() -> Array[Placement.SolidPlacement]:
	var slab := Vector3(
		Pods.ROOM_LENGTH + 2.0 * WALL_THICKNESS,
		WALL_THICKNESS,
		Pods.ROOM_WIDTH + 2.0 * WALL_THICKNESS
	)
	var wall_along_x := Vector3(
		Pods.ROOM_LENGTH + 2.0 * WALL_THICKNESS,
		Pods.ROOM_CEILING_HEIGHT,
		WALL_THICKNESS
	)
	var wall_along_z := Vector3(WALL_THICKNESS, Pods.ROOM_CEILING_HEIGHT, Pods.ROOM_WIDTH)
	var mid_height := Pods.ROOM_CEILING_HEIGHT / 2.0
	return [
		Placement.SolidPlacement.new(Vector3(0.0, -WALL_THICKNESS / 2.0, 0.0), slab),
		Placement.SolidPlacement.new(
			Vector3(0.0, Pods.ROOM_CEILING_HEIGHT + WALL_THICKNESS / 2.0, 0.0),
			slab
		),
		Placement.SolidPlacement.new(
			Vector3(0.0, mid_height, -(Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0)),
			wall_along_x
		),
		Placement.SolidPlacement.new(
			Vector3(0.0, mid_height, Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0),
			wall_along_x
		),
		Placement.SolidPlacement.new(
			Vector3(-(Pods.ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0), mid_height, 0.0),
			wall_along_z
		),
		Placement.SolidPlacement.new(
			Vector3(Pods.ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0, mid_height, 0.0),
			wall_along_z
		),
	]

## The hatch group's five boxes in fixed order: the -Z frame post, the
## +Z frame post, the lintel, the sill, and the ajar door slab. The group
## itself sits at the identity transform, so these are world placements.
static func hatch_solids() -> Array[Placement.SolidPlacement]:
	var post := Vector3(FRAME_DEPTH, HATCH_HEIGHT + FRAME_POST_WIDTH, FRAME_POST_WIDTH)
	var lintel := Vector3(FRAME_DEPTH, FRAME_POST_WIDTH, HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH)
	var sill := Vector3(FRAME_DEPTH, SILL_HEIGHT, HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH)
	var door_rotation := Quaternion(Vector3.UP, -HATCH_DOOR_AJAR)
	var door_group_origin := Vector3(HATCH_DOOR_X, 0.0, -(HATCH_WIDTH / 2.0 - DOOR_HINGE_INSET))
	var door_center: Vector3 = door_group_origin + door_rotation * Vector3(0.0, DOOR_HEIGHT / 2.0, DOOR_WIDTH / 2.0)
	return [
		Placement.SolidPlacement.new(
			Vector3(
				HATCH_FRAME_X,
				(HATCH_HEIGHT + FRAME_POST_WIDTH) / 2.0,
				-(HATCH_WIDTH + FRAME_POST_WIDTH) / 2.0
			),
			post
		),
		Placement.SolidPlacement.new(
			Vector3(
				HATCH_FRAME_X,
				(HATCH_HEIGHT + FRAME_POST_WIDTH) / 2.0,
				(HATCH_WIDTH + FRAME_POST_WIDTH) / 2.0
			),
			post
		),
		Placement.SolidPlacement.new(
			Vector3(HATCH_FRAME_X, HATCH_HEIGHT + FRAME_POST_WIDTH / 2.0, 0.0),
			lintel
		),
		Placement.SolidPlacement.new(Vector3(HATCH_FRAME_X, SILL_HEIGHT / 2.0, 0.0), sill),
		Placement.SolidPlacement.new(
			door_center,
			Vector3(DOOR_THICKNESS, DOOR_HEIGHT, DOOR_WIDTH),
			door_rotation
		),
	]

## The torn ceiling's cable trays, concentrated over the room center: a
## junction of runs and one stub toward the player row, each tipped off
## level about its run axis.
static func cable_trays() -> Array[Placement.SolidPlacement]:
	return [
		Placement.SolidPlacement.new(
			Vector3(-0.5, Pods.ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP, 0.35),
			Vector3(6.0, TRAY_HEIGHT, TRAY_WIDTH),
			Quaternion(Vector3.UP, 0.0) * Quaternion(Vector3.RIGHT, 0.06)
		),
		Placement.SolidPlacement.new(
			Vector3(0.9, Pods.ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP - 0.04, -0.7),
			Vector3(4.5, TRAY_HEIGHT, TRAY_WIDTH),
			Quaternion(Vector3.UP, PI / 2.0) * Quaternion(Vector3.RIGHT, -0.04)
		),
		Placement.SolidPlacement.new(
			Vector3(1.6, Pods.ROOM_CEILING_HEIGHT - TRAY_CEILING_DROP + 0.05, 1.1),
			Vector3(3.0, TRAY_HEIGHT, TRAY_WIDTH),
			Quaternion(Vector3.UP, 0.0) * Quaternion(Vector3.RIGHT, -0.09)
		),
	]

## The five hanging wire loops over the room center.
static func wire_loops() -> Array[Placement.WireLoop]:
	var loops: Array[Placement.WireLoop] = []
	var authored: Array[Vector4] = [
		Vector4(-1.3, 2.7, 0.5, 0.4),
		Vector4(-0.4, 2.55, 0.2, 1.3),
		Vector4(0.3, 2.78, -0.5, 2.2),
		Vector4(1.1, 2.62, 0.8, 0.9),
		Vector4(2.0, 2.5, -0.2, 2.9),
	]
	for entry: Vector4 in authored:
		loops.append(
			Placement.WireLoop.new(
				Vector3(entry.x, entry.y, entry.z),
				Quaternion(Vector3.RIGHT, PI / 2.0) * Quaternion(Vector3.UP, entry.w)
			)
		)
	return loops

## The pod status indicator plate, in the POD-LOCAL frame: the scene
## spawns it under each pod group.
static func indicator_plate() -> Placement.SolidPlacement:
	return Placement.SolidPlacement.new(
		Vector3(0.0, PLATE_MOUNT_HEIGHT, Pods.POD_LENGTH / 2.0 + PLATE_STANDOFF),
		Vector3(PLATE_WIDTH, PLATE_HEIGHT, PLATE_THICKNESS)
	)

## The pod group transform the scene spawns pod groups with: the yaw
## rotation and the floor translation derived from the registry
## placement, as `[rotation, translation]`.
static func pod_world_transform(placement: Pods.PodPlacement) -> Array:
	return [
		Quaternion(Vector3.UP, placement.yaw_radians),
		Vector3(placement.center.x, 0.0, placement.center.y),
	]

## Build the whole static collider set from the same placement data the
## scene spawns: the room shell, every pod's construction solids through
## the pod group's world transform, and the hatch group, in that fixed
## insertion order. The status plates, cable trays, and wire loops are
## dressing outside the walking envelope and are deliberately not
## colliders, so the exit aperture mouth stays exactly as authored.
static func scene_collider_set(registry: Pods.PodRegistry) -> ColliderSet:
	var set := ColliderSet.new()
	for placement: Placement.SolidPlacement in room_shell():
		_insert_placement(set, placement, Quaternion.IDENTITY, Vector3.ZERO)
	for pod: Pods.Pod in registry.pods():
		var frame := pod_world_transform(pod.placement())
		for solid: PodBody.PodSolid in PodBody.pod_solids(pod.state()):
			_insert_pod_solid(set, solid, frame[0], frame[1])
	for placement: Placement.SolidPlacement in hatch_solids():
		_insert_placement(set, placement, Quaternion.IDENTITY, Vector3.ZERO)
	return set

## Insert one world-frame placement as a collider box, through an optional
## parent transform.
static func _insert_placement(
	set: ColliderSet,
	placement: Placement.SolidPlacement,
	parent_rotation: Quaternion,
	parent_translation: Vector3
) -> void:
	var rotation: Quaternion = parent_rotation * placement.rotation
	var center: Vector3 = parent_rotation * placement.center + parent_translation
	_insert_box(set, center, placement.size, rotation)

## Insert one pod-local construction solid through the pod group's world
## transform: the group yaw carries the local frame into the room, and
## the solid's local roll composes inside it.
static func _insert_pod_solid(
	set: ColliderSet,
	solid: PodBody.PodSolid,
	group_rotation: Quaternion,
	group_translation: Vector3
) -> void:
	var rotation: Quaternion = group_rotation * Quaternion(Vector3.RIGHT, solid.roll_radians)
	var center: Vector3 = group_rotation * solid.center + group_translation
	_insert_box(set, center, solid.size, rotation)

## The conservative world AABB of one placed box: the hull of its eight
## transformed corners. Exact for axis-aligned rotations; a tight
## conservative hull otherwise.
static func _insert_box(set: ColliderSet, center: Vector3, size: Vector3, rotation: Quaternion) -> void:
	var half := size * 0.5
	var lo := Vector3(INF, INF, INF)
	var hi := Vector3(-INF, -INF, -INF)
	for x: float in [-1.0, 1.0]:
		for y: float in [-1.0, 1.0]:
			for z: float in [-1.0, 1.0]:
				var corner: Vector3 = center + rotation * (Vector3(x, y, z) * half)
				lo = lo.min(corner)
				hi = hi.max(corner)
	var result: ColliderSet.Result = ColliderSet.Aabb.from_min_max(lo, hi)
	assert(result.is_ok(), "the frozen placement data derives a valid collider box")
	set.insert(result.box)
