class_name ShipGeometry
extends RefCounted
## Pure box recipes used by presentation and collision. Opening recipes keep
## their original bay-local coordinates until production adopts ShipLayout.

const WALL_THICKNESS: float = ShipLayout.WALL
const HATCH_WIDTH: float = ShipLayout.HATCH_WIDTH
const HATCH_HEIGHT: float = ShipLayout.HATCH_HEIGHT
const FRAME_DEPTH: float = 0.18
const FRAME_POST_WIDTH: float = 0.16
const SILL_HEIGHT: float = 0.08
# Andrew's 2026-11-05 proportions: a narrow raised bead, not a deep box frame.
const HATCH_CORNER_RADIUS: float = 0.24
const HATCH_RING_WIDTH: float = 0.09
# Driver decision after the generated-frame contract stop: only the source's
# visible front relief fits these 22 mm. Keep 2 mm flushness margin and the
# existing rear sealing plane; reserve no hidden tube depth inside the wall.
const HATCH_RING_FRONT: float = -0.028
const HATCH_RING_REAR: float = -0.006
# The existing pocket lap must not change with decorative bead relief.
const HATCH_POCKET_SEATING_LAP: float = 0.014
const HATCH_FLOOR_SKIN_HEIGHT: float = 0.001
const HATCH_RIVET_RADIUS: float = 0.021
const HATCH_RIVET_DEPTH: float = 0.025
const HATCH_RIVET_PITCH: float = 0.13
const WIRE_INNER_RADIUS: float = 0.035
const WIRE_OUTER_RADIUS: float = 0.11

class WireLoop:
	extends RefCounted
	var center: Vector3
	var rotation: Quaternion
	func _init(p_center: Vector3, p_rotation: Quaternion) -> void:
		center = p_center
		rotation = p_rotation

const SILL_WALK_WIDTH: float = 1.0
const DOOR_WIDTH: float = 1.12
const DOOR_HEIGHT: float = 2.2
const DOOR_THICKNESS: float = 0.06
const DOOR_RECESS: float = 0.1
const DOOR_HINGE_INSET: float = 0.04
const HATCH_DOOR_AJAR: float = deg_to_rad(8.0)
const HATCH_FRAME_X: float = Pods.ROOM_LENGTH / 2.0 - FRAME_DEPTH / 2.0
const HATCH_DOOR_X: float = Pods.ROOM_LENGTH / 2.0 - DOOR_RECESS
const HALL_LENGTH: float = Pods.ROOM_LENGTH * 2.0
const HALL_WIDTH: float = ShipLayout.CORRIDOR_WIDTH
const HALL_START_X: float = Pods.ROOM_LENGTH / 2.0
const HALL_END_X: float = HALL_START_X + HALL_LENGTH
const HALL_CEILING_HEIGHT: float = Pods.ROOM_CEILING_HEIGHT
const WALL: float = WALL_THICKNESS
const DOORWAY_WIDTH: float = HATCH_WIDTH
const DOORWAY_HEIGHT: float = HATCH_HEIGHT
const ROOM_SHELL_EAST_WALL_INDEX: int = 5
const SIDE_DOOR_WIDTH: float = 1.0
const SIDE_DOOR_HEIGHT: float = 2.2
const SIDE_DOOR_THICKNESS: float = 0.06
const POWER_DOOR_X: float = ShipLayout.POWER_CENTER_X
const ROOM_CENTER_X: float = POWER_DOOR_X
const ROOM_START_Z: float = ShipLayout.POWER_NEAR_Z
const ROOM_END_Z: float = ShipLayout.POWER_FAR_Z
const ROOM_START_X: float = ShipLayout.POWER_MIN_X
const ROOM_END_X: float = ShipLayout.POWER_MAX_X
const ROOM_CEILING: float = Pods.ROOM_CEILING_HEIGHT
const CONSOLE_HEALTHS := {
	"dead_black": 0,
	"dead_busted": 1,
	"active": 2,
}
const GENERATOR_CENTER: Vector3 = ShipLayout.POWER_GENERATOR_CENTER
const GENERATOR_RADIUS: float = 0.8
const GENERATOR_HEIGHT: float = ROOM_CEILING

class SolidSpec:
	extends RefCounted
	var id: StringName
	var _local_center: Vector3
	var _local_rotation: Quaternion
	var _parent := Transform3D.IDENTITY
	var size: Vector3
	var material_role: StringName
	var collision_role: StringName
	var hatch_profile: ShipLayout.DoorSpec
	var section := PackedVector2Array()
	var collision_outline := PackedVector2Array()
	var wall_corner_boxes: Array[ColliderSet.Aabb] = []
	var wall_seat_section := PackedVector2Array()
	var surface_owner: StringName
	var surface_part: StringName
	var transform: Transform3D:
		get: return _parent * Transform3D(Basis(_local_rotation), _local_center)
	var center: Vector3:
		get: return _parent * _local_center
	var rotation: Quaternion:
		get: return _parent.basis.get_rotation_quaternion() * _local_rotation
	func _init(p_center: Vector3, p_size: Vector3, p_rotation: Quaternion = Quaternion.IDENTITY, p_id: StringName = &"", p_material_role: StringName = &"wall", p_collision_role: StringName = &"static") -> void:
		id = p_id
		_local_center = p_center
		_local_rotation = p_rotation
		size = p_size
		material_role = p_material_role
		collision_role = p_collision_role
		var path := String(id).split("/")
		if path.size() > 1:
			surface_owner = StringName(path[0])
			path.remove_at(0)
			if path.size() > 1 and path[-1].is_valid_int(): path.remove_at(path.size() - 1)
			if path[0] == "FRAME": path = PackedStringArray(["FRAME"])
			if path[0] in ["BLOCKER", "PARKED", "SWING"]: path = PackedStringArray(["LEAF"])
			surface_part = StringName("/".join(path))
	func surface_identity(owner: StringName, part: StringName) -> void:
		surface_owner = owner
		surface_part = part
	func corner(local: Vector3) -> Vector3:
		# Preserve authored quaternion arithmetic, then apply exact cardinal frames.
		return _parent * (_local_center + _local_rotation * local)

class ConsoleStation:
	extends RefCounted

	var position: Vector3
	var yaw: float
	var health: int

	static func make(position: Vector3, yaw: float, health: int) -> ConsoleStation:
		var station := ConsoleStation.new()
		station.position = position
		station.yaw = yaw
		station.health = health
		return station

static func room_shell(open_east_wall: bool = false) -> Array[ShipGeometry.SolidSpec]:
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
	# The hall owns the shared band. Bay-side caps must stop at its bay face,
	# rather than compete with its differently lit, coplanar corridor face.
	if open_east_wall: wall_along_x.x -= WALL_THICKNESS
	var side_center_x := -WALL_THICKNESS / 2.0 if open_east_wall else 0.0
	var wall_along_z := Vector3(WALL_THICKNESS, Pods.ROOM_CEILING_HEIGHT, Pods.ROOM_WIDTH)
	var mid_height := Pods.ROOM_CEILING_HEIGHT / 2.0
	return _shell_roles([
		ShipGeometry.SolidSpec.new(Vector3(0.0, -WALL_THICKNESS / 2.0, 0.0), slab),
		ShipGeometry.SolidSpec.new(
			Vector3(0.0, Pods.ROOM_CEILING_HEIGHT + WALL_THICKNESS / 2.0, 0.0),
			slab
		),
		ShipGeometry.SolidSpec.new(
			Vector3(side_center_x, mid_height, -(Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0)),
			wall_along_x
		),
		ShipGeometry.SolidSpec.new(
			Vector3(side_center_x, mid_height, Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0),
			wall_along_x
		),
		ShipGeometry.SolidSpec.new(
			Vector3(-(Pods.ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0), mid_height, 0.0),
			wall_along_z
		),
		ShipGeometry.SolidSpec.new(
			Vector3(Pods.ROOM_LENGTH / 2.0 + WALL_THICKNESS / 2.0, mid_height, 0.0),
			wall_along_z
		),
	], ShipLayout.BAY_ID, [&"PORT", &"STARBOARD", &"FORE", &"AFT"])

