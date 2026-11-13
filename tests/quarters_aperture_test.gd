extends SimTestCase

const QUERY := preload("res://tests/hatch_render_faces.gd")

func test_header_closes_the_full_wall_depth_at_the_aperture_crown() -> void:
	var walls := _entrance()
	var y := QuartersLayout.FLOOR_Y + 2.4
	var checked := 0
	for ix: int in range(1, 12):
		for iz: int in range(1, 20):
			var origin := Vector3(44.4 + ix * 0.1, y - 0.01, 1.5 + iz * 0.01)
			var hit := _ray(walls, origin, origin + Vector3.UP * 0.02)
			assert_false(hit.is_empty(), "no open slit over the 2.4 m crown between wall faces: " + str(origin))
			if not hit.is_empty(): assert_float_in_range(hit.position.y, y - 0.00001, y + 0.00001, "header underside meets aperture exactly")
			checked += 1
	assert_int_equal(checked, 209, "full width/depth crown grid")
	walls.free()

func test_no_rays_escape_through_either_face_above_the_open_door() -> void:
	var walls := _entrance()
	for ix: int in range(1, 12):
		for iy: int in range(1, 16):
			var point := Vector3(44.4 + ix * 0.1, QuartersLayout.FLOOR_Y + 2.4 + iy * 0.05, 1.6)
			for side: float in [-1, 1]:
				assert_false(_ray(walls, point + Vector3(0, 0, side * 0.3), point - Vector3(0, 0, side * 0.3)).is_empty(), "no through-opening above aperture")
	for side: float in [-1, 1]:
		assert_true(_ray(walls, Vector3(45, -9.8, 1.6 + side * 0.3), Vector3(45, -9.8, 1.6 - side * 0.3)).is_empty(), "the intended open passage is not filled")
	walls.free()

func _entrance() -> Node3D:
	var layout := ShipLayout.authored().layout
	var root := Node3D.new()
	for solid: ShipGeometry.SolidSpec in ShipGeometry.section_solids(layout, layout.section(QuartersLayout.SECTION)) + QuartersGeometry.shell():
		if solid.material_role == &"wall": root.add_child(ShipSection.surface(solid, Lighting.QUARTERS_MASK, layout))
	root.add_child(SlidingDoorModel.frame(layout.door(QuartersLayout.DOOR), Lighting.QUARTERS_MASK))
	return root

func _ray(walls: Node3D, origin: Vector3, target: Vector3) -> Dictionary:
	var faces := PackedVector3Array()
	QUERY.collect(walls, origin, Lighting.QUARTERS_MASK, faces)
	var mesh := TriangleMesh.new()
	assert_true(mesh.create_from_faces(faces), "entrance has opaque front-facing triangles")
	return mesh.intersect_segment(origin, target)
