class_name Hallway
extends Node3D
## The hallway behind the stasis room's door (issue #59's prerequisite
## milestone): the door now opens on act into a straight crew corridor
## running out from the doorway — double the stasis room's length, the
## pod bay's aisle width, the room's ceiling height. Closed side doors
## read crew passage, and a red domed pushbutton beside the doorway, on
## the pierced wall's hall face, lights the hall's red emergency
## fixtures — dark until the flip, steady red after it, with no blackout
## trick: the fixtures simply hold level zero. Since issue #59 the north
## wall is pierced at the power door and the power room module owns the
## room behind it; when the secondary power activates, the red emergency
## fixtures hand the corridor over to the dim regular white strips at
## the same stations. Surfaces wear the stasis room's shared surface
## materials; no suspended cable trays or smoke live in this subtree.
## The hallway's colliders extend the walk sim's set from solids authored
## here (Placement stays untouched):
## one construction path — the scene spawns these placements verbatim
## and the collider set derives from the same data.

## The corridor's interior length along +X: double the stasis room's
## length, per the milestone's envelope brief.
const HALL_LENGTH = ShipGeometry.HALL_LENGTH

## The corridor's interior width: the pod bay's authored aisle width
## carried through the doorway, so the walk sim's comfortable band
## continues without a pinch.
const HALL_WIDTH = ShipGeometry.HALL_WIDTH

## The corridor starts at the room's +X wall inner face and runs to
## HALL_END_X; the ceiling matches the room's height language exactly.
const HALL_START_X = ShipGeometry.HALL_START_X
const HALL_END_X = ShipGeometry.HALL_END_X
const HALL_CEILING_HEIGHT = ShipGeometry.HALL_CEILING_HEIGHT
const WALL = ShipGeometry.WALL

## The doorway pierces the room's +X wall with the hatch opening's
## exact width and height, so the frame's opening and the wall's hole
## are one aperture.
const DOORWAY_WIDTH = ShipGeometry.DOORWAY_WIDTH
const DOORWAY_HEIGHT = ShipGeometry.DOORWAY_HEIGHT

## The room shell's +X wall index, the one wall this module's doorway
## replaces in both the render and the collider set.
const ROOM_SHELL_EAST_WALL_INDEX = ShipGeometry.ROOM_SHELL_EAST_WALL_INDEX

## Closed side doors: one-meter leaves at six-meter pitch — a berth
## block every six meters reads crew passage, not arcade corridor.
const SIDE_DOOR_WIDTH = ShipGeometry.SIDE_DOOR_WIDTH
const SIDE_DOOR_HEIGHT = ShipGeometry.SIDE_DOOR_HEIGHT
const SIDE_DOOR_THICKNESS = ShipGeometry.SIDE_DOOR_THICKNESS
## The emergency-power room entrance (issue #59 proper): the last door
## on the left walking out of the stasis room — the north (-Z) wall,
## pierced here. The PowerRoom module authors the door's leaf, its
## deterministic slide, and the room behind the wall.
const POWER_DOOR_X = ShipGeometry.POWER_DOOR_X

## The switch plate beside the door: proud of the pierced wall's hall
## face, at working height on the latch side of the aperture — the
## button sits next to the door it lights, one arm's reach from the
## threshold. A small dark plate with a domed red pushbutton, the
## fuel-stop pattern. No emission — before the flip it is invisible in
## the dark by nature of the darkness.
const SWITCH_PLATE_SIZE: Vector3 = Vector3(0.04, 0.24, 0.16)
static var SWITCH_PLATE_CENTER: Vector3 = ShipLayout.authored().layout.anchor(&"D14-HALL-SWITCH").origin
const SWITCH_DOME_RADIUS: float = 0.055
const SWITCH_DOME_COLOR: Color = Color(0.55, 0.04, 0.03)
const SWITCH_PLATE_SHADE: float = 0.16

## The hallway's fixtures hold the stasis bay's exact style and levels:
## a pair over every berth station, the power door's station included,
## so the whole corridor reads one rhythm from the doorway to the far
## end. The lit fixtures hold their red steady — blinking belongs to
## the automatic fire circuit, and the hall has no fire.
const FIXTURE_STATIONS_X: Array[float] = [9.0, 15.0, 21.0, POWER_DOOR_X]

## The regular-service white strips down the corridor's centerline, one
## per emergency station: dead until the secondary power activates,
## then the corridor's light — dim but ordinary — while the red
## emergency pair at every station hands off to them.
const REGULAR_STATIONS_X: Array[float] = [9.0, 15.0, 21.0, POWER_DOOR_X]

