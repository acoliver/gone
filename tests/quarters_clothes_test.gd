extends SimTestCase

const CLOTHES := {"her_jacket": "Item_her_jacket", "her_dresses": "Placement_wardrobe/her_dresses"}

func test_clothes_replace_standins_with_unmodified_state_assets_on_real_furniture() -> void:
	for state: StringName in QuartersProps.STATES:
		var room := QuartersFurnishings.build(state)
		assert_true(room.find_children("Standin_her_*", "", true, false).is_empty(), "all her clothing stand-ins removed")
		for id: String in CLOTHES:
			var asset := room.get_node_or_null(CLOTHES[id]) as Node3D
			assert_true(asset != null, "real clothing: " + id)
			if asset == null: continue
			var suffix := ".glb" if state == &"as_built" else "_aged.glb"
			assert_true(asset.scene_file_path == QuartersFurnishings.ROOT + id + suffix, "matching state asset: " + id)
			var support := room.get_node("Placement_dining_chair_1/dining_chair" if id == "her_jacket" else "Placement_wardrobe/wardrobe") as Node3D
			assert_true(asset.transform == support.transform, "authored furniture origin and complete transform: " + id)
			for mesh: MeshInstance3D in asset.find_children("*", "MeshInstance3D", true, false):
				assert_true(mesh.material_override == null, "no furniture finish on clothing")
				for surface: int in range(mesh.mesh.get_surface_count()):
					assert_true(mesh.get_surface_override_material(surface) == null, "authored wool, hangers and fibres retained")
		room.free()

func test_clothes_clear_chair_wardrobe_and_existing_tunic_triangles() -> void:
	for state: StringName in QuartersProps.STATES:
		var room := QuartersFurnishings.build(state)
		for id: String in CLOTHES:
			var asset := room.get_node_or_null(CLOTHES[id]) as Node3D
			assert_true(asset != null, "real clothing for clearance: " + id)
			if asset == null: continue
			var supports: Array = [room.get_node("Placement_dining_chair_1/dining_chair")] if id == "her_jacket" else [room.get_node("Placement_wardrobe/wardrobe"), room.get_node("Placement_wardrobe/HangingUniform"), room.get_node("Placement_wardrobe/UniformFragments")]
			for support: Node in supports:
				assert_false(_crosses(asset, support), "%s %s clears %s triangles" % [state, id, support.name])
		room.free()

func test_aged_fibre_heaps_rest_on_seat_floor_and_wardrobe_shelf() -> void:
	var room := QuartersFurnishings.build(&"aged")
	var jacket := room.get_node_or_null("Item_her_jacket")
	var dresses := room.get_node_or_null("Placement_wardrobe/her_dresses")
	assert_true(jacket != null and dresses != null, "real aged clothes for fibre support")
	if jacket != null and dresses != null:
		var seat := room.get_node("Placement_dining_chair_1/dining_chair").find_child("SeatPad", true, false) as MeshInstance3D
		var shelf := room.get_node("Placement_wardrobe/wardrobe").find_child("BottomPanel", true, false) as MeshInstance3D
		var dust := jacket.find_child("SeatFibreDust", true, false) as MeshInstance3D
		assert_true(dust != null, "seat fibre deposit retained")
		if dust != null: _assert_supported(dust, seat)
		var floor_dust := jacket.find_child("FloorFibreDust", true, false) as MeshInstance3D
		assert_true(floor_dust != null, "floor fibre deposit retained")
		if floor_dust != null:
			var bounds := ShipScene._world_frame(floor_dust) * floor_dust.get_aabb()
			assert_float_in_range(bounds.position.y - QuartersLayout.FLOOR_Y, 0.0, 0.003, "jacket fibres rest on room floor")
		for dress: String in ["RoseDress", "BlueDress"]:
			for suffix: String in ["_FibreHeap", "_FibreHeap_Base"]:
				var heap := dresses.find_child(dress + suffix, true, false) as MeshInstance3D
				assert_true(heap != null, "dress fibre heap retained: " + dress + suffix)
				if heap != null: _assert_supported(heap, shelf)
	room.free()

