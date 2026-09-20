class_name Hallway
extends Node3D
## The hallway behind the stasis room's door (issue #59's prerequisite
## milestone): the door now opens on act into a straight crew corridor
## running out from the doorway — double the stasis room's length, the
## pod bay's aisle width, the room's ceiling height. Closed side doors
## read crew passage (the last door on the right is the future
## emergency-power room entrance), a red domed pushbutton on the far
## wall lights the hall's red emergency fixtures — dark until the flip,
## with no blackout trick: the fixtures simply hold level zero. Surfaces
## wear the stasis room's shared surface materials and the ceiling
## carries the same damage dressing language; no smoke anywhere in this
## subtree. The hallway's colliders extend the walk sim's set from
## solids authored here (Placement stays untouched): one construction
## path — the scene spawns these placements verbatim and the collider
## set derives from the same data.

## The corridor's interior length along +X: double the stasis room's
## length, per the milestone's envelope brief.
const HALL_LENGTH: float = Pods.ROOM_LENGTH * 2.0

## The corridor's interior width: the pod bay's authored aisle width
## carried through the doorway, so the walk sim's comfortable band
## continues without a pinch.
const HALL_WIDTH: float = Pods.AISLE_HALF_WIDTH * 2.0

## The corridor starts at the room's +X wall inner face and runs to
## HALL_END_X; the ceiling matches the room's height language exactly.
const HALL_START_X: float = Pods.ROOM_LENGTH / 2.0
const HALL_END_X: float = HALL_START_X + HALL_LENGTH
const HALL_CEILING_HEIGHT: float = Pods.ROOM_CEILING_HEIGHT
const WALL: float = Placement.WALL_THICKNESS

## The doorway pierces the room's +X wall with the hatch opening's
## exact width and height, so the frame's opening and the wall's hole
## are one aperture.
const DOORWAY_WIDTH: float = Placement.HATCH_WIDTH
const DOORWAY_HEIGHT: float = Placement.HATCH_HEIGHT

## The room shell's +X wall index, the one wall this module's doorway
## replaces in both the render and the collider set.
const ROOM_SHELL_EAST_WALL_INDEX: int = 5

## Closed side doors: one-meter leaves at six-meter pitch — a berth
## block every six meters reads crew passage, not arcade corridor.
const SIDE_DOOR_WIDTH: float = 1.0
const SIDE_DOOR_HEIGHT: float = 2.2
const SIDE_DOOR_THICKNESS: float = 0.06
const SIDE_DOOR_STATIONS_X: Array[float] = [9.0, 15.0, 21.0]
## The future emergency-power room entrance (issue #59 proper): the
## last door on the right walking out of the stasis room — the north
## (-Z) wall. Closed and non-interactive this milestone.
const POWER_DOOR_X: float = 27.0

## The switch plate on the far wall, centered on the corridor axis at
## working height: a small dark plate with a domed red pushbutton, the
## fuel-stop pattern. No emission — before the flip it is invisible in
## the dark by nature of the darkness.
const SWITCH_PLATE_SIZE: Vector3 = Vector3(0.04, 0.24, 0.16)
const SWITCH_PLATE_CENTER: Vector3 = Vector3(
	HALL_END_X - SWITCH_PLATE_SIZE.x / 2.0, 1.25, 0.0)
const SWITCH_DOME_RADIUS: float = 0.055
const SWITCH_DOME_COLOR: Color = Color(0.55, 0.04, 0.03)
const SWITCH_PLATE_SHADE: float = 0.16

## The hallway's fixtures hold the stasis bay's exact style and levels:
## pairs over each side-door station plus one over the far wall above
## the switch, mirroring the stasis bay's lintel-over-door fixture.
const FIXTURE_STATIONS_X: Array[float] = SIDE_DOOR_STATIONS_X

const SIDE_DOOR_SHADE: float = Hatch.HATCH_DOOR_SHADE

static var _box_cache: Dictionary = {}

var _game: Game = null
var _fade: Intensity.FixtureFade = null
var _lights: Array[OmniLight3D] = []
var _lenses: Array[MeshInstance3D] = []
var _lens_mesh: BoxMesh = null
var _lens_material: StandardMaterial3D = null
var _remainder: float = 0.0

