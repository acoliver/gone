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

## The hanging wires' authored centerline sampling resolution: points
## per wire, shared by every strand. Fine enough that the catenaries and
## the strands' opposing bends render as smooth curves.
const HANGING_WIRE_SAMPLES: int = 17

## The camera-clearance floor for every hanging-wire point, tube surface
## included: the player's standing eye is 1.6 m, so 2.1 m holds margin
## above the whole view path.
const HANGING_WIRE_CLEARANCE: float = 2.1

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

class HangingWire:
	extends RefCounted
	## One authored hanging wire: the sampled world-space centerline
	## polyline and the tube radius.

	var points: Array[Vector3] = []
	var radius: float = 0.0

	func _init(p_points: Array[Vector3], p_radius: float) -> void:
		points = p_points
		radius = p_radius

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

## The authored hanging wires under the torn ceiling, in fixed order:
## five looped bundles (both ends anchored, sagging on parabolic
## catenaries deep enough to read at greybox scale), five dangling
## strands (one anchored end, hanging on S-bends that bow opposite ways
## above and below the hang's midpoint), and two frayed offshoots split
## from a parent wire's insulation. Anchors cluster at the spark strobe
## spots (the tray centers less 0.2 m, as Hazards builds them) so the
## arcs read as traveling the wires. The two pod-area runs — the torn
## run whipped off the tray across the player pod and the segment
## caught between the wall edge and the pod's canopy corner — cross
## inside the lying wake view's up-facing cone over the player pod, so
## wires read from the first opening blink. Pure authored math, no
## randomness: two builds are identical, and every point stays above
## the HANGING_WIRE_CLEARANCE floor.
static func hanging_wires() -> Array[Placement.HangingWire]:
	var wires: Array[Placement.HangingWire] = []
	# The pod-ward torn run: ripped off tray 1's -X end, whipping across
	# over the player pod's body; its far half reads in the lying view.
	var pod_run := _loop_points(Vector3(-3.42, 3.00, 0.32), Vector3(-5.45, 2.96, 3.60), 0.72)
	wires.append(Placement.HangingWire.new(pod_run, 0.034))
	# The caught run: a whole segment torn free at both ends, hung
	# between the -X wall edge and the player pod's canopy corner, its
	# catenary sagging dead center in the lying up-facing view.
	wires.append(Placement.HangingWire.new(
		_loop_points(Vector3(-5.75, 3.02, 2.30), Vector3(-4.05, 2.98, 3.75), 0.78), 0.036))
	# The loop at spark strobe 1 (tray 1's center run).
	var spark_one_loop := _loop_points(Vector3(-0.74, 3.00, 0.26), Vector3(-0.26, 3.00, 0.46), 0.68)
	wires.append(Placement.HangingWire.new(spark_one_loop, 0.040))
	# The loop at spark strobe 2 (the cross run over tray 2).
	wires.append(Placement.HangingWire.new(
		_loop_points(Vector3(0.66, 2.97, -0.92), Vector3(1.14, 2.97, -0.48), 0.62), 0.038))
	# The loop at spark strobe 3 (the stub run over tray 3).
	wires.append(Placement.HangingWire.new(
		_loop_points(Vector3(1.28, 3.06, 1.00), Vector3(1.88, 3.06, 1.20), 0.78), 0.028))
	# Dangling strands: the first three hang through the three spark
	# strobe spots; the fourth hangs off the pod-area damage, square in
	# the lying view; the last dresses the tray run's far end.
	wires.append(Placement.HangingWire.new(
		_strand_points(Vector3(-0.50, 3.00, 0.35), Vector3(-0.62, 2.44, 0.24), Vector3(0.26, 0.0, -0.18)), 0.021))
	wires.append(Placement.HangingWire.new(
		_strand_points(Vector3(0.90, 2.97, -0.70), Vector3(0.78, 2.40, -0.82), Vector3(-0.24, 0.0, 0.20)), 0.023))
	wires.append(Placement.HangingWire.new(
		_strand_points(Vector3(1.60, 3.06, 1.10), Vector3(1.74, 2.52, 1.02), Vector3(0.22, 0.0, 0.16)), 0.019))
	wires.append(Placement.HangingWire.new(
		_strand_points(Vector3(-4.42, 3.01, 2.75), Vector3(-4.62, 2.46, 3.15), Vector3(0.30, 0.0, -0.22)), 0.020))
	wires.append(Placement.HangingWire.new(
		_strand_points(Vector3(2.42, 3.01, 0.30), Vector3(2.30, 2.48, 0.18), Vector3(-0.30, 0.0, -0.05)), 0.022))
	# Frayed offshoots: thin splits off a spark loop and off the
	# pod-ward run, hanging below the parent's insulation.
	wires.append(Placement.HangingWire.new(
		_fray_points(spark_one_loop, 0.5, Vector3(-0.66, 2.20, 0.50)), 0.012))
	wires.append(Placement.HangingWire.new(
		_fray_points(pod_run, 0.8, Vector3(-5.25, 2.38, 3.40)), 0.011))
	return wires

## A sagging run between two anchored ends: the parabolic catenary
## approximation, sampled at the authored resolution.
static func _loop_points(anchor_a: Vector3, anchor_b: Vector3, sag: float) -> Array[Vector3]:
	var points: Array[Vector3] = []
	for index: int in range(HANGING_WIRE_SAMPLES):
		var t: float = float(index) / float(HANGING_WIRE_SAMPLES - 1)
		points.append(anchor_a.lerp(anchor_b, t) - Vector3(0.0, sag * 4.0 * t * (1.0 - t), 0.0))
	return points

## A dangling strand: one anchored end, an authored tip, and an authored
## S-bend that bows to one side through the upper hang and the opposite
## side through the lower, so the strand swings instead of reading as a
## straight rod.
static func _strand_points(anchor: Vector3, tip: Vector3, bend: Vector3) -> Array[Vector3]:
	var points: Array[Vector3] = []
	for index: int in range(HANGING_WIRE_SAMPLES):
		var t: float = float(index) / float(HANGING_WIRE_SAMPLES - 1)
		points.append(anchor.lerp(tip, t) + bend * sin(TAU * t))
	return points

## A frayed offshoot: starts at an authored parameter along the parent
## wire's sampled centerline, then splits away to its authored tip.
static func _fray_points(parent: Array[Vector3], t_parent: float, tip: Vector3) -> Array[Vector3]:
	var start := _polyline_sample(parent, t_parent)
	var points: Array[Vector3] = []
	for index: int in range(HANGING_WIRE_SAMPLES):
		var t: float = float(index) / float(HANGING_WIRE_SAMPLES - 1)
		points.append(start.lerp(tip, t))
	return points

## The point at parameter t along a sampled polyline, by segment length
## fraction (the wires are sampled near uniformly, so this stays close
## to arc length).
static func _polyline_sample(points: Array[Vector3], t: float) -> Vector3:
	var scaled: float = clampf(t, 0.0, 1.0) * float(points.size() - 1)
	var index: int = clampi(int(floor(scaled)), 0, points.size() - 2)
	return points[index].lerp(points[index + 1], scaled - float(index))

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
