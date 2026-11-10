extends SimTestCase

func test_one_source_failure_is_above_the_pickup_and_old_damage_is_repaired() -> void:
	assert_true(BayCeiling.EMPTY_CELLS == [Vector2i(4, 4)], "#110: one opening at bay (-0.6,-0.9)")
	var rows := BayCeiling.layout()
	var cells := {}
	for row: Dictionary in rows: cells[row.cell] = row
	for cell: Vector2i in [Vector2i(3,8),Vector2i(2,8),Vector2i(3,9)]:
		assert_true(cells.has(cell) and cells[cell].variant == &"intact", "old damage is repaired")
	assert_true(cells[Vector2i(3,4)].variant == &"sag", "sag stays next to the failed tile")
	assert_true(cells[Vector2i(4,5)].variant == &"brokenedge", "broken edge stays beside the failed tile; south neighbor is an unchanged beam cassette")

func test_pickup_is_the_passed_middle_with_one_measured_floor_transform() -> void:
	var rod := Rod.build()
	var bar := rod.get_node("RodBar") as Node3D
	assert_true(bar != null and not bar is MeshInstance3D, "#110 user-redrawn ceiling component replaces round-bar render only")
	assert_vec3_equal(bar.position, Vector3(-0.6,0.018042830046183175,-1.4), "measured source pose applied once")
	assert_vec3_equal(bar.basis.x, Vector3(0.9902680687415704,0,0.13917310096006547), "known long axis +X, no cylinder lay-down applied twice")
	var meshes: Array[MeshInstance3D] = []
	BayCeiling._collect_meshes(bar,Transform3D.IDENTITY,meshes)
	var bounds := AABB()
	for i in range(meshes.size()):
		var mesh := meshes[i]
		assert_true(mesh.mesh.resource_path.contains("middle.glb"), "exact passed middle export, not independent geometry")
		for vertex: Vector3 in mesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]:
			var point := mesh.transform * vertex
			if bounds.size == Vector3.ZERO: bounds = AABB(point,Vector3(0.0000000001,0.0000000001,0.0000000001))
			else: bounds = bounds.expand(point)
		mesh.free()
	assert_float_in_range(bounds.position.y,-0.000001,0.000001,"actual floor contact")
	assert_float_in_range(bounds.end.y,0.0436926,0.0436930,"known exported 115-degree floor height")
	var world := ShipLayout.authored().layout.bay_to_world() * bounds
	var center := ShipLayout.authored().layout.anchor(&"D14-BAY-ROD").origin
	var proxy := AABB(center-Vector3(0.11,0,0.575),Vector3(0.22,0.1,1.15))
	assert_true(proxy.grow(0.000001).encloses(world),"unchanged world click proxy contains actual new render")
	assert_float_in_range(Interactions.ROD_PICKUP_REACH,1.3,1.3,"walking-only reach unchanged")
	rod.free()

func test_actual_picker_keeps_the_original_proxy_boundary() -> void:
	var layout := ShipLayout.authored().layout
	var target: Interactions.Target
	for candidate: Interactions.Target in Interactions.new(layout).targets_on_deck(14):
		if candidate.id == &"D14-BAY-ROD": target = candidate
	assert_true(target != null,"existing pickup target remains registered")
	var center := target.center
	assert_float_in_range(ClickPicker._target_distance(center+Vector3(0.109,1,0.574),Vector3.DOWN,target,layout),0.8999,0.9001,"22cm x 10cm x 1.15m proxy retains its inside corner")
	assert_float_in_range(ClickPicker._target_distance(center+Vector3(0.111,1,0),Vector3.DOWN,target,layout),-1,-1,"unchanged 11cm half-width rejects outside click")
	assert_float_in_range(ClickPicker._target_distance(center+Vector3(0,1,0.576),Vector3.DOWN,target,layout),-1,-1,"unchanged 57.5cm half-length rejects outside click")
	assert_float_in_range(ClickPicker._target_distance(center+Vector3(0.2,0.101,0),Vector3.LEFT,target,layout),-1,-1,"unchanged 10cm proxy top rejects outside click")
