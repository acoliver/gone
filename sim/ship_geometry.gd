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
const GENERATOR_HEIGHT: float = 2.6

class SolidSpec:
	extends RefCounted
	var id: StringName
	var _local_center: Vector3
	var _local_rotation: Quaternion
	var _parent := Transform3D.IDENTITY
	var size: Vector3
	var material_role: StringName
	var collision_role: StringName
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

static func room_shell() -> Array[ShipGeometry.SolidSpec]:
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
	return _shell_roles([
		ShipGeometry.SolidSpec.new(Vector3(0.0, -WALL_THICKNESS / 2.0, 0.0), slab),
		ShipGeometry.SolidSpec.new(
			Vector3(0.0, Pods.ROOM_CEILING_HEIGHT + WALL_THICKNESS / 2.0, 0.0),
			slab
		),
		ShipGeometry.SolidSpec.new(
			Vector3(0.0, mid_height, -(Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0)),
			wall_along_x
		),
		ShipGeometry.SolidSpec.new(
			Vector3(0.0, mid_height, Pods.ROOM_WIDTH / 2.0 + WALL_THICKNESS / 2.0),
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
	])

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
	])

static func power_door_leaf() -> ShipGeometry.SolidSpec:
	return ShipGeometry.SolidSpec.new(
		Vector3(
			ShipGeometry.POWER_DOOR_X,
			SIDE_DOOR_HEIGHT / 2.0,
			-(ShipGeometry.HALL_WIDTH / 2.0 - SIDE_DOOR_THICKNESS / 2.0)
		),
		Vector3(SIDE_DOOR_WIDTH, SIDE_DOOR_HEIGHT, SIDE_DOOR_THICKNESS)
	)

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

static func transformed(solid: SolidSpec, frame: Transform3D, id: StringName = &"") -> SolidSpec:
	var placed := SolidSpec.new(solid._local_center, solid.size, solid._local_rotation, solid.id if id == &"" else id, solid.material_role, solid.collision_role)
	placed._parent = frame * solid._parent
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
		placed.append(transformed(pieces[index], frame, StringName("%s/%03d" % [owner, index])))
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
	if door.kind() == ShipLayout.DoorKind.BAY:
		return portal_wall(StringName("%s/STARBOARD" % section.id()), frame, Vector2(bounds.position.x - frame.origin.x, bounds.end.x + WALL - frame.origin.x), ShipLayout.CLEAR_HEIGHT, aperture)
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
	return transformed(SolidSpec.new(Vector3(0, door.aperture().y / 2, -SIDE_DOOR_THICKNESS / 2), Vector3(door.aperture().x, door.aperture().y, SIDE_DOOR_THICKNESS), Quaternion.IDENTITY, StringName("%s/LEAF" % door.id()), &"door"), door.frame())

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
	var solids: Array[SolidSpec] = []
	for side: int in [-1, 1]:
		solids.append(transformed(SolidSpec.new(Vector3(side * (aperture.x / 2 + FRAME_POST_WIDTH / 2), aperture.y / 2, WALL / 2), Vector3(FRAME_POST_WIDTH, aperture.y, WALL + 0.12), Quaternion.IDENTITY, StringName("%s/FRAME/%s" % [door.id(), "LEFT" if side < 0 else "RIGHT"]), &"frame"), door.frame()))
	solids.append(transformed(SolidSpec.new(Vector3(0, aperture.y + FRAME_POST_WIDTH / 2, WALL / 2), Vector3(aperture.x + 2 * FRAME_POST_WIDTH, FRAME_POST_WIDTH, WALL + 0.12), Quaternion.IDENTITY, StringName("%s/FRAME/TOP" % door.id()), &"frame"), door.frame()))
	solids.append(transformed(SolidSpec.new(Vector3(0, SILL_HEIGHT / 2, WALL / 2), Vector3(aperture.x + 2 * FRAME_POST_WIDTH, SILL_HEIGHT, WALL + 0.12), Quaternion.IDENTITY, StringName("%s/COAMING" % door.id()), &"frame"), door.frame()))
	return solids

