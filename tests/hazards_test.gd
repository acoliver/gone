extends SimTestCase
## Visual-half pins for issue #33: the ceiling smoke renders as a lean
## field of individual billboard puffs — a shader whose two seed-placed
## lobes reach zero alpha inside the quad edge — while the authored
## ceiling-dense distribution and the spark strobes stay exactly as
## they were.

func test_smoke_draw_pass_is_a_structured_billboard_shader_puff() -> void:
	var hazards := Hazards.build()
	var smoke: GPUParticles3D = hazards.get_node("CeilingSmoke")
	var quad := smoke.draw_pass_1 as QuadMesh
	assert_float_equal(quad.size.x, quad.size.y,
		"the puff quad is square, so rotation never shows a rectangular silhouette")
	assert_true(quad.size.x >= 1.4, "the puff quad keeps the authored coverage footprint")
	var material := quad.material as ShaderMaterial
	assert_true(material.shader.resource_path == "res://app/smoke_puff.gdshader",
		"the smoke runs the structured puff shader")
	var opacity: float = material.get_shader_parameter("opacity")
	assert_float_in_range(opacity, 0.48 - 1e-3, 0.48 + 1e-3,
		"per-puff opacity is pinned to the authored billow strength, still translucent")
	var tint: Color = material.get_shader_parameter("tint")
	assert_true(tint == Color(0.26, 0.25, 0.25), "the lit grey keeps the authored albedo")
	var emission: Color = material.get_shader_parameter("emission_tint")
	assert_true(emission.r > emission.g and emission.r > emission.b,
		"the emission whisper stays red so the haze reads under emergency light")

func test_smoke_distribution_stays_ceiling_dense_and_slow() -> void:
	var hazards := Hazards.build()
	var smoke: GPUParticles3D = hazards.get_node("CeilingSmoke")
	assert_vec3_equal(smoke.position, Vector3(0.0, 2.8, 0.0), "the emitter hugs the ceiling")
	assert_int_equal(smoke.amount, 144, "the authored particle budget stays pinned")
	assert_float_equal(smoke.lifetime, 8.0, "the authored puff lifetime stays pinned for overlap")
	assert_float_equal(smoke.preprocess, 7.0, "the haze exists from the first captured frame")
	var process := smoke.process_material as ParticleProcessMaterial
	assert_vec3_equal(process.emission_box_extents, Vector3(5.0, 0.4, 3.0),
		"the ceiling-high spawn volume keeps its top edge at the 3.2 m ceiling plane")
	assert_vec3_equal(process.direction, Vector3(0.0, -1.0, 0.0), "smoke drifts downward")
	assert_float_equal(process.spread, 25.0, "the narrow downward cone is unchanged")
	assert_float_in_range(process.initial_velocity_min,
		Hazards.SMOKE_FALL_SPEED * 0.5 - 1e-3, Hazards.SMOKE_FALL_SPEED * 0.5 + 1e-3,
		"the slow fall keeps its authored floor")
	assert_float_in_range(process.initial_velocity_max,
		Hazards.SMOKE_FALL_SPEED - 1e-3, Hazards.SMOKE_FALL_SPEED + 1e-3,
		"the slow fall keeps its authored ceiling")
	assert_vec3_equal(process.gravity, Vector3(0.0, -0.05, 0.0), "the faint downward pull is unchanged")
	assert_float_in_range(process.scale_min, 1.25 - 1e-3, 1.25 + 1e-3,
		"the per-particle size floor keeps the small billows whole")
	assert_float_in_range(process.scale_max, 2.4 - 1e-3, 2.4 + 1e-3,
		"the per-particle size ceiling keeps the big billows")
	assert_true(process.angular_velocity_min < 0.0 and process.angular_velocity_max > 0.0,
		"puffs spin both ways for per-particle rotation")

func test_spark_strobes_keep_their_hard_ember_quads() -> void:
	var hazards := Hazards.build()
	var sprays: Array[Node] = hazards.find_children("SparkSpray", "GPUParticles3D", true, false)
	assert_int_equal(sprays.size(), Hazards.SPARK_COUNT, "one spray per authored spark spot")
	for node: Node in sprays:
		var spray := node as GPUParticles3D
		assert_true(spray.one_shot, "spark sprays stay one-shot")
		assert_false(spray.emitting, "spark sprays stay idle until a burst")
		assert_int_equal(spray.amount, 16, "spark spray budget is unchanged")
		assert_float_equal(spray.lifetime, 0.45, "spark spray lifetime is unchanged")
		var quad := spray.draw_pass_1 as QuadMesh
		var material := quad.material as StandardMaterial3D
		assert_true(material.shading_mode == BaseMaterial3D.SHADING_MODE_UNSHADED,
			"embers stay unshaded")
		assert_true(material.emission_enabled, "embers stay emissive")
	var strobes: Array[Node] = hazards.find_children("*", "OmniLight3D", true, false)
	assert_int_equal(strobes.size(), Hazards.SPARK_COUNT, "one strobed light per spark spot")
	for node: Node in strobes:
		var light := node as OmniLight3D
		assert_true(light.light_color == Color(1.5, 0.35, 0.1), "strobe color is unchanged")
		assert_float_equal(light.omni_range, 5.0, "strobe range is unchanged")
		assert_float_equal(light.light_energy, 0.0, "strobes idle dark between bursts")
