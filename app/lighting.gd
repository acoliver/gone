class_name Lighting
extends Node3D
## Emergency fixtures and the read-only power bridge, ported from
## gone_app lighting.rs (issue #10): eight red OmniLight3D fixtures —
## seven wall-mounted above each registry pod plus one over the hatch
## lintel — with shared lens cuboids whose single emissive material the
## FixtureFade bridge interpolates. Secondary power hands these fixtures
## over to six regular white ceiling strips. The bridge only reads Game;
## ambient stays black and fog stays off.

const FIXTURE_LUMENS: float = 45.0
const FIXTURE_RANGE: float = 6.0
const EMERGENCY_POOL_RANGE: float = 2.5
const FIXTURE_ATTENUATION: float = 3.0
const BAY_POOL_RANGE: float = 3.5
const BAY_POOL_ATTENUATION: float = 1.0
const BAY_HATCH_POOL_RANGE: float = 5.5
const BAY_HATCH_ATTENUATION: float = 1.0
const FIXTURE_EMISSIVE: float = 2.6
const FIXTURE_SETTLE_TICKS: int = 30
const EMERGENCY_RED: Color = Color(1.0, 0.28, 0.12)
const EMERGENCY_ENERGY_MULTIPLIER: float = 1.0
# Independent rooms have no fill; stronger keys restore readability on the darker steel.
const EMERGENCY_NO_FILL_KEY_MULTIPLIER: float = 1.916
const EMERGENCY_FILL_SHARE: float = 0.28
const EMERGENCY_BAY_FILL_SHARE: float = 0.56
const EMERGENCY_FILL_COLOR: Color = Color(1.0, 0.97, 0.92)
const EMERGENCY_END_FILL_SHARE: float = 0.84
const EMERGENCY_END_FILL_COLOR: Color = Color(1.0, 0.80, 0.62)
const EMERGENCY_FILL_RANGE: float = 4.0
const SMOKE_EMISSION_STRENGTH: float = 0.03
const SMOKE_EMISSION: Color = Color(EMERGENCY_RED.r * SMOKE_EMISSION_STRENGTH, EMERGENCY_RED.g * SMOKE_EMISSION_STRENGTH, EMERGENCY_RED.b * SMOKE_EMISSION_STRENGTH)
# Layers 18-20 belong only to the three switched-room fills.
const BAY_FILL_MASK: int = 1 << 17
const HALL_FILL_MASK: int = 1 << 18
const POWER_FILL_MASK: int = 1 << 19
const LENS_SIZE: Vector3 = Vector3(0.42, 0.16, 0.12)
const LENS_BASE_COLOR: Color = Color(0.18, 0.05, 0.025)

static func emergency_energy() -> float:
	return FIXTURE_ENERGY * EMERGENCY_ENERGY_MULTIPLIER

static func bind_smoke_emission(material: ShaderMaterial) -> void:
	material.set_shader_parameter("emission_tint", SMOKE_EMISSION)
	assert(material.get_shader_parameter("emission_tint") == SMOKE_EMISSION, "smoke material requires the shared emission policy")

static func emergency_emission(level: float) -> Color:
	var emission := EMERGENCY_RED * FIXTURE_EMISSIVE * level
	emission.a = 1.0
	return emission

