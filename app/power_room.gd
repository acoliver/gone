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
const CONSOLE_HEALTHS = ShipGeometry.CONSOLE_HEALTHS
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
var _white_lens_material: StandardMaterial3D = null
var _generator_light: OmniLight3D = null
var _generator_ring_material: StandardMaterial3D = null
var _door_leaf: MeshInstance3D = null
var _door_leaf_base: Vector3 = Vector3.ZERO
var _door_binding: Surfaces.MotionBinding
var _console_state: int = -1
var _screen_material: StandardMaterial3D = null
const StatusBoardScript = preload("res://app/status_board.gd")

var console_display: ShipDisplay = null
var status_board = null
var _text_cache: ShipTextCache
var _remainder: float = 0.0
static var _box_cache: Dictionary = {}
static var _crack_texture_cache: Texture2D = null

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
	room.add_child(CeilingProps.build(game.layout, ShipLayout.POWER_ID))
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

	var stations := console_stations()
	for index: int in range(stations.size()):
		var console := room._build_console(stations[index])
		console.name = "ConsoleStation%d" % index
		room.add_child(console)
	room.add_child(room._build_status_panel())

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

	room._white_lens_material = CeilingFixture.glass_material(white_level)
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

## One generated terminal and its matching keyboard tray. Each source model
## shares the authored station frame; only the active station owns live text.
func _build_console(station: ConsoleStation) -> Node3D:
	var group := Node3D.new()
	group.name = "ConsoleStation"
	group.position = station.position
	group.rotation.y = station.yaw
	var terminal := load("res://assets/props/terminal/terminal.glb").instantiate() as Node3D
	terminal.name = "TerminalModel"
	group.add_child(terminal)
	var keyboard := load("res://assets/props/terminal/keyboard-tray.glb").instantiate() as Node3D
	keyboard.name = "KeyboardTray"
	group.add_child(keyboard)
	if station.health == CONSOLE_HEALTHS["dead_busted"]:
		var hinge := Vector3(0.0, -0.85, 1.10)
		var droop := deg_to_rad(7.0)
		var hinge_rotation := Basis(Vector3.RIGHT, droop)
		keyboard.position = hinge + hinge_rotation * (keyboard.position - hinge)
		keyboard.rotation.x = droop
		assert(is_equal_approx(rad_to_deg(keyboard.rotation.x), 7.0), "busted tray droops seven degrees around its flange hinge")
		for cap_name: String in ["Keycap 03 onset p", "Keycap 24 control number"]:
			var missing_cap := keyboard.find_child(cap_name, true, false) as MeshInstance3D
			assert(missing_cap != null, "busted keyboard contains " + cap_name)
			missing_cap.visible = false
	var socket := terminal.find_child("ScreenSocket", true, false) as Node3D
	assert(socket != null, "terminal GLB exports its screen socket")
	var display_plane := terminal.find_child("DisplayPlane", true, false) as MeshInstance3D
	assert(display_plane != null, "terminal GLB exports its display plane")
	if station.health == CONSOLE_HEALTHS["active"]:
		_screen_material = StandardMaterial3D.new()
		_screen_material.albedo_color = Color(0.025, 0.035, 0.04)
		_screen_material.roughness = 0.3
		_screen_material.emission_enabled = true
		_screen_material.emission = Lighting.REGULAR_WHITE * 0.10
		var screen := MeshInstance3D.new()
		screen.name = "ScreenGlass"
		screen.mesh = _box_mesh(Vector3(0.54, 0.28, 0.008))
		screen.material_override = _screen_material
		screen.visible = false
		group.add_child(screen)
		var terminal_fit := terminal.find_child("Terminal_GeneratedFit", true, false) as MeshInstance3D
		assert(terminal_fit != null, "terminal GLB exports its fitted housing")
		var plane_transform := terminal.transform * display_plane.transform
		var display_frame := _upright_screen_frame(group, plane_transform, display_plane.mesh.get_aabb())
		screen.transform = display_frame.transform
		screen.mesh = _box_mesh(Vector3(display_frame.size.x, display_frame.size.y, 0.008))
		var plane_size: Vector2 = display_frame.size
		assert(display_frame.transform.basis.z.dot(Vector3.BACK) > 0.0, "terminal display plane faces out from its screen")
		display_plane.visible = false
		console_display = ShipDisplay.build(_game.writing_memory, _text_cache)
		console_display.transform = display_frame.transform
		console_display.position += display_frame.transform.basis.z * 0.003
		var text_quad := console_display.get_node("TextSurface") as MeshInstance3D
		(text_quad.mesh as QuadMesh).size = plane_size
		group.add_child(console_display)
	else:
		var glass := StandardMaterial3D.new()
		glass.albedo_color = Color(0.018, 0.02, 0.025)
		glass.roughness = 0.38
		if station.health == CONSOLE_HEALTHS["dead_busted"]:
			glass.albedo_color = Color.WHITE
			glass.albedo_texture = _crack_texture()
		var dead_screen := MeshInstance3D.new()
		dead_screen.name = "ScreenGlass"
		var dead_transform := terminal.transform * display_plane.transform
		var dead_frame := _upright_screen_frame(group, dead_transform, display_plane.mesh.get_aabb())
		dead_screen.mesh = _box_mesh(Vector3(dead_frame.size.x, dead_frame.size.y, 0.008))
		dead_screen.material_override = glass
		dead_screen.transform = dead_frame.transform
		group.add_child(dead_screen)
	return group

