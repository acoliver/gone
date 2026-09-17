class_name Hazards
extends Node3D
## Greybox ceiling hazards near the torn cable runs: occasional
## short-lived electrical spark bursts (a strobed OmniLight3D flash plus
## a one-shot particle spray) and slow smoke hanging densest at the
## ceiling. GPUParticles3D is the chosen smoke path: a FogVolume height
## ramp needs a custom density shader, while a stock particle emitter
## with a ceiling emission box and slow fall drift is reliable in 4.7.2
## Forward+. Dressing only: no colliders, no sim role.

const SPARK_LIGHT_COLOR: Color = Color(1.5, 0.35, 0.1)
const SPARK_MIN_ENERGY: float = 2.5
const SPARK_MAX_ENERGY: float = 7.5
const SPARK_RANGE: float = 5.0
const SPARK_FLASH_SECS: float = 0.35
const SPARK_MIN_INTERVAL: float = 0.8
const SPARK_MAX_INTERVAL: float = 3.0
const SPARK_COUNT: int = 3
const SMOKE_FALL_SPEED: float = 0.12

var auto_bursts: bool = true
var _spark_lights: Array[OmniLight3D] = []
var _spark_particles: Array[GPUParticles3D] = []
var _flash_remaining: float = 0.0
var _next_burst_in: float = 1.5
var _active_index: int = -1
var _next_spot: int = 0
var _rng := RandomNumberGenerator.new()

static func build() -> Hazards:
	var hazards := Hazards.new()
	hazards.name = "Hazards"
	hazards._rng.randomize()
	var trays := Placement.cable_trays()
	assert(trays.size() >= SPARK_COUNT, "the authored ceiling damage carries spark spots")
	var spark_material := _spark_material()
	for index: int in range(SPARK_COUNT):
		var spot: Vector3 = trays[index].center + Vector3(0.0, -0.2, 0.0)
		hazards.add_child(hazards._spark_spot(spot, spark_material))
	hazards.add_child(hazards._smoke())
	return hazards

func _spark_spot(spot: Vector3, spark_material: StandardMaterial3D) -> Node3D:
	var group := Node3D.new()
	group.name = "SparkSpot"
	group.position = spot
	var light := OmniLight3D.new()
	light.light_color = SPARK_LIGHT_COLOR
	light.light_energy = 0.0
	light.omni_range = SPARK_RANGE
	light.shadow_enabled = false
	group.add_child(light)
	var particles := GPUParticles3D.new()
	particles.name = "SparkSpray"
	particles.one_shot = true
	particles.emitting = false
	particles.amount = 16
	particles.lifetime = 0.45
	particles.explosiveness = 1.0
	particles.process_material = _spark_process()
	particles.draw_pass_1 = _spark_draw_pass(spark_material)
	group.add_child(particles)
	_spark_lights.append(light)
	_spark_particles.append(particles)
	return group

## The smoke emitter: particles spawn in a thin ceiling-high box, drift
## slowly downward, and preprocess so the haze exists from the first
## captured frame. Density falls off away from the ceiling because the
## spawn volume itself hugs the ceiling.
func _smoke() -> GPUParticles3D:
	var smoke := GPUParticles3D.new()
	smoke.name = "CeilingSmoke"
	smoke.position = Vector3(0.0, 3.0, 0.0)
	smoke.amount = 48
	smoke.lifetime = 7.0
	smoke.preprocess = 6.0
	smoke.visibility_aabb = AABB(Vector3(-6.5, -3.5, -4.5), Vector3(13.0, 5.0, 9.0))
	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(5.0, 0.2, 2.5)
	process.direction = Vector3(0.0, -1.0, 0.0)
	process.spread = 25.0
	process.initial_velocity_min = SMOKE_FALL_SPEED * 0.5
	process.initial_velocity_max = SMOKE_FALL_SPEED
	process.gravity = Vector3(0.0, -0.05, 0.0)
	process.angular_velocity_min = -0.4
	process.angular_velocity_max = 0.4
	process.scale_min = 1.0
	process.scale_max = 1.8
	smoke.process_material = process
	var quad := QuadMesh.new()
	quad.size = Vector2(1.4, 1.0)
	quad.material = _smoke_material()
	smoke.draw_pass_1 = quad
	return smoke

func _physics_process(delta: float) -> void:
	if _flash_remaining > 0.0:
		_flash_remaining = maxf(_flash_remaining - delta, 0.0)
		if _flash_remaining == 0.0:
			_spark_lights[_active_index].light_energy = 0.0
		else:
			_strobe()
	if not auto_bursts:
		return
	_next_burst_in -= delta
	if _next_burst_in <= 0.0:
		fire_burst()

## Fire a burst now, cycling the spark spots deterministically. The
## capture smoke uses this to stage a spark-active frame.
func fire_burst() -> void:
	_active_index = _next_spot
	_next_spot = (_next_spot + 1) % _spark_lights.size()
	_flash_remaining = SPARK_FLASH_SECS
	_strobe()
	_spark_particles[_active_index].restart()
	_next_burst_in = _rng.randf_range(SPARK_MIN_INTERVAL, SPARK_MAX_INTERVAL)

func is_spark_active() -> bool:
	return _flash_remaining > 0.0

## The strobe: rapid random energy flicker for the flash's life.
func _strobe() -> void:
	_spark_lights[_active_index].light_energy = _rng.randf_range(
		SPARK_MIN_ENERGY, SPARK_MAX_ENERGY
	)

static func _spark_process() -> ParticleProcessMaterial:
	var process := ParticleProcessMaterial.new()
	process.direction = Vector3(0.0, -1.0, 0.0)
	process.spread = 180.0
	process.initial_velocity_min = 1.5
	process.initial_velocity_max = 3.5
	process.gravity = Vector3(0.0, -7.0, 0.0)
	process.scale_min = 0.6
	process.scale_max = 1.0
	return process

static func _spark_draw_pass(spark_material: StandardMaterial3D) -> QuadMesh:
	var quad := QuadMesh.new()
	quad.size = Vector2(0.05, 0.05)
	quad.material = spark_material
	return quad

## Tiny unshaded red-orange embers; redder than white arcs so a lit
## capture keeps its red channel dominance.
static func _spark_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.emission_enabled = true
	material.emission = Color(2.0, 0.55, 0.2)
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	return material

## Smoke is a lit translucent grey with a whisper of red emission so it
## reads under the emergency fixtures without becoming a light source.
static func _smoke_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(0.22, 0.21, 0.21, 0.16)
	material.emission_enabled = true
	material.emission = Color(0.05, 0.0, 0.0)
	material.roughness = 1.0
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	return material