static func emergency_lens_material(level: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = LENS_BASE_COLOR
	material.emission_enabled = true
	material.emission = emergency_emission(level)
	material.roughness = 0.8
	return material

class EmergencyFill:
	extends OmniLight3D
	var energy_share: float
	func apply_level(level: float) -> void:
		light_energy = Lighting.emergency_energy() * energy_share * level

static func emergency_fill(origin: Vector3, level: float, room_mask: int, share: float = EMERGENCY_FILL_SHARE, color: Color = EMERGENCY_FILL_COLOR) -> EmergencyFill:
	var fill := EmergencyFill.new()
	fill.name = "EmergencyFill"
	fill.position = origin
	fill.light_color = color
	fill.energy_share = share
	fill.apply_level(level)
	fill.omni_range = EMERGENCY_FILL_RANGE
	fill.light_cull_mask = room_mask
	fill.shadow_enabled = false
	return fill
## The regular-service white the activated secondary power restores
## (issue #59): warm-neutral strips in the hallway and the power room,
## dim by design, shared by the bay, hallway and power room.
const REGULAR_WHITE: Color = Color(1.0, 0.97, 0.90)
const REGULAR_EMISSIVE: float = 1.1
const REGULAR_RANGE: float = 7.0
## What share of an emergency fixture's throw a regular strip holds
## once lit: the "dim but regular" brief.
const REGULAR_DIM_SHARE: float = 0.55
const REGULAR_END_FILL_SHARE: float = 0.12

class RegularEndFill:
	extends OmniLight3D
	func apply_level(level: float) -> void:
		light_energy = Lighting.regular_energy() * Lighting.REGULAR_END_FILL_SHARE * level

static func regular_end_fill(origin: Vector3, level: float) -> RegularEndFill:
	var fill := RegularEndFill.new()
	fill.name = "RegularFillEnd"
	fill.position = origin
	fill.light_color = REGULAR_WHITE
	fill.omni_range = EMERGENCY_FILL_RANGE
	fill.light_cull_mask = HALL_FILL_MASK
	fill.shadow_enabled = false
	fill.apply_level(level)
	return fill

## A lit regular strip's omni energy, one definition for every module.
static func regular_energy() -> float:
	return FIXTURE_ENERGY * REGULAR_DIM_SHARE
const WALL_MOUNT_HEIGHT: float = 2.65
const WALL_STANDOFF: float = 0.10
## Lumen->energy: 45 lm / (4*pi) ~= 3.58 candela, read directly as
## OmniLight3D energy under Godot's non-physical omni falloff.
const FIXTURE_ENERGY: float = FIXTURE_LUMENS / (2.0 * TAU)
## Plain exposure multiplier standing in for the Rust slice's EV100 0.
const EXPOSURE_MULTIPLIER: float = 2.0

var _game: Game
var _white_fade: Intensity.FixtureFade
var _white_lights: Array[OmniLight3D] = []
var _white_lens_material: StandardMaterial3D
var _fade: Intensity.FixtureFade = null
var _fixtures: Array[Node3D] = []
var _fixtures_by_id: Dictionary[StringName, Node3D] = {}
var _lights: Array[OmniLight3D] = []
var _fill_lights: Array[Lighting.EmergencyFill] = []
var _lenses: Array[MeshInstance3D] = []
var _lens_mesh: BoxMesh = null
var _lens_material: StandardMaterial3D = null
var _remainder: float = 0.0

static func build(game: Game) -> Lighting:
	var lighting := Lighting.new()
	lighting.name = "Lighting"
	lighting._game = game
	var level: float = lighting._circuit_target()
	lighting._lens_mesh = BoxMesh.new()
	lighting._lens_mesh.size = LENS_SIZE
	lighting._lens_material = emergency_lens_material(level)
	lighting._lens_mesh.material = lighting._lens_material
	var held: Intensity.Result = Intensity.FixtureFade.holding(level)
	assert(held.is_ok(), "power maps to a finite nonnegative level")
	lighting._fade = held.fade
	for spec: ShipLayout.EmergencyFixtureSpec in game.layout.bay().emergency_fixtures(game.registry):
		lighting.add_child(lighting._fixture(spec, level))
	var hatch_key := lighting.fixture(ShipLayout.BAY_HATCH_KEY_ID)
	assert(hatch_key.get_meta(&"light_role") == ShipLayout.EmergencyLightRole.BAY_HATCH, "bay hatch identity requires the doorway profile")
	var white_level := 1.0 if game.power_active else 0.0
	lighting._white_fade = Intensity.FixtureFade.holding(white_level).fade
	lighting._white_lens_material = StandardMaterial3D.new()
	lighting._white_lens_material.albedo_color = Hallway.REGULAR_LENS_BASE_COLOR
	lighting._white_lens_material.emission_enabled = true
	lighting._white_lens_material.roughness = 0.8
	var white_mesh := BoxMesh.new()
	white_mesh.size = Hallway.REGULAR_LENS_SIZE
	white_mesh.material = lighting._white_lens_material
	var fill_positions := game.layout.bay().emergency_fill_positions()
	for frame: Transform3D in game.layout.bay().regular_light_frames():
		lighting.add_child(lighting._white_fixture(frame, white_mesh))
		var fill := emergency_fill(fill_positions[lighting._fill_lights.size()], level, BAY_FILL_MASK, EMERGENCY_BAY_FILL_SHARE)
		fill.name = "EmergencyFill%d" % lighting._fill_lights.size()
		lighting.add_child(fill)
		lighting._fill_lights.append(fill)
	lighting._apply_white_level(white_level)
	lighting.add_child(_world_environment())
	return lighting

static func switched_key(role: ShipLayout.EmergencyLightRole, level: float) -> OmniLight3D:
	var light := OmniLight3D.new()
	match role:
		ShipLayout.EmergencyLightRole.BAY_POOL:
			light.omni_range = BAY_POOL_RANGE
			light.omni_attenuation = BAY_POOL_ATTENUATION
		ShipLayout.EmergencyLightRole.BAY_HATCH:
			light.omni_range = BAY_HATCH_POOL_RANGE
			light.omni_attenuation = BAY_HATCH_ATTENUATION
		ShipLayout.EmergencyLightRole.ROOM_POOL:
			light.omni_range = EMERGENCY_POOL_RANGE
			light.omni_attenuation = FIXTURE_ATTENUATION
		_:
			assert(false, "switched emergency key requires an authored role")
	light.light_color = EMERGENCY_RED
	light.light_energy = emergency_energy() * level
	light.light_cull_mask = 1
	light.shadow_enabled = false
	return light

## The fixture group holds the light and the lens as siblings. The lens
## never rides on the OmniLight3D node itself, so no mesh bounds can
## stand in for the light's influence volume (culling parity with the
## Rust fix).
func _fixture(spec: ShipLayout.EmergencyFixtureSpec, level: float) -> Node3D:
	assert(not _fixtures_by_id.has(spec.id), "emergency fixture identity is unique")
	var fixture := Node3D.new()
	fixture.name = "EmergencyFixture"
	fixture.transform = spec.frame
	fixture.set_meta(&"fixture_id", spec.id)
	fixture.set_meta(&"light_role", spec.role)
	_fixtures_by_id[spec.id] = fixture
	var light := switched_key(spec.role, level)
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "emergency")
	lens.mesh = _lens_mesh
	fixture.add_child(lens)
	_fixtures.append(fixture)
	_lights.append(light)
	_lenses.append(lens)
	return fixture

