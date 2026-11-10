extends SimTestCase

const QUERY := preload("res://tests/hatch_render_faces.gd")

func test_present_cabinet_interiors_have_front_facing_opaque_panels() -> void:
	var furnishings := QuartersFurnishings.build(&"aged")
	var wardrobe := furnishings.get_node("Placement_wardrobe/wardrobe") as Node3D
	var checked := _check_cage(wardrobe, ["SidePanel_L", "SidePanel_R", "BackPanel", "TopPanel", "BottomPanel"])
	var lockers := furnishings.get_node("Placement_lockers_over_bed/lockers_over_bed") as Node3D
	for bay: int in range(3):
		var names: Array[String] = []
		for part: String in ["SideL", "SideR", "Back", "Top", "Bottom"]: names.append("Bay_%d_%s" % [bay, part])
		checked += _check_cage(lockers, names)
	assert_int_equal(checked, 500, "25 interior rays per panel across four five-sided cabinet cages")
	furnishings.free()

func _check_cage(cabinet: Node3D, names: Array[String]) -> int:
	var cage := AABB()
	for name: String in names:
		var panel := cabinet.find_child(name, true, false) as MeshInstance3D
		assert_true(panel != null, "cabinet panel exists: " + name)
		if panel == null: return 0
		var bounds := ShipScene._world_frame(panel) * panel.get_aabb()
		cage = bounds if not cage.has_volume() else cage.merge(bounds)
	var checked := 0
	for name: String in names:
		var panel := cabinet.find_child(name, true, false) as MeshInstance3D
		var bounds := ShipScene._world_frame(panel) * panel.get_aabb()
		var axis := bounds.size.min_axis_index()
		var u := (axis + 1) % 3
		var v := (axis + 2) % 3
		for row: int in range(5):
			for column: int in range(5):
				var target := bounds.get_center()
				target[u] = lerpf(bounds.position[u], bounds.end[u], .15 + .175 * row)
				target[v] = lerpf(bounds.position[v], bounds.end[v], .15 + .175 * column)
				var origin := target
				origin[axis] = cage.get_center()[axis]
				var faces := PackedVector3Array()
				QUERY.collect(panel, origin, 0xfffff, faces)
				var triangles := TriangleMesh.new()
				assert_true(triangles.create_from_faces(faces), "opaque interior-facing triangles: " + name)
				var hit := triangles.intersect_segment(origin, origin + (target - origin) * 1.2)
				assert_false(hit.is_empty(), "solid rendered interior surface: " + name)
				checked += 1
	return checked