func test_triangle_clearance_detects_penetration_but_allows_separated_meshes() -> void:
	var surface := MeshInstance3D.new()
	surface.mesh = BoxMesh.new()
	var crossing := MeshInstance3D.new()
	crossing.mesh = BoxMesh.new()
	crossing.position = Vector3(0.4, 0.3, 0.2)
	assert_true(_crosses(surface, crossing), "triangle check detects crossing boxes")
	crossing.position.x = 2
	assert_false(_crosses(surface, crossing), "triangle check permits separated boxes")
	surface.free()
	crossing.free()

func test_clothing_close_views_are_accepted_and_required_in_both_states() -> void:
	for view: String in ["jacket", "wardrobe"]:
		var scenario := {"name": "clothes-view", "mode": "capture", "content": "gameplay", "start": "quarters", "beats": [{"name": "view", "tick": 1, "quarters_view": view}]}
		assert_true(HarnessScenario.parse(JSON.stringify(scenario)).error == "", "clothing camera accepted: " + view)
		for state: String in ["remembered", "present"]:
			assert_true(QuartersCapture.REQUIRED.has(state + "-" + view), "required clothing capture: " + state + "-" + view)

func _assert_supported(heap: MeshInstance3D, support: MeshInstance3D) -> void:
	var frame := ShipScene._world_frame(heap)
	var support_frame := ShipScene._world_frame(support)
	var bounds := frame * heap.get_aabb()
	var top := support_frame * support.get_aabb()
	assert_true(bounds.position.x >= top.position.x and bounds.end.x <= top.end.x and bounds.position.z >= top.position.z and bounds.end.z <= top.end.z, "heap fits support: " + String(heap.name))
	var triangles := support.mesh.generate_triangle_mesh()
	var inverse := support_frame.affine_inverse()
	var gap := INF
	for vertex: Vector3 in heap.mesh.get_faces():
		var point := frame * vertex
		var hit := triangles.intersect_segment(inverse * (point + Vector3.UP * 0.01), inverse * (point + Vector3.DOWN * 0.1))
		if not hit.is_empty():
			var distance: float = point.y - (support_frame * hit.position).y
			assert_true(distance >= -0.00001, "fibre does not penetrate support: " + String(heap.name))
			gap = minf(gap, distance)
	assert_float_in_range(gap, 0.0, 0.003, "heap contacts real support within 3 mm: " + String(heap.name))

func _crosses(first: Node3D, second: Node3D) -> bool:
	var left := _meshes(first)
	var right := _meshes(second)
	for a: MeshInstance3D in left:
		for b: MeshInstance3D in right:
			var a_bounds := ShipScene._world_frame(a) * a.get_aabb()
			var b_bounds := ShipScene._world_frame(b) * b.get_aabb()
			if not a_bounds.intersects(b_bounds): continue
			if _edges_cross(a, b) or _edges_cross(b, a): return true
	return false

func _meshes(node: Node3D) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	if not node.visible: return result
	if node is MeshInstance3D: result.append(node)
	for child: Node in node.get_children():
		if child is Node3D: result.append_array(_meshes(child))
	return result

func _edges_cross(source: MeshInstance3D, target: MeshInstance3D) -> bool:
	var frame := ShipScene._world_frame(target).affine_inverse() * ShipScene._world_frame(source)
	var triangles := target.mesh.generate_triangle_mesh()
	var faces := source.mesh.get_faces()
	for index: int in range(0, faces.size(), 3):
		for edge: int in range(3):
			var start := frame * faces[index + edge]
			var end := frame * faces[index + (edge + 1) % 3]
			var direction := (end - start).normalized() * 0.00001
			if not triangles.intersect_segment(start + direction, end - direction).is_empty(): return true
	return false
