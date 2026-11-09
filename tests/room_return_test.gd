extends SimTestCase

func _policy() -> GDScript:
	return load("res://app/room_return.gd")

func test_return_tracks_live_keys_without_inventing_a_light_source() -> void:
	var policy := _policy()
	assert_true(policy != null, "bounded diffuse return implementation exists")
	if policy == null: return
	var red := Lighting.switched_key(ShipLayout.EmergencyLightRole.BAY_POOL, 1.0)
	var white := OmniLight3D.new()
	white.light_color = Lighting.REGULAR_WHITE
	white.light_energy = 0.0
	var bounds := AABB(Vector3(30, 0, -1.5), Vector3(6, 3.2, 3))
	var keys: Array[OmniLight3D] = [red]
	var strips: Array[OmniLight3D] = [white]
	var probe: ReflectionProbe = policy.build(bounds, keys, strips, 8192)
	assert_vec3_equal(probe.position, bounds.get_center(), "room-local return volume")
	assert_vec3_equal(probe.size, bounds.size, "return cannot spill beyond the room")
	assert_int_equal(probe.reflection_mask, 8192, "only this room's receivers")
	assert_int_equal(probe.cull_mask, 0, "diffuse-only probe does not capture specular or emissive geometry")
	assert_true(probe.interior, "no sky contribution")
	assert_int_equal(probe.ambient_mode, ReflectionProbe.AMBIENT_COLOR, "local diffuse return")
	assert_int_equal(probe.find_children("*", "Light3D", true, false).size(), 0, "no additional emitter")
	assert_true(probe.ambient_color.is_equal_approx(Lighting.EMERGENCY_RED), "return retains key colour")
	var red_energy := red.light_energy
	assert_float_equal(probe.ambient_color_energy, red_energy * 0.1, "fixed tenth-share return")
	red.light_energy *= 0.5
	probe.refresh()
	assert_float_equal(probe.ambient_color_energy, red_energy * 0.05, "return follows actual key fade")
	red.light_energy = 0.0
	white.light_energy = Lighting.regular_energy()
	probe.refresh()
	assert_true(probe.ambient_color.is_equal_approx(Lighting.REGULAR_WHITE), "secondary handoff uses the white keys")
	assert_float_equal(probe.ambient_color_energy, (white.light_color.srgb_to_linear() * white.light_energy * 0.1).r, "white return uses the same policy")
	white.light_energy = 0.0
	probe.refresh()
	assert_float_equal(probe.ambient_color_energy, 0.0, "no return in a dark room")
	assert_true(probe.ambient_color == Color.BLACK, "no stale colour after blackout")
	red.free()
	white.free()
	probe.free()

func test_density_and_handoff_do_not_multiply_return_or_change_emitters() -> void:
	var policy := _policy()
	assert_true(policy != null, "bounded diffuse return implementation exists")
	if policy == null: return
	var red := Lighting.switched_key(ShipLayout.EmergencyLightRole.BAY_POOL, 0.5)
	var white := OmniLight3D.new()
	white.light_color = Lighting.REGULAR_WHITE
	white.light_energy = Lighting.regular_energy() * 0.5
	var original_energy := red.light_energy
	var keys: Array[OmniLight3D] = [red, red]
	var strips: Array[OmniLight3D] = [white]
	var probe: ReflectionProbe = policy.build(AABB(Vector3.ZERO, Vector3(6, 3.2, 3)), keys, strips, 1)
	var expected := (red.light_color.srgb_to_linear() * red.light_energy + white.light_color.srgb_to_linear() * white.light_energy) * 0.1
	assert_float_equal(probe.ambient_color_energy, expected.r, "mean key radiance is independent of fixture density")
	assert_true(probe.ambient_color == (expected / expected.r).linear_to_srgb(), "handoff sums actual key radiance in linear space")
	assert_float_equal(red.light_energy, original_energy, "source energy is unchanged")
	assert_true(red.light_color == Lighting.EMERGENCY_RED, "source colour is unchanged")
	assert_vec3_equal(red.position, Vector3.ZERO, "source placement is unchanged")
	red.free()
	white.free()
	probe.free()
