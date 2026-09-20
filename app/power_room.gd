class_name PowerRoom
extends Node3D
## The emergency power room behind the hallway's last right-hand door
## (issue #59): the same footprint as the stasis room, pierced off the
## corridor's north wall at the power door. The room's consoles read
## futuristic-but-broken — flatscreens, blank colored-button keyboards,
## nothing mechanical — with exactly one working screen; the room's
## center holds the secondary generator, a sleek black column that
## looks inexplicably new next to the damaged walls (the stasis pods
## share that too-new quality; the reason is a later reveal). Under the
## emergency circuit the room reads red like the hall; actioning the
## working console twice (Inactivo → Activo) lights the generator and
## hands the hallway and this room over to dim regular white while the
## stasis bay keeps its red. Colliders extend the hallway's set from
## solids authored here (Placement stays untouched): one construction
## path — the scene spawns these placements verbatim and the collider
## set derives from the same data.

## The room's envelope mirrors the stasis room's exactly: the corridor
## supplies the south wall band (pierced at the power door), this room
## supplies the rest of the shell — the same wall thickness, ceiling,
## and tucked floor slabs as the hallway's construction language.
const WALL: float = Placement.WALL_THICKNESS
const ROOM_CENTER_X: float = Hallway.POWER_DOOR_X
const ROOM_START_Z: float = -(Hallway.HALL_WIDTH / 2.0 + WALL)
const ROOM_END_Z: float = ROOM_START_Z - Pods.ROOM_WIDTH
const ROOM_START_X: float = ROOM_CENTER_X - Pods.ROOM_LENGTH / 2.0
const ROOM_END_X: float = ROOM_CENTER_X + Pods.ROOM_LENGTH / 2.0
const ROOM_CEILING: float = Pods.ROOM_CEILING_HEIGHT

## The power door's leaf: the side doors' exact dimensions, proud of
## the corridor side of the wall band, sliding aside along the wall
## when it opens (the animation contract lives in PlayerMotion).
const DOOR_WIDTH: float = Hallway.SIDE_DOOR_WIDTH
const DOOR_HEIGHT: float = Hallway.SIDE_DOOR_HEIGHT
const DOOR_THICKNESS: float = Hallway.SIDE_DOOR_THICKNESS
const DOOR_SHADE: float = Hallway.SIDE_DOOR_SHADE

## Console station construction, all in the station's local frame (the
## origin at the wall's inner face, the panel facing +Z into the room):
## a wall spine, a flatscreen at working height, a keyboard shelf, and
## blank colored buttons — a 4x3 grid plus three wider function buttons
## off to the side. Nothing mechanical, no letters; the alien alphabet
## is a later milestone.
const CONSOLE_HEALTHS := {
	"dead_black": 0,
	"dead_busted": 1,
	"active": 2,
}
const SCREEN_SIZE: Vector3 = Vector3(0.92, 0.58, 0.06)
const SCREEN_CENTER_Y: float = 1.30
const SHELF_SIZE: Vector3 = Vector3(1.10, 0.05, 0.42)
const SHELF_CENTER_Y: float = 0.97
const BUTTON_SIZE: Vector3 = Vector3(0.07, 0.05, 0.07)
const FUNCTION_BUTTON_SIZE: Vector3 = Vector3(0.055, 0.05, 0.055)
## The grid's column pitch and the function block's side position, in
## the shelf's local frame.
const GRID_COLUMNS_X: Array[float] = [-0.295, -0.205, -0.115, -0.025]
const GRID_ROWS_Z: Array[float] = [0.15, 0.24, 0.33]
const FUNCTION_BUTTONS_X: Array[float] = [0.18, 0.28, 0.38]
## The blank buttons' deterministic palette: colored, no letters.
const BUTTON_PALETTE: Array[Color] = [
	Color(0.72, 0.10, 0.08),
	Color(0.75, 0.45, 0.06),
	Color(0.16, 0.55, 0.14),
	Color(0.08, 0.42, 0.55),
	Color(0.12, 0.18, 0.60),
	Color(0.48, 0.10, 0.45),
	Color(0.68, 0.66, 0.60),
	Color(0.60, 0.50, 0.08),
	Color(0.10, 0.48, 0.42),
	Color(0.70, 0.28, 0.05),
	Color(0.35, 0.58, 0.10),
	Color(0.38, 0.16, 0.52),
]
## A visibly busted console drops two grid buttons and its screen hangs
## forward off the mount.
const BUSTED_MISSING_BUTTONS: Array[int] = [4, 7]
const BUSTED_SCREEN_TILT: float = 0.55

