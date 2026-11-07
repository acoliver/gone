class_name PowerRoom
extends Node3D
## The emergency power room behind the hallway's last port (-Z) door walking aft (+X)
## (issue #59): the same footprint as the stasis room, pierced off the
## corridor's north wall at the power door. The room's consoles read
## futuristic-but-broken — flatscreens, blank colored-button keyboards,
## nothing mechanical — with exactly one working screen; the room's
## center holds the secondary generator, a sleek black column that
## looks inexplicably new next to the damaged walls (the stasis pods
## share that too-new quality; the reason is a later reveal). Under the
## emergency circuit the room reads red like the hall; actioning the
## working console once (palo / INACTIVO to shenu / EN FUNCIONAMIENTO) lights the generator and
## hands the hallway, bay and this room over to dim regular white.
## Colliders extend the hallway's set from
## solids authored here (Placement stays untouched): one construction
## path — the scene spawns these placements verbatim and the collider
## set derives from the same data.

## The room's envelope mirrors the stasis room's exactly: the corridor
## supplies the south wall band (pierced at the power door), this room
## supplies the rest of the shell — the same wall thickness, ceiling,
## and tucked floor slabs as the hallway's construction language.
const WALL: float = Placement.WALL_THICKNESS
const ROOM_CENTER_X = ShipGeometry.ROOM_CENTER_X
const ROOM_START_Z = ShipGeometry.ROOM_START_Z
const ROOM_END_Z = ShipGeometry.ROOM_END_Z
const ROOM_START_X = ShipGeometry.ROOM_START_X
const ROOM_END_X = ShipGeometry.ROOM_END_X
const ROOM_CEILING = ShipGeometry.ROOM_CEILING

## Regular steel is inset into the wall and slides into its drawn pocket.
const DOOR_WIDTH: float = Hallway.SIDE_DOOR_WIDTH
const DOOR_HEIGHT: float = Hallway.SIDE_DOOR_HEIGHT
const DOOR_THICKNESS: float = Hallway.SIDE_DOOR_THICKNESS
const DOOR_SHADE: float = Hallway.SIDE_DOOR_SHADE

## Console station construction, all in the station's local frame (the
## origin at the wall's inner face, the panel facing +Z into the room):
## a wall spine, a flatscreen at working height, a keyboard shelf, and
## blank colored buttons — a 4x3 grid plus three wider function buttons
## off to the side. Nothing mechanical; buttons carry no letters.
## Only the working screen carries native writing.
const CONSOLE_HEALTHS = ShipGeometry.CONSOLE_HEALTHS
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

const HEADING_ID: String = "secondary_power.heading"

## The secondary generator at the room's center: a sleek black column,
## unaged next to the damaged consoles and walls, reading as a black
## cylinder tinted red under the emergency circuit until the console
## activation lights it slick.
const GENERATOR_CENTER = ShipGeometry.GENERATOR_CENTER
const GENERATOR_RADIUS = ShipGeometry.GENERATOR_RADIUS
const GENERATOR_HEIGHT = ShipGeometry.GENERATOR_HEIGHT
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
## The bay uses the same secondary-powered handoff.
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
const ConsoleStation = ShipGeometry.ConsoleStation

var _game: Game = null
var _fade: Intensity.FixtureFade = null
var _white_fade: Intensity.FixtureFade = null
var _generator_fade: Intensity.FixtureFade = null
var _lights: Array[OmniLight3D] = []
var _fill_lights: Array[Lighting.EmergencyFill] = []
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
var _door_binding: Surfaces.MotionBinding
var _console_state: int = -1
var _screen_material: StandardMaterial3D = null
var console_display: ShipDisplay = null
var _text_cache: ShipTextCache
var _remainder: float = 0.0
static var _box_cache: Dictionary = {}
var _palette_cache: Dictionary = {}

## The room's shell in fixed order: floor, ceiling, the west and east
## side walls, the far (north) wall, and the south wall's gap band east
## of the corridor's pierce — the corridor's north band covers the rest
## of the south face. The slabs tuck under the wall bands so the power
## doorway's tunnel shows no seam.
static func room_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.power_room_solids()

