class_name QuartersLayout
extends RefCounted
## The approved plan looks into +Z; its screen-right +X maps to ship -X.

const ID: StringName = &"D16-QUARTERS"
const SECTION: StringName = &"D16-S-042"
const DOOR: StringName = &"D16-S-042-SIDE-009-STARBOARD"
const DECK := 16
const FLOOR_Y := -11.0
const WIDTH := 8.0
const DEPTH := 6.0
const HEIGHT := 3.2
const WALL := 0.2
const ENTRANCE_Z := 1.7
const CONSOLE: StringName = &"D16-QUARTERS-CONSOLE"

const RELEASE: StringName = &"D16-QUARTERS-RELEASE"
const RELEASE_SIZE := Vector2(0.26, 0.44)

static func release_frame() -> Transform3D:
	return Transform3D(Basis(Vector3.UP, PI), Vector3(44.1, -9.7, 1.48))

static func to_world(point: Vector3) -> Vector3:
	return Vector3(49.0 - point.x, FLOOR_Y + point.y, ENTRANCE_Z + point.z)

static func from_world(point: Vector3) -> Vector3:
	return Vector3(49.0 - point.x, point.y - FLOOR_Y, point.z - ENTRANCE_Z)

static func bounds() -> AABB:
	return AABB(Vector3(41, FLOOR_Y, ENTRANCE_Z), Vector3(WIDTH, HEIGHT, DEPTH))

static func envelope() -> AABB:
	return AABB(bounds().position - Vector3(WALL, WALL, WALL), bounds().size + Vector3.ONE * WALL * 2)

static func console_frame() -> Transform3D:
	return Transform3D(Basis(Vector3.FORWARD, Vector3.UP, Vector3.RIGHT), to_world(Vector3(7.45, 0.76, 2.0)))