func _upright_screen_frame(group: Node3D, plane_transform: Transform3D, bounds: AABB) -> Dictionary:
	var group_basis := group.transform.basis.orthonormalized()
	var plane_normal_world := (group_basis * plane_transform.basis.z).normalized()
	var up_world := (Vector3.UP - plane_normal_world * Vector3.UP.dot(plane_normal_world)).normalized()
	var right_world := up_world.cross(plane_normal_world).normalized()
	var inverse_group_basis := group_basis.inverse()
	var frame_basis := Basis(
		(inverse_group_basis * right_world).normalized(),
		(inverse_group_basis * up_world).normalized(),
		(inverse_group_basis * plane_normal_world).normalized()
	)
	var plane_center := plane_transform * bounds.get_center()
	var left := INF
	var right := -INF
	var bottom := INF
	var top := -INF
	for x: float in [bounds.position.x, bounds.end.x]:
		for y: float in [bounds.position.y, bounds.end.y]:
			for z: float in [bounds.position.z, bounds.end.z]:
				var corner := plane_transform * Vector3(x, y, z)
				var relative := group_basis * (corner - plane_center)
				var horizontal := relative.dot(right_world)
				var vertical := relative.dot(up_world)
				left = minf(left, horizontal)
				right = maxf(right, horizontal)
				bottom = minf(bottom, vertical)
				top = maxf(top, vertical)
	return {
		"transform": Transform3D(frame_basis, plane_center),
		"size": Vector2(right - left, top - bottom),
	}

static func _crack_texture() -> Texture2D:
	if _crack_texture_cache != null:
		return _crack_texture_cache
	var image := Image.create(128, 64, false, Image.FORMAT_RGBA8)
	image.fill(Color(0.025, 0.02, 0.02, 1.0))
	var paths: Array[PackedVector2Array] = [
		PackedVector2Array([Vector2(64, 31), Vector2(55, 23), Vector2(52, 13), Vector2(43, 7)]),
		PackedVector2Array([Vector2(55, 23), Vector2(44, 25), Vector2(36, 32)]),
		PackedVector2Array([Vector2(52, 13), Vector2(56, 5)]),
		PackedVector2Array([Vector2(64, 31), Vector2(73, 23), Vector2(85, 20), Vector2(97, 12)]),
		PackedVector2Array([Vector2(73, 23), Vector2(76, 35), Vector2(88, 43)]),
		PackedVector2Array([Vector2(85, 20), Vector2(94, 28), Vector2(108, 29)]),
		PackedVector2Array([Vector2(64, 31), Vector2(57, 42), Vector2(49, 48)]),
		PackedVector2Array([Vector2(57, 42), Vector2(66, 53)]),
	]
	for path: PackedVector2Array in paths:
		for index: int in range(path.size() - 1):
			var start := Vector2i(path[index])
			var finish := Vector2i(path[index + 1])
			var steps := maxi(absi(finish.x - start.x), absi(finish.y - start.y))
			for step: int in range(steps + 1):
				var point := Vector2i(roundi(lerpf(start.x, finish.x, float(step) / steps)), roundi(lerpf(start.y, finish.y, float(step) / steps)))
				image.set_pixel(point.x, point.y, Color(0.92, 0.96, 1.0, 1.0))
				if point.y + 1 < image.get_height():
					image.set_pixel(point.x, point.y + 1, Color(0.30, 0.38, 0.44, 1.0))
	_crack_texture_cache = ImageTexture.create_from_image(image)
	return _crack_texture_cache

func _build_status_panel() -> Node3D:
	var mount := Node3D.new()
	mount.name = "StatusPanelMount"
	mount.position = Vector3(27.0, 1.4, ROOM_END_Z)
	var panel := load("res://assets/props/status_panel/panel.glb").instantiate() as Node3D
	panel.name = "StatusPanelModel"
	mount.add_child(panel)
	var socket := panel.find_child("ScreenSocket", true, false) as Node3D
	assert(socket != null, "status panel GLB exports its screen socket")
	status_board = StatusBoardScript.build(_game.writing_memory)
	status_board.transform = socket.transform
	status_board.position += socket.basis.z * 0.002
	mount.add_child(status_board)
	return mount


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
	var collar := MeshInstance3D.new()
	collar.name = "CeilingCollar"
	collar.mesh = HatchModel.cylinder(GENERATOR_RADIUS + 0.08, 0.08)
	collar.position.y = GENERATOR_HEIGHT - 0.04
	collar.material_override = shell
	group.add_child(collar)
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
	_generator_light.position = Vector3(0.0, 1.9, 0.0)
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
	DressingMounts.ceiling_stem(fixture, ROOM_CEILING, Surfaces.surface_frame(_game.layout, ShipLayout.POWER_ID, &"CEILING"))
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
	var light := OmniLight3D.new()
	light.light_color = Lighting.REGULAR_WHITE
	light.light_energy = Lighting.regular_energy() * level
	light.omni_range = Lighting.REGULAR_RANGE
	light.light_cull_mask = 1
	light.shadow_enabled = false
	light.position = Vector3(0.0, -0.12, 0.0)
	fixture.add_child(light)
	var lens := CeilingFixture.mount(fixture, ROOM_CEILING, 1 | Lighting.POWER_FILL_MASK, _white_lens_material)
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
	status_board.tick_attention(eye, camera_forward)

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