## The screen's label text (Spanish this milestone, alien language
## later): the console's state machine owns the wording, pinned by the
## tests and the lane's machine checks. The screen renders the heading
## small and the state word large — the readable control-display look.
const LABEL_HEAD: String = "Control de energía secundaria:"
const LABEL_TAIL_INACTIVE: String = "Inactivo"
const LABEL_TAIL_ACTIVE: String = "Activo"

## The secondary generator at the room's center: a sleek black column,
## unaged next to the damaged consoles and walls, reading as a black
## cylinder tinted red under the emergency circuit until the console
## activation lights it slick.
const GENERATOR_CENTER: Vector3 = Vector3(ROOM_CENTER_X, 0.0, (ROOM_START_Z + ROOM_END_Z) / 2.0)
const GENERATOR_RADIUS: float = 0.8
const GENERATOR_HEIGHT: float = 2.6
const GENERATOR_RING_RADII_Y: Array[float] = [0.7, 1.5, 2.3]
const GENERATOR_RING_INNER: float = 0.66
const GENERATOR_RING_OUTER: float = 0.84
const GENERATOR_GLOW: Color = Color(0.80, 0.90, 1.00)
const GENERATOR_EMISSIVE: float = 2.4
const GENERATOR_LIGHT_ENERGY: float = 1.2

## The room's fixtures mirror the hallway's pair of circuits: red
## emergency domes on the walls (dark until the beside-door switch
## lights the corridor's circuit) and regular white ceiling strips down
## the room's centerline (dead until the secondary power activates).
## The stasis bay's red circuit is separate and keeps its red.
const FIXTURE_WALL_MOUNT_Y: float = Lighting.WALL_MOUNT_HEIGHT
const FIXTURE_STANDOFF: float = Lighting.WALL_STANDOFF
const RED_FIXTURE_POSITIONS: Array[Vector3] = [
	Vector3(ROOM_START_X + FIXTURE_STANDOFF, FIXTURE_WALL_MOUNT_Y, -3.7),
	Vector3(ROOM_START_X + FIXTURE_STANDOFF, FIXTURE_WALL_MOUNT_Y, -7.5),
	Vector3(ROOM_END_X - FIXTURE_STANDOFF, FIXTURE_WALL_MOUNT_Y, -3.7),
	Vector3(ROOM_END_X - FIXTURE_STANDOFF, FIXTURE_WALL_MOUNT_Y, -7.5),
	Vector3(24.5, FIXTURE_WALL_MOUNT_Y, ROOM_END_Z + FIXTURE_STANDOFF),
	Vector3(29.5, FIXTURE_WALL_MOUNT_Y, ROOM_END_Z + FIXTURE_STANDOFF),
]
const REGULAR_LENS_SIZE: Vector3 = Vector3(1.15, 0.05, 0.18)
const REGULAR_LENS_BASE_COLOR: Color = Color(0.72, 0.72, 0.70)
const REGULAR_MOUNT_Y: float = ROOM_CEILING - 0.08
const REGULAR_STATIONS_X: Array[float] = [24.0, ROOM_CENTER_X, 30.0]
const REGULAR_STATIONS_Z: Array[float] = [-3.7, -7.7]

## One console station's authored frame: the position is the origin at
## the wall's inner face (station-local +Z faces into the room), the
## yaw turns the panel off the wall, the health picks the broken look.
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