static func hatch_solids() -> Array[ShipGeometry.SolidSpec]:
	var post := Vector3(FRAME_DEPTH, HATCH_HEIGHT + FRAME_POST_WIDTH, FRAME_POST_WIDTH)
	var lintel := Vector3(FRAME_DEPTH, FRAME_POST_WIDTH, HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH)
	var sill := Vector3(FRAME_DEPTH, SILL_HEIGHT, HATCH_WIDTH + 2.0 * FRAME_POST_WIDTH)
	var door_rotation := Quaternion(Vector3.UP, -HATCH_DOOR_AJAR)
	var door_group_origin := Vector3(HATCH_DOOR_X, 0.0, -(HATCH_WIDTH / 2.0 - DOOR_HINGE_INSET))
	var door_center: Vector3 = door_group_origin + door_rotation * Vector3(0.0, DOOR_HEIGHT / 2.0, DOOR_WIDTH / 2.0)
	return [
		ShipGeometry.SolidSpec.new(
			Vector3(
				HATCH_FRAME_X,
				(HATCH_HEIGHT + FRAME_POST_WIDTH) / 2.0,
				-(HATCH_WIDTH + FRAME_POST_WIDTH) / 2.0
			),
			post
		),
		ShipGeometry.SolidSpec.new(
			Vector3(
				HATCH_FRAME_X,
				(HATCH_HEIGHT + FRAME_POST_WIDTH) / 2.0,
				(HATCH_WIDTH + FRAME_POST_WIDTH) / 2.0
			),
			post
		),
		ShipGeometry.SolidSpec.new(
			Vector3(HATCH_FRAME_X, HATCH_HEIGHT + FRAME_POST_WIDTH / 2.0, 0.0),
			lintel
		),
		ShipGeometry.SolidSpec.new(Vector3(HATCH_FRAME_X, SILL_HEIGHT / 2.0, 0.0), sill),
		ShipGeometry.SolidSpec.new(
			door_center,
			Vector3(DOOR_THICKNESS, DOOR_HEIGHT, DOOR_WIDTH),
			door_rotation
		),
	]

static func pod_world_transform(placement: Pods.PodPlacement) -> Array:
	return [
		Quaternion(Vector3.UP, placement.yaw_radians),
		Vector3(placement.center.x, 0.0, placement.center.y),
	]

static func doorway_wall_solids(layout: ShipLayout = ShipLayout.authored().layout) -> Array[ShipGeometry.SolidSpec]:
	return _section_portal_solids(layout, layout.section(&"D14-S-041"), layout.door(ShipLayout.BAY_DOOR_ID))

static func doorway_block(layout: ShipLayout = ShipLayout.authored().layout) -> ShipGeometry.SolidSpec:
	return door_blockers(layout.door(ShipLayout.BAY_DOOR_ID))[0]

static func power_doorway_wall_solids(layout: ShipLayout = ShipLayout.authored().layout) -> Array[ShipGeometry.SolidSpec]:
	return _section_portal_solids(layout, layout.section(&"D14-S-041"), layout.door(ShipLayout.POWER_DOOR_ID))

## Preserve the opening's ordered shell adapter over the shared section recipe.
static func hallway_solids(layout: ShipLayout = ShipLayout.authored().layout) -> Array[ShipGeometry.SolidSpec]:
	var solids: Array[SolidSpec] = []
	for solid: SolidSpec in section_solids(layout, layout.section(&"D14-S-041")):
		if solid.material_role != &"door":
			solids.append(solid)
	return solids

static func side_door_solids(layout: ShipLayout = ShipLayout.authored().layout) -> Array[ShipGeometry.SolidSpec]:
	return _section_side_leaves(layout, layout.section(&"D14-S-041"))

static func power_room_solids() -> Array[ShipGeometry.SolidSpec]:
	var mid_height := ROOM_CEILING / 2.0
	var slab_x_center := (ROOM_START_X - WALL + ROOM_END_X + WALL) / 2.0
	var slab_x_size := (ROOM_END_X + WALL) - (ROOM_START_X - WALL)
	var slab_z_center := (ROOM_START_Z + ROOM_END_Z - WALL) / 2.0
	var slab_z_size := (ROOM_START_Z - ROOM_END_Z) + 2.0 * WALL
	return _shell_roles([
		ShipGeometry.SolidSpec.new(
			Vector3(slab_x_center, -WALL / 2.0, slab_z_center),
			Vector3(slab_x_size, WALL, slab_z_size)
		),
		ShipGeometry.SolidSpec.new(
			Vector3(slab_x_center, ROOM_CEILING + WALL / 2.0, slab_z_center),
			Vector3(slab_x_size, WALL, slab_z_size)
		),
		ShipGeometry.SolidSpec.new(
			Vector3(ROOM_START_X - WALL / 2.0, mid_height, slab_z_center),
			Vector3(WALL, ROOM_CEILING, slab_z_size)
		),
		ShipGeometry.SolidSpec.new(
			Vector3(ROOM_END_X + WALL / 2.0, mid_height, slab_z_center),
			Vector3(WALL, ROOM_CEILING, slab_z_size)
		),
		ShipGeometry.SolidSpec.new(
			Vector3(slab_x_center, mid_height, ROOM_END_Z - WALL / 2.0),
			Vector3(slab_x_size, ROOM_CEILING, WALL)
		),
	], ShipLayout.POWER_ID, [&"FORE", &"AFT", &"PORT"])

static func power_door_leaf() -> ShipGeometry.SolidSpec:
	return SlidingDoorParts.leaf_solid(ShipLayout.authored().layout.door(ShipLayout.POWER_DOOR_ID))

static func console_stations() -> Array[ConsoleStation]:
	var positions := ShipLayout.power_console_positions()
	var yaws := ShipLayout.power_console_yaws()
	var healths: Array[int] = [0, 2, 1, 0, 1, 0]
	var stations: Array[ConsoleStation] = []
	for index: int in range(positions.size()):
		stations.append(ConsoleStation.make(positions[index], yaws[index], healths[index]))
	return stations

static func console_act_center() -> Vector3:
	var station := console_stations()[1]
	return station.position + Vector3(sin(station.yaw), 0.0, cos(station.yaw)) * 1.05

static func door_act_center() -> Vector3:
	return Vector3(
		ShipGeometry.POWER_DOOR_X,
		0.0,
		-(ShipGeometry.HALL_WIDTH / 2.0) + 0.6
	)

static func console_solid(station: ConsoleStation) -> ShipGeometry.SolidSpec:
	var facing := Vector3(sin(station.yaw), 0.0, cos(station.yaw))
	var along := Vector3(facing.z, 0.0, -facing.x)
	var local_size := Vector3(1.25, 1.75, 0.56)
	var center := station.position + facing * 0.28
	return ShipGeometry.SolidSpec.new(
		Vector3(center.x, 0.875, center.z),
		Vector3(
			absf(along.x) * local_size.x + absf(facing.x) * local_size.z,
			local_size.y,
			absf(along.z) * local_size.x + absf(facing.z) * local_size.z
		)
	)

static func generator_solid() -> ShipGeometry.SolidSpec:
	return ShipGeometry.SolidSpec.new(
		Vector3(
			GENERATOR_CENTER.x,
			GENERATOR_HEIGHT / 2.0,
			GENERATOR_CENTER.z
		),
		Vector3(
			GENERATOR_RADIUS * 2.0,
			GENERATOR_HEIGHT,
			GENERATOR_RADIUS * 2.0
		)
	)


## Transform the original eight corners, never an already-expanded AABB.
static func box_aabb(solid: SolidSpec, parent: Transform3D = Transform3D.IDENTITY) -> ColliderSet.Aabb:
	var half := solid.size * 0.5
	var lo := Vector3(INF, INF, INF)
	var hi := Vector3(-INF, -INF, -INF)
	for x: float in [-1.0, 1.0]:
		for y: float in [-1.0, 1.0]:
			for z: float in [-1.0, 1.0]:
				var corner := parent * solid.corner(Vector3(x, y, z) * half)
				lo = lo.min(corner)
				hi = hi.max(corner)
	var result := ColliderSet.Aabb.from_min_max(lo, hi)
	assert(result.is_ok(), "authored solid derives a valid AABB: %s" % solid.id)
	return result.box

