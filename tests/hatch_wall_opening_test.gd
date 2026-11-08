extends SimTestCase

const QUERY := preload("res://tests/hatch_render_faces.gd")

func test_every_hatch_wall_has_three_continuous_rounded_faces_and_no_corner_fillers() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(door)
		assert_int_equal(solids.size(), 3, "rounded opening belongs to the three wall pieces, without corner filler solids: " + id)
		for solid: ShipGeometry.SolidSpec in solids:
			assert_false("/POCKET/" in String(solid.id), "no separate corner filler remains: " + solid.id)
			assert_true(solid.hatch_profile == door and not solid.section.is_empty(), "the wall face itself carries the rounded cut: " + solid.id)

func test_no_wall_face_in_the_square_corner_region_precedes_the_round_ring() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var outer := ShipGeometry.hatch_ring_outline(door, ShipGeometry.HATCH_RING_WIDTH)
		var center := Vector2(0, (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2)
		var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var front := ShipGeometry.HATCH_RING_FRONT if into > 0 else ShipLayout.WALL - ShipGeometry.HATCH_RING_FRONT
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(door)
		for solid: ShipGeometry.SolidSpec in solids:
			var relative := door.frame().affine_inverse() * solid.transform
			var vertices: PackedVector3Array = HatchModel.solid_mesh(solid).get_faces()
			for vertex: Vector3 in vertices:
				var point := relative * vertex
				var xy := Vector2(point.x, point.y)
				if absf(xy.x) >= door.aperture().x / 2 + ShipGeometry.HATCH_RING_WIDTH or xy.y <= 0 or xy.y >= door.aperture().y: continue
				if Geometry2D.is_point_in_polygon(xy - center, outer): continue
				assert_true((point.z - front) * into >= 0, "the square-minus-round corner contains only wall behind the bead: " + solid.id)

func test_wall_faces_meet_the_round_frame_without_a_square_outline_on_either_side() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var walls := Node3D.new()
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(door)
		for solid: ShipGeometry.SolidSpec in solids:
			if "/POCKET/" in String(solid.id): continue
			walls.add_child(DoorView.split_surface(solid, door.frame(), 1, 1))
		var outline := ShipGeometry.hatch_ring_outline(door, ShipGeometry.HATCH_RING_WIDTH)
		var center := Vector2(0, (door.aperture().y + ShipGeometry.SILL_HEIGHT) / 2)
		var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var plane := ShipGeometry.HATCH_RING_REAR if into > 0 else ShipLayout.WALL - ShipGeometry.HATCH_RING_REAR
		for side: int in [-1, 1]:
			var eye := Vector3(0, 1.6, side * 3)
			var faces := PackedVector3Array()
			QUERY.collect(walls, eye, 1, faces)
			var mesh := TriangleMesh.new()
			assert_true(mesh.create_from_faces(faces), "wall has facing triangles")
			var checked := 0
			for edge: int in range(outline.size()):
				var a := outline[edge]
				var b := outline[(edge + 1) % outline.size()]
				if absf(a.x - b.x) < 0.000001 or absf(a.y - b.y) < 0.000001: continue
				var outward := Vector2((b - a).y, -(b - a).x).normalized()
				var xy := (a + b) / 2 + center + outward * 0.001
				if xy.y <= 0 or xy.y >= door.aperture().y: continue
				var origin := Vector3(xy.x, xy.y, plane + side * 0.25)
				var target := Vector3(xy.x, xy.y, plane - side * 0.25)
				var hit := mesh.intersect_segment(origin, target)
				assert_false(hit.is_empty(), "wall, not a separate filler, reaches curved corner: %s edge=%d side=%d" % [id, edge, side])
				if not hit.is_empty():
					var expected := ShipGeometry.HATCH_RING_REAR if side < 0 else ShipLayout.WALL - ShipGeometry.HATCH_RING_REAR
					var point: Vector3 = hit.position
					assert_float_in_range(point.z, expected - 1e-6, expected + 1e-6, "each side has its own rounded wall face, not a ray through to the opposite skin: %s side=%d" % [id, side])
				checked += 1
			assert_true(checked > 0, "curved corners sampled")
		walls.free()

func test_every_hatch_wall_preserves_steel_mapping_and_flat_face_normals() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in layout.door_ids():
		var door := layout.door(id)
		if door.animation() != ShipLayout.AnimationRecipe.HINGE: continue
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(door)
		for solid: ShipGeometry.SolidSpec in solids:
			var neighbour := ShipGeometry.SolidSpec.new(solid.center, solid.size)
			neighbour.surface_identity(solid.surface_owner, solid.surface_part)
			var reference := MeshInstance3D.new()
			Surfaces.bind_solid(reference, layout, neighbour)
			var walls := Node3D.new()
			walls.transform = door.frame()
			var split := DoorView.split_surface(solid, door.frame(), 1, 1)
			walls.add_child(split)
			for piece: MeshInstance3D in split.get_children():
				assert_true(piece.material_override == reference.material_override, "same wall surface role: " + solid.id)
				for point: Vector3 in [solid.center, solid.center + Vector3.RIGHT, solid.center + Vector3.UP, solid.center + Vector3.BACK]:
					assert_vec3_equal(Surfaces.sample_position(piece, point), Surfaces.sample_position(reference, point), "same metre-scale mapping, orientation and panel origin: " + solid.id)
			walls.free()
			reference.free()
			var arrays := HatchModel.solid_mesh(solid).surface_get_arrays(0)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for triangle: int in range(0, indices.size(), 3):
				var a := vertices[indices[triangle]]
				var b := vertices[indices[triangle + 1]]
				var c := vertices[indices[triangle + 2]]
				var normal := (c - a).cross(b - a).normalized()
				for corner: int in range(3):
					assert_true(normal.dot(normals[indices[triangle + corner]]) > 0.999, "flat wall normals preserve steel projection, without interpolated streaks: " + solid.id)

func test_wall_backs_the_ring_behind_the_upper_hinge_clearance() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]:
		var door := layout.door(id)
		var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var view := DoorView.build(door)
		view.transform = door.frame()
		for solid: ShipGeometry.SolidSpec in ShipGeometry.hatch_wall_solids(door):
			view.add_child(DoorView.split_surface(solid, door.frame(), 1, 1))
		var eye := door.frame() * Vector3(0, 1.4, ShipLayout.WALL / 2 - into * 2)
		var target := door.frame() * Vector3(-0.626465, 2.136172, ShipLayout.WALL / 2)
		var faces := PackedVector3Array()
		QUERY.collect(view, eye, 1, faces)
		var query := TriangleMesh.new()
		assert_true(query.create_from_faces(faces), "closed hatch has opaque faces")
		assert_false(query.intersect_segment(eye, eye + (target - eye).normalized() * 6).is_empty(), "continuous wall backs the stationary ring at its upper hinge clearance: " + id)
		view.free()
