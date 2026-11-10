extends SimTestCase

const Presenter = preload("res://app/stasis_wiring.gd")

func test_static_proofs_reuse_imported_resources_and_external_source() -> void:
	var first := Presenter.build(&"supported-transition", false)
	var cache := Presenter.cache_size()
	var second := Presenter.build(&"supported-transition", false)
	assert_true(Presenter.cache_size() == cache, "repeat build uses the same finite packed-scene cache")
	# Issue 110: end-wall mounting aligns actual local +Z sockets with the +X trunk.
	var enclosure := first.get_node("PhysicalSourceEnclosure") as Node3D
	assert_true(enclosure.position == Vector3(-5.935,2.75,-3.1), "source back is mounted on the X=-6 end wall")
	assert_true((enclosure.basis * Vector3.BACK).distance_to(Vector3.RIGHT) < 0.000001, "socket axes face the supported trunk, without service loopbacks")
	var left: Array[MeshInstance3D] = []
	var right: Array[MeshInstance3D] = []
	_meshes(first,left)
	_meshes(second,right)
	assert_true(left.size() >= 5 and left.size() == right.size(), "static geometry and actual enclosure import")
	for i: int in range(left.size()):
		assert_true(left[i].mesh == right[i].mesh, "proof instances share baked meshes")
	first.free()
	second.free()

func test_fault_context_has_eight_panels_and_isolated_fragment() -> void:
	var proof := Presenter.build(&"fault-frame-pair")
	var context := proof.get_node("ProofContext")
	assert_true(context.get_child_count() == 9, "one missing tile in a nine-cell proof; eight actual panels and floor")
	Presenter.isolate_fragment(proof)
	var meshes: Array[MeshInstance3D] = []
	_meshes(proof.get_child(0),meshes)
	var visible_count := 0
	for mesh: MeshInstance3D in meshes:
		if mesh.visible:
			visible_count += 1
			assert_true(String(mesh.name).begins_with("fallen_fragment"), "isolated proof retains only the paired rail fragment")
	assert_true(visible_count == 1, "fallen fragment is one material-grouped static mesh")
	proof.free()

func test_lower_seat_shares_pbr_and_matches_measured_rod_pose() -> void:
	var proof := Presenter.build(&"fault-frame-pair", false)
	var meshes: Array[MeshInstance3D] = []
	_meshes(proof, meshes)
	var seat_count := 0
	for mesh: MeshInstance3D in meshes:
		if String(mesh.name).begins_with("seat_") or String(mesh.name).begins_with("fallen_fragment"):
			seat_count += 1
			assert_true(mesh.material_override == SeatRailComponent.material(), "installed seat and fallen middle share one actual source PBR resource")
	assert_true(seat_count == 4, "healthy group, individual imported left/right sources and fallen middle are present")
	for part: String in ["left", "right"]:
		var source := proof.get_child(0).get_node("SeatRail_" + part) as Node3D
		assert_true(source.position == BayCeiling.FAILED_SEAT_CENTER, "retained imported source has its measured bearing placement")
	var pose := SeatRailComponent.floor_pose()
	var old_axis := (Basis(Vector3.UP, Rod.YAW_RADIANS) * Basis(Vector3.RIGHT, PI / 2.0)) * Vector3.UP
	assert_true(pose.basis.x.distance_to(old_axis) < 0.000001, "X-long rail follows the old cylinder Y axis after its actual laydown and yaw")
	assert_true(Vector2(pose.origin.x,pose.origin.z).distance_to(Vector2(-0.6,-1.4)) < 0.000001, "pickup center is unchanged")
	assert_true(absf(rad_to_deg(atan2(-pose.basis.z.y,pose.basis.y.y))-115.0) < 0.00001, "physical roll opens the C sideways and up")
	var carrier := proof.get_child(0).get_node("steel_frame") as MeshInstance3D
	var hardware := carrier.material_override as StandardMaterial3D
	assert_true(hardware != null and hardware == Presenter._hardware_material(), "separate carrier uses the actual accepted BayCeiling hardware resource")
	assert_true(hardware.albedo_texture == BayCeilingMaterial.ALBEDO[&"intact"] and is_equal_approx(hardware.metallic,0.62) and is_equal_approx(hardware.roughness,0.78), "carrier is not bound to the coarse world-projected steel shader")
	proof.free()

func test_imported_boots_and_nuts_preserve_distinct_source_pbr() -> void:
	var proof := Presenter.build(&"supported-transition", false)
	var enclosure := proof.get_node("PhysicalSourceEnclosure") as Node3D
	var meshes: Array[MeshInstance3D] = []
	_meshes(enclosure, meshes)
	var boots := 0
	var nuts := 0
	for mesh: MeshInstance3D in meshes:
		var label := String(mesh.name)
		if not label.contains("compression"): continue
		assert_true(mesh.material_override == null and mesh.get_surface_override_material(0) == null, "source materials are not repainted by the static presenter")
		var pbr := mesh.get_active_material(0) as StandardMaterial3D
		assert_true(pbr != null, "source part retains native PBR")
		if label.contains("black"):
			boots += 1
			var linear := pbr.albedo_color.srgb_to_linear()
			assert_true(absf(linear.r-0.018)<0.00001 and absf(linear.g-0.022)<0.00001 and absf(linear.b-0.020)<0.00001, "black polymer linear RGB matches exported glTF")
			assert_true(is_equal_approx(pbr.metallic,0.02) and is_equal_approx(pbr.roughness,0.67), "boot remains matte nonmetallic polymer")
		else:
			nuts += 1
			assert_true(is_equal_approx(pbr.metallic,0.88) and is_equal_approx(pbr.roughness,0.31), "hex nuts retain their distinct zinc PBR")
	assert_true(boots == 3 and nuts == 3, "two power ports and one compact data port retain both part types")
	proof.free()

func _meshes(node: Node, output: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D: output.append(node as MeshInstance3D)
	for child: Node in node.get_children(): _meshes(child,output)
