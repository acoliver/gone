extends SimTestCase
## Port of the engine-independent assertions from gone_app
## lighting_tests.rs: fixture placement from the registry, the fade
## settle counts with repeated-target stability, held/fractional frame
## timing, the bridge's no-write-to-grid boundary, the retired pod
## plates' absence, and the authored no-light environment.

func test_fixture_inventory_places_eight_red_lights_from_registry() -> void:
	var game := Game.new()
	var lighting := Lighting.build(game)
	var fixtures: Array[Node3D] = lighting.fixtures()
	var lights: Array[OmniLight3D] = lighting.lights()
	assert_int_equal(fixtures.size(), 8, "seven wall fixtures and one over the hatch")
	assert_int_equal(lights.size(), 8, "one light per fixture")
	var registry_pods: Array[Pods.Pod] = game.registry.pods()
	for index: int in range(registry_pods.size()):
		var placement := registry_pods[index].placement()
		var side := signf(placement.center.y)
		var expected := Vector3(
			placement.center.x,
			2.65,
			side * (Pods.ROOM_WIDTH / 2.0 - 0.10)
		)
		assert_vec3_equal(
			fixtures[index].position,
			expected,
			"wall fixture %d uses its registry pod's X and wall side" % index
		)
	var lintel: Placement.SolidPlacement = Placement.hatch_solids()[2]
	assert_vec3_equal(
		fixtures[7].position,
		lintel.center + Vector3(-0.10, 0.22, 0.0),
		"hatch fixture uses the lintel placement at 2.70 m"
	)
	for light: OmniLight3D in lights:
		assert_true(light.light_color == Color(1.0, 0.0, 0.0), "fixture color is linear red")
		assert_float_equal(light.omni_range, 6.0, "fixture range is 6 m")
		assert_false(light.shadow_enabled, "fixture shadows are disabled")
		assert_true(
			absf(light.light_energy - Lighting.FIXTURE_ENERGY) < 1e-4,
			"opening energy translates the authored 45 lumens"
		)
	for fixture: Node3D in fixtures:
		assert_true(fixture.position.y > 2.4, "fixtures sit outside the walking envelope")
	assert_int_equal(_count_class(lighting, "OmniLight3D"), 8, "the only omni lights are the fixtures")
	assert_int_equal(_count_class(lighting, "DirectionalLight3D"), 0, "no directional light is authored")
	assert_int_equal(_count_class(lighting, "SpotLight3D"), 0, "no spot light is authored")

func test_lenses_share_one_cuboid_and_never_ride_the_light_node() -> void:
	var lighting := Lighting.build(Game.new())
	var lenses: Array[MeshInstance3D] = lighting.lenses()
	assert_int_equal(lenses.size(), 8, "one lens per fixture")
	var shared_mesh: BoxMesh = lenses[0].mesh
	assert_vec3_equal(shared_mesh.size, Vector3(0.42, 0.16, 0.12), "lens cuboid is 0.42 x 0.16 x 0.12")
	for lens: MeshInstance3D in lenses:
		assert_true(lens.mesh == shared_mesh, "all lenses share one mesh resource")
		assert_true(
			shared_mesh.material == lighting.lens_material(),
			"all lenses share one material resource"
		)
		assert_false(
			lens.get_parent() is OmniLight3D,
			"a lens mesh never rides the light node itself"
		)
		assert_int_equal(
			lens.get_parent().get_child_count(),
			2,
			"fixture groups pair one light with one lens"
		)
	assert_true(
		lighting.lens_material().emission == Color(2.6, 0.0, 0.0),
		"full-power lens emission is linear (2.6, 0, 0)"
	)

func test_bridge_follows_sim_fade_and_repeated_dead_does_not_restart() -> void:
	var game := Game.new()
	var lighting := Lighting.build(game)
	_assert_output(lighting, 1.0)
	var material: StandardMaterial3D = lighting.lens_material()
	game.power.cut_emergency_power()
	lighting.process_frame(0.0)
	_assert_output(lighting, 1.0)
	var held: Intensity.Result = Intensity.FixtureFade.try_new(
		1.0, 0.0, Lighting.FIXTURE_SETTLE_TICKS
	)
	assert_true(held.is_ok(), "the mirror fade is valid")
	var mirror: Intensity.FixtureFade = held.fade
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		game.power.cut_emergency_power()
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
		var expected: float = mirror.tick()
		_assert_output(lighting, expected)
	assert_true(mirror.is_settled(), "the mirror fade settles at the settle tick")
	for _hold: int in range(20):
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
		_assert_output(lighting, 0.0)
	assert_true(
		lighting.lens_material() == material,
		"no material is allocated per tick"
	)
	assert_true(game.power.state() == Power.State.DEAD, "the grid holds Dead")