var _game: Game = null
var _fade: Intensity.FixtureFade = null
var _white_fade: Intensity.FixtureFade = null
var _generator_fade: Intensity.FixtureFade = null
var _lights: Array[OmniLight3D] = []
var _lenses: Array[MeshInstance3D] = []
var _lens_mesh: BoxMesh = null
var _lens_material: StandardMaterial3D = null
var _white_lights: Array[OmniLight3D] = []
var _white_lenses: Array[MeshInstance3D] = []
var _white_lens_mesh: BoxMesh = null
var _white_lens_material: StandardMaterial3D = null
var _generator_light: OmniLight3D = null
var _generator_ring_material: StandardMaterial3D = null
var _door_leaf: MeshInstance3D = null
var _door_leaf_base: Vector3 = Vector3.ZERO
var _console_state: int = -1
var _screen_material: StandardMaterial3D = null
var _label_head: Label3D = null
var _label: Label3D = null
var _remainder: float = 0.0
static var _box_cache: Dictionary = {}
var _palette_cache: Dictionary = {}

## The room's shell in fixed order: floor, ceiling, the west and east
## side walls, the far (north) wall, and the south wall's gap band east
## of the corridor's pierce — the corridor's north band covers the rest
## of the south face. The slabs tuck under the wall bands so the power
## doorway's tunnel shows no seam.
static func room_solids() -> Array[Placement.SolidPlacement]:
	var mid_height := ROOM_CEILING / 2.0
	var slab_x_center := (ROOM_START_X - WALL + ROOM_END_X + WALL) / 2.0
	var slab_x_size := (ROOM_END_X + WALL) - (ROOM_START_X - WALL)
	var slab_z_center := (ROOM_START_Z + ROOM_END_Z - WALL) / 2.0
	var slab_z_size := (ROOM_START_Z - ROOM_END_Z) + 2.0 * WALL
	return [
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, -WALL / 2.0, slab_z_center),
			Vector3(slab_x_size, WALL, slab_z_size)
		),
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, ROOM_CEILING + WALL / 2.0, slab_z_center),
			Vector3(slab_x_size, WALL, slab_z_size)
		),
		Placement.SolidPlacement.new(
			Vector3(ROOM_START_X - WALL / 2.0, mid_height, slab_z_center),
			Vector3(WALL, ROOM_CEILING, slab_z_size)
		),
		Placement.SolidPlacement.new(
			Vector3(ROOM_END_X + WALL / 2.0, mid_height, slab_z_center),
			Vector3(WALL, ROOM_CEILING, slab_z_size)
		),
		Placement.SolidPlacement.new(
			Vector3(slab_x_center, mid_height, ROOM_END_Z - WALL / 2.0),
			Vector3(slab_x_size, ROOM_CEILING, WALL)
		),
		Placement.SolidPlacement.new(
			Vector3(
				Hallway.HALL_END_X + WALL + (ROOM_END_X + WALL - Hallway.HALL_END_X - WALL) / 2.0,
				mid_height,
				-(Hallway.HALL_WIDTH / 2.0 + WALL / 2.0)
			),
			Vector3(
				(ROOM_END_X + WALL) - (Hallway.HALL_END_X + WALL),
				ROOM_CEILING,
				WALL
			)
		),
	]

## The power door's closed leaf: the side doors' exact proud-mount
## placement on the corridor side of the north wall band, at the power
## door station. Slides into the wall band when it opens; the collider
## rides only while shut, exactly like the stasis hatch's slab.
static func door_leaf() -> Placement.SolidPlacement:
	return Placement.SolidPlacement.new(
		Vector3(
			Hallway.POWER_DOOR_X,
			DOOR_HEIGHT / 2.0,
			-(Hallway.HALL_WIDTH / 2.0 - DOOR_THICKNESS / 2.0)
		),
		Vector3(DOOR_WIDTH, DOOR_HEIGHT, DOOR_THICKNESS)
	)