const SIDE_DOOR_SHADE: float = HatchModel.DOOR_SHADE

static var _box_cache: Dictionary = {}

var side_leaves: Dictionary = {}
var _game: Game = null
var _fade: Intensity.FixtureFade = null
var _lights: Array[OmniLight3D] = []
var _fill_lights: Array[Lighting.EmergencyFill] = []
var _lenses: Array[MeshInstance3D] = []
var _lens_mesh: BoxMesh = null
var _lens_material: StandardMaterial3D = null
var _white_fade: Intensity.FixtureFade = null
var _white_lights: Array[OmniLight3D] = []
var _white_end_fill: Lighting.RegularEndFill
var _white_lenses: Array[MeshInstance3D] = []
var _white_lens_material: StandardMaterial3D = null
var _remainder: float = 0.0

## The pierced +X wall: the original wall slab's envelope with the
## doorway aperture removed — two side pieces and a lintel, all
## axis-aligned in the wall's band.
static func doorway_wall_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.doorway_wall_solids()

## The doorway's closed blocker: fills the aperture exactly while the
## door is shut, dropped from the collider set the tick the opening
## animation completes.
static func doorway_block() -> Placement.SolidPlacement:
	return ShipGeometry.doorway_block()

## The north wall pierced by the power doorway (issue #59): the side
## wall's exact envelope with the power door's aperture removed — two
## side pieces and a lintel, all axis-aligned in the wall's band, in
## the same construction language as the east wall's pierce. The
## aperture matches the side doors' leaf dimensions, and the PowerRoom
## module's leaf fills it while shut.
static func power_doorway_wall_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.power_doorway_wall_solids()

## The corridor's shell in fixed order: floor, ceiling, the north
## wall's pierce pieces at the power doorway, the south side wall, and
## the far endcap wall. The floor and ceiling slabs tuck under the
## room's wall band so the doorway tunnel shows no seam.
static func hallway_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.hallway_solids()

## The closed side doors, flush-mounted leaves proud of the side walls.
## The power door is not one of these: the PowerRoom module authors its
## leaf, its slide, and its colliders.
static func side_door_solids() -> Array[Placement.SolidPlacement]:
	return ShipGeometry.side_door_solids()

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
	return ShipCollision.hallway_set(registry, door_open)

static func build(game: Game) -> Hallway:
	var hallway := Hallway.new()
	hallway.name = "Hallway"
	hallway._game = game
	var level := 1.0 if (game.hallway_lit and not game.power_active) else 0.0
	hallway._lens_mesh = BoxMesh.new()
	hallway._lens_mesh.size = Lighting.LENS_SIZE
	hallway._lens_material = Lighting.emergency_lens_material(level)
	hallway._lens_mesh.material = hallway._lens_material
	var held: Intensity.Result = Intensity.FixtureFade.holding(level)
	assert(held.is_ok(), "the hallway's level maps to a finite nonnegative fade")
	hallway._fade = held.fade

	var surface_names := [
		"HallFloor",
		"HallCeiling",
		"HallWallNorthWest",
		"HallWallNorthEast",
		"HallWallNorthLintel",
		"HallWallSouthWest",
		"HallWallSouthEast",
		"HallWallSouthLintel",
	]
	var surface_roles := ["floor", "ceiling", "wall", "wall", "wall", "wall", "wall", "wall"]
	var hall_solids := ShipGeometry.hallway_solids(game.layout)
	assert(
		hall_solids.size() == surface_names.size(),
		"every hallway surface carries its name"
	)
	for index: int in range(hall_solids.size()):
		var piece := _surface_instance(surface_roles[index], hall_solids[index], game.layout)
		piece.name = surface_names[index]
		if hall_solids[index].material_role == &"floor": piece.visible = false
		hallway.add_child(piece)

	hallway.add_child(CorridorDressing.build(game.layout, &"D14-S-041"))
	hallway.add_child(CeilingProps.build(game.layout, &"D14-S-041"))

	var doors := Node3D.new()
	doors.name = "HallSideDoors"
	var by_solid_id: Dictionary = {}
	for id: StringName in game.layout.section(&"D14-S-041").side_door_ids():
		by_solid_id[StringName("%s/LEAF" % id)] = id
	for solid: ShipGeometry.SolidSpec in ShipGeometry.side_door_solids(game.layout):
		var spec := game.layout.door(by_solid_id[solid.id])
		var leaf := SlidingDoorModel.leaf(spec, 1, game.layout)
		doors.add_child(SlidingDoorModel.frame(spec))
		leaf.set_meta(&"solid_id", solid.id)
		hallway.side_leaves[by_solid_id[solid.id]] = leaf
		doors.add_child(leaf)
	hallway.add_child(doors)

	hallway.add_child(_build_switch())

	for fixture_transform: Transform3D in game.layout.section(&"D14-S-041").emergency_fixture_frames():
		hallway.add_child(hallway._fixture(fixture_transform, level))

	var white_level := 1.0 if game.power_active else 0.0
	hallway._white_lens_material = CeilingFixture.glass_material(white_level)
	var white_held: Intensity.Result = Intensity.FixtureFade.holding(white_level)
	assert(white_held.is_ok(), "the white strip level maps to a valid fade")
	hallway._white_fade = white_held.fade
	for frame: Transform3D in game.layout.section(&"D14-S-041").regular_light_frames():
		var fixture := hallway._white_fixture(frame, white_level)
		hallway.add_child(fixture)
	var section := game.layout.section(&"D14-S-041")
	for position: Vector3 in section.emergency_fill_positions():
		var fill := Lighting.emergency_fill(position, level, Lighting.HALL_FILL_MASK)
		fill.name = "EmergencyFill%d" % hallway._fill_lights.size()
		hallway.add_child(fill)
		hallway._fill_lights.append(fill)
	var bounce := Lighting.emergency_fill(section.emergency_end_fill_position(), level, Lighting.HALL_FILL_MASK, Lighting.EMERGENCY_END_FILL_SHARE, Lighting.EMERGENCY_END_FILL_COLOR)
	bounce.name = "EmergencyFillEnd"
	hallway.add_child(bounce)
	hallway._fill_lights.append(bounce)
	# Ceiling strips cannot directly light the downward arch. Reuse the
	# layout-owned end bounce on the regular circuit, leaving emergency off.
	hallway._white_end_fill = Lighting.regular_end_fill(section.emergency_end_fill_position(), white_level)
	hallway.add_child(hallway._white_end_fill)
	Lighting.mesh_layers(hallway, Lighting.architectural_mask(game.layout, section.id()))
	return hallway