## Closed collider and rendered leaf share the sim-owned in-wall dimensions.
static func door_leaf() -> Placement.SolidPlacement:
	return ShipGeometry.power_door_leaf()

## The console stations: six wall stations, most dead (blacked or
## visibly busted), exactly one working — its screen is the room's only
## active one, the secondary power's control surface.
static func console_stations() -> Array[ConsoleStation]:
	return ShipGeometry.console_stations()

## The working console's act volume center: on the floor plane, in
## front of the active station's screen.
static func console_act_center() -> Vector3:
	return ShipGeometry.console_act_center()

## The power door's act volume center: on the floor plane, in front of
## the closed leaf, on the corridor side.
static func door_act_center() -> Vector3:
	return ShipGeometry.door_act_center()

## One station's collider hull: the station-local frame's extent box
## spun by the station yaw — a multiple of a quarter turn, so the hull
## stays axis-aligned and cheap.
static func console_solid(station: ConsoleStation) -> Placement.SolidPlacement:
	return ShipGeometry.console_solid(station)

## The generator's collider: the column's conservative square hull.
static func generator_solid() -> Placement.SolidPlacement:
	return ShipGeometry.generator_solid()

## Both authored layers, flattened for the harness.
static func console_labels(state: int) -> Dictionary:
	var id := _state_message_id(state)
	if id.is_empty():
		return {"native": "", "perceived_es": ""}
	var head := ShipText.message(HEADING_ID)
	var tail := ShipText.message(id)
	return {
		"native": head.native + " " + tail.native,
		"perceived_es": head.perceived_es + " " + tail.perceived_es,
	}

static func _state_message_id(state: int) -> String:
	match state:
		Game.ConsoleState.INACTIVE:
			return "secondary_power.inactive"
		Game.ConsoleState.ACTIVE:
			return "secondary_power.active"
		_:
			return ""

static func console_state_name(state: int) -> String:
	match state:
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
	return ShipCollision.opening_set(registry, door_open, power_door_open)