## The console stations: six wall stations, most dead (blacked or
## visibly busted), exactly one working — its screen is the room's only
## active one, the secondary power's control surface.
static func console_stations() -> Array[ConsoleStation]:
	return [
		ConsoleStation.make(
			Vector3(ROOM_START_X, 0.0, -3.7), PI / 2.0, CONSOLE_HEALTHS["dead_black"]),
		ConsoleStation.make(
			Vector3(ROOM_START_X, 0.0, -7.5), PI / 2.0, CONSOLE_HEALTHS["active"]),
		ConsoleStation.make(
			Vector3(ROOM_END_X, 0.0, -3.7), -PI / 2.0, CONSOLE_HEALTHS["dead_busted"]),
		ConsoleStation.make(
			Vector3(ROOM_END_X, 0.0, -7.5), -PI / 2.0, CONSOLE_HEALTHS["dead_black"]),
		ConsoleStation.make(
			Vector3(24.5, 0.0, ROOM_END_Z), 0.0, CONSOLE_HEALTHS["dead_busted"]),
		ConsoleStation.make(
			Vector3(29.5, 0.0, ROOM_END_Z), 0.0, CONSOLE_HEALTHS["dead_black"]),
	]

## The working console's act volume center: on the floor plane, in
## front of the active station's screen.
static func console_act_center() -> Vector3:
	var station := console_stations()[1]
	return station.position + Vector3(sin(station.yaw), 0.0, cos(station.yaw)) * 1.05

## The power door's act volume center: on the floor plane, in front of
## the closed leaf, on the corridor side.
static func door_act_center() -> Vector3:
	return Vector3(
		Hallway.POWER_DOOR_X,
		0.0,
		-(Hallway.HALL_WIDTH / 2.0) + 0.6
	)

## One station's collider hull: the station-local frame's extent box
## spun by the station yaw — a multiple of a quarter turn, so the hull
## stays axis-aligned and cheap.
static func console_solid(station: ConsoleStation) -> Placement.SolidPlacement:
	var facing := Vector3(sin(station.yaw), 0.0, cos(station.yaw))
	var along := Vector3(facing.z, 0.0, -facing.x)
	var local_size := Vector3(1.25, 1.75, 0.56)
	var center := station.position + facing * 0.28
	return Placement.SolidPlacement.new(
		Vector3(center.x, 0.875, center.z),
		Vector3(
			absf(along.x) * local_size.x + absf(facing.x) * local_size.z,
			local_size.y,
			absf(along.z) * local_size.x + absf(facing.z) * local_size.z
		)
	)