## The fixture group mirrors the stasis bay's: a pair at every station
## standoff from both side walls, so the whole corridor reads one
## rhythm from the doorway to the power door.
static func fixture_transforms() -> Array[Transform3D]:
	return ShipLayout.authored().layout.section(&"D14-S-041").emergency_fixture_frames()

## The fixture group holds the light and the lens as siblings, exactly
## as the stasis bay's do, so no mesh bounds stand in for the light's
## influence volume.
func _fixture(fixture_transform: Transform3D, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "HallFixture"
	fixture.transform = fixture_transform
	var light := Lighting.switched_key(_game.layout.section(&"D14-S-041").emergency_light_role(), level)
	fixture.add_child(light)
	DressingMounts.ceiling_stem(fixture, _game.layout.section(&"D14-S-041").bounds().end.y, Surfaces.surface_frame(_game.layout, &"D14-S-041", &"CEILING"))
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "emergency")
	lens.mesh = _lens_mesh
	fixture.add_child(lens)
	_lights.append(light)
	_lenses.append(lens)
	return fixture

## One regular-service strip: a ceiling lens down the centerline with
## its light just beneath, dead until the secondary power hands the
## corridor over from emergency red.
func _white_fixture(frame: Transform3D, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "HallRegularStrip"
	fixture.transform = frame
	var light := OmniLight3D.new()
	light.light_color = Lighting.REGULAR_WHITE
	light.light_energy = Lighting.regular_energy() * level
	light.omni_range = Lighting.REGULAR_RANGE
	light.light_cull_mask = 1
	light.shadow_enabled = false
	light.position = Vector3(0.0, -0.12, 0.0)
	fixture.add_child(light)
	var lens := CeilingFixture.mount(fixture, _game.layout.section(&"D14-S-041").bounds().end.y, Lighting.architectural_mask(_game.layout, &"D14-S-041"), _white_lens_material)
	_white_lights.append(light)
	_white_lenses.append(lens)
	return fixture

## The fuel-stop switch beside the door: small dark plate, domed red
## pushbutton facing the hall. Plain albedo only — the dark hall hides
## it until the fixtures light.
static func _build_switch() -> Node3D:
	var group := Node3D.new()
	group.name = "HallSwitch"
	group.position = SWITCH_PLATE_CENTER
	group.basis = Basis(Vector3(0, 0, -1), Vector3.UP, Vector3.RIGHT)
	var plate := MeshInstance3D.new()
	plate.name = "Plate"
	var plate_mesh := BoxMesh.new()
	var wall_depth := ShipLayout.CORRIDOR_WIDTH / 2 - SWITCH_PLATE_CENTER.z
	var front := SWITCH_PLATE_SIZE.x / 2
	plate_mesh.size = Vector3(front + wall_depth, SWITCH_PLATE_SIZE.y, SWITCH_PLATE_SIZE.z)
	plate.position.x = (front - wall_depth) / 2
	plate.mesh = plate_mesh
	plate.material_override = _flat_grey(SWITCH_PLATE_SHADE)
	group.add_child(plate)
	var dome := MeshInstance3D.new()
	dome.name = "Dome"
	var dome_mesh := SphereMesh.new()
	dome_mesh.radius = SWITCH_DOME_RADIUS
	dome_mesh.height = SWITCH_DOME_RADIUS
	dome_mesh.is_hemisphere = true
	var cap := SurfaceTool.new()
	cap.begin(Mesh.PRIMITIVE_TRIANGLES)
	cap.append_from(dome_mesh, 0, Transform3D(Basis(Vector3.BACK, -PI / 2), Vector3(-SWITCH_DOME_RADIUS * 0.55 - 0.001, 0, 0)))
	dome.mesh = cap.commit()
	dome.position = Vector3(
		SWITCH_PLATE_SIZE.x / 2.0 + SWITCH_DOME_RADIUS * 0.55, 0.0, 0.0)
	var dome_material := StandardMaterial3D.new()
	dome_material.albedo_color = SWITCH_DOME_COLOR
	dome_material.roughness = 0.35
	dome.material_override = dome_material
	group.add_child(dome)
	var bezel_material := _flat_grey(0.20)
	bezel_material.metallic = 0.75
	bezel_material.roughness = 0.67
	var bezel := HatchModel.mesh_piece(HatchModel.cylinder(SWITCH_DOME_RADIUS * 1.15, 0.012), Transform3D(Basis(Vector3.BACK, -PI / 2), Vector3(front, 0, 0)), 1, bezel_material)
	bezel.name = "ButtonBezel"
	group.add_child(bezel)
	return group

## One render-bridge frame, mirroring the stasis bay's Lighting bridge:
## retarget only on the sim-side target change (the switch flip, the
## secondary power's activation), consume whole logical ticks from the
## elapsed seconds, then project both fade levels onto the fixture
## energies and the shared lens emissions. The emergency red holds its
## level while the corridor is on the switch; once the secondary power
## activates, the red hands off to the regular white strips. The sim's
## Game container is the only authority; this writes render state.
func process_frame(delta_secs: float) -> void:
	var red_target := 1.0 if (_game.hallway_lit and not _game.power_active) else 0.0
	var white_target := 1.0 if _game.power_active else 0.0
	if _fade.target() != red_target:
		_fade.retarget(red_target, Lighting.FIXTURE_SETTLE_TICKS)
	if _white_fade.target() != white_target:
		_white_fade.retarget(white_target, Lighting.FIXTURE_SETTLE_TICKS)
	_remainder += delta_secs
	while _remainder >= Sim.LOGICAL_TICK_SECS:
		_remainder -= Sim.LOGICAL_TICK_SECS
		_fade.tick()
		_white_fade.tick()
	_apply_level(_fade.intensity())
	_apply_white_level(_white_fade.intensity())

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

## Writes the regular strips' render state the same way.
func _apply_white_level(level: float) -> void:
	var energy: float = Lighting.regular_energy() * level
	_white_end_fill.apply_level(level)
	for light: OmniLight3D in _white_lights:
		if light.light_energy != energy:
			light.light_energy = energy
	var emissive := Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE * level
	if _white_lens_material.emission != emissive:
		_white_lens_material.emission = emissive

## The emergency red circuit's level: full while the switch lights the
## corridor, zero once the secondary power takes over.
func level() -> float:
	return _fade.intensity()

## The regular white strips' level.
func white_level() -> float:
	return _white_fade.intensity()

func is_settled() -> bool:
	return _fade.is_settled() and _white_fade.is_settled()

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

## One textured surface piece wearing the stasis room's shared material
## for its role — the same resource instance, never a copy.
static func _surface_instance(role: String, placement: Placement.SolidPlacement, layout: ShipLayout = ShipLayout.authored().layout) -> MeshInstance3D:
	assert(StringName(role) == placement.material_role, "surface role agrees with pure recipe")
	var piece := _box_instance(placement, Surfaces.material(placement.material_role), layout)
	Surfaces.bind_solid(piece, layout, placement)
	return piece

static func _box_instance(placement: Placement.SolidPlacement, material: Material, layout: ShipLayout = ShipLayout.authored().layout) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = SlidingDoorModel.wall_mesh(layout, placement) if placement.material_role == &"wall" else HatchModel.solid_mesh(placement)
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
