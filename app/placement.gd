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
const WALL_THICKNESS = ShipGeometry.WALL_THICKNESS

## The hatch opening's size, in meters, and the frame pieces around it.
const HATCH_WIDTH = ShipGeometry.HATCH_WIDTH
const HATCH_HEIGHT = ShipGeometry.HATCH_HEIGHT
const FRAME_DEPTH = ShipGeometry.FRAME_DEPTH
const FRAME_POST_WIDTH = ShipGeometry.FRAME_POST_WIDTH
const SILL_HEIGHT = ShipGeometry.SILL_HEIGHT

## The hatch door slab: smaller than the opening, recessed behind the
## frame front, ajar about its hinge edge, leaning into the room.
const DOOR_WIDTH = ShipGeometry.DOOR_WIDTH
const DOOR_HEIGHT = ShipGeometry.DOOR_HEIGHT
const DOOR_THICKNESS = ShipGeometry.DOOR_THICKNESS
const DOOR_RECESS = ShipGeometry.DOOR_RECESS
const DOOR_HINGE_INSET = ShipGeometry.DOOR_HINGE_INSET
const HATCH_DOOR_AJAR = ShipGeometry.HATCH_DOOR_AJAR

## X of the hatch frame's center plane: protruding FRAME_DEPTH from the
## wall's inner face.
const HATCH_FRAME_X = ShipGeometry.HATCH_FRAME_X

## X of the hatch door slab's center plane: recessed behind the frame's
## front face.
const HATCH_DOOR_X = ShipGeometry.HATCH_DOOR_X

## Minimum overhead dressing height, above the standing camera.
const OVERHEAD_CLEARANCE: float = 2.1

## The status indicator plate, in meters: mounted on the pod's foot face.
const PLATE_WIDTH: float = 0.2
const PLATE_HEIGHT: float = 0.1
const PLATE_THICKNESS: float = 0.04
const PLATE_STANDOFF: float = 0.02
const PLATE_MOUNT_HEIGHT: float = 0.55

const SolidPlacement = ShipGeometry.SolidSpec

const WireLoop = ShipGeometry.WireLoop

## The room shell's six boxes in fixed order: floor, ceiling, then the
## -Z, +Z, -X, and +X walls. The playable interior is exactly
## ROOM_LENGTH by ROOM_WIDTH with its ceiling at ROOM_CEILING_HEIGHT.
static func room_shell(open_east_wall: bool = false) -> Array[Placement.SolidPlacement]:
	return ShipGeometry.room_shell(open_east_wall)

## The hatch group's five boxes in fixed order: the -Z frame post, the
## +Z frame post, the lintel, the sill, and the ajar door slab. The group
## itself sits at the identity transform, so these are world placements.
static func hatch_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.hatch_solids()

## Generated from the installed fault's three physical copper tips.
static func spark_spots() -> Array[Vector3]:
	return StasisWiringRoutes.power_tips()

static func wire_loops() -> Array[Placement.WireLoop]:
	return []

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
	return ShipGeometry.pod_world_transform(placement)

## Build the whole static collider set from the same placement data the
## scene spawns: the room shell, every pod's construction solids through
## the pod group's world transform, and the hatch group, in that fixed
## insertion order. The status plates and hanging wires are
## dressing outside the walking envelope and are deliberately not
## colliders, so the exit aperture mouth stays exactly as authored.
static func scene_collider_set(registry: Pods.PodRegistry) -> ColliderSet:
	return ShipCollision.bay_set(registry)