## The generator's collider: the column's conservative square hull.
static func generator_solid() -> Placement.SolidPlacement:
	return Placement.SolidPlacement.new(
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

## The console label's two-line text for a state, or the empty string
## while the screen sits at its standby glow.
static func console_label(state: int) -> String:
	var tail := _label_tail(state)
	if tail.is_empty():
		return ""
	return LABEL_HEAD + "\n" + tail

## The label flattened to one line, the form the lane's machine checks
## pin.
static func console_label_flat(state: int) -> String:
	var tail := _label_tail(state)
	if tail.is_empty():
		return ""
	return LABEL_HEAD + " " + tail

static func _label_tail(state: int) -> String:
	match state:
		Game.ConsoleState.INACTIVE:
			return LABEL_TAIL_INACTIVE
		Game.ConsoleState.ACTIVE:
			return LABEL_TAIL_ACTIVE
		_:
			return ""

static func console_state_name(state: int) -> String:
	match state:
		Game.ConsoleState.STANDBY:
			return "standby"
		Game.ConsoleState.INACTIVE:
			return "inactive"
		Game.ConsoleState.ACTIVE:
			return "active"
		_:
			return "unknown"

## The power room's collider set: the hallway's set (which extends the
## walk sim's) plus this room's shell, its console hulls, the generator
## hull, and the door leaf while it is shut. One construction path, the
## same insertion order the scene builds in.
static func scene_collider_set(
	registry: Pods.PodRegistry, door_open: bool, power_door_open: bool
) -> ColliderSet:
	var set := Hallway.scene_collider_set(registry, door_open)
	for placement: Placement.SolidPlacement in room_solids():
		_insert_placement(set, placement)
	for station: ConsoleStation in console_stations():
		_insert_placement(set, console_solid(station))
	_insert_placement(set, generator_solid())
	if not power_door_open:
		_insert_placement(set, door_leaf())
	return set

## Insert one world-frame placement as a collider box: the conservative
## corner-hull AABB, mirroring Placement's derivation.
static func _insert_placement(set: ColliderSet, placement: Placement.SolidPlacement) -> void:
	_insert_box(set, placement.center, placement.size, placement.rotation)

static func _insert_box(
	set: ColliderSet, center: Vector3, size: Vector3, rotation: Quaternion
) -> void:
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
	assert(result.is_ok(), "the frozen power room placement data derives a valid collider box")
	set.insert(result.box)

static func build(game: Game) -> PowerRoom:
	var room := PowerRoom.new()
	room.name = "PowerRoom"
	room._game = game
	var level := 1.0 if (game.hallway_lit and not game.power_active) else 0.0
	var white_level := 1.0 if game.power_active else 0.0
	var glow_level := 1.0 if game.power_active else 0.0

	var surface_names := [
		"PowerFloor",
		"PowerCeiling",
		"PowerWallWest",
		"PowerWallEast",
		"PowerWallNorth",
		"PowerWallSouthGap",
	]
	var surface_roles := ["floor", "ceiling", "wall", "wall", "wall", "wall"]
	var solids := room_solids()
	assert(
		solids.size() == surface_names.size(),
		"every power room surface carries its name"
	)
	for index: int in range(solids.size()):
		var piece := _surface_instance(surface_roles[index], solids[index])
		piece.name = surface_names[index]
		room.add_child(piece)

	room._door_leaf = _box_instance(door_leaf(), _flat_grey(DOOR_SHADE))
	room._door_leaf.name = "PowerDoorLeaf"
	room._door_leaf_base = door_leaf().center
	room.add_child(room._door_leaf)

	for station: ConsoleStation in console_stations():
		room.add_child(room._build_console(station))

	room.add_child(room._build_generator(glow_level))

	room._lens_mesh = BoxMesh.new()
	room._lens_mesh.size = Lighting.LENS_SIZE
	room._lens_material = StandardMaterial3D.new()
	room._lens_material.albedo_color = Lighting.LENS_BASE_COLOR
	room._lens_material.emission = Color(Lighting.FIXTURE_EMISSIVE * level, 0.0, 0.0)
	room._lens_material.roughness = 0.8
	room._lens_mesh.material = room._lens_material
	var held: Intensity.Result = Intensity.FixtureFade.holding(level)
	assert(held.is_ok(), "the power room's level maps to a valid fade")
	room._fade = held.fade
	for position: Vector3 in RED_FIXTURE_POSITIONS:
		room.add_child(room._fixture(position, level))

	room._white_lens_mesh = BoxMesh.new()
	room._white_lens_mesh.size = REGULAR_LENS_SIZE
	room._white_lens_material = StandardMaterial3D.new()
	room._white_lens_material.albedo_color = REGULAR_LENS_BASE_COLOR
	room._white_lens_material.emission = Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * white_level
	room._white_lens_material.roughness = 0.8
	room._white_lens_mesh.material = room._white_lens_material
	var white_held: Intensity.Result = Intensity.FixtureFade.holding(white_level)
	assert(white_held.is_ok(), "the white strip level maps to a valid fade")
	room._white_fade = white_held.fade
	for station_x: float in REGULAR_STATIONS_X:
		for station_z: float in REGULAR_STATIONS_Z:
			room.add_child(room._white_fixture(station_x, station_z, white_level))

	room._apply_console_state(game.console_state)
	return room

## One console station: spine, screen, shelf, and the blank colored
## buttons. The broken looks differ by health — a blacked station holds
## a dead screen; a busted one drops buttons and hangs its screen
## forward — and the working station's screen is the room's only one
## that glows.
func _build_console(station: ConsoleStation) -> Node3D:
	var group := Node3D.new()
	group.name = "ConsoleStation"
	group.position = station.position
	group.rotation.y = station.yaw
	var spine := MeshInstance3D.new()
	spine.name = "Spine"
	spine.mesh = _box_mesh(Vector3(0.06, 1.7, 0.10))
	spine.material_override = _flat_grey(0.10)
	spine.position = Vector3(0.0, 0.85, 0.05)
	group.add_child(spine)
	var screen := MeshInstance3D.new()
	screen.name = "Screen"
	screen.mesh = _box_mesh(SCREEN_SIZE)
	if station.health == CONSOLE_HEALTHS["active"]:
		_screen_material = StandardMaterial3D.new()
		_screen_material.albedo_color = Color(0.05, 0.05, 0.05)
		_screen_material.roughness = 0.35
		_screen_material.emission_enabled = true
		_screen_material.emission = Lighting.REGULAR_WHITE * 0.10
		screen.material_override = _screen_material
		screen.position = Vector3(0.0, SCREEN_CENTER_Y, 0.13)
	elif station.health == CONSOLE_HEALTHS["dead_busted"]:
		var busted := StandardMaterial3D.new()
		busted.albedo_color = Color(0.03, 0.03, 0.03)
		busted.roughness = 0.4
		screen.material_override = busted
		# The screen hangs forward off its mount, tilted past level.
		screen.position = Vector3(0.0, SCREEN_CENTER_Y - 0.18, 0.20)
		screen.rotation.x = -BUSTED_SCREEN_TILT
	else:
		var blacked := StandardMaterial3D.new()
		blacked.albedo_color = Color(0.04, 0.04, 0.04)
		blacked.roughness = 0.4
		screen.material_override = blacked
		screen.position = Vector3(0.0, SCREEN_CENTER_Y, 0.13)
	group.add_child(screen)
	if station.health == CONSOLE_HEALTHS["active"]:
		_label_head = Label3D.new()
		_label_head.name = "ScreenHead"
		_label_head.font_size = 13
		_label_head.pixel_size = 0.004
		_label_head.modulate = Color(0.75, 0.85, 0.95)
		_label_head.position = Vector3(0.0, SCREEN_CENTER_Y + 0.12, 0.165)
		group.add_child(_label_head)
		_label = Label3D.new()
		_label.name = "ScreenLabel"
		_label.font_size = 26
		_label.pixel_size = 0.004
		_label.modulate = Color(0.85, 0.95, 1.0)
		_label.outline_size = 4
		_label.outline_modulate = Color(0.0, 0.0, 0.0)
		_label.position = Vector3(0.0, SCREEN_CENTER_Y - 0.10, 0.165)
		group.add_child(_label)
	var shelf := MeshInstance3D.new()
	shelf.name = "Shelf"
	shelf.mesh = _box_mesh(SHELF_SIZE)
	shelf.material_override = _flat_grey(0.12)
	shelf.position = Vector3(0.0, SHELF_CENTER_Y, 0.26)
	group.add_child(shelf)
	var button_index := 0
	for row_z: float in GRID_ROWS_Z:
		for column_x: float in GRID_COLUMNS_X:
			var busted_missing: bool = (
				station.health == CONSOLE_HEALTHS["dead_busted"]
				and BUSTED_MISSING_BUTTONS.has(button_index)
			)
			if not busted_missing:
				group.add_child(_button(
					Vector3(column_x, SHELF_CENTER_Y + 0.05, row_z),
					BUTTON_SIZE,
					BUTTON_PALETTE[button_index % BUTTON_PALETTE.size()]
				))
			button_index += 1
	for function_x: float in FUNCTION_BUTTONS_X:
		group.add_child(_button(
			Vector3(function_x, SHELF_CENTER_Y + 0.05, 0.24),
			FUNCTION_BUTTON_SIZE,
			Color(0.55, 0.55, 0.52)
		))
	return group

func _button(position: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
	var button := MeshInstance3D.new()
	button.name = "Button"
	button.mesh = _box_mesh(size)
	button.material_override = _palette_material(color)
	button.position = position
	return button

## The secondary generator: a sleek black column with light rings that
## sit dark until the console activation, then glow slick while an omni
## under its crown lights the room's center.
func _build_generator(glow_level: float) -> Node3D:
	var group := Node3D.new()
	group.name = "Generator"
	group.position = GENERATOR_CENTER
	var column := MeshInstance3D.new()
	column.name = "Column"
	var column_mesh := CylinderMesh.new()
	column_mesh.top_radius = GENERATOR_RADIUS
	column_mesh.bottom_radius = GENERATOR_RADIUS
	column_mesh.height = GENERATOR_HEIGHT
	column_mesh.radial_segments = 24
	column.mesh = column_mesh
	var shell := StandardMaterial3D.new()
	shell.albedo_color = Color(0.05, 0.05, 0.06)
	shell.metallic = 0.85
	shell.roughness = 0.20
	column.material_override = shell
	column.position = Vector3(0.0, GENERATOR_HEIGHT / 2.0, 0.0)
	group.add_child(column)
	_generator_ring_material = StandardMaterial3D.new()
	_generator_ring_material.albedo_color = Color(0.07, 0.07, 0.08)
	_generator_ring_material.metallic = 0.6
	_generator_ring_material.roughness = 0.3
	_generator_ring_material.emission_enabled = true
	_generator_ring_material.emission = GENERATOR_GLOW * GENERATOR_EMISSIVE * glow_level
	for ring_y: float in GENERATOR_RING_RADII_Y:
		var ring := MeshInstance3D.new()
		ring.name = "Ring"
		var ring_mesh := TorusMesh.new()
		ring_mesh.inner_radius = GENERATOR_RING_INNER
		ring_mesh.outer_radius = GENERATOR_RING_OUTER
		ring.mesh = ring_mesh
		ring.material_override = _generator_ring_material
		ring.position = Vector3(0.0, ring_y, 0.0)
		group.add_child(ring)
	_generator_light = OmniLight3D.new()
	_generator_light.name = "Glow"
	_generator_light.light_color = GENERATOR_GLOW
	_generator_light.light_energy = GENERATOR_LIGHT_ENERGY * glow_level
	_generator_light.omni_range = 6.5
	_generator_light.shadow_enabled = false
	_generator_light.position = Vector3(0.0, GENERATOR_HEIGHT - 0.7, 0.0)
	group.add_child(_generator_light)
	var glow_held: Intensity.Result = Intensity.FixtureFade.holding(glow_level)
	assert(glow_held.is_ok(), "the generator's glow level maps to a valid fade")
	_generator_fade = glow_held.fade
	return group

## One red emergency wall fixture: the hallway's exact style, so the
## room reads on the corridor's circuit.
func _fixture(position: Vector3, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "PowerFixture"
	fixture.position = position
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

## One regular white ceiling strip.
func _white_fixture(station_x: float, station_z: float, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "PowerRegularStrip"
	fixture.position = Vector3(station_x, REGULAR_MOUNT_Y, station_z)
	var light := OmniLight3D.new()
	light.light_color = Lighting.REGULAR_WHITE
	light.light_energy = Lighting.regular_energy() * level
	light.omni_range = Lighting.REGULAR_RANGE
	light.shadow_enabled = false
	light.position = Vector3(0.0, -0.12, 0.0)
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.mesh = _white_lens_mesh
	fixture.add_child(lens)
	_white_lights.append(light)
	_white_lenses.append(lens)
	return fixture

func _physics_process(_delta: float) -> void:
	process_frame(Sim.LOGICAL_TICK_SECS)

## One render-bridge frame, the hallway's exact pattern: retarget only
## on the sim-side target change, consume whole logical ticks, project
## the fades onto the render state. The console's screen state reads
## the sim's console state machine; the red emergency circuit holds the
## corridor's level until the secondary power activates, then hands off
## to the white strips and the generator's glow.
func process_frame(delta_secs: float) -> void:
	var red_target := 1.0 if (_game.hallway_lit and not _game.power_active) else 0.0
	var white_target := 1.0 if _game.power_active else 0.0
	var glow_target := 1.0 if _game.power_active else 0.0
	if _fade.target() != red_target:
		_fade.retarget(red_target, Lighting.FIXTURE_SETTLE_TICKS)
	if _white_fade.target() != white_target:
		_white_fade.retarget(white_target, Lighting.FIXTURE_SETTLE_TICKS)
	if _generator_fade.target() != glow_target:
		_generator_fade.retarget(glow_target, Lighting.FIXTURE_SETTLE_TICKS)
	_remainder += delta_secs
	while _remainder >= Sim.LOGICAL_TICK_SECS:
		_remainder -= Sim.LOGICAL_TICK_SECS
		_fade.tick()
		_white_fade.tick()
		_generator_fade.tick()
	_apply_level(_fade.intensity())
	_apply_white_level(_white_fade.intensity())
	_apply_generator_glow(_generator_fade.intensity())
	if _console_state != _game.console_state:
		_apply_console_state(_game.console_state)

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

func _apply_white_level(level: float) -> void:
	var energy: float = Lighting.regular_energy() * level
	for light: OmniLight3D in _white_lights:
		if light.light_energy != energy:
			light.light_energy = energy
	var emissive := Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * level
	if _white_lens_material.emission != emissive:
		_white_lens_material.emission = emissive

func _apply_generator_glow(level: float) -> void:
	var energy: float = GENERATOR_LIGHT_ENERGY * level
	if _generator_light.light_energy != energy:
		_generator_light.light_energy = energy
	var emissive := GENERATOR_GLOW * GENERATOR_EMISSIVE * level
	if _generator_ring_material.emission != emissive:
		_generator_ring_material.emission = emissive

## The working console's screen: the standby glow carries no text; the
## Inactivo and Activo labels carry the Spanish state wording pinned by
## the tests and the lane's machine checks.
func _apply_console_state(state: int) -> void:
	_console_state = state
	if _screen_material == null or _label == null:
		return
	var tail := _label_tail(state)
	if _label.text != tail:
		_label.text = tail
	if _label_head.text != LABEL_HEAD:
		_label_head.text = LABEL_HEAD
	var emission: float = 0.0
	match state:
		Game.ConsoleState.STANDBY:
			emission = 0.10
		Game.ConsoleState.INACTIVE:
			emission = 0.30
		Game.ConsoleState.ACTIVE:
			emission = 0.45
	_screen_material.emission = Lighting.REGULAR_WHITE * emission

## The door leaf's animated offset from its authored pose, in world
## space: the deterministic projection this module's leaf renders.
func set_door_offset(offset: Vector3) -> void:
	_door_leaf.position = _door_leaf_base + offset

## The emergency red circuit's level in this room.
func level() -> float:
	return _fade.intensity()

## The regular white strips' level.
func white_level() -> float:
	return _white_fade.intensity()

## The generator's glow level: the lane's machine checks read this for
## the lit state.
func generator_lit() -> float:
	return _generator_fade.intensity()

func is_settled() -> bool:
	return (
		_fade.is_settled()
		and _white_fade.is_settled()
		and _generator_fade.is_settled()
	)

func lights() -> Array[OmniLight3D]:
	return _lights

func lenses() -> Array[MeshInstance3D]:
	return _lenses

func lens_material() -> StandardMaterial3D:
	return _lens_material

func white_lights() -> Array[OmniLight3D]:
	return _white_lights

func white_lenses() -> Array[MeshInstance3D]:
	return _white_lenses

func white_lens_material() -> StandardMaterial3D:
	return _white_lens_material

## The console state this module last rendered.
func rendered_console_state() -> String:
	return console_state_name(_console_state)

## The state word the working console's screen last rendered.
func label_text() -> String:
	return _label.text if _label != null else ""

## One textured surface piece wearing the stasis room's shared material
## for its role — the same resource instance, never a copy.
static func _surface_instance(
	role: String, placement: Placement.SolidPlacement
) -> MeshInstance3D:
	var material := RoomGeometry.wall_material()
	if role == "floor":
		material = RoomGeometry.floor_material()
	elif role == "ceiling":
		material = RoomGeometry.ceiling_material()
	return _box_instance(placement, material)

static func _box_instance(
	placement: Placement.SolidPlacement, material: Material
) -> MeshInstance3D:
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

## One shared material per palette color across every console's
## buttons: the blank colored buttons read in rows without per-button
## material churn.
func _palette_material(color: Color) -> StandardMaterial3D:
	if _palette_cache.has(color):
		return _palette_cache[color]
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.6
	_palette_cache[color] = material
	return material
