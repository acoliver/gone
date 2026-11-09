extends SimTestCase

const Bounce := preload("res://app/real_bounce.gd")

func test_sdfgi_uses_no_environment_energy_or_gain() -> void:
	var world := Lighting._world_environment()
	Bounce.configure(world.environment, "sdfgi")
	assert_true(world.environment.sdfgi_enabled, "prototype enables actual SDFGI")
	assert_int_equal(world.environment.sdfgi_cascades, 4, "four camera-following cascades")
	assert_true(is_equal_approx(world.environment.sdfgi_min_cell_size, .1), "10 cm minimum cells")
	assert_float_equal(world.environment.sdfgi_energy, 1.0, "no GI boost")
	assert_false(world.environment.sdfgi_read_sky_light, "no sky input")
	assert_int_equal(world.environment.ambient_light_source, Environment.AMBIENT_SOURCE_DISABLED, "ambient remains disabled")
	assert_float_equal(world.environment.ambient_light_energy, 0.0, "no ambient energy")
	assert_true(world.environment.ambient_light_color == Color.BLACK, "black ambient color")
	world.free()

func test_ssil_retains_default_intensity_and_no_ambient() -> void:
	var world := Lighting._world_environment()
	Bounce.configure(world.environment, "ssil")
	assert_true(world.environment.ssil_enabled, "SSIL comparison")
	assert_float_equal(world.environment.ssil_intensity, 1.0, "no screen-space boost")
	assert_float_equal(world.environment.ssil_radius, 5.0, "default radius")
	assert_int_equal(world.environment.ambient_light_source, Environment.AMBIENT_SOURCE_DISABLED, "no ambient path change")
	world.free()

func test_gi_does_not_change_real_sources_or_double_count_lenses() -> void:
	var world := Node3D.new()
	var game := Game.new(91)
	var ship := ShipScene.build_into(world, game, false)
	var sources := world.find_children("*", "Light3D", true, false)
	var energies: Array[float] = []
	for light: Light3D in sources: energies.append(light.light_energy)
	Bounce.prepare_geometry(world, "sdfgi")
	for index: int in range(sources.size()):
		var light := sources[index] as Light3D
		assert_float_equal(light.light_energy, energies[index], "unchanged source energy")
		assert_float_equal(light.light_indirect_energy, 1.0, "default source indirect energy")
		assert_int_equal(light.light_bake_mode, Light3D.BAKE_DYNAMIC, "handoff stays dynamic")
	for mesh: MeshInstance3D in world.find_children("*", "MeshInstance3D", true, false):
		for index: int in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(index) as BaseMaterial3D
			if material != null and material.emission_enabled:
				assert_int_equal(mesh.gi_mode, GeometryInstance3D.GI_MODE_DISABLED, "emission is not counted as another light")
	ship.prepare_near(Vector3(26, 0, 0))
	var streamed_count := world.find_children("*", "Light3D", true, false).size()
	Bounce.prepare_geometry(world, "sdfgi")
	assert_int_equal(streamed_count, world.find_children("*", "Light3D", true, false).size(), "GI creates no sources in streamed geometry")
	world.free()
