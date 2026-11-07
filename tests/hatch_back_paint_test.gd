extends SimTestCase

func test_visible_backing_uses_one_reverse_paint_projection() -> void:
	var layout := ShipLayout.authored().layout
	for id: StringName in [ShipLayout.BAY_DOOR_ID, &"D14-C-001-H-FORE"]:
		var door := layout.door(id)
		var variant := HatchAsset.variant(door)
		var into := signf(door.hinge_frame().origin.z - ShipLayout.WALL / 2)
		var reverse_side := 1 if into > 0 else 0
		var view := DoorView.build(door)
		var probe := HatchBandProbe.new()
		probe.collect(view.label_leaf())
		probe.build()
		var frame := Surfaces.world_frame(view.label_leaf())
		var eye := frame * Vector3(0.3, 1.7, into * 2)
		var hit := probe.cast(eye, -frame.basis.z * into)
		assert_true(not hit.is_empty() and hit.part == "BackingLapBody/lap", "check the actual visible back skin, not the concealed reverse slab")
		var reverse_plate: Dictionary
		var reverse_pose: Transform3D
		for group: Dictionary in variant.groups:
			for part: Dictionary in group.parts:
				if int(group.side) == reverse_side and String(part.id).ends_with("Steel/plate"):
					reverse_plate = part
					reverse_pose = HatchAsset.pose(group.transform) * HatchAsset.pose(part.transform)
		var mesh := HatchAsset.leaf_mesh(variant, 0)
		var arrays := mesh.surface_get_arrays(0)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var colours: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
		var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
		var ranges: Dictionary = mesh.get_meta(&"part_ranges")
		var checked := 0
		for name: StringName in [&"BackingLapBody/lap", &"BackingLapLatch/lap"]:
			var row: Dictionary = ranges[name]
			for triangle: int in range(int(row.index_start), int(row.index_start + row.index_count), 3):
				var a := points[indices[triangle]]
				var b := points[indices[triangle + 1]]
				var c := points[indices[triangle + 2]]
				if (c - a).cross(b - a).normalized().dot(Vector3.BACK * into) < .99: continue
				for corner: int in range(3):
					var index := indices[triangle + corner]
					var point := reverse_pose.affine_inverse() * points[index]
					# glTF exports Blender's upward V into Godot's downward texture V.
					var expected := Vector2(point.x / float(reverse_plate.size[0]) + .5, .5 - point.y / float(reverse_plate.size[1]))
					assert_true(colours[index].r > .99 and is_equal_approx(colours[index].g, float(reverse_side)), "visible backing selects reverse paint instead of repeating steel/oxide scans")
					assert_true(uvs[index].distance_to(expected) < .000001, "visible cap shares the slab's whole-face affine UV2, without per-tile resets")
					checked += 1
		print("BACK_PAINT id=%s visible_part=%s checked=%d" % [id, hit.get("part", ""), checked])
		assert_true(checked > 50, "both visible backing caps checked")
		view.free()

func test_both_wheels_share_the_same_smooth_source() -> void:
	for variant: Dictionary in HatchAsset.document().variants:
		var wheels: Array[Dictionary] = []
		for group: Dictionary in variant.groups:
			if group.path not in ["Wheel", "ReverseWheel"]: continue
			var mesh := HatchAsset.group_mesh(int(variant.index), group)
			var row: Dictionary = mesh.get_meta(&"part_ranges")[StringName(group.path + "/hub")]
			var arrays := mesh.surface_get_arrays(0)
			# The selected 4,000-triangle budget cache contains 3,910 retained faces.
			assert_int_equal(int(row.index_count) / 3, 3910, "each wheel retains the entire selected wheel cache")
			var triangles: Dictionary = {}
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			for index: int in range(int(row.index_start), int(row.index_start + row.index_count), 3):
				var corners: Array[Array] = []
				for corner: int in range(3):
					var vertex := indices[index + corner]
					corners.append([points[vertex], normals[vertex]])
				corners.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
				triangles[corners] = true
			wheels.append(triangles)
		assert_int_equal(wheels.size(), 2, "front and reverse wheel exist")
		assert_true(wheels[0] == wheels[1], "reverse wheel preserves the front wheel geometry and normal field")