func test_held_frames_and_fractional_steps_obey_the_logical_clock() -> void:
	var game := Game.new()
	var lighting := Lighting.build(game)
	game.power.cut_emergency_power()
	for _hold: int in range(20):
		lighting.process_frame(0.0)
		_assert_output(lighting, 1.0)
	lighting.process_frame(Sim.LOGICAL_TICK_SECS / 2.0)
	_assert_output(lighting, 1.0)
	lighting.process_frame(Sim.LOGICAL_TICK_SECS / 2.0)
	var mirror: Intensity.FixtureFade = Intensity.FixtureFade.try_new(
		1.0, 0.0, Lighting.FIXTURE_SETTLE_TICKS
	).fade
	_assert_output(lighting, mirror.tick())
	lighting.process_frame(Sim.LOGICAL_TICK_SECS * 3.0)
	for _burst: int in range(3):
		mirror.tick()
	_assert_output(lighting, mirror.intensity())

func test_render_observations_cannot_change_power_and_are_projected_from_sim() -> void:
	var game := Game.new()
	var lighting := Lighting.build(game)
	for light: OmniLight3D in lighting.lights():
		light.light_energy = 0.0
	lighting.process_frame(0.0)
	assert_true(
		game.power.state() == Power.State.EMERGENCY,
		"the bridge never writes the grid"
	)
	_assert_output(lighting, 1.0)

func test_bridge_running_alone_never_changes_power() -> void:
	var game := Game.new()
	var lighting := Lighting.build(game)
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS * 2):
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(
		game.power.state() == Power.State.EMERGENCY,
		"only the sim's story layer moves power"
	)
	_assert_output(lighting, 1.0)
	game.power.cut_emergency_power()
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS):
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
	assert_true(game.power.state() == Power.State.DEAD, "the grid holds the test-delivered cut")
	_assert_output(lighting, 0.0)

func test_no_pod_indicator_plates_render_across_power_changes() -> void:
	var game := Game.new()
	var pods := StasisPods.build(game.registry)
	var plate_center: Vector3 = Placement.indicator_plate().center
	game.power.cut_emergency_power()
	var lighting := Lighting.build(game)
	for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS + 1):
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
		var plates := 0
		for group: Node in pods.get_children():
			for child: Node in group.get_children():
				if child is MeshInstance3D and (child as MeshInstance3D).position == plate_center:
					plates += 1
		assert_int_equal(plates, 0, "the retired indicator plates stay gone through the power cut")

func test_authored_environment_contributes_no_light() -> void:
	var lighting := Lighting.build(Game.new())
	var world: WorldEnvironment = _find_world_environment(lighting)
	if world == null:
		_fail("the lighting node authors a WorldEnvironment")
		return
	var environment: Environment = world.environment
	assert_true(
		environment.ambient_light_source == Environment.AMBIENT_SOURCE_DISABLED,
		"no ambient source is authored"
	)
	assert_float_equal(environment.ambient_light_energy, 0.0, "ambient energy is zero")
	assert_false(environment.fog_enabled, "fog stays off")
	assert_true(environment.background_color == Color(0.0, 0.0, 0.0), "the background is black")

## The bridge's projected output at one fade level: every light energy
## and the shared lens emission, matching assert_output in the Rust
## tests.
func _assert_output(lighting: Lighting, level: float) -> void:
	var energy: float = Lighting.FIXTURE_ENERGY * level
	var emission_red: float = Lighting.FIXTURE_EMISSIVE * level
	for light: OmniLight3D in lighting.lights():
		assert_true(
			absf(light.light_energy - energy) < 1e-4,
			"light energy tracks the fade: expected %.5f, got %.5f"
			% [energy, light.light_energy]
		)
	var emissive: Color = lighting.lens_material().emission
	assert_true(
		absf(emissive.r - emission_red) < 1e-5,
		"lens emission tracks the fade: expected %.5f, got %.5f"
		% [emission_red, emissive.r]
	)
	assert_float_equal(emissive.g, 0.0, "lens emission stays red")
	assert_float_equal(emissive.b, 0.0, "lens emission stays red")

func _count_class(node: Node, native_class: String) -> int:
	var total := 0
	if node.get_class() == native_class:
		total += 1
	for child: Node in node.get_children():
		total += _count_class(child, native_class)
	return total

func _find_world_environment(node: Node) -> WorldEnvironment:
	for child: Node in node.get_children():
		if child is WorldEnvironment:
			return child
	return null
