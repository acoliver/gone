extends SimTestCase

const Probe = preload("res://tools/hatch_band_probe.gd")

func test_probe_reports_geometric_normal_without_turning_back_faces_toward_the_ray() -> void:
	var probe := Probe.new()
	probe.add_triangle(Vector3(-1, -1, 0), Vector3(0, 1, 0), Vector3(1, -1, 0), "test", "plane")
	probe.build()
	var front := probe.cast(Vector3(0, 0, 1), Vector3(0, 0, -1))
	var back := probe.cast(Vector3(0, 0, -1), Vector3(0, 0, 1))
	assert_true(not front.is_empty() and not back.is_empty(), "two-sided diagnosis reports culled faces too")
	assert_true(front.normal.distance_to(Vector3.BACK) < 0.000001 and back.normal.distance_to(Vector3.BACK) < 0.000001, "normal follows actual submitted winding, not ray direction")
	assert_true(front.part == "plane" and back.node == "test", "triangle provenance survives BVH")

func test_probe_collects_service_triangles_without_optional_uvs() -> void:
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for point: Vector3 in [Vector3(-1, -1, 0), Vector3(0, 1, 0), Vector3(1, -1, 0)]: tool.add_vertex(point)
	var mesh := tool.commit()
	var piece := HatchModel.mesh_piece(mesh, Transform3D.IDENTITY, 1, Surfaces.material(&"frame"))
	var probe := Probe.new()
	probe.collect(piece)
	assert_int_equal(probe.provenance.size(), 1, "untextured service triangles still cast shadows")
	piece.free()

func test_close_camera_visible_reveal_and_threshold_have_outward_normals() -> void:
	var probe := Probe.from_hatch()
	var samples := 0
	# Andrew's shallow flush bead moves the soffit to rows 180/181 in the
	# unchanged camera; the former 190/200 rays now hit the leaf itself.
	for pixel: Vector2 in [Vector2(600, 180), Vector2(600, 181), Vector2(600, 1170), Vector2(600, 1180)]:
		var hit := probe.camera_hit(pixel)
		assert_true(not hit.is_empty(), "band camera ray hits steel")
		if hit.is_empty(): continue
		print("BAND_RAY pixel=%s node=%s part=%s normal=%s camera=%.6f key=%.6f blocker=%s" % [pixel, hit.node, hit.part, hit.normal, hit.camera_dot, hit.key_dot, hit.blocker])
		assert_true(hit.camera_dot > 0, "visible band has an outward camera-facing normal: " + hit.part)
		var production := probe.camera_hit(pixel, probe.production_key)
		print("BAND_PRODUCTION pixel=%s key_position=%s key_dot=%.6f blocker=%s" % [pixel, probe.production_key, production.key_dot, production.blocker])
		# The upper ring/lip/throat is a downward soffit, below an above-door lamp.
		# Requiring it to face that key is impossible. Native capture checks require
		# fill-lit (nonblack) soffit samples darker than the leaf instead.
		if pixel.y < 300:
			assert_true(hit.normal.y < -0.9 and production.key_dot < 0, "arch underside retains its downward outward normal")
		else:
			assert_true(hit.key_dot > 0 and hit.blocker == "", "upward threshold faces the lookdev key without self-shadow")
			assert_true(production.key_dot > 0 and production.blocker == "", "threshold faces production key without self-shadow")
		samples += 1
	assert_int_equal(samples, 4, "all fixed band rays tested")