## The pierced +X wall: the original wall slab's envelope with the
## doorway aperture removed — two side pieces and a lintel, all
## axis-aligned in the wall's band.
static func doorway_wall_solids() -> Array[Placement.SolidPlacement]:
	var east_wall_center_x := HALL_START_X + WALL / 2.0
	var mid_height := HALL_CEILING_HEIGHT / 2.0
	var side_length: float = (Pods.ROOM_WIDTH - DOORWAY_WIDTH) / 2.0
	var side_offset: float = DOORWAY_WIDTH / 2.0 + side_length / 2.0
	return [
		Placement.SolidPlacement.new(
			Vector3(east_wall_center_x, mid_height, -side_offset),
			Vector3(WALL, HALL_CEILING_HEIGHT, side_length)
		),
		Placement.SolidPlacement.new(
			Vector3(east_wall_center_x, mid_height, side_offset),
			Vector3(WALL, HALL_CEILING_HEIGHT, side_length)
		),
		Placement.SolidPlacement.new(
			Vector3(
				east_wall_center_x,
				(DOORWAY_HEIGHT + HALL_CEILING_HEIGHT) / 2.0,
				0.0
			),
			Vector3(WALL, HALL_CEILING_HEIGHT - DOORWAY_HEIGHT, DOORWAY_WIDTH)
		),
	]

## The doorway's closed blocker: fills the aperture exactly while the
## door is shut, dropped from the collider set the tick the opening
## animation completes.
static func doorway_block() -> Placement.SolidPlacement:
	return Placement.SolidPlacement.new(
		Vector3(HALL_START_X + WALL / 2.0, DOORWAY_HEIGHT / 2.0, 0.0),
		Vector3(WALL, DOORWAY_HEIGHT, DOORWAY_WIDTH)
	)

## The corridor's shell in fixed order: floor, ceiling, the north and
## south side walls, and the far wall carrying the switch. The floor
## and ceiling slabs tuck under the room's wall band so the doorway
## tunnel shows no seam.
static func hallway_solids() -> Array[Placement.SolidPlacement]:
	var slab_x_size := (HALL_END_X + WALL) - HALL_START_X
	var slab_x_center := (HALL_START_X + HALL_END_X + WALL) / 2.0
	var side_z := HALL_WIDTH / 2.0 + WALL / 2.0
	var slab_z := HALL_WIDTH + 2.0 * WALL
	var mid_height := HALL_CEILING_HEIGHT / 2.0
	return [
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, -WALL / 2.0, 0.0),
			Vector3(slab_x_size, WALL, slab_z)
		),
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, HALL_CEILING_HEIGHT + WALL / 2.0, 0.0),
			Vector3(slab_x_size, WALL, slab_z)
		),
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, mid_height, -side_z),
			Vector3(slab_x_size, HALL_CEILING_HEIGHT, WALL)
		),
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, mid_height, side_z),
			Vector3(slab_x_size, HALL_CEILING_HEIGHT, WALL)
		),
		Placement.SolidPlacement.new(
			Vector3(HALL_END_X + WALL / 2.0, mid_height, 0.0),
			Vector3(WALL, HALL_CEILING_HEIGHT, slab_z)
		),
	]

## The closed side doors, flush-mounted leaves proud of the side walls.
static func side_door_solids() -> Array[Placement.SolidPlacement]:
	var doors: Array[Placement.SolidPlacement] = []
	for station_x: float in SIDE_DOOR_STATIONS_X:
		for side: float in [-1.0, 1.0]:
			doors.append(_side_door(station_x, side))
	doors.append(_side_door(POWER_DOOR_X, -1.0))
	return doors

static func _side_door(station_x: float, side: float) -> Placement.SolidPlacement:
	return Placement.SolidPlacement.new(
		Vector3(
			station_x,
			SIDE_DOOR_HEIGHT / 2.0,
			side * (HALL_WIDTH / 2.0 - SIDE_DOOR_THICKNESS / 2.0)
		),
		Vector3(SIDE_DOOR_WIDTH, SIDE_DOOR_HEIGHT, SIDE_DOOR_THICKNESS)
	)

## The switch's floor-plan act center: where the reach test measures.
static func switch_act_center() -> Vector3:
	return Vector3(SWITCH_PLATE_CENTER.x, 0.0, SWITCH_PLATE_CENTER.z)

