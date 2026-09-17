class_name Lighting
extends Node3D
## Emergency fixtures and the read-only power bridge, ported from
## gone_app lighting.rs (issue #10): eight red OmniLight3D fixtures —
## seven wall-mounted above each registry pod plus one over the hatch
## lintel — with shared lens cuboids whose single emissive material the
## FixtureFade bridge interpolates. The bridge reads the Game's PowerGrid
## and never writes it. Ambient stays black, fog stays off, and the room
## authors no other light source. The sim is authoritative.

const FIXTURE_LUMENS: float = 45.0
const FIXTURE_RANGE: float = 6.0
const FIXTURE_EMISSIVE: float = 2.6
const FIXTURE_SETTLE_TICKS: int = 30
const EMERGENCY_RED: Color = Color(1.0, 0.0, 0.0)
const LENS_SIZE: Vector3 = Vector3(0.42, 0.16, 0.12)
const LENS_BASE_COLOR: Color = Color(0.18, 0.01, 0.01)
const WALL_MOUNT_HEIGHT: float = 2.65
const WALL_STANDOFF: float = 0.10
## Lumen->energy: 45 lm / (4*pi) ~= 3.58 candela, read directly as
## OmniLight3D energy under Godot's non-physical omni falloff.
const FIXTURE_ENERGY: float = FIXTURE_LUMENS / (2.0 * TAU)
## Plain exposure multiplier standing in for the Rust slice's EV100 0.
const EXPOSURE_MULTIPLIER: float = 2.0

var _grid: Power.Grid = null
var _fade: Intensity.FixtureFade = null
var _fixtures: Array[Node3D] = []
var _lights: Array[OmniLight3D] = []
var _lenses: Array[MeshInstance3D] = []
var _lens_mesh: BoxMesh = null
var _lens_material: StandardMaterial3D = null
var _remainder: float = 0.0

static func build(game: Game) -> Lighting:
	var lighting := Lighting.new()
	lighting.name = "Lighting"
	lighting._grid = game.power
	var level: float = game.emergency_circuit_target()
	lighting._lens_mesh = BoxMesh.new()
	lighting._lens_mesh.size = LENS_SIZE
	lighting._lens_material = StandardMaterial3D.new()
	lighting._lens_material.albedo_color = LENS_BASE_COLOR
	lighting._lens_material.emission = Color(FIXTURE_EMISSIVE * level, 0.0, 0.0)
	lighting._lens_material.roughness = 0.8
	lighting._lens_mesh.material = lighting._lens_material
	var held: Intensity.Result = Intensity.FixtureFade.holding(level)
	assert(held.is_ok(), "power maps to a finite nonnegative level")
	lighting._fade = held.fade
	for fixture_transform: Transform3D in fixture_transforms(game.registry):
		lighting.add_child(lighting._fixture(fixture_transform, level))
	lighting.add_child(_world_environment())
	return lighting

## One wall fixture above each registry pod and one above the existing
## hatch lintel. All sit outside the standing envelope; route solids are
## untouched.
static func fixture_transforms(registry: Pods.PodRegistry) -> Array[Transform3D]:
	var transforms: Array[Transform3D] = []
	for pod: Pods.Pod in registry.pods():
		var placement := pod.placement()
		var side := signf(placement.center.y)
		transforms.append(
			Transform3D(
				Basis(),
				Vector3(
					placement.center.x,
					WALL_MOUNT_HEIGHT,
					side * (Pods.ROOM_WIDTH / 2.0 - WALL_STANDOFF)
				)
			)
		)
	var lintel: Placement.SolidPlacement = Placement.hatch_solids()[2]
	transforms.append(
		Transform3D(
			Basis(Vector3.UP, PI / 2.0),
			lintel.center + Vector3(-WALL_STANDOFF, 0.22, 0.0)
		)
	)
	return transforms

## The fixture group holds the light and the lens as siblings. The lens
## never rides on the OmniLight3D node itself, so no mesh bounds can
## stand in for the light's influence volume (culling parity with the
## Rust fix).
func _fixture(fixture_transform: Transform3D, level: float) -> Node3D:
	var fixture := Node3D.new()
	fixture.name = "EmergencyFixture"
	fixture.transform = fixture_transform
	var light := OmniLight3D.new()
	light.light_color = EMERGENCY_RED
	light.light_energy = FIXTURE_ENERGY * level
	light.omni_range = FIXTURE_RANGE
	light.shadow_enabled = false
	fixture.add_child(light)
	var lens := MeshInstance3D.new()
	lens.name = "Lens"
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

func _physics_process(_delta: float) -> void:
	process_frame(Sim.LOGICAL_TICK_SECS)

## One render-bridge frame: retarget only on a sim-side target change,
## consume whole logical ticks from the elapsed seconds, then project
## the fade level onto the light energies and the shared lens emission.
## Held frames (zero delta) retarget without ticking; fractional deltas
## accumulate, so batching cannot change a value.
func process_frame(delta_secs: float) -> void:
	var target: float = _circuit_target()
	if _fade.target() != target:
		_fade.retarget(target, FIXTURE_SETTLE_TICKS)
	_remainder += delta_secs
	while _remainder >= Sim.LOGICAL_TICK_SECS:
		_remainder -= Sim.LOGICAL_TICK_SECS
		_fade.tick()
	_apply_level(_fade.intensity())

func _circuit_target() -> float:
	return 1.0 if Power.emergency_fixtures_lit(_grid.state()) else 0.0

## Writes render state only, and only when a value actually changed: no
## per-tick material allocation.
func _apply_level(level: float) -> void:
	var energy: float = FIXTURE_ENERGY * level
	for light: OmniLight3D in _lights:
		if light.light_energy != energy:
			light.light_energy = energy
	var emissive := Color(FIXTURE_EMISSIVE * level, 0.0, 0.0)
	if _lens_material.emission != emissive:
		_lens_material.emission = emissive

func level() -> float:
	return _fade.intensity()

func is_settled() -> bool:
	return _fade.is_settled()

func fixtures() -> Array[Node3D]:
	return _fixtures

func lights() -> Array[OmniLight3D]:
	return _lights

func lenses() -> Array[MeshInstance3D]:
	return _lenses

func lens_material() -> StandardMaterial3D:
	return _lens_material
