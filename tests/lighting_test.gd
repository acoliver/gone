extends SimTestCase
## Port of the engine-independent assertions from gone_app
## lighting_tests.rs: fixture placement from the registry, the fade
## settle counts with repeated-target stability, held/fractional frame
## timing, the bridge's no-write-to-grid boundary, the retired pod
## plates' absence, and the authored no-light environment.

func test_bay_handoff_matches_hallway_without_darkness() -> void:
	var game := Game.new(71)
	game.light_hallway()
	var bay := Lighting.build(game)
	var hall := Hallway.build(game)
	game.press_console()
	game.press_console()
	for _tick in range(Lighting.FIXTURE_SETTLE_TICKS):
		bay.process_frame(Sim.LOGICAL_TICK_SECS)
		hall.process_frame(Sim.LOGICAL_TICK_SECS)
		assert_float_equal(bay.level(), hall.level(), "red handoff matches hallway")
		assert_float_equal(bay.white_level(), hall.white_level(), "white handoff matches hallway")
		assert_float_equal(bay.level() + bay.white_level(), 1.0, "no blackout in handoff")
	_assert_output(bay, 0.0)
	assert_float_equal(bay.white_level(), 1.0, "white settles lit")
	for light: SpotLight3D in bay.white_lights():
		assert_true(light.light_color == Lighting.REGULAR_WHITE, "regular white color")
		assert_true(is_equal_approx(light.light_energy, Lighting.regular_energy()), "regular white energy")
	assert_true(bay.white_lens_material().emission == Lighting.REGULAR_WHITE * Lighting.REGULAR_EMISSIVE, "white lenses glow")
	assert_true(bay.is_settled(), "both bay circuits settle")
	var rebuilt := Lighting.build(game)
	assert_float_equal(rebuilt.level(), 0.0, "powered scene does not rebuild red")
	assert_float_equal(rebuilt.white_level(), 1.0, "powered scene rebuilds white")
	bay.free()
	hall.free()
	rebuilt.free()

func test_connectors_and_outer_sections_keep_their_steady_red_circuits() -> void:
	var game := Game.new(71)
	var nodes: Array[Node3D] = []
	for id: StringName in game.layout.deck(14).connector_ids():
		nodes.append(ShipConnector.build(game.layout, game.layout.connector(id)))
	for number: int in [40, 42]:
		nodes.append(ShipSection.build(game.layout, game.layout.section(ShipLayout.section_id(14, number))))
	game.press_console()
	game.press_console()
	for node: Node3D in nodes:
		var lights := node.find_children("*", "OmniLight3D", true, false)
		assert_true(not lights.is_empty(), "room has emergency fixtures")
		for light: OmniLight3D in lights:
			assert_true(light.light_color == Lighting.EMERGENCY_RED, "independent circuit stays red")
			assert_true(is_equal_approx(light.light_energy, Lighting.FIXTURE_ENERGY * Lighting.EMERGENCY_NO_FILL_KEY_MULTIPLIER), "independent circuit stays steady")
			assert_true(light.light_cull_mask != 1, "independent circuit stays isolated from bay")
		node.free()