## The whole static collider set with the hallway present: the room
## shell minus the pierced east wall, the doorway wall pieces, the
## doorway block while the door is shut, every pod's construction
## solids, the hatch frame (the ajar slab rides only while shut — once
## open it slides into the wall band behind the pierce pieces), and the
## hallway shell plus side doors. Mirrors Placement.scene_collider_set's
## insertion order so the boxes derive from the same construction path.
static func scene_collider_set(registry: Pods.PodRegistry, door_open: bool) -> ColliderSet:
	var set := ColliderSet.new()
	var shell := Placement.room_shell()
	assert(
		shell[ROOM_SHELL_EAST_WALL_INDEX].center.x > 0.0,
		"the east wall's authored shell index holds"
	)
	for index: int in range(shell.size()):
		if index == ROOM_SHELL_EAST_WALL_INDEX:
			continue
		_insert_placement(set, shell[index])
	for placement: Placement.SolidPlacement in doorway_wall_solids():
		_insert_placement(set, placement)
	if not door_open:
		_insert_placement(set, doorway_block())
	for pod: Pods.Pod in registry.pods():
		var frame := Placement.pod_world_transform(pod.placement())
		for solid: PodBody.PodSolid in PodBody.pod_solids(pod.state()):
			_insert_pod_solid(set, solid, frame[0], frame[1])
	var hatch := Placement.hatch_solids()
	for index: int in range(Hatch.HATCH_FRAME_PIECES):
		_insert_placement(set, hatch[index])
	if not door_open:
		_insert_placement(set, hatch[Hatch.HATCH_FRAME_PIECES])
	for placement: Placement.SolidPlacement in hallway_solids():
		_insert_placement(set, placement)
	for placement: Placement.SolidPlacement in side_door_solids():
		_insert_placement(set, placement)
	return set

## Insert one world-frame placement as a collider box: the conservative
## corner-hull AABB, mirroring Placement's derivation.
static func _insert_placement(set: ColliderSet, placement: Placement.SolidPlacement) -> void:
	_insert_box(set, placement.center, placement.size, placement.rotation)

## Insert one pod-local construction solid through the pod group's world
## transform, mirroring Placement's derivation.
static func _insert_pod_solid(
	set: ColliderSet,
	solid: PodBody.PodSolid,
	group_rotation: Quaternion,
	group_translation: Vector3
) -> void:
	var rotation: Quaternion = group_rotation * Quaternion(Vector3.RIGHT, solid.roll_radians)
	var center: Vector3 = group_rotation * solid.center + group_translation
	_insert_box(set, center, solid.size, rotation)

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
	assert(result.is_ok(), "the frozen hallway placement data derives a valid collider box")
	set.insert(result.box)

static func build(game: Game) -> Hallway:
	var hallway := Hallway.new()
	hallway.name = "Hallway"
	hallway._game = game
	var level := 1.0 if game.hallway_lit else 0.0
	hallway._lens_mesh = BoxMesh.new()
	hallway._lens_mesh.size = Lighting.LENS_SIZE
	hallway._lens_material = StandardMaterial3D.new()
	hallway._lens_material.albedo_color = Lighting.LENS_BASE_COLOR
	hallway._lens_material.emission = Color(Lighting.FIXTURE_EMISSIVE * level, 0.0, 0.0)
	hallway._lens_material.roughness = 0.8
	hallway._lens_mesh.material = hallway._lens_material
	var held: Intensity.Result = Intensity.FixtureFade.holding(level)
	assert(held.is_ok(), "the hallway's level maps to a finite nonnegative fade")
	hallway._fade = held.fade

	var doorway := Node3D.new()
	doorway.name = "DoorwayWall"
	for placement: Placement.SolidPlacement in doorway_wall_solids():
		doorway.add_child(_surface_instance("wall", placement))
	hallway.add_child(doorway)

	var surface_names := ["HallFloor", "HallCeiling", "HallWallNorth", "HallWallSouth", "HallWallFar"]
	var surface_roles := ["floor", "ceiling", "wall", "wall", "wall"]
	var hall_solids := hallway_solids()
	for index: int in range(hall_solids.size()):
		var piece := _surface_instance(surface_roles[index], hall_solids[index])
		piece.name = surface_names[index]
		hallway.add_child(piece)

	hallway.add_child(_build_ceiling_damage())

	var doors := Node3D.new()
	doors.name = "HallSideDoors"
	var door_material := _flat_grey(SIDE_DOOR_SHADE)
	for placement: Placement.SolidPlacement in side_door_solids():
		doors.add_child(_box_instance(placement, door_material))
	hallway.add_child(doors)

	hallway.add_child(_build_switch())

	for fixture_transform: Transform3D in fixture_transforms():
		hallway.add_child(hallway._fixture(fixture_transform, level))
	return hallway