## One conservative box per reservation. Sectioned collars retain exact Y/Z
## contact planes; the floor skin remains below standing capsule clearance.
static func collision_boxes(solid: SolidSpec) -> Array[ColliderSet.Aabb]:
	if solid.collision_role == &"frame_detail": return []
	if String(solid.id).ends_with("/STEP/000"):
		# The collar and lower ring already cover the raised step's walk band.
		# Its single additional box covers only the floor skin, never an early ledge.
		var box := box_aabb(solid)
		var center := box.center()
		var half := box.half_extents()
		center.y = solid._parent.origin.y + HATCH_FLOOR_SKIN_HEIGHT / 2
		half.y = HATCH_FLOOR_SKIN_HEIGHT / 2
		return [ColliderSet.Aabb.from_parts(center, half)]
	if solid.hatch_profile != null:
		var boxes: Array[ColliderSet.Aabb] = [box_aabb(solid)]
		boxes.append_array(solid.wall_corner_boxes)
		return boxes
	if solid.section.is_empty(): return [box_aabb(solid)]
	assert(not solid.collision_outline.is_empty(), "sectioned hatch has its outer collision boundary")
	var minimum := -solid.size / 2
	var maximum := solid.size / 2
	for y: float in [minimum.y, maximum.y]:
		var span := Vector2(INF, -INF)
		for edge: int in range(solid.collision_outline.size()):
			var a := solid.collision_outline[edge]
			var b := solid.collision_outline[(edge + 1) % solid.collision_outline.size()]
			if y < minf(a.y, b.y) - 0.000001 or y > maxf(a.y, b.y) + 0.000001: continue
			if absf(b.y - a.y) < 0.0000001:
				span.x = minf(span.x, minf(a.x, b.x))
				span.y = maxf(span.y, maxf(a.x, b.x))
			else:
				var x := lerpf(a.x, b.x, clampf((y - a.y) / (b.y - a.y), 0, 1))
				span.x = minf(span.x, x)
				span.y = maxf(span.y, x)
		minimum.x = maxf(minimum.x, span.x)
		maximum.x = minf(maximum.x, span.y)
	assert(maximum.x > minimum.x, "inscribed hatch collision has positive width: " + String(solid.id))
	var cell := SolidSpec.new(solid._local_center + solid._local_rotation * ((minimum + maximum) / 2), maximum - minimum, solid._local_rotation)
	cell._parent = solid._parent
	return [box_aabb(cell)]

static func transformed(solid: SolidSpec, frame: Transform3D, id: StringName = &"") -> SolidSpec:
	var placed := SolidSpec.new(solid._local_center, solid.size, solid._local_rotation, solid.id if id == &"" else id, solid.material_role, solid.collision_role)
	placed._parent = frame * solid._parent
	placed.hatch_profile = solid.hatch_profile
	placed.section = solid.section
	placed.collision_outline = solid.collision_outline
	placed.wall_corner_boxes = solid.wall_corner_boxes
	placed.wall_seat_section = solid.wall_seat_section
	if solid.surface_owner != &"": placed.surface_identity(solid.surface_owner, solid.surface_part)
	return placed

## The wall's local X interval, pierced once, with +Z wall-band depth.
static func portal_wall(owner: StringName, frame: Transform3D, interval: Vector2, height: float, aperture: Vector2) -> Array[SolidSpec]:
	assert(interval.x < -aperture.x / 2 and interval.y > aperture.x / 2 and height > aperture.y, "portal fits inside its wall")
	var half_width := aperture.x / 2.0
	var west := -half_width - interval.x
	var east := interval.y - half_width
	var pieces: Array[SolidSpec] = [
		SolidSpec.new(Vector3(interval.x + west / 2, height / 2, WALL / 2), Vector3(west, height, WALL)),
		SolidSpec.new(Vector3(half_width + east / 2, height / 2, WALL / 2), Vector3(east, height, WALL)),
		SolidSpec.new(Vector3(0, (height + aperture.y) / 2, WALL / 2), Vector3(aperture.x, height - aperture.y, WALL)),
	]
	var placed: Array[SolidSpec] = []
	for index: int in range(pieces.size()):
		var piece := transformed(pieces[index], frame, StringName("%s/%03d" % [owner, index]))
		# Quantize the world centre once, not once locally and again at the
		# parent offset. The latter moves a wall boundary by a native ULP.
		var x := interval.x + west / 2 if index == 0 else (half_width + east / 2 if index == 1 else 0.0)
		var y := height / 2 if index < 2 else (height + aperture.y) / 2
		var coordinates: Array[float] = [x, y, WALL / 2]
		var centre := Vector3.ZERO
		for axis: int in range(3):
			var coordinate: float = frame.origin[axis]
			for column: int in range(3): coordinate += frame.basis[column][axis] * coordinates[column]
			centre[axis] = coordinate
		piece._parent = Transform3D(frame.basis, centre)
		piece._local_center = Vector3.ZERO
		if index < 2:
			# Anchor the outer wall edge after the native-precision world transform.
			var edge := interval.x if index == 0 else interval.y
			var anchor := frame * Vector3(edge, height / 2, WALL / 2)
			piece.size.x = absf((piece.center - anchor).dot(frame.basis.x)) * 2
		placed.append(piece)
	return placed

static func section_solids(layout: ShipLayout, section: ShipLayout.SectionSpec) -> Array[SolidSpec]:
	var solids: Array[SolidSpec] = []
	var bounds := section.bounds()
	var slab_bounds := bounds
	var portals: Dictionary = {}
	for id: StringName in section.opening_ids():
		var door := layout.door(id)
		if door.kind() in [ShipLayout.DoorKind.BAY, ShipLayout.DoorKind.POWER]:
			var side := -1 if door.frame().basis.z.z < 0 else 1
			assert(not portals.has(side), "one room portal per section wall")
			portals[side] = door
			# The opening floor bridges the room wall band at its aft edge.
			slab_bounds.size.x = bounds.size.x + WALL
			slab_bounds.position.z = bounds.position.z - WALL
			slab_bounds.size.z = bounds.size.z + 2 * WALL
	_add_slabs(solids, section.id(), slab_bounds)
	for side: int in [-1, 1]:
		if portals.has(side):
			solids.append_array(_section_portal_solids(layout, section, portals[side]))
		else:
			var owner := StringName("%s/%s/000" % [section.id(), "PORT" if side < 0 else "STARBOARD"])
			solids.append(SolidSpec.new(Vector3(bounds.get_center().x, bounds.get_center().y, bounds.get_center().z + side * (bounds.size.z + WALL) / 2), Vector3(bounds.size.x, bounds.size.y, WALL), Quaternion.IDENTITY, owner))
	solids.append_array(_section_side_leaves(layout, section))
	return solids

