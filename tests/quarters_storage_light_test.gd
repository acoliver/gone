extends SimTestCase

func test_black_wide_view_pixels_hit_solid_storage_and_receive_bounce() -> void:
	var game := Game.new(114)
	game.power_active = true
	var room := QuartersRoom.build(game)
	var eye := QuartersLayout.to_world(Vector3(0.75, 2.2, 0.10))
	var camera_basis := Basis.looking_at(QuartersLayout.to_world(Vector3(4.0, 1.15, 3.6)) - eye)
	var bounce := room.get_node_or_null("EntranceStorageBounce") as OmniLight3D
	assert_true(bounce != null, "solid entrance-facing storage needs indirect light")
	for state: Node3D in [room.remembered, room.present]:
		var infill := state.get_node("Placement_storage_left_near/Standin_storage_left_near_infill") as MeshInstance3D
		var faces := PackedVector3Array()
		HatchRenderFaces.collect(infill, eye, Lighting.QUARTERS_MASK, faces)
		var mesh := TriangleMesh.new()
		assert_true(mesh.create_from_faces(faces), "front-facing opaque storage infill")
		for pixel: Vector2 in [Vector2(200, 250), Vector2(225, 350), Vector2(250, 400)]:
			var ray := camera_basis * Vector3((2 * pixel.x / 1536 - 1) * tan(deg_to_rad(66)), (1 - 2 * pixel.y / 864) * tan(deg_to_rad(66)) * 864 / 1536, -1)
			var hit := mesh.intersect_segment(eye, eye + ray.normalized() * 10)
			assert_false(hit.is_empty(), "black-region pixel hits a solid panel, not the doorway: " + str(pixel))
			if hit.is_empty() or bounce == null: continue
			assert_close(hit.normal, Vector3.FORWARD, "entrance-facing panel normal")
			var to_light: Vector3 = bounce.position - hit.position
			assert_true(to_light.length() < bounce.omni_range, "bounce reaches black-region panel")
			assert_true(to_light.normalized().dot(hit.normal) > 0.1, "bounce is on the visible side of the solid panel")
			assert_true((infill.layers & bounce.light_cull_mask) != 0, "panel receives the local bounce")
	if bounce != null:
		assert_true(bounce.light_energy > 0, "secondary-power bounce is lit")
		assert_int_equal(bounce.light_cull_mask, Lighting.QUARTERS_MASK, "bounce cannot illuminate D14")
		assert_float_equal(bounce.light_specular, 0, "indirect diffuse light has no point-source glint")
	room.free()

func test_storage_bounce_fades_with_secondary_power_in_both_states() -> void:
	var game := Game.new(114)
	game.power_active = true
	var room := QuartersRoom.build(game)
	var bounce := room.get_node_or_null("EntranceStorageBounce") as OmniLight3D
	assert_true(bounce != null, "entrance storage bounce exists")
	if bounce != null:
		assert_float_equal(bounce.light_energy, Vector3(Lighting.regular_energy() * 0.35, 0, 0).x, "local bounce power share")
		game.power_active = false
		for tick: int in range(30): room.process_frame()
		assert_float_equal(bounce.light_energy, 0, "no secondary bounce after power fade")
		game.power_active = true
		for tick: int in range(30): room.process_frame()
		assert_float_equal(bounce.light_energy, Vector3(Lighting.regular_energy() * 0.35, 0, 0).x, "secondary bounce restored")
	room.free()