## Black room: ambient source disabled, black background, fog off. The
## exposure multiplier is sized for the dim red emitters.
static func _world_environment() -> WorldEnvironment:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.0, 0.0, 0.0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.ambient_light_color = Color(0.0, 0.0, 0.0)
	environment.ambient_light_energy = 0.0
	environment.fog_enabled = false
	var attributes := CameraAttributes.new()
	attributes.exposure_multiplier = EXPOSURE_MULTIPLIER
	var world := WorldEnvironment.new()
	world.name = "RoomEnvironment"
	world.environment = environment
	world.camera_attributes = attributes
	return world

## One render-bridge frame: retarget only on a sim-side target change,
## consume whole logical ticks from the elapsed seconds, then project
## the fade level onto the light energies and the shared lens emission.
## Held frames (zero delta) retarget without ticking; fractional deltas
## accumulate, so batching cannot change a value.
func process_frame(delta_secs: float) -> void:
	var target: float = _circuit_target()
	if _fade.target() != target:
		_fade.retarget(target, FIXTURE_SETTLE_TICKS)
	var white_target := 1.0 if _game.power_active else 0.0
	if _white_fade.target() != white_target:
		_white_fade.retarget(white_target, FIXTURE_SETTLE_TICKS)
	_remainder += delta_secs
	while _remainder >= Sim.LOGICAL_TICK_SECS:
		_remainder -= Sim.LOGICAL_TICK_SECS
		_fade.tick()
		_white_fade.tick()
	_apply_level(_fade.intensity())
	_apply_white_level(_white_fade.intensity())

func _circuit_target() -> float:
	return 0.0 if _game.power_active else _game.emergency_circuit_target()

