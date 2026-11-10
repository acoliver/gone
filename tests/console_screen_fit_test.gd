extends SimTestCase

func test_every_screen_follows_the_body_over_a_nine_by_seven_grid() -> void:
	var room := PowerRoom.build(Game.new(0))
	for index in range(6):
		var station := room.get_node("ConsoleStation%d" % index) as Node3D
		var glass := station.get_node("ScreenGlass") as MeshInstance3D
		var body := station.get_node("TerminalModel/ConsoleBody") as MeshInstance3D
		var query := body.mesh.generate_triangle_mesh()
		var relative := body.transform.affine_inverse() * glass.transform
		var size := (glass.mesh as BoxMesh).size
		var normal := relative.basis.z.normalized()
		for row in range(7):
			for column in range(9):
				var front := relative * Vector3(size.x * (column / 8.0 - 0.5), size.y * (row / 6.0 - 0.5), size.z * 0.5)
				var hit := query.intersect_ray(front + normal * 0.01, -normal)
				assert_false(hit.is_empty(), "%s grid ray reaches the body" % station.name)
				if hit.is_empty(): continue
				var gap := (front - (hit.position as Vector3)).dot(normal)
				assert_float_in_range(gap, 0.0, 0.004, "%s screen grid (%d,%d) is neither floating nor buried: %.6f m" % [station.name, column, row, gap])
	room.free()

func test_glass_corners_are_inside_the_bezel_opening() -> void:
	var room := PowerRoom.build(Game.new(0))
	for index in range(6):
		var station := room.get_node("ConsoleStation%d" % index) as Node3D
		var glass := station.get_node("ScreenGlass") as MeshInstance3D
		var body := station.get_node("TerminalModel/ConsoleBody") as MeshInstance3D
		var query := body.mesh.generate_triangle_mesh()
		var relative := body.transform.affine_inverse() * glass.transform
		var size := (glass.mesh as BoxMesh).size
		for x: float in [-0.5, 0.5]:
			for y: float in [-0.5, 0.5]:
				var corner := Vector3(size.x * x, size.y * y, size.z * 0.5)
				var normal := relative.basis.z.normalized()
				var hit := query.intersect_ray(relative * corner + normal * 0.05, -normal)
				assert_false(hit.is_empty(), "each corner is backed by the recess")
				if hit.is_empty(): continue
				assert_true(absf((hit.normal as Vector3).dot(normal)) > 0.99, "glass corner stays on the flat recess, clear of the curved bezel")
				for direction: Vector3 in [Vector3(signf(x), 0, 0), Vector3(0, signf(y), 0)]:
					var bezel_distance := INF
					for step in range(1, 81):
						var probe := relative * (corner + direction * step * 0.001)
						var bezel := query.intersect_ray(probe + normal * 0.1, -normal)
						if not bezel.is_empty() and ((bezel.position as Vector3) - probe).dot(normal) > 0.003:
							bezel_distance = step * 0.001
							break
					assert_float_in_range(bezel_distance, 0.003, 0.080, "actual raised bezel frames each corner with clearance")
	room.free()

func test_side_view_edge_rays_reach_glass_or_bezel_at_every_station() -> void:
	var room := PowerRoom.build(Game.new(0))
	for index in range(6):
		var station := room.get_node("ConsoleStation%d" % index) as Node3D
		var glass := station.get_node("ScreenGlass") as MeshInstance3D
		var body := station.get_node("TerminalModel/ConsoleBody") as MeshInstance3D
		var body_query := body.mesh.generate_triangle_mesh()
		var glass_query := glass.mesh.generate_triangle_mesh()
		var size := (glass.mesh as BoxMesh).size
		for side: float in [-1.0, 1.0]:
			var normal_distance := cos(deg_to_rad(60.0))
			var up_distance := (1.65 - glass.position.y - glass.basis.z.y * normal_distance) / glass.basis.y.y
			var right_distance := side * sqrt(pow(sin(deg_to_rad(60.0)), 2) - up_distance * up_distance)
			var eye := glass.position + glass.basis.z * normal_distance + glass.basis.y * up_distance + glass.basis.x * right_distance
			for edge: Vector2 in [Vector2(-0.5, 0), Vector2(0.5, 0), Vector2(0, -0.5), Vector2(0, 0.5)]:
				var target := glass.transform * Vector3(size.x * edge.x, size.y * edge.y, size.z * 0.5)
				var finish := eye + (target - eye) * 1.5
				var glass_inverse := glass.transform.affine_inverse()
				var body_inverse := body.transform.affine_inverse()
				var glass_hit := glass_query.intersect_segment(glass_inverse * eye, glass_inverse * finish)
				var body_hit := body_query.intersect_segment(body_inverse * eye, body_inverse * finish)
				assert_true(not glass_hit.is_empty() or not body_hit.is_empty(), "%s side %.0f edge %s never exposes empty space or wall" % [station.name, side, edge])
				if not body_hit.is_empty():
					var point := glass_inverse * (body.transform * (body_hit.position as Vector3))
					var body_first := glass_hit.is_empty() or eye.distance_to(body.transform * (body_hit.position as Vector3)) < eye.distance_to(glass.transform * (glass_hit.position as Vector3))
					if body_first:
						assert_true(absf(point.x) >= size.x * 0.5 or absf(point.y) >= size.y * 0.5, "a side ray blocked by the body hits the surrounding bezel, not the recessed screen")
	room.free()
