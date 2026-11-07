extends SimTestCase

const IDS: Array[StringName] = [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE", &"D14-C-001-H-AFT"]
const QUERY := preload("res://tests/hatch_render_faces.gd")

func test_wall_and_frame_seal_the_whole_pocket_outside_the_mouth() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in IDS:
		var spec := layout.door(id)
		var view := DoorView.build(spec)
		var walls := Node3D.new()
		walls.transform = spec.frame()
		var solids := ShipGeometry.doorway_wall_solids(layout) if id == ShipLayout.BAY_DOOR_ID else ShipGeometry.hatch_wall_solids(spec)
		for solid: ShipGeometry.SolidSpec in solids:
			walls.add_child(DoorView.split_surface(solid, spec.frame(), 1, 1))
		var half_width := spec.aperture().x / 2 + ShipGeometry.HATCH_RING_WIDTH
		var targets: Array[Vector2] = []
		var mouth := ShipGeometry.hatch_ring_outline(spec)
		var center_y := (spec.aperture().y + ShipGeometry.SILL_HEIGHT) / 2
		# Sample the entire widened rectangle, including its curved feet/crown.
		# The intended mouth includes the existing 5 mm reveal on each side.
		# Stay 0.1 mm off the rectangle edges for float32 world transforms.
		for column: int in range(139):
			for row: int in range(241):
				var xy := Vector2(lerpf(-half_width + 0.0001, half_width - 0.0001, column / 138.0), lerpf(0.0001, spec.aperture().y - 0.0001, row / 240.0))
				if not Geometry2D.is_point_in_polygon(xy - Vector2(0, center_y), mouth): targets.append(xy)
		var into := signf(spec.hinge_frame().origin.z - ShipLayout.WALL / 2)
		# Anchor oblique rays at the actual mouth, where the bead meets the wall.
		# A point halfway down a cleared sweep pocket can be seen through an
		# open mouth legitimately, despite lying outside its XY projection.
		var mouth_z := ShipGeometry.HATCH_RING_REAR if into > 0 else ShipLayout.WALL - ShipGeometry.HATCH_RING_REAR
		for angle: float in [0.0, spec.swing_radians(0)]:
			view.get_node("Hinge").basis = Basis(Vector3.UP, angle)
			for side: float in [-1.0, 1.0]:
				# A single parallel query covers every straight-on pocket ray.
				var eyes: Array[Vector3] = [Vector3(0, 1.6, 0.1 + side * 3), Vector3(-0.68, 1.6, 0.1 + side * 3), Vector3(0.68, 1.6, 0.1 + side * 3)]
				for eye_index: int in range(eyes.size() + 1):
					var eye := spec.frame() * eyes[maxi(eye_index - 1, 0)]
					var faces := PackedVector3Array()
					# Exclude the movable leaf: an open mouth must never depend on it.
					QUERY.collect(view.get_node("Frame"), eye, 1, faces)
					QUERY.collect(walls, eye, 1, faces)
					var mesh := TriangleMesh.new()
					assert_true(mesh.create_from_faces(faces), "wall/frame union has facing triangles")
					var misses := 0
					var first := Vector2.ZERO
					for xy: Vector2 in targets:
						var target := spec.frame() * Vector3(xy.x, xy.y, mouth_z)
						var origin := spec.frame() * Vector3(xy.x, xy.y, 0.1 + side * 3) if eye_index == 0 else eye
						if mesh.intersect_segment(origin, origin + (target - origin) * 2).is_empty():
							if misses == 0: first = xy
							misses += 1
					print("POCKET_SEAL id=%s angle=%.3f side=%+.0f eye=%d rays=%d misses=%d first=%s" % [id, rad_to_deg(angle), side, eye_index, targets.size(), misses, first])
					assert_int_equal(misses, 0, "wall/frame seals full pocket %s side=%s eye=%d first=%s" % [id, side, eye_index, first])
		view.free()
		walls.free()