func test_fixture_inventory_places_eight_red_lights_from_registry() -> void:
	var game := Game.new(0)
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
			([-4.8, -1.6, 1.6, 4.8][index] if index < 4 else [-4.0, 0.0, 4.0][index - 4]),
			2.5,
			side * (Pods.ROOM_WIDTH / 2.0 - 0.10)
		)
		assert_vec3_equal(
			fixtures[index].position,
			expected,
			"architectural fixture %d stays on the wall; separate pod keys follow #88's inset" % index
		)
	var lintel: Placement.SolidPlacement = Placement.hatch_solids()[2]
	assert_vec3_equal(
		lighting.fixture(ShipLayout.BAY_HATCH_KEY_ID).position,
		lintel.center + Vector3(-0.10, 0.22, 0.0),
		"hatch fixture uses the lintel placement at 2.70 m"
	)
	for light: OmniLight3D in lights:
		assert_float_equal(light.light_color.r, 1.0, "merged source retains full red output")
		var index := lights.find(light)
		assert_float_equal(light.omni_range, 5.5 if index == 7 else EmergencyFixtureProfile.BAY[index].z, "throw belongs to the consolidated wall profile")
		assert_false(light.shadow_enabled, "fixture shadows are disabled")
		assert_true(
			absf(light.light_energy - Lighting.FIXTURE_ENERGY * float(light.get_meta(&"energy_share"))) < 1e-4,
			"opening energy translates the authored 45 lumens"
		)
	for fixture: Node3D in fixtures:
		assert_true(fixture.position.y > 2.4, "fixtures sit outside the walking envelope")
	assert_int_equal(_count_class(lighting, "OmniLight3D"), 8 + 6 * Pods.POD_COUNT, "eight single-source wall keys and six status spill samples per pod")
	assert_int_equal(lighting.find_children("*", "Light3D", true, false).size(), 14 + 6 * Pods.POD_COUNT, "eight single-source cages, six regular beams and status-belt samples")
	for light: SpotLight3D in lighting.white_lights():
		assert_float_equal(light.light_energy, 0.0, "regular strips start dark")
	assert_int_equal(_count_class(lighting, "DirectionalLight3D"), 0, "no directional light is authored")
	assert_int_equal(_count_class(lighting, "SpotLight3D"), 6, "six unchanged downward regular beams")

func test_lenses_share_rounded_glass_inside_weathered_cages() -> void:
	var lighting := Lighting.build(Game.new(0))
	var lenses := lighting.lenses()
	assert_int_equal(lenses.size(), 8, "one lens per fixture")
	var shared_mesh := lenses[0].mesh
	assert_false(shared_mesh is BoxMesh, "a bare cuboid cannot stand in for a lamp")
	assert_close(shared_mesh.get_aabb().size, Vector3(0.26, 0.16, 0.07), "rounded hatch glass dimensions")
	for lens: MeshInstance3D in lenses:
		assert_true(lens.mesh == shared_mesh, "all cages reuse the same glass geometry")
		assert_true(lens.material_override == lighting.lens_material(), "cages share their circuit material")
		assert_false(lens.get_parent() is OmniLight3D, "wall glass and key remain siblings")
		assert_int_equal(lens.get_parent().get_child_count(), 3, "light, rounded glass and caged housing with integrated stock")
		assert_true(lens.get_parent().get_child(0) is OmniLight3D, "key remains first child")
		assert_true(_wall_contact(lens.get_parent().get_node("Steel"), lighting._game.layout), "native hatch bracket reaches the wall")
		assert_true(lens.get_parent().get_node("Steel") is MeshInstance3D, "rounded housing and protective grille are present")
	var expected := Lighting.EMERGENCY_RED * Lighting.FIXTURE_EMISSIVE
	expected.a = 1.0
	assert_true(lighting.lens_material().emission == expected, "full-power lens retains the approved output")
	lighting.free()

func test_cage_and_its_mount_share_one_weathered_draw_surface() -> void:
	var lighting := Lighting.build(Game.new(0))
	for lens: MeshInstance3D in lighting.lenses():
		var fixture := lens.get_parent()
		var steel: MeshInstance3D = fixture.get_node("Steel")
		assert_int_equal(steel.mesh.get_surface_count(), 1, "cage and stock share one draw surface")
		assert_true(steel.mesh.has_meta(&"service_bounds"), "housing retains each wall fitting's physical bounds")
		assert_true(_wall_contact(steel, lighting._game.layout), "one weathered draw includes the physical wall bracket")
		assert_false(fixture.has_node("CeilingMount"), "stock is rendered in the housing, not a second draw")
	lighting.free()