static func hatch_wall_solids(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	return portal_wall(StringName("%s/WALL" % door.id()), door.frame(), Vector2(-ShipLayout.CORRIDOR_WIDTH / 2, ShipLayout.CORRIDOR_WIDTH / 2), ShipLayout.CLEAR_HEIGHT, door.aperture())

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
		var width := door.aperture().x
		var half_thickness := ShipLayout.WALL / 2.0
		var radius := sqrt(width * width + half_thickness * half_thickness)
		var into := 1.0 if door.swing_radians() < 0 else -1.0
		var minimum := Vector3(-width / 2.0 - half_thickness, 0, ShipLayout.WALL / 2.0 - (half_thickness if into > 0 else radius))
		var size := Vector3(width + half_thickness * 2.0, door.aperture().y, radius + half_thickness)
		var envelope := SolidSpec.new(minimum + size / 2.0, size, Quaternion.IDENTITY, StringName("%s/SWING" % door.id()), &"door", &"door_sweep")
		solids.append(transformed(envelope, door.frame()))
	return solids

static func open_door_solids(door: ShipLayout.DoorSpec) -> Array[SolidSpec]:
	if door.animation() != ShipLayout.AnimationRecipe.HINGE:
		return []
	var hinge := door.hinge_frame()
	hinge.basis = Basis(Vector3.UP, door.swing_radians())
	var leaf := SolidSpec.new(Vector3(door.aperture().x / 2.0, door.aperture().y / 2.0, 0), Vector3(door.aperture().x, door.aperture().y, ShipLayout.WALL), Quaternion.IDENTITY, StringName("%s/PARKED" % door.id()), &"door", &"parked_leaf")
	return [transformed(leaf, door.frame() * hinge)]

static func _shell_roles(solids: Array[SolidSpec]) -> Array[SolidSpec]:
	solids[0].material_role = &"floor"
	solids[1].material_role = &"ceiling"
	return solids

static func opening_hall_solids(registry: Pods.PodRegistry, door_open: bool, layout: ShipLayout) -> Array[ShipGeometry.SolidSpec]:
	var solids: Array[ShipGeometry.SolidSpec] = []
	var frame := layout.bay_to_world()
	var shell := ShipGeometry.room_shell()
	for index: int in range(shell.size()):
		if index != ShipGeometry.ROOM_SHELL_EAST_WALL_INDEX:
			solids.append(ShipGeometry.transformed(shell[index], frame, StringName("D14-BAY/SHELL/%03d" % index)))
	if not door_open:
		var block := ShipGeometry.doorway_block(layout)
		block.id = &"D14-BAY-DOOR/BLOCKER"
		solids.append(block)
	for pod: Pods.Pod in registry.pods():
		var pod_frame := ShipGeometry.pod_world_transform(pod.placement())
		var pieces := PodGeometry.pod_solids(pod.state())
		for index: int in range(pieces.size()):
			var piece: PodGeometry.PodSolid = pieces[index]
			var rotation: Quaternion = pod_frame[0] * Quaternion(Vector3.RIGHT, piece.roll_radians)
			var center: Vector3 = pod_frame[0] * piece.center + pod_frame[1]
			solids.append(ShipGeometry.transformed(ShipGeometry.SolidSpec.new(center, piece.size, rotation), frame, StringName("D14-BAY/POD-%03d/%03d" % [pod.id().index(), index])))
	var hatch := ShipGeometry.hatch_solids()
	for index: int in range(4):
		solids.append(ShipGeometry.transformed(hatch[index], frame, StringName("D14-BAY/FRAME/%03d" % index)))
	if not door_open:
		solids.append(ShipGeometry.transformed(hatch[4], frame, &"D14-BAY-DOOR/LEAF"))
	_named_solids(solids, ShipGeometry.hallway_solids(layout), "D14-S-041/SHELL")
	_named_solids(solids, ShipGeometry.side_door_solids(layout), "D14-S-041/SIDE-LEAF")
	return solids

static func opening_scene_solids(registry: Pods.PodRegistry, door_open: bool, power_door_open: bool, layout: ShipLayout, open_ids: Dictionary = {}, include_blockers: bool = true) -> Array[ShipGeometry.SolidSpec]:
	var solids := opening_hall_solids(registry, door_open, layout)
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
				solids.append_array(ShipGeometry.open_door_solids(door) if open_ids.has(id) else ShipGeometry.door_blockers(door))
	return solids

static func _named_solids(target: Array[ShipGeometry.SolidSpec], pieces: Array[ShipGeometry.SolidSpec], owner: String) -> void:
	for index: int in range(pieces.size()):
		pieces[index].id = StringName("%s/%03d" % [owner, index])
		target.append(pieces[index])