static func _section_portal_solids(layout: ShipLayout, section: ShipLayout.SectionSpec, door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var bounds := section.bounds()
	var frame := door.frame()
	var aperture := door.aperture()
	if door.animation() == ShipLayout.AnimationRecipe.HINGE:
		# The narrow front ring owns the 1.2 m mouth. Its hidden wall pocket
		# clears the thicker slab's offset-axis sweep without widening that mouth.
		aperture.x += 2 * HATCH_RING_WIDTH
	if door.kind() == ShipLayout.DoorKind.BAY:
		var walls := portal_wall(StringName("%s/STARBOARD" % section.id()), frame, Vector2(bounds.position.x - frame.origin.x, bounds.end.x + WALL - frame.origin.x), ShipLayout.CLEAR_HEIGHT, aperture)
		_profile_hatch_walls(walls, door, Vector2(bounds.position.x - frame.origin.x, bounds.end.x + WALL - frame.origin.x), ShipLayout.CLEAR_HEIGHT)
		return walls
	var end := bounds.end.x + WALL
	if door.kind() == ShipLayout.DoorKind.POWER:
		end = layout.power_room().bounds().end.x + WALL
	var west := frame.origin.x - aperture.x / 2 - bounds.position.x
	var east := end - (frame.origin.x + aperture.x / 2)
	assert(west > 0 and east > 0 and bounds.size.y > aperture.y, "section portal fits its wall")
	var z := frame.origin.z + frame.basis.z.z * WALL / 2
	var y := frame.origin.y + bounds.size.y / 2
	var owner := "%s/%s" % [section.id(), "PORT" if frame.basis.z.z < 0 else "STARBOARD"]
	return [
		SolidSpec.new(Vector3(bounds.position.x + west / 2, y, z), Vector3(west, bounds.size.y, WALL), Quaternion.IDENTITY, StringName(owner + "/000")),
		SolidSpec.new(Vector3(end - east / 2, y, z), Vector3(east, bounds.size.y, WALL), Quaternion.IDENTITY, StringName(owner + "/001")),
		SolidSpec.new(Vector3(frame.origin.x, frame.origin.y + (aperture.y + bounds.size.y) / 2, z), Vector3(aperture.x, bounds.size.y - aperture.y, WALL), Quaternion.IDENTITY, StringName(owner + "/002")),
	]

static func _section_side_leaves(layout: ShipLayout, section: ShipLayout.SectionSpec) -> Array[SolidSpec]:
	var solids: Array[SolidSpec] = []
	var ids := section.side_door_ids()
	ids.sort_custom(func(a: StringName, b: StringName) -> bool: return String(a) < String(b))
	for id: StringName in ids:
		solids.append(side_door_leaf(layout.door(id)))
	return solids

static func side_door_leaf(door: ShipLayout.DoorSpec) -> SolidSpec:
	return SlidingDoorParts.leaf_solid(door)

static func connector_solids(layout: ShipLayout, connector: ShipLayout.ConnectorSpec) -> Array[SolidSpec]:
	var solids: Array[SolidSpec] = []
	var bounds := connector.bounds()
	var id := connector.id()
	_add_slabs(solids, id, bounds)
	var port := connector.port_opening()
	port.basis = Basis(Vector3(-1, 0, 0), Vector3.UP, Vector3(0, 0, -1))
	var start := bounds.position.x
	if connector.deck_number() == 14 and connector.pitch_index() == 1:
		start = layout.power_room().bounds().end.x + WALL
	solids.append_array(portal_wall(StringName("%s/PORT" % id), port, Vector2(port.origin.x - bounds.end.x, port.origin.x - start), bounds.size.y, layout.well(connector.well_id()).doorway_size()))
	var lift := layout.lift(connector.lift_id())
	var door := layout.door(lift.door_id())
	solids.append_array(portal_wall(StringName("%s/STARBOARD" % id), door.frame(), Vector2(bounds.position.x - door.frame().origin.x, bounds.end.x - door.frame().origin.x), bounds.size.y, door.aperture()))
	var well := layout.well(connector.well_id())
	var landing := well.landing_bounds(connector.deck_number())
	_add_slabs(solids, StringName("%s/LANDING" % id), landing)
	var shaft := well.bounds()
	for side: int in [-1, 1]:
		var x := shaft.position.x - WALL / 2 if side < 0 else shaft.end.x + WALL / 2
		solids.append(SolidSpec.new(Vector3(x, bounds.get_center().y, (shaft.position.z + bounds.position.z - WALL) / 2), Vector3(WALL, bounds.size.y, bounds.position.z - WALL - shaft.position.z), Quaternion.IDENTITY, StringName("%s/LANDING/%s/000" % [id, "PORT" if side < 0 else "STARBOARD"])))
	solids.append(SolidSpec.new(Vector3(shaft.get_center().x, bounds.get_center().y, shaft.position.z - WALL / 2), Vector3(shaft.size.x + 2 * WALL, bounds.size.y, WALL), Quaternion.IDENTITY, StringName("%s/LANDING/BACK/000" % id)))
	var shell := lift.bounds()
	for side: int in [-1, 1]:
		solids.append(SolidSpec.new(Vector3(shell.get_center().x + side * (shell.size.x + WALL) / 2, shell.get_center().y, shell.get_center().z), Vector3(WALL, shell.size.y, shell.size.z), Quaternion.IDENTITY, StringName("%s/SIDE-%d/000" % [lift.id(), side])))
	solids.append(SolidSpec.new(Vector3(shell.get_center().x, shell.get_center().y, shell.end.z + WALL / 2), Vector3(shell.size.x, shell.size.y, WALL), Quaternion.IDENTITY, StringName("%s/BACK/000" % lift.id())))
	_add_slabs(solids, lift.id(), shell)
	return solids

static func hatch_frame_solids(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var aperture := door.aperture()
	var hinge := door.hinge_frame().origin
	var minimum_depth := minf(-0.06, hinge.z)
	var depth := maxf(WALL + 0.06, hinge.z) - minimum_depth
	var center_depth := minimum_depth + depth / 2
	var solids: Array[SolidSpec] = []
	# The flush bead owns the rounded corners. Vertical supports stop at its
	# tangencies, retaining positive inscribed boxes inside the narrower outline.
	var post_bottom := SILL_HEIGHT + (aperture.x - SILL_WALK_WIDTH) / 2
	var post_height := aperture.y - HATCH_CORNER_RADIUS - post_bottom
	var post_y := post_bottom + post_height / 2
	for side: int in [-1, 1]:
		var minimum := Vector3(-aperture.x / 2 - FRAME_POST_WIDTH, post_bottom, 0)
		var size := Vector3(FRAME_POST_WIDTH - 0.06, post_height, WALL)
		if side > 0:
			# Carry the latch jamb out to the offset closed leaf, without filling its swing.
			minimum.x = aperture.x / 2 + HATCH_RING_WIDTH - 0.03
			minimum.z = minimum_depth
			size.x = aperture.x / 2 + FRAME_POST_WIDTH - minimum.x
			size.z = depth
		solids.append(transformed(SolidSpec.new(minimum + size / 2, size, Quaternion.IDENTITY, StringName("%s/FRAME/%s" % [door.id(), "LEFT" if side < 0 else "RIGHT"]), &"frame"), door.frame()))
	var lintel_height := hatch_lintel_height(door)
	# Like the posts, the crown stops at the curve tangencies. Extending a
	# rectangular return into the bead's arcs creates near-flat clipped wedges.
	var crown_width := aperture.x + 0.01 - 2 * HATCH_CORNER_RADIUS
	solids.append(transformed(SolidSpec.new(Vector3(0, aperture.y + lintel_height / 2, center_depth), Vector3(crown_width, lintel_height, depth), Quaternion.IDENTITY, StringName("%s/FRAME/TOP" % door.id()), &"frame"), door.frame()))
	# Preserve oblique lower-corner sealing on both faces as the hinge moves
	# forward. The footplate spans the mouth; the bead owns its curved feet.
	# Neither its depth nor width changes the 80 mm walking height.
	var coaming_depth := maxf(depth, 0.40)
	solids.append(transformed(SolidSpec.new(Vector3(0, SILL_HEIGHT / 2, WALL / 2), Vector3(aperture.x, SILL_HEIGHT, coaming_depth), Quaternion.IDENTITY, StringName("%s/COAMING" % door.id()), &"frame"), door.frame()))
	var stop_depth := 0.03125
	var stop_width := 0.125
	var into := signf(hinge.z - WALL / 2)
	var stop_z := hinge.z - into * (HatchParts.APPROACH_SLAB_DEPTH + stop_depth / 2)
	var edge := hinge.x + HatchParts.HINGE_OUTSET + door.leaf_aperture().x
	var lap := HatchParts.SEAL_LAP / 8
	var cross_width := door.leaf_aperture().x - HatchParts.HINGE_RETURN_WIDTH
	var cross_x := hinge.x + HatchParts.HINGE_OUTSET + HatchParts.HINGE_RETURN_WIDTH + cross_width / 2
	var hinge_stop_z := stop_z
	var stops: Array[SolidSpec] = [
		SolidSpec.new(Vector3(hinge.x - stop_width / 2 - 0.001, post_y, hinge_stop_z), Vector3(stop_width, post_height, stop_depth), Quaternion.IDENTITY, StringName("%s/FRAME/STOP-LEFT" % door.id()), &"frame"),
		SolidSpec.new(Vector3(edge + (stop_width - lap) / 2, post_y, stop_z), Vector3(stop_width + lap, post_height, stop_depth), Quaternion.IDENTITY, StringName("%s/FRAME/STOP-RIGHT" % door.id()), &"frame"),
		SolidSpec.new(Vector3(0, aperture.y + (stop_width - lap) / 2, stop_z), Vector3(crown_width, stop_width + lap, stop_depth), Quaternion.IDENTITY, StringName("%s/FRAME/STOP-TOP" % door.id()), &"frame"),
		SolidSpec.new(Vector3(cross_x, (SILL_HEIGHT - lap) / 2, stop_z), Vector3(cross_width, SILL_HEIGHT + lap, stop_depth), Quaternion.IDENTITY, StringName("%s/FRAME/STOP-BOTTOM" % door.id()), &"frame"),
	]
	for stop: SolidSpec in stops: solids.append(transformed(stop, door.frame()))
	# All fixed returns remain inside the raised bead's outer silhouette.
	for solid: SolidSpec in solids: _clip_hatch_frame(door, solid)
	solids.append_array(hatch_surround_solids(door))
	var outer := hatch_ring_outline(door, HATCH_RING_WIDTH)
	var center_y := (aperture.y + SILL_HEIGHT) / 2
	for solid: SolidSpec in solids:
		var parent := Transform3D(door.frame().basis.inverse() * solid._parent.basis, Vector3(0, 0, WALL if "/SURROUND/AFT/" in String(solid.id) else 0.0))
		var inverse := (parent * Transform3D(Basis(solid._local_rotation), solid._local_center)).affine_inverse()
		for point: Vector2 in outer:
			var local := inverse * Vector3(point.x, point.y + center_y, 0)
			solid.collision_outline.append(Vector2(local.x, local.y))
	solids.append_array(hatch_fixed_hardware(door))
	return solids

static func hatch_fixed_hardware(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var hinge := door.hinge_frame().origin
	var into := signf(hinge.z - WALL / 2)
	var front := HATCH_RING_FRONT if into > 0 else WALL - HATCH_RING_FRONT
	var solids: Array[SolidSpec] = []
	for index: int in range(HatchParts.HINGE_HEIGHTS.size()):
		var y := HatchParts.HINGE_HEIGHTS[index] + HatchParts.HINGE_STACK_SHIFTS[index]
		# Both stationary knuckles carry the barrel into one bolted frame leaf.
		# Only their bridges cross the depth gap; the moving barrel stays free.
		var plate := HatchParts.FRAME_LEAF_SIZE
		var plate_center := Vector3(hinge.x - plate.x / 2, y + HatchParts.BARREL_OFFSET, front - into * (plate.z / 2 - 0.002))
		solids.append(SolidSpec.new(plate_center, plate, Quaternion.IDENTITY, StringName("%s/HINGE/PLATE-%d" % [door.id(), index]), &"frame", &"frame_detail"))
		for upper: bool in [false, true]:
			var zone := "UPPER" if upper else "LOWER"
			var center := Vector3(hinge.x, y + HatchParts.fixed_knuckle_offset(upper), hinge.z)
			var length := HatchParts.FIXED_KNUCKLE_LENGTH
			var diameter := HatchParts.FIXED_KNUCKLE_RADIUS * 2
			var seat := hinge.z - into * HatchParts.FIXED_KNUCKLE_RADIUS / 2
			var minimum := Vector3(hinge.x - plate.x, center.y - length / 2, minf(front, seat))
			var maximum := Vector3(hinge.x, center.y + length / 2, maxf(front, seat))
			solids.append(SolidSpec.new((minimum + maximum) / 2, maximum - minimum, Quaternion.IDENTITY, StringName("%s/HINGE/BRIDGE-%s-%d" % [door.id(), zone, index]), &"frame", &"frame_detail"))
			solids.append(SolidSpec.new(center, Vector3(diameter, length, diameter), Quaternion.IDENTITY, StringName("%s/HINGE/KNUCKLE-%s-%d" % [door.id(), zone, index]), &"frame", &"frame_detail"))
			var cap := center + Vector3.UP * (1 if upper else -1) * (length + HatchParts.PIN_CAP_LENGTH) / 2
			solids.append(SolidSpec.new(cap, Vector3(diameter, HatchParts.PIN_CAP_LENGTH, diameter), Quaternion.IDENTITY, StringName("%s/HINGE/CAP-%s-%d" % [door.id(), zone, index]), &"frame", &"frame_detail"))
			for bolt: int in range(3):
				# The upper crown tapers the leaf; seat its bolt heads in the
				# remaining ring width, without moving or widening that ring.
				var bolt_x := hinge.x - 0.014 if index == 1 else plate_center.x
				var point := Vector3(bolt_x, center.y + (bolt - 1) * 0.025, front - into * (plate.z - 0.002 + 0.004))
				solids.append(SolidSpec.new(point, Vector3(0.018, 0.008, 0.018), Quaternion(Vector3.UP, Vector3(0, 0, -into)), StringName("%s/HINGE/BOLT-%s-%d-%d" % [door.id(), zone, bolt, index]), &"frame", &"frame_detail"))
	var edge := hinge.x + HatchParts.HINGE_OUTSET + door.leaf_aperture().x
	for index: int in range(HatchParts.DOG_HEIGHTS.size()):
		solids.append(SolidSpec.new(Vector3(edge + 0.04, HatchParts.DOG_HEIGHTS[index], front - into * 0.02), Vector3(0.08, 0.16, 0.04), Quaternion.IDENTITY, StringName("%s/KEEPER/%d" % [door.id(), index]), &"frame", &"frame_detail"))
	var placed: Array[SolidSpec] = []
	for solid: SolidSpec in solids:
		# Plates and bridges follow the ring silhouette. Keep the circular
		# hardware's exact axial bounds and its coaxial pivot registration.
		var circular := "/HINGE/KNUCKLE-" in String(solid.id) or "/HINGE/CAP-" in String(solid.id) or "/HINGE/BOLT-" in String(solid.id)
		if not circular: _clip_hatch_frame(door, solid)
		solid.surface_identity(door.id(), &"FRAME")
		placed.append(transformed(solid, door.frame()))
	return placed

static func _clip_hatch_frame(door: ShipLayout.DoorSpec, solid: SolidSpec) -> void:
	var outer := hatch_ring_outline(door, HATCH_RING_WIDTH)
	var center_y := (door.aperture().y + SILL_HEIGHT) / 2
	for index: int in range(outer.size()): outer[index].y += center_y
	var center := Vector2(solid._local_center.x, solid._local_center.y)
	var half := Vector2(solid.size.x, solid.size.y) / 2
	var rectangle := PackedVector2Array([center - half, center + Vector2(half.x, -half.y), center + half, center + Vector2(-half.x, half.y)])
	var clipped := Geometry2D.intersect_polygons(rectangle, outer)
	assert(clipped.size() == 1 and clipped[0].size() >= 3, "fixed collar intersects the ring outline")
	var polygon: PackedVector2Array = clipped[0]
	# Integer-grid clipping may move a boundary by a few micrometres. Never
	# raise the authored coaming or expand a collar outside its reservation.
	for index: int in range(polygon.size()): polygon[index] = polygon[index].clamp(center - half, center + half)
	var lo := polygon[0]
	var hi := lo
	for point: Vector2 in polygon:
		lo = lo.min(point)
		hi = hi.max(point)
	center = (lo + hi) / 2
	solid._local_center.x = center.x
	solid._local_center.y = center.y
	solid.size.x = hi.x - lo.x
	solid.size.y = hi.y - lo.y
	for point: Vector2 in polygon: solid.section.append(point - center)

static func hatch_frame_vertex(door: ShipLayout.DoorSpec, solid: SolidSpec, vertex: Vector3) -> Vector3:
	# Cut the wall-side underside back into the shared collision envelope.
	# A horizontal return is black under ceiling-only direct lighting.
	var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
	if String(solid.id).ends_with("/STEP/000") and vertex.z > 0:
		vertex.z = 0.27 - solid._local_center.z
	if String(solid.id).ends_with("/FRAME/STOP-TOP") and vertex.z * into < 0 and vertex.y < 0:
		vertex.y += solid.size.y - HatchParts.SEAL_DEPTH
	if String(solid.id).ends_with("/FRAME/TOP"):
		if vertex.z * into < 0 and vertex.y < 0:
			vertex.y += solid.size.y - HatchParts.SEAL_DEPTH
		if vertex.z * into > 0 and vertex.y > 0:
			vertex.y -= solid.size.y - HatchParts.SEAL_DEPTH
	if vertex.z * into < 0 and String(solid.id).ends_with("/FRAME/RIGHT") and vertex.x < 0:
		vertex.x += solid.size.x - HatchParts.SEAL_DEPTH
	var xy := Vector2(vertex.x, vertex.y)
	if not solid.section.is_empty() and not Geometry2D.is_point_in_polygon(xy, solid.section):
		var nearest := Vector2.INF
		for index: int in range(solid.section.size()):
			var point := Geometry2D.get_closest_point_to_segment(xy, solid.section[index], solid.section[(index + 1) % solid.section.size()])
			if point.distance_squared_to(xy) < nearest.distance_squared_to(xy): nearest = point
		vertex.x = nearest.x
		vertex.y = nearest.y
	return vertex

static func hatch_lintel_height(door: ShipLayout.DoorSpec) -> float:
	var hinge := door.hinge_frame().origin.z
	var depth := maxf(WALL + 0.06, hinge) - minf(-0.06, hinge)
	return maxf(FRAME_POST_WIDTH, depth * 0.75)

static func hatch_wall_vertex(solid: SolidSpec, vertex: Vector3) -> Vector3:
	if solid.hatch_profile == null or not String(solid.id).ends_with("/002") or vertex.y >= 0: return vertex
	var door := solid.hatch_profile
	var relative := door.frame().affine_inverse() * solid.transform
	var point := relative * vertex
	var hinge := door.hinge_frame().origin.z
	var wall_end := minf(-0.06, hinge) if hinge > WALL / 2 else maxf(WALL + 0.06, hinge)
	var fraction := clampf((hinge - point.z) / (hinge - wall_end), 0, 1)
	point.y = door.aperture().y + (hatch_lintel_height(door) - HatchParts.SEAL_DEPTH) * fraction
	return relative.affine_inverse() * point

static func hatch_wall_solids(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var pocket := door.aperture() + Vector2(2 * HATCH_RING_WIDTH, 0)
	var walls := portal_wall(StringName("%s/WALL" % door.id()), door.frame(), Vector2(-ShipLayout.CORRIDOR_WIDTH / 2, ShipLayout.CORRIDOR_WIDTH / 2), ShipLayout.CLEAR_HEIGHT, pocket)
	_profile_hatch_walls(walls, door, Vector2(-ShipLayout.CORRIDOR_WIDTH / 2, ShipLayout.CORRIDOR_WIDTH / 2), ShipLayout.CLEAR_HEIGHT)
	return walls

static func _profile_hatch_walls(walls: Array[SolidSpec], door: ShipLayout.DoorSpec, interval: Vector2, height: float) -> void:
	var contour := hatch_ring_outline(door, HATCH_RING_WIDTH - HATCH_POCKET_SEATING_LAP)
	var center_y := (door.aperture().y + SILL_HEIGHT) / 2
	var crown := -INF
	for index: int in range(contour.size()):
		contour[index].y += center_y
		crown = maxf(crown, contour[index].y)
	# Three continuous wall faces replace the rectangular face and its four
	# patches. The narrow seating lap is hidden under the bead's rear edge.
	var regions: Array[PackedVector2Array] = [
		PackedVector2Array([Vector2(interval.x, 0), Vector2(0, 0), Vector2(0, crown), Vector2(interval.x, crown)]),
		PackedVector2Array([Vector2(0, 0), Vector2(interval.y, 0), Vector2(interval.y, crown), Vector2(0, crown)]),
		PackedVector2Array([Vector2(interval.x, crown), Vector2(interval.y, crown), Vector2(interval.y, height), Vector2(interval.x, height)]),
	]
	var seat := hatch_ring_outline(door)
	for index: int in range(seat.size()): seat[index].y += center_y
	for index: int in range(walls.size()):
		var wall := walls[index]
		wall.hatch_profile = door
		var inverse := (door.frame().affine_inverse() * wall.transform).affine_inverse()
		# The far mouth closes the wall behind the ring's inner opening.
		# Oblique views through hinge clearances must still meet the wall.
		for boundary: PackedVector2Array in [contour, seat]:
			var polygons: Array[PackedVector2Array] = []
			if index < 2: polygons = Geometry2D.clip_polygons(regions[index], boundary)
			else: polygons.append(regions[index])
			assert(polygons.size() == 1, "one continuous face per hatch wall piece")
			var section := PackedVector2Array()
			for point: Vector2 in polygons[0]:
				var local := inverse * Vector3(point.x, point.y, WALL / 2)
				section.append(Vector2(local.x, local.y))
			if wall.section.is_empty(): wall.section = section
			else: wall.wall_seat_section = section
	# Retain the old conservative contact reservations independently of the
	# drawn face. Removing presentation patches must not change player physics.
	walls[2].wall_corner_boxes = _hatch_corner_collision_boxes(door)

static func _hatch_corner_collision_boxes(door: ShipLayout.DoorSpec) -> Array[ColliderSet.Aabb]:
	var aperture := door.aperture()
	var half_width := aperture.x / 2 + HATCH_RING_WIDTH
	var center_y := (aperture.y + SILL_HEIGHT) / 2
	var mouth := hatch_ring_outline(door)
	# Lap by the bead's depth beneath its rounded rear edge. Touching only
	# its outer silhouette leaves cracks where the bead profile narrows.
	var contour := hatch_ring_outline(door, HATCH_RING_WIDTH - HATCH_POCKET_SEATING_LAP)
	for index: int in range(contour.size()): contour[index].y += center_y
	var corners: Array[PackedVector2Array] = []
	for upper: bool in [false, true]:
		var bottom := mouth[0].y + center_y if upper else 0.0
		var top := aperture.y if upper else mouth[mouth.size() / 2].y + center_y
		# Straight posts seal the middle; the coaming seals the lower walk
		# band. Keep the four new reservations outside those existing solids.
		var inner_x := 0.0 if upper else SILL_WALK_WIDTH / 2
		for side: int in [-1, 1]:
			var left := -half_width if side < 0 else inner_x
			var right := -inner_x if side < 0 else half_width
			var rectangle := PackedVector2Array([Vector2(left, bottom), Vector2(right, bottom), Vector2(right, top), Vector2(left, top)])
			corners.append_array(Geometry2D.clip_polygons(rectangle, contour))
	assert(corners.size() == 4, "four existing corner collision reservations")
	var into := signf(door.hinge_frame().origin.z - WALL / 2)
	var front := HATCH_RING_REAR if into > 0 else WALL
	var rear := 0.0 if into > 0 else WALL - HATCH_RING_REAR
	var boxes: Array[ColliderSet.Aabb] = []
	for polygon: PackedVector2Array in corners:
		var lo := polygon[0]
		var hi := lo
		for point: Vector2 in polygon:
			lo = lo.min(point)
			hi = hi.max(point)
		var center := (lo + hi) / 2
		var reservation := SolidSpec.new(Vector3(center.x, center.y, (front + rear) / 2), Vector3(hi.x - lo.x, hi.y - lo.y, rear - front))
		boxes.append(box_aabb(transformed(reservation, door.frame())))
	return boxes

static func d14_extension_solids(layout: ShipLayout) -> Array[SolidSpec]:
	var solids: Array[SolidSpec] = []
	for id: StringName in layout.deck(14).section_ids():
		if layout.section(id).number() != 41:
			solids.append_array(section_solids(layout, layout.section(id)))
	for id: StringName in layout.deck(14).connector_ids():
		solids.append_array(connector_solids(layout, layout.connector(id)))
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.deck_number() == 14 and door.kind() == ShipLayout.DoorKind.HATCH:
			solids.append_array(hatch_wall_solids(door))
			solids.append_array(hatch_frame_solids(door))
	return solids

## Full-height shaft shell; deck floors and ceilings remain landing-only.
static func well_solids(well: ShipLayout.LadderWellSpec) -> Array[SolidSpec]:
	var bounds := well.bounds()
	var shaft_end := well.landing_bounds(well.top_deck()).position.z
	var depth := shaft_end - bounds.position.z
	var solids: Array[SolidSpec] = []
	for side: int in [-1, 1]:
		var x := bounds.position.x - WALL / 2 if side < 0 else bounds.end.x + WALL / 2
		solids.append(SolidSpec.new(Vector3(x, bounds.get_center().y, bounds.position.z + depth / 2), Vector3(WALL, bounds.size.y, depth), Quaternion.IDENTITY, StringName("%s/%s" % [well.id(), "LEFT" if side < 0 else "RIGHT"])))
	solids.append(SolidSpec.new(Vector3(bounds.get_center().x, bounds.get_center().y, bounds.position.z - WALL / 2), Vector3(bounds.size.x + 2 * WALL, bounds.size.y, WALL), Quaternion.IDENTITY, StringName("%s/BACK" % well.id())))
	for top: bool in [false, true]:
		var y := bounds.end.y + WALL / 2 if top else bounds.position.y - WALL / 2
		solids.append(SolidSpec.new(Vector3(bounds.get_center().x, y, bounds.position.z + depth / 2), Vector3(bounds.size.x, WALL, depth), Quaternion.IDENTITY, StringName("%s/%s" % [well.id(), "TOP" if top else "BOTTOM"]), &"ceiling" if top else &"floor"))
	return solids

static func deck_static_solids(layout: ShipLayout, deck: int) -> Array[SolidSpec]:
	if deck == 14:
		return opening_scene_solids(layout.bay().template(), true, true, layout, {}, false)
	var solids: Array[SolidSpec] = []
	for id: StringName in layout.deck(deck).connector_ids():
		solids.append_array(connector_solids(layout, layout.connector(id)))
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.deck_number() == deck and door.kind() == ShipLayout.DoorKind.HATCH:
			solids.append_array(hatch_wall_solids(door))
			solids.append_array(hatch_frame_solids(door))
	solids.sort_custom(func(a: SolidSpec, b: SolidSpec) -> bool: return String(a.id) < String(b.id))
	return solids

static func _add_slabs(solids: Array[SolidSpec], owner: StringName, bounds: AABB) -> void:
	for ceiling: bool in [false, true]:
		var y := bounds.end.y + WALL / 2 if ceiling else bounds.position.y - WALL / 2
		solids.append(SolidSpec.new(Vector3(bounds.get_center().x, y, bounds.get_center().z), Vector3(bounds.size.x, WALL, bounds.size.z), Quaternion.IDENTITY, StringName("%s/%s/000" % [owner, "CEILING" if ceiling else "FLOOR"]), &"ceiling" if ceiling else &"floor"))

static func door_blockers(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var bounds := door.closed_blocker()
	var solid := SolidSpec.new(bounds.get_center(), bounds.size, Quaternion.IDENTITY, StringName("%s/BLOCKER" % door.id()), &"door", &"door_blocker")
	var solids: Array[SolidSpec] = [transformed(solid, door.frame())]
	if door.animation() == ShipLayout.AnimationRecipe.HINGE:
		var swept := AABB()
		var samples := 1 if door.policy() == ShipLayout.Policy.NEVER_OPENS else 131
		for degree: int in range(samples):
			var hinge := door.hinge_frame()
			hinge.basis = Basis(Vector3.UP, signf(door.swing_radians()) * deg_to_rad(degree))
			var swept_pose := hinge * hatch_leaf_bounds(door)
			swept = swept_pose if degree == 0 else swept.merge(swept_pose)
		# Enclose the continuous extrema between the one-degree samples.
		swept = swept.grow(0.001)
		var envelope := SolidSpec.new(swept.get_center(), swept.size, Quaternion.IDENTITY, StringName("%s/SWING" % door.id()), &"door", &"door_sweep")
		solids.append(transformed(envelope, door.frame()))
	return solids

static var _leaf_bounds: Dictionary = {}

## Retain the movement reservation, enclosing every shared physical part.
static func hatch_leaf_bounds(door: ShipLayout.DoorSpec) -> AABB:
	var aperture := door.leaf_aperture()
	var key := [aperture, signf(door.hinge_frame().origin.z - WALL / 2)]
	if _leaf_bounds.has(key): return _leaf_bounds[key]
	var bounds := AABB(Vector3(-0.12, 0.09, -0.23), Vector3(aperture.x + 0.20, door.aperture().y - 0.06, 0.46))
	for group: HatchParts.Group in HatchParts.leaf(door):
		for part: HatchParts.Part in group.parts:
			bounds = bounds.merge(HatchParts.part_bounds(part, group.transform * part.transform))
	_leaf_bounds[key] = bounds
	return bounds

class SightBox:
	extends RefCounted
	var id: StringName
	var local_transform: Transform3D
	var bounds: AABB
	var inverse: Transform3D
	func _init(part: HatchParts.Part, group: Transform3D, leaf: Transform3D) -> void:
		id = part.id
		local_transform = group * part.transform
		bounds = AABB(-part.size / 2, part.size)
		inverse = (leaf * local_transform).affine_inverse()

## Sight keeps physical pieces oriented, excluding reserved motion volumes.
static func hatch_sight_boxes(door: ShipLayout.DoorSpec, angle: float, wheel_degrees: float = 0.0) -> Array[SightBox]:
	var hinge := door.hinge_frame()
	hinge.basis = Basis(Vector3.UP, angle)
	var frame := door.frame() * hinge
	var boxes: Array[SightBox] = []
	for group: HatchParts.Group in HatchParts.leaf(door):
		var pose := group.transform
		if group.path in [NodePath("Wheel"), NodePath("ReverseWheel")]:
			pose.basis *= Basis(Vector3.BACK, deg_to_rad(wheel_degrees) * (1 if group.side == 0 else -1))
		for part: HatchParts.Part in group.parts:
			boxes.append(SightBox.new(part, pose, frame))
	return boxes

static func open_door_solids(door: ShipLayout.DoorSpec, run_seed: int = 0) -> Array[SolidSpec]:
	if door.animation() != ShipLayout.AnimationRecipe.HINGE:
		return []
	var hinge := door.hinge_frame()
	hinge.basis = Basis(Vector3.UP, door.swing_radians(run_seed))
	# Transform each physical part before enclosing it. Rotating a whole-leaf
	# box combines unrelated hardware extrema and blocks the clear walking lane.
	var bounds := AABB()
	var first := true
	for group: HatchParts.Group in HatchParts.leaf(door):
		for part: HatchParts.Part in group.parts:
			var placed := HatchParts.part_bounds(part, door.frame() * hinge * group.transform * part.transform)
			bounds = placed if first else bounds.merge(placed)
			first = false
	return [SolidSpec.new(bounds.get_center(), bounds.size, Quaternion.IDENTITY, StringName("%s/PARKED" % door.id()), &"door", &"parked_leaf")]

static func _shell_roles(solids: Array[SolidSpec], owner: StringName, walls: Array[StringName]) -> Array[SolidSpec]:
	solids[0].material_role = &"floor"
	solids[1].material_role = &"ceiling"
	var parts: Array[StringName] = [&"FLOOR", &"CEILING"]
	parts.append_array(walls)
	for index: int in range(solids.size()): solids[index].surface_identity(owner, parts[index])
	return solids

static func opening_hall_solids(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout, include_blockers: bool = true, run_seed: int = 0) -> Array[ShipGeometry.SolidSpec]:
	var solids: Array[ShipGeometry.SolidSpec] = []
	var frame := layout.bay_to_world()
	var shell := ShipGeometry.room_shell(true)
	for index: int in range(shell.size()):
		if index != ShipGeometry.ROOM_SHELL_EAST_WALL_INDEX:
			solids.append(ShipGeometry.transformed(shell[index], frame, StringName("D14-BAY/SHELL/%03d" % index)))
	var bay_door := layout.door(ShipLayout.BAY_DOOR_ID)
	if include_blockers and not door_open:
		solids.append(door_blockers(bay_door)[0])
	for pod: Pods.Pod in registry.pods():
		var pod_frame := ShipGeometry.pod_world_transform(pod.placement())
		var pieces := PodGeometry.pod_solids(pod.state())
		for index: int in range(pieces.size()):
			var piece: PodGeometry.PodSolid = pieces[index]
			var rotation: Quaternion = pod_frame[0] * Quaternion(Vector3.RIGHT, piece.roll_radians)
			var center: Vector3 = pod_frame[0] * piece.center + pod_frame[1]
			solids.append(ShipGeometry.transformed(ShipGeometry.SolidSpec.new(center, piece.size, rotation), frame, StringName("D14-BAY/POD-%03d/%03d" % [pod.id().index(), index])))
	solids.append_array(hatch_frame_solids(bay_door))
	if include_blockers:
		solids.append_array(open_door_solids(bay_door, run_seed) if door_open else [door_blockers(bay_door)[1]])
	_named_solids(solids, ShipGeometry.hallway_solids(layout), "D14-S-041/SHELL")
	_named_solids(solids, ShipGeometry.side_door_solids(layout), "D14-S-041/SIDE-LEAF")
	return solids

static func opening_scene_solids(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout, open_ids: Dictionary = {}, include_blockers: bool = true, run_seed: int = 0) -> Array[ShipGeometry.SolidSpec]:
	var solids := opening_hall_solids(registry, door_open, layout, include_blockers, run_seed)
	_named_solids(solids, ShipGeometry.power_room_solids(), "D14-POWER/SHELL")
	var stations := ShipGeometry.console_stations()
	for index: int in range(stations.size()):
		var solid := ShipGeometry.console_solid(stations[index])
		solid.id = StringName("D14-POWER/CONSOLE/%03d" % index)
		solids.append(solid)
	var generator := ShipGeometry.generator_solid()
	generator.id = &"D14-POWER/GENERATOR"
	solids.append(generator)
	if not power_door_open:
		var leaf := ShipGeometry.power_door_leaf()
		leaf.id = &"D14-POWER-DOOR/LEAF"
		solids.append(leaf)
	solids.append_array(ShipGeometry.d14_extension_solids(layout))
	if include_blockers:
		for id: StringName in layout.door_ids():
			var door := layout.door(id)
			if door.deck_number() == 14 and door.kind() in [ShipLayout.DoorKind.HATCH, ShipLayout.DoorKind.LIFT]:
				solids.append_array(ShipGeometry.open_door_solids(door, run_seed) if open_ids.has(id) else ShipGeometry.door_blockers(door))
	return solids

static func _named_solids(target: Array[ShipGeometry.SolidSpec], pieces: Array[ShipGeometry.SolidSpec], owner: String) -> void:
	for index: int in range(pieces.size()):
		pieces[index].id = StringName("%s/%03d" % [owner, index])
		target.append(pieces[index])

static func _hatch_inner_outline(aperture: Vector2, clearance: float, radius: float) -> PackedVector2Array:
	var size := Vector2(aperture.x + clearance, aperture.y - SILL_HEIGHT)
	var points := HatchParts.outline(size, radius)
	# Keep the lower arcs outside the walk band instead of flattening their
	# vertices into sharp joins that cannot carry a constant-width offset.
	var lower_radius := (size.x - SILL_WALK_WIDTH) / 2 - 0.005
	assert(lower_radius > 0 and lower_radius <= radius, "lower hatch returns fit outside the walk band")
	var lower := HatchParts.outline(size, lower_radius)
	for index: int in range(points.size() / 2, points.size()):
		points[index] = lower[index]
	return points

static func _hatch_offset_outline(inner: PackedVector2Array, offset: float) -> PackedVector2Array:
	var outer := PackedVector2Array()
	for index: int in range(inner.size()):
		var incoming := (inner[index] - inner[(index + inner.size() - 1) % inner.size()]).normalized()
		var outgoing := (inner[(index + 1) % inner.size()] - inner[index]).normalized()
		var previous_normal := Vector2(incoming.y, -incoming.x)
		var next_normal := Vector2(outgoing.y, -outgoing.x)
		# Intersect adjacent parallel edge offsets, retaining their correspondence
		# for convex ring cells rather than rounding two rectangles separately.
		outer.append(inner[index] + (previous_normal + next_normal) * offset / (1 + previous_normal.dot(next_normal)))
	return outer

static func _hatch_ring_outline(aperture: Vector2, offset: float) -> PackedVector2Array:
	return _hatch_offset_outline(_hatch_inner_outline(aperture, 0.01, HATCH_CORNER_RADIUS), offset)

## Centered XY; portal placement adds (aperture.y + SILL_HEIGHT) / 2 to Y.
static func hatch_ring_outline(door: ShipLayout.DoorSpec, offset: float = 0.0) -> PackedVector2Array:
	return _hatch_ring_outline(door.aperture(), offset)

## Portal-local XY including center Y, Z=0; cylinder axes point along +Z.
static func hatch_frame_rivet_stations(aperture: Vector2) -> Array[Transform3D]:
	var contour := _hatch_ring_outline(aperture, HATCH_RING_WIDTH / 2)
	var perimeter := 0.0
	for index: int in range(contour.size()):
		perimeter += contour[index].distance_to(contour[(index + 1) % contour.size()])
	var count := roundi(perimeter / HATCH_RIVET_PITCH)
	var pitch := perimeter / count
	var stations: Array[Transform3D] = []
	var edge := 0
	var edge_start := 0.0
	var edge_length := contour[0].distance_to(contour[1])
	var center_y := (aperture.y + SILL_HEIGHT) / 2
	for index: int in range(count):
		var distance := index * pitch
		while distance > edge_start + edge_length:
			edge_start += edge_length
			edge += 1
			edge_length = contour[edge].distance_to(contour[(edge + 1) % contour.size()])
		var point := contour[edge].lerp(contour[(edge + 1) % contour.size()], (distance - edge_start) / edge_length)
		stations.append(Transform3D(Basis(Vector3.RIGHT, PI / 2), Vector3(point.x, point.y + center_y, 0)))
	return stations

static func hatch_seating_outline(door: ShipLayout.DoorSpec) -> PackedVector2Array:
	var opening := hatch_ring_outline(door)
	var seating := _hatch_offset_outline(opening, -HatchParts.SEAL_LAP)
	var walk_edge := SILL_WALK_WIDTH / 2 + 0.005
	var lower_radius := (door.aperture().x + 0.01) / 2 - walk_edge
	# Inset the lower flanks horizontally, tapering to zero at the walk
	# tangencies. A normal offset here would raise the 80 mm threshold.
	for index: int in range(opening.size() / 2, opening.size()):
		var fraction := clampf((absf(opening[index].x) - walk_edge) / lower_radius, 0, 1)
		seating[index] = Vector2(opening[index].x - signf(opening[index].x) * HatchParts.SEAL_LAP * fraction, opening[index].y)
	return seating

static func hatch_surround_solids(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	var solids: Array[SolidSpec] = []
	var aperture := door.aperture()
	var center_y := (aperture.y + SILL_HEIGHT) / 2
	var into := signf(door.hinge_frame().origin.z - WALL / 2)
	for side: int in [0 if into > 0 else 1]:
		var face := Transform3D.IDENTITY if side == 0 else Transform3D(Basis(Vector3.RIGHT, Vector3.UP, Vector3.FORWARD), Vector3(0, 0, WALL))
		var owner := "%s/SURROUND/%s" % [door.id(), "FORE" if side == 0 else "AFT"]
		var ring := hatch_ring_outline(door)
		var opening := ring
		var seating := hatch_seating_outline(door)
		_annulus(solids, owner + "/RING", door.frame() * face, ring, hatch_ring_outline(door, HATCH_RING_WIDTH), center_y, HATCH_RING_FRONT, HATCH_RING_REAR)
		# The stationary rear lip laps the rounded leaf, including its corners.
		_annulus(solids, owner + "/LIP", door.frame() * face, seating, _hatch_offset_outline(opening, 0.035), center_y, HATCH_RING_REAR, -0.004)
		if (side == 0 and into > 0) or (side == 1 and into < 0):
			_annulus(solids, owner + "/THROAT", door.frame() * face, opening, _hatch_offset_outline(opening, 0.05), center_y, -0.004, -0.002, WALL / 2 + absf(door.hinge_frame().origin.z - WALL / 2) - Vector2(HatchParts.HINGE_RETURN_WIDTH, WALL / 2).length() - 0.001)
		var bridge_rear := WALL + absf(door.hinge_frame().origin.z - WALL / 2) + HatchParts.SEAL_LAP
		var steps: Array[SolidSpec] = [
			SolidSpec.new(Vector3(0, SILL_HEIGHT / 2, (-0.098 + bridge_rear) / 2), Vector3(SILL_WALK_WIDTH, SILL_HEIGHT, bridge_rear + 0.098)),
		]
		for index: int in range(steps.size()):
			var step := transformed(steps[index], door.frame() * face, StringName("%s/STEP/%03d" % [owner, index]))
			step.material_role = &"sill"
			step.surface_identity(door.id(), &"COAMING")
			solids.append(step)
	return solids

## Floor skin attached to the step mesh, supported by the structural floor.
## Its 1 mm lap is below capsule clearance but above TriangleMesh welding precision.
static func hatch_floor_bridge(step: SolidSpec) -> SolidSpec:
	var bridge := SolidSpec.new(Vector3(0, HATCH_FLOOR_SKIN_HEIGHT / 2, step._local_center.z), Vector3(SILL_WALK_WIDTH, HATCH_FLOOR_SKIN_HEIGHT, step.size.z))
	bridge._parent = step._parent
	return bridge

static func _annulus(solids: Array[SolidSpec], owner: String, frame: Transform3D, inner: PackedVector2Array, outer: PackedVector2Array, center_y: float, front: float, rear: float, hinge_rear: float = INF) -> void:
	for index: int in range(inner.size()):
		var next := (index + 1) % inner.size()
		var points := PackedVector2Array([inner[index], inner[next], outer[next], outer[index]])
		var lo := points[0]
		var hi := lo
		for point: Vector2 in points:
			lo = lo.min(point)
			hi = hi.max(point)
		var center := (lo + hi) / 2
		# One reveal depth for the whole annulus: a depth chosen per side steps at the arch.
		var cell_rear := minf(rear, hinge_rear)
		var cell := SolidSpec.new(Vector3(center.x, center.y + center_y, (front + cell_rear) / 2), Vector3(hi.x - lo.x, hi.y - lo.y, cell_rear - front), Quaternion.IDENTITY, StringName("%s/%03d" % [owner, index]), &"frame")
		for point: Vector2 in points: cell.section.append(point - center)
		cell.surface_identity(StringName(owner.get_slice("/", 0)), &"FRAME")
		solids.append(transformed(cell, frame))