func test_bridge_follows_sim_fade_and_repeated_dead_does_not_restart() -> void:
	var game := Game.new(0)
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
	var game := Game.new(0)
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
	var game := Game.new(0)
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
	var game := Game.new(0)
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
	var game := Game.new(0)
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
	var lighting := Lighting.build(Game.new(0))
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
			absf(light.light_energy - energy * float(light.get_meta(&"energy_share"))) < 1e-4,
			"light energy tracks the fade: expected %.5f, got %.5f"
			% [energy, light.light_energy]
		)
	var emissive: Color = lighting.lens_material().emission
	assert_true(
		absf(emissive.r - emission_red) < 1e-5,
		"lens emission tracks the fade: expected %.5f, got %.5f"
		% [emission_red, emissive.r]
	)
	var palette_emission := Color(1.0, 0.28, 0.12) * Lighting.FIXTURE_EMISSIVE * level
	assert_float_equal(emissive.g, palette_emission.g, "lens emission follows palette green")
	assert_float_equal(emissive.b, palette_emission.b, "lens emission follows palette blue")

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

func test_bay_reflections_cover_the_room_without_adding_light() -> void:
	var game := Game.new(71)
	var lighting := Lighting.build(game)
	var probe := lighting.get_node("BayReflections") as ReflectionProbe
	assert_true(probe != null, "one reflection probe is built with bay lighting")
	assert_vec3_equal(probe.position, Vector3(0, 1.6, 0), "probe is centered in bay-local space")
	assert_vec3_equal(probe.size, Vector3(12, 3.2, 8), "probe covers the stasis room")
	assert_true(probe.box_projection and probe.interior, "room reflections use interior box projection")
	assert_int_equal(probe.update_mode, ReflectionProbe.UPDATE_ONCE, "steady lighting does not recapture every frame")
	assert_int_equal(probe.cull_mask, 1 | Lighting.POD_STATUS_MASK, "probe captures bay architecture and the isolated pod receivers")
	assert_false(probe.enable_shadows, "reflection capture needs no shadow pass")
	assert_int_equal(probe.ambient_mode, ReflectionProbe.AMBIENT_DISABLED, "probe adds no ambient fill")
	assert_int_equal(_count_class(lighting, "OmniLight3D") + _count_class(lighting, "SpotLight3D"), 14 + 6 * Pods.POD_COUNT, "reflections add no lights beyond consolidated wall keys, regular strips and status spill")
	assert_int_equal(_count_class(lighting, "CollisionShape3D"), 0, "reflections add no colliders")
	lighting.free()

func test_reflections_refresh_once_after_power_handoff_or_blackout() -> void:
	for activate_secondary: bool in [true, false]:
		var game := Game.new(71)
		var lighting := Lighting.build(game)
		var initial_id := lighting.get_node("BayReflections").get_instance_id()
		if activate_secondary:
			game.press_console()
			game.press_console()
		else:
			game.power.cut_emergency_power()
		for _tick: int in range(Lighting.FIXTURE_SETTLE_TICKS - 1):
			lighting.process_frame(Sim.LOGICAL_TICK_SECS)
			assert_int_equal(lighting.get_node("BayReflections").get_instance_id(), initial_id,
				"fading lights do not schedule repeated reflection captures")
		lighting.process_frame(Sim.LOGICAL_TICK_SECS)
		var settled_id := lighting.get_node("BayReflections").get_instance_id()
		assert_true(settled_id != initial_id, "settled power state gets a fresh reflection capture")
		assert_int_equal(lighting.get_node("BayReflections").update_mode, ReflectionProbe.UPDATE_ONCE,
			"refreshed capture is still once-only")
		for _tick: int in range(60):
			lighting.process_frame(Sim.LOGICAL_TICK_SECS)
			assert_int_equal(lighting.get_node("BayReflections").get_instance_id(), settled_id,
				"steady lighting retains its reflection capture")
		lighting.free()

func _wall_contact(steel: MeshInstance3D, layout: ShipLayout) -> bool:
	var mounting: SimTestCase = load("res://tests/light_mounting_test.gd").new()
	return mounting._wall_contact(steel, mounting._walls(layout, 14), layout.bay_to_world())