static func build(game: Game, text_cache: ShipTextCache = null) -> PowerRoom:
	var room := PowerRoom.new()
	room.name = "PowerRoom"
	room._game = game
	room._text_cache = text_cache
	var level := 1.0 if (game.hallway_lit and not game.power_active) else 0.0
	var white_level := 1.0 if game.power_active else 0.0
	var glow_level := 1.0 if game.power_active else 0.0

	var surface_names := [
		"PowerFloor",
		"PowerCeiling",
		"PowerWallWest",
		"PowerWallEast",
		"PowerWallNorth",
	]
	var surface_roles := ["floor", "ceiling", "wall", "wall", "wall"]
	var solids := room_solids()
	assert(
		solids.size() == surface_names.size(),
		"every power room surface carries its name"
	)
	for index: int in range(solids.size()):
		var piece := _surface_instance(surface_roles[index], solids[index], game.layout)
		piece.name = surface_names[index]
		room.add_child(piece)

	room._door_leaf = SlidingDoorModel.leaf(game.layout.door(ShipLayout.POWER_DOOR_ID), 1, game.layout)
	var door_frame := SlidingDoorModel.frame(game.layout.door(ShipLayout.POWER_DOOR_ID))
	room.add_child(door_frame)
	room._door_binding = Surfaces.MotionBinding.new(room._door_leaf)
	room._door_binding.pieces.append(room._door_leaf)
	room._door_leaf.name = "PowerDoorLeaf"
	room._door_leaf_base = room._door_leaf.position
	room.add_child(room._door_leaf)

	for station: ConsoleStation in console_stations():
		room.add_child(room._build_console(station))

	room.add_child(room._build_generator(glow_level))

	room._lens_mesh = BoxMesh.new()
	room._lens_mesh.size = Lighting.LENS_SIZE
	room._lens_material = Lighting.emergency_lens_material(level)
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
	var fill_positions := game.layout.power_room().emergency_fill_positions()
	for station_x: float in REGULAR_STATIONS_X:
		for station_z: float in REGULAR_STATIONS_Z:
			room.add_child(room._white_fixture(station_x, station_z, white_level))
			var fill := Lighting.emergency_fill(fill_positions[room._fill_lights.size()], level, Lighting.POWER_FILL_MASK)
			fill.name = "EmergencyFill%d" % room._fill_lights.size()
			room.add_child(fill)
			room._fill_lights.append(fill)

	room._apply_console_state(game.console_state)
	Lighting.mesh_layers(room, 1 | Lighting.POWER_FILL_MASK)
	# This steel borders both rooms; the room-wide pass must not exclude hall fill.
	var door_mask := 1 | Lighting.HALL_FILL_MASK | Lighting.POWER_FILL_MASK
	room._door_leaf.layers = door_mask
	Lighting.mesh_layers(door_frame, door_mask)
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
		console_display = ShipDisplay.build(_game.writing_memory, _text_cache)
		console_display.position = Vector3(0.0, SCREEN_CENTER_Y, 0.166)
		group.add_child(console_display)
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
	_generator_light.light_cull_mask = 1
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
	DressingMounts.ceiling_stem(fixture, ROOM_CEILING)
	var light := Lighting.switched_key(_game.layout.power_room().emergency_light_role(), level)
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "emergency")
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
	DressingMounts.ceiling_stem(fixture, ROOM_CEILING)
	var light := OmniLight3D.new()
	light.light_color = Lighting.REGULAR_WHITE
	light.light_energy = Lighting.regular_energy() * level
	light.omni_range = Lighting.REGULAR_RANGE
	light.light_cull_mask = 1
	light.shadow_enabled = false
	light.position = Vector3(0.0, -0.12, 0.0)
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "white")
	lens.mesh = _white_lens_mesh
	fixture.add_child(lens)
	_white_lights.append(light)
	_white_lenses.append(lens)
	return fixture

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
	var energy: float = Lighting.emergency_energy() * level
	for light: OmniLight3D in _lights:
		if light.light_energy != energy:
			light.light_energy = energy
	for fill: Lighting.EmergencyFill in _fill_lights:
		fill.apply_level(level)
	var emissive := Lighting.emergency_emission(level)
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

func _apply_console_state(state: int) -> void:
	if _console_state == state:
		return
	_console_state = state
	console_display.set_messages(HEADING_ID, _state_message_id(state))
	var emission: float = 0.0
	match state:
		Game.ConsoleState.INACTIVE:
			emission = 0.30
		Game.ConsoleState.ACTIVE:
			emission = 0.45
	_screen_material.emission = Lighting.REGULAR_WHITE * emission

## The door leaf's animated offset from its authored pose, in world
## space: the deterministic projection this module's leaf renders.
func set_door_offset(offset: Vector3) -> void:
	_door_leaf.position = _door_leaf_base + offset
	_door_binding.refresh()

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

func native_state_text() -> String:
	return console_display.native_canvas.state_word

func perceived_state_text() -> String:
	return console_display.perceived_canvas.state_word

## Called after the player's eye and look have advanced on the fixed tick.
func tick_console_attention(eye: Vector3, camera_forward: Vector3) -> void:
	if eye.distance_to(_game.layout.door(ShipLayout.POWER_DOOR_ID).frame().origin + Vector3.UP * 1.6) <= DisplayPerception.ATTENTION_RANGE:
		console_display.prefetch(HEADING_ID, ["secondary_power.inactive", "secondary_power.active"])
	_apply_console_state(_game.console_state)
	console_display.tick_attention(eye, camera_forward)

## One textured surface piece wearing the stasis room's shared material
## for its role — the same resource instance, never a copy.
static func _surface_instance(role: String, placement: Placement.SolidPlacement, layout: ShipLayout = ShipLayout.authored().layout) -> MeshInstance3D:
	assert(StringName(role) == placement.material_role, "surface role agrees with pure recipe")
	var piece := _box_instance(placement, Surfaces.material(placement.material_role))
	Surfaces.bind_solid(piece, layout, placement)
	return piece

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
