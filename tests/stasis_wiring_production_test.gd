extends SimTestCase

func test_installation_reuses_baked_meshes_and_native_materials_without_context() -> void:
	var first := StasisWiring.installation()
	var second := StasisWiring.installation()
	assert_true(first.get_child_count()==2, "one network and one physical source, no proof context")
	var source := first.get_node("PhysicalSourceEnclosure") as Node3D
	assert_vec3_equal(source.position, StasisWiringRoutes.SOURCE, "source is mounted at the measured end-wall position")
	assert_true((source.basis*Vector3.BACK).is_equal_approx(Vector3.RIGHT), "glands face +X")
	var left: Array[MeshInstance3D] = []
	var right: Array[MeshInstance3D] = []
	_meshes(first,left)
	_meshes(second,right)
	assert_true(left.size()==right.size() and left.size()>7, "network and source imported meshes exist")
	for i in range(left.size()):
		assert_true(left[i].mesh==right[i].mesh, "repeated scene builds share imported meshes")
		assert_true(left[i].get_active_material(0)==right[i].get_active_material(0), "native PBR resources are shared")
		assert_true(left[i].material_override==null, "installation preserves native muted metal and insulation")
		assert_true(not String(left[i].name).contains("steel_frame"), "no duplicated proof ceiling grid")
		assert_true(left[i].mesh.get_aabb().end.y<3.15, "export stays in +Y-up bay frame")
	assert_true(_static_only(first), "no scripts, colliders, particles, lights or runtime cable physics below installation")
	first.free()
	second.free()

func test_baked_fault_endpoints_agree_with_the_single_production_opening() -> void:
	var graph := StasisWiringRoutes.graph()
	assert_true(StasisWiringRoutes.validate(graph).is_empty(), "installed graph is connected")
	assert_true(graph.fault.opening_cell==BayCeiling.EMPTY_CELLS[0], "one existing opening is shared")
	for point: Vector3 in graph.fault.connection_endpoints:
		assert_float_in_range(point.y,2.81999,2.82001,"power stays above full pod lid sweep")
		assert_float_in_range(point.z,-.614,-.586,"connections follow the failed lower seat at Z=-0.6")
		assert_true(is_equal_approx(point.x,-1.15) or is_equal_approx(point.x,-.05), "connections reach both retained ends")
	assert_true(graph.fault.released_cores_and_sparks_installed, "production includes released cores and three real tip sparks")
	assert_true(graph.fault.power_tip_positions==Placement.spark_spots(), "effects use the generated physical tip inventory")

func _static_only(node: Node) -> bool:
	if node.get_script()!=null or node is CollisionObject3D or node is CollisionShape3D or node is Light3D or node is GPUParticles3D: return false
	for child: Node in node.get_children():
		if not _static_only(child): return false
	return true

func _meshes(node: Node, output: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D: output.append(node as MeshInstance3D)
	for child: Node in node.get_children(): _meshes(child,output)