## The fixture group mirrors the stasis bay's: pairs at each side-door
## station standoff from both side walls, one above the far wall's
## switch like the bay's hatch-lintel fixture.
static func fixture_transforms() -> Array[Transform3D]:
	var transforms: Array[Transform3D] = []
	for station_x: float in FIXTURE_STATIONS_X:
		for side: float in [-1.0, 1.0]:
			transforms.append(Transform3D(
				Basis(),
				Vector3(
					station_x,
					Lighting.WALL_MOUNT_HEIGHT,
					side * (HALL_WIDTH / 2.0 - Lighting.WALL_STANDOFF)
				)
			))
	transforms.append(Transform3D(
		Basis(Vector3.UP, PI / 2.0),
		Vector3(
			HALL_END_X - Lighting.WALL_STANDOFF,
			Lighting.WALL_MOUNT_HEIGHT,
			0.0
		)
	))
	return transforms

## The fixture group holds the light and the lens as siblings, exactly
## as the stasis bay's do, so no mesh bounds stand in for the light's
## influence volume.
func _fixture(fixture_transform: Transform3D, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "HallFixture"
	fixture.transform = fixture_transform
	var light := OmniLight3D.new()
	light.light_color = Lighting.EMERGENCY_RED
	light.light_energy = Lighting.FIXTURE_ENERGY * level
	light.omni_range = Lighting.FIXTURE_RANGE
	light.shadow_enabled = false
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.mesh = _lens_mesh
	fixture.add_child(lens)
	_lights.append(light)
	_lenses.append(lens)
	return fixture

## The fuel-stop switch: small dark plate, domed red pushbutton. Plain
## albedo only — the dark hall hides it until the fixtures light.
static func _build_switch() -> Node3D:
	var group := Node3D.new()
	group.name = "HallSwitch"
	group.position = SWITCH_PLATE_CENTER
	var plate := MeshInstance3D.new()
	plate.name = "Plate"
	var plate_mesh := BoxMesh.new()
	plate_mesh.size = SWITCH_PLATE_SIZE
	plate.mesh = plate_mesh
	plate.material_override = _flat_grey(SWITCH_PLATE_SHADE)
	group.add_child(plate)
	var dome := MeshInstance3D.new()
	dome.name = "Dome"
	var dome_mesh := SphereMesh.new()
	dome_mesh.radius = SWITCH_DOME_RADIUS
	dome_mesh.height = SWITCH_DOME_RADIUS * 2.0
	dome.mesh = dome_mesh
	dome.position = Vector3(
		-SWITCH_PLATE_SIZE.x / 2.0 - SWITCH_DOME_RADIUS * 0.55, 0.0, 0.0)
	var dome_material := StandardMaterial3D.new()
	dome_material.albedo_color = SWITCH_DOME_COLOR
	dome_material.roughness = 0.35
	dome.material_override = dome_material
	group.add_child(dome)
	return group

## The hall's ceiling damage, in the stasis room's language: tray runs
## tipped off level, hanging wire loops beneath them. Dressing only —
## outside the walking envelope, deliberately not colliders.
static func _build_ceiling_damage() -> Node3D:
	var damage := Node3D.new()
	damage.name = "HallCeilingDamage"
	var tray_material := _flat_grey(RoomGeometry.TRAY_SHADE)
	var wire_material := _flat_grey(RoomGeometry.WIRE_SHADE)
	for placement: Placement.SolidPlacement in _ceiling_trays():
		damage.add_child(_box_instance(placement, tray_material))
	for loop: Placement.WireLoop in _ceiling_loops():
		var mesh := TorusMesh.new()
		mesh.inner_radius = Placement.WIRE_INNER_RADIUS
		mesh.outer_radius = Placement.WIRE_OUTER_RADIUS
		var wire := MeshInstance3D.new()
		wire.mesh = mesh
		wire.material_override = wire_material
		wire.position = loop.center
		wire.quaternion = loop.rotation
		damage.add_child(wire)
	return damage

## One long tray run down the corridor and one torn cross stub, tipped
## off level the way the stasis room's trays read.
static func _ceiling_trays() -> Array[Placement.SolidPlacement]:
	var drop := HALL_CEILING_HEIGHT - Placement.TRAY_CEILING_DROP
	return [
		Placement.SolidPlacement.new(
			Vector3(16.5, drop, 0.35),
			Vector3(9.0, Placement.TRAY_HEIGHT, Placement.TRAY_WIDTH),
			Quaternion(Vector3.UP, 0.0) * Quaternion(Vector3.RIGHT, 0.05)
		),
		Placement.SolidPlacement.new(
			Vector3(23.0, drop - 0.04, -0.55),
			Vector3(3.2, Placement.TRAY_HEIGHT, Placement.TRAY_WIDTH),
			Quaternion(Vector3.UP, PI / 2.0) * Quaternion(Vector3.RIGHT, -0.06)
		),
	]

## Two hanging wire loops under the tray run, at the stasis room's
## scale and above the camera-clearance floor.
static func _ceiling_loops() -> Array[Placement.WireLoop]:
	return [
		Placement.WireLoop.new(
			Vector3(13.6, 2.72, 0.42),
			Quaternion(Vector3.RIGHT, PI / 2.0) * Quaternion(Vector3.UP, 0.8)
		),
		Placement.WireLoop.new(
			Vector3(21.4, 2.66, -0.48),
			Quaternion(Vector3.RIGHT, PI / 2.0) * Quaternion(Vector3.UP, 2.1)
		),
	]

func _physics_process(_delta: float) -> void:
	process_frame(Sim.LOGICAL_TICK_SECS)

## One render-bridge frame, mirroring the stasis bay's Lighting bridge:
## retarget only on the sim-side target change (the switch flip), consume
## whole logical ticks from the elapsed seconds, then project the fade
## level onto the fixture energies and the shared lens emission. The
## sim's Game container is the only authority; this writes render state.
func process_frame(delta_secs: float) -> void:
	var target := 1.0 if _game.hallway_lit else 0.0
	if _fade.target() != target:
		_fade.retarget(target, Lighting.FIXTURE_SETTLE_TICKS)
	_remainder += delta_secs
	while _remainder >= Sim.LOGICAL_TICK_SECS:
		_remainder -= Sim.LOGICAL_TICK_SECS
		_fade.tick()
	_apply_level(_fade.intensity())

## Writes render state only, and only when a value actually changed: no
## per-tick material allocation.
func _apply_level(level: float) -> void:
	var energy: float = Lighting.FIXTURE_ENERGY * level
	for light: OmniLight3D in _lights:
		if light.light_energy != energy:
			light.light_energy = energy
	var emissive := Color(Lighting.FIXTURE_EMISSIVE * level, 0.0, 0.0)
	if _lens_material.emission != emissive:
		_lens_material.emission = emissive

func level() -> float:
	return _fade.intensity()

func is_settled() -> bool:
	return _fade.is_settled()

func lights() -> Array[OmniLight3D]:
	return _lights

func lenses() -> Array[MeshInstance3D]:
	return _lenses

func lens_material() -> StandardMaterial3D:
	return _lens_material

## One textured surface piece wearing the stasis room's shared material
## for its role — the same resource instance, never a copy.
static func _surface_instance(role: String, placement: Placement.SolidPlacement) -> MeshInstance3D:
	var material := RoomGeometry.wall_material()
	if role == "floor":
		material = RoomGeometry.floor_material()
	elif role == "ceiling":
		material = RoomGeometry.ceiling_material()
	return _box_instance(placement, material)

static func _box_instance(placement: Placement.SolidPlacement, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = _box_mesh(placement.size)
	instance.material_override = material
	instance.position = placement.center
	instance.quaternion = placement.rotation
	return instance

static func _box_mesh(size: Vector3) -> BoxMesh:
	if _box_cache.has(size):
		return _box_cache[size]
	var mesh := BoxMesh.new()
	mesh.size = size
	_box_cache[size] = mesh
	return mesh

static func _flat_grey(shade: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(shade, shade, shade)
	material.roughness = 0.95
	return material