func _white_fixture(frame: Transform3D, mesh: BoxMesh) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "BayRegularStrip"
	fixture.transform = frame
	var light := OmniLight3D.new()
	light.light_color = REGULAR_WHITE
	light.omni_range = REGULAR_RANGE
	light.light_cull_mask = 1
	light.shadow_enabled = false
	light.position.y = -0.12
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "white")
	lens.mesh = mesh
	fixture.add_child(lens)
	_white_lights.append(light)
	return fixture

func _apply_white_level(level: float) -> void:
	for light: OmniLight3D in _white_lights:
		light.light_energy = regular_energy() * level
	_white_lens_material.emission = REGULAR_WHITE * REGULAR_EMISSIVE * level

func white_level() -> float:
	return _white_fade.intensity()

func white_lights() -> Array[OmniLight3D]:
	return _white_lights

func white_lens_material() -> StandardMaterial3D:
	return _white_lens_material

## Writes render state only, and only when a value actually changed: no
## per-tick material allocation.
func _apply_level(level: float) -> void:
	var energy: float = emergency_energy() * level
	for light: OmniLight3D in _lights:
		if light.light_energy != energy:
			light.light_energy = energy
	for fill: Lighting.EmergencyFill in _fill_lights:
		fill.apply_level(level)
	var emissive := emergency_emission(level)
	if _lens_material.emission != emissive:
		_lens_material.emission = emissive

func level() -> float:
	return _fade.intensity()

func is_settled() -> bool:
	return _fade.is_settled() and _white_fade.is_settled()

func fixtures() -> Array[Node3D]:
	return _fixtures

func fixture(id: StringName) -> Node3D:
	assert(_fixtures_by_id.has(id), "layout-owned emergency fixture must exist: %s" % id)
	return _fixtures_by_id[id]

func lights() -> Array[OmniLight3D]:
	return _lights

func lenses() -> Array[MeshInstance3D]:
	return _lenses

func lens_material() -> StandardMaterial3D:
	return _lens_material

static func architectural_mask(layout: ShipLayout, id: StringName) -> int:
	var mask := space_mask(layout, id)
	if layout.architectural_light_role(id) == ShipLayout.ArchitecturalLightRole.HALL_FILL:
		mask |= HALL_FILL_MASK
	return mask

static func space_mask(layout: ShipLayout, id: StringName) -> int:
	if id == &"D14-S-040":
		return 2
	if id == &"D14-S-042":
		return 4
	if id in layout.deck(14).connector_ids():
		return 8 << layout.connector(id).pitch_index()
	if id in layout.connector_ids():
		var spec := layout.connector(id)
		return 1 << (5 + spec.pitch_index() * 5 + (spec.deck_number() - 1) % 5)
	# Inaccessible faces on remote decks use the same local circuit.
	if String(id).begins_with("D") and "-S-" in String(id):
		var deck := String(id).substr(1, 2).to_int()
		if deck != 14:
			# Alternate remote section faces by deck; keep layers 18-20 for fills.
			return 1 << (15 + (deck - 1) % 2)
	return 1

static func mesh_layers(node: Node, mask: int) -> void:
	if node is GeometryInstance3D:
		node.layers = mask
	for child: Node in node.get_children():
		mesh_layers(child, mask)

static func isolate_lights(node: Node, mask: int) -> void:
	if node is Light3D:
		node.light_cull_mask = mask
	for child: Node in node.get_children():
		isolate_lights(child, mask)

static func steady_fixture(origin: Vector3, mask: int, radius: float, attenuation: float = 1.0) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "EmergencyFixture"
	fixture.position = origin
	var light := OmniLight3D.new()
	light.light_color = EMERGENCY_RED
	light.light_energy = emergency_energy() * EMERGENCY_NO_FILL_KEY_MULTIPLIER
	light.omni_range = radius
	light.omni_attenuation = attenuation
	light.light_cull_mask = mask
	light.shadow_enabled = false
	fixture.add_child(light)
	var material := emergency_lens_material(1.0)
	var lens := HatchModel.mesh_piece(Hallway._box_mesh(LENS_SIZE), Transform3D.IDENTITY, mask, material)
	lens.name = "Lens"
	lens.set_meta(&"lamp_circuit", "emergency")
	fixture.add_child(lens)
	return fixture
