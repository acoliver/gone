extends SimTestCase
# New pod #88: pins follow the fitted asset, row centers and eight-piece topology.
## The authored pod keeps envelope and sit-up clearance parity while all
## seven instances share five smooth mesh nodes and five materials (#88). Collision data
## stays independent of this presentation mesh.

## The lying eye, pod-local, from the authored pose table (sim/exit.gd):
## the tray floor plus the capsule radius and penetration tolerance, at
## the head sphere's station.
const EYE_POD: Vector3 = Vector3(0.0, 0.545, -0.575)

## The sit-up arc's pivot and radius, pod-local: the capsule pivots
## about the foot sphere from lying to upright.
const ARC_CENTER: Vector3 = Vector3(0.0, 0.545, 0.575)
const ARC_RADIUS: float = 1.15
const ARC_SAMPLES: int = 17

var _tri_a: Array[Vector3] = []
var _tri_b: Array[Vector3] = []
var _tri_c: Array[Vector3] = []
var _tri_min: Array[Vector3] = []
var _tri_max: Array[Vector3] = []

func test_fabric_reflectance_keeps_the_padding_distinct() -> void:
	var couch := PodMesh.couch_material()
	var pillow: StandardMaterial3D = PodMesh._materials["PillowFabric"]
	assert_true(couch.albedo_color == Color(.50,.51,.52).linear_to_srgb(), "light neutral medical padding remains visible through the glass")
	assert_true(pillow.albedo_color == Color(.70,.71,.72).linear_to_srgb(), "the near-white pillow stays distinct from the couch")
	assert_true(absf(couch.roughness - .9) < 1e-4, "medical padding has a rough cloth finish")
	assert_true(absf(pillow.roughness - .9) < 1e-4, "the pillow has the same rough cloth finish")
	assert_false(couch.emission_enabled, "the padding is lit fabric, not a luminous panel")
	assert_false(pillow.emission_enabled, "the pillow reflects the pod and room lights")

func test_exported_padding_matches_the_runtime_material_pins() -> void:
	var source: PackedScene = load(PodMesh.POD_PATH)
	var shell: Node3D = source.instantiate()
	for entry: Array in [["Couch", PodMesh.COUCH_ALBEDO], ["Pillow", PodMesh.PILLOW_ALBEDO]]:
		var mesh: MeshInstance3D = shell.get_node("PodBase/" + entry[0])
		var material: StandardMaterial3D = mesh.mesh.surface_get_material(0)
		assert_true(material.albedo_color.is_equal_approx(entry[1].linear_to_srgb()), "exported %s preserves its authored linear reflectance" % entry[0])
		assert_true(absf(material.roughness - PodMesh.FABRIC_ROUGHNESS) < 1e-4, "exported cloth preserves its authored roughness")
		assert_float_equal(material.metallic, 0.0, "padding is dielectric")
		assert_false(material.emission_enabled, "exported padding remains non-emissive")
	shell.free()

func test_all_seven_pods_share_the_one_shell_mesh() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	var groups: Array[Node] = pods.get_children()
	assert_int_equal(groups.size(), Pods.POD_COUNT, "every registry pod gets a group")
	var total_shells := 0
	var shared: Dictionary[String, Mesh] = {}
	for group: Node in groups:
		var shell := _shell_of(group)
		assert_true(shell != null, "%s carries exactly one shell hierarchy" % group.name)
		if shell == null:
			continue
		total_shells += 1
		var meshes := shell.find_children("*", "MeshInstance3D", true, false)
		assert_int_equal(meshes.size(), 5, "new pod #88 retains five authored mesh nodes")
		for instance: MeshInstance3D in meshes:
			if shared.has(String(instance.name)):
				assert_true(instance.mesh == shared[String(instance.name)], "all pods share %s" % instance.name)
			else:
				shared[String(instance.name)] = instance.mesh
	assert_int_equal(total_shells, Pods.POD_COUNT, "all seven pods share the one shell hierarchy")

func test_every_pod_envelope_matches_the_authored_footprint() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	var bounds: AABB = PodMesh.shell_mesh(Pods.PodState.SEALED).get_aabb()
	for group: Node in pods.get_children():
		var shell := _shell_of(group)
		if shell == null:
			assert_true(false, "%s carries a shell" % group.name)
			continue
		var lo := Vector3(INF, INF, INF)
		var hi := Vector3(-INF, -INF, -INF)
		for x: float in [bounds.position.x, bounds.end.x]:
			for y: float in [bounds.position.y, bounds.end.y]:
				for z: float in [bounds.position.z, bounds.end.z]:
					var corner: Vector3 = PodMesh.shell_transform() * Vector3(x, y, z)
					lo = lo.min(corner)
					hi = hi.max(corner)
		var size := hi - lo
		assert_float_in_range(size.x / Pods.POD_WIDTH, 0.99, 1.01, "%s width parity vs authored %.2f m" % [group.name, Pods.POD_WIDTH])
		assert_float_in_range(size.y / Pods.POD_HEIGHT, 0.99, 1.01, "%s height parity vs authored %.2f m" % [group.name, Pods.POD_HEIGHT])
		assert_float_in_range(size.z / Pods.POD_LENGTH, 0.99, 1.01, "%s length parity vs authored %.2f m" % [group.name, Pods.POD_LENGTH])

func test_player_pod_renders_only_the_shell_canopy() -> void:
	var registry := Pods.PodRegistry.frozen()
	var pods := StasisPods.build(registry)
	var group: Node = pods.get_child(registry.player_pod().id().index())
	if _shell_of(group) == null:
		assert_true(false, "the player pod carries its shell")
		return
	assert_int_equal(
		_box_children(group).size(),
		0,
		"the player pod renders no greybox boxes: no canopy, no plate"
	)

func test_shell_resource_loads_and_stays_cheap() -> void:
	var scene: PackedScene = load(PodMesh.POD_PATH)
	assert_true(scene != null and scene.can_instantiate(), "the pod shell GLB loads and instantiates")
	if scene == null or not scene.can_instantiate():
		return
	var mesh: Mesh = PodMesh.shell_mesh()
	if mesh == null:
		assert_true(false, "the shell mesh extracts from the GLB")
		return
	# Issue #88 replaces the scan's single bone-white lacquer with pristine
	# neutral plastic, dark glass, and rough fabric on authored geometry.
	assert_int_equal(mesh.get_surface_count(), 5, "new pod #88 has plastic, tint, couch, pillow and gasket surfaces")
	var expected: Array[Material] = [PodMesh.shell_material(), PodMesh.canopy_material(), PodMesh.couch_material(), PodMesh._materials["PillowFabric"], PodMesh._materials["Gasket"]]
	var triangles := 0
	for surface: int in range(mesh.get_surface_count()):
		assert_true(mesh.surface_get_material(surface) == expected[surface], "surface material is cached, nothing per-instance")
		var arrays: Array = mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		assert_int_equal(indices.size() % 3, 0, "surface index buffer is whole triangles")
		triangles += indices.size() / 3
		assert_true(vertices.size() < indices.size() / 2, "curved surfaces reuse smooth vertices rather than split every triangle")
	var lacquer := PodMesh.shell_material()
	assert_true(lacquer.albedo_color == Color(0.95, 0.95, 0.95).linear_to_srgb(), "the shell is near-white without a warm bone tint")
	assert_true(absf(lacquer.roughness - 0.12) < 1e-4, "plastic has a low-roughness highlight")
	assert_float_equal(lacquer.metallic, 0.0, "plastic is dielectric")
	assert_true(lacquer.clearcoat_enabled, "plastic carries a clearcoat")
	assert_float_equal(lacquer.clearcoat, 1.0, "clearcoat is full")
	assert_true(absf(lacquer.clearcoat_roughness - 0.08) < 1e-4, "clearcoat highlight stays tight")
	assert_false(lacquer.emission_enabled, "plastic reflects room light without emitting")
	for material: Material in expected:
		if material is StandardMaterial3D:
			assert_true(material.albedo_texture == null and material.normal_texture == null and material.roughness_texture == null, "opaque surfaces have no grunge textures")
		else:
			# #88: replace the opaque color pin with the tested thin-glass contract.
			assert_true(material == PodMesh.canopy_material() and material is ShaderMaterial, "only glazing uses a shader")
			assert_true(material.shader.get_shader_uniform_list().is_empty(), "glass needs no texture bindings")
	assert_true(PodMesh.couch_material().albedo_color == Color(.50, .51, .52).linear_to_srgb(), "couch is light neutral medical padding")
	assert_true(absf(PodMesh.couch_material().roughness - 0.9) < 1e-4, "fabric stays rough")
	assert_true(triangles > 0, "the pod mesh is not empty")
	assert_true(triangles <= 20000, "the entire pod stays cheap: %d tris must be <= 20000" % triangles)

func test_shell_transforms_are_deterministic() -> void:
	var first := PodMesh.shell_transform()
	var second := PodMesh.shell_transform()
	assert_true(first == Transform3D.IDENTITY, "asset is authored directly in pod-local meters")
	assert_vec3_equal(first.origin, second.origin, "the transform origin rebuilds identically")
	assert_true(first.basis == second.basis, "the transform basis rebuilds identically")
	var shell_a := PodMesh.make_shell()
	var shell_b := PodMesh.make_shell()
	assert_true(shell_a.transform == shell_b.transform, "fresh shell instances land on the identical transform")
	assert_true((shell_a.get_node("PodBase") as MeshInstance3D).mesh == (shell_b.get_node("PodBase") as MeshInstance3D).mesh, "fresh shell hierarchies share the one base mesh")
	var pods_a := StasisPods.build(Pods.PodRegistry.frozen())
	var pods_b := StasisPods.build(Pods.PodRegistry.frozen())
	assert_int_equal(pods_b.get_child_count(), pods_a.get_child_count(), "both scene builds carry every pod group")
	for index: int in range(pods_a.get_child_count()):
		var from_a := _shell_of(pods_a.get_child(index))
		var from_b := _shell_of(pods_b.get_child(index))
		if from_a == null or from_b == null:
			assert_true(false, "pod %d carries its shell in both builds" % index)
			continue
		assert_true(from_a.transform == from_b.transform, "pod %d's shell transform is identical across scene rebuilds" % index)

func test_sit_up_corridor_stays_clear() -> void:
	_ensure_triangles()
	var worst := INF
	for step: int in range(ARC_SAMPLES):
		var phi: float = PI * 0.5 * float(step) / float(ARC_SAMPLES - 1)
		var sample: Vector3 = ARC_CENTER + Vector3(0.0, sin(phi) * ARC_RADIUS, -cos(phi) * ARC_RADIUS)
		var distance := _min_distance(sample, 1.5)
		assert_true(distance < 1.5, "arc sample (%s) finds the shell, got %s" % [str(sample), str(distance)])
		if step == 0:
			assert_close(sample, EYE_POD, "the arc starts at the authored lying eye")
			assert_true(distance >= 0.04, "the lying eye clears the shell by >= 0.04 m, got %.4f" % distance)
		worst = minf(worst, distance)
	assert_true(worst >= 0.03, "the sit-up corridor's worst clearance is >= 0.03 m, got %.4f" % worst)

func test_greybox_dressing_is_fully_retired() -> void:
	var registry := Pods.PodRegistry.frozen()
	var pods := StasisPods.build(registry)
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var sealed_lids := 0
	var open_lids := 0
	var blankets := 0
	var plates := 0
	for pod: Pods.Pod in registry.pods():
		var group: Node = pods.get_child(pod.id().index())
		for instance: MeshInstance3D in _box_children(group):
			if instance.position == plate.center and (instance.mesh as BoxMesh).size == plate.size:
				plates += 1
				continue
			if _matches_solid(instance, PodBody.sealed_lid()):
				sealed_lids += 1
			if _matches_solid(instance, PodBody.open_lid()):
				open_lids += 1
			if _matches_solid(instance, PodBody.hanging_blanket()):
				blankets += 1
		assert_int_equal(
			_box_children(group).size(),
			0,
			"pod %d renders zero box children in any state, empty-open included" % pod.id().index()
		)
	assert_int_equal(sealed_lids, 0, "no sealed pod keeps its flat lid")
	assert_int_equal(open_lids, 0, "no empty-open pod keeps its tilted lid")
	assert_int_equal(blankets, 0, "no empty-open pod keeps its hanging blanket")
	assert_int_equal(plates, 0, "no pod keeps its indicator plate")

## The pod group's shell instance, or null when the group lacks one.
func _shell_of(group: Node) -> Node3D:
	return group.get_node_or_null("PodShell") as Node3D

## The group's BoxMesh instances: with the greybox kit and the hanging
## blankets retired, no box renders in a pod group at all.
func _box_children(group: Node) -> Array[MeshInstance3D]:
	var boxes: Array[MeshInstance3D] = []
	for child: Node in group.get_children():
		var instance := child as MeshInstance3D
		if instance != null and instance.mesh is BoxMesh:
			boxes.append(instance)
	return boxes

## Whether one dressing instance sits at an authored solid's placement:
## same box size, same center, same roll about the pod's X axis. The
## roll compares approximately because Node3D stores its rotation as a
## basis, so the quaternion property does not roundtrip bit-exactly.
func _matches_solid(instance: MeshInstance3D, solid: PodBody.PodSolid) -> bool:
	var box: BoxMesh = instance.mesh
	var roll := Quaternion(Vector3.RIGHT, solid.roll_radians)
	return box.size == solid.size and instance.position == solid.center and instance.quaternion.is_equal_approx(roll)

## Load the shell triangles into the pod frame once: the test instance
## survives the whole file, so later tests reuse the same arrays.
func _ensure_triangles() -> void:
	if not _tri_a.is_empty():
		return
	var to_pod := PodMesh.shell_transform()
	var mesh := PodMesh.shell_mesh()
	for surface: int in range(mesh.get_surface_count()):
		var arrays: Array = mesh.surface_get_arrays(surface)
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		for index: int in range(indices.size() / 3):
			var a: Vector3 = to_pod * verts[indices[index * 3]]
			var b: Vector3 = to_pod * verts[indices[index * 3 + 1]]
			var c: Vector3 = to_pod * verts[indices[index * 3 + 2]]
			_tri_a.append(a)
			_tri_b.append(b)
			_tri_c.append(c)
			_tri_min.append(a.min(b.min(c)))
			_tri_max.append(a.max(b.max(c)))

## Minimum distance from a pod-frame point to the transformed shell
## surface, or 99.0 when no triangle sits within the prune radius.
## Ray-AABB pruning keeps the per-point triangle tests low.
func _min_distance(point: Vector3, prune: float) -> float:
	var best: float = prune * prune + 1.0
	var found := false
	for index: int in range(_tri_a.size()):
		var lo: Vector3 = _tri_min[index]
		var hi: Vector3 = _tri_max[index]
		if point.x < lo.x - prune or point.x > hi.x + prune:
			continue
		if point.y < lo.y - prune or point.y > hi.y + prune:
			continue
		if point.z < lo.z - prune or point.z > hi.z + prune:
			continue
		var distance_sq := _point_tri_distance_sq(point, index)
		if distance_sq < best:
			best = distance_sq
			found = true
	if not found:
		return 99.0
	return sqrt(best)

## Squared distance from a point to one triangle (Ericson's closest
## point), in the pod frame. Assumes the caller pruned by AABB already.
func _point_tri_distance_sq(point: Vector3, index: int) -> float:
	var a: Vector3 = _tri_a[index]
	var ab: Vector3 = _tri_b[index] - a
	var ac: Vector3 = _tri_c[index] - a
	var ap: Vector3 = point - a
	var d1: float = ab.dot(ap)
	var d2: float = ac.dot(ap)
	if d1 <= 0.0 and d2 <= 0.0:
		return ap.length_squared()
	var bp: Vector3 = point - _tri_b[index]
	var d3: float = ab.dot(bp)
	var d4: float = ac.dot(bp)
	if d3 >= 0.0 and d4 <= d3:
		return bp.length_squared()
	var vc: float = d1 * d4 - d3 * d2
	if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
		var v: float = d1 / (d1 - d3)
		return (ap - ab * v).length_squared()
	var cp: Vector3 = point - _tri_c[index]
	var d5: float = ab.dot(cp)
	var d6: float = ac.dot(cp)
	if d6 >= 0.0 and d5 <= d6:
		return cp.length_squared()
	var vb: float = d5 * d2 - d1 * d6
	if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
		var w: float = d2 / (d2 - d6)
		return (ap - ac * w).length_squared()
	var va: float = d3 * d6 - d5 * d4
	if va <= 0.0 and d4 - d3 >= 0.0 and d5 - d6 >= 0.0:
		var w2: float = (d4 - d3) / ((d4 - d3) + (d5 - d6))
		return (bp - (_tri_c[index] - _tri_b[index]) * w2).length_squared()
	var denom: float = 1.0 / (va + vb + vc)
	var v2: float = vb * denom
	var w3: float = vc * denom
	return (ap - ab * v2 - ac * w3).length_squared()

func test_presentation_and_exit_path_share_pure_tray_geometry() -> void:
	assert_true(PodBody.pod_solids(Pods.PodState.PLAYER)[0] is PodGeometry.PodSolid, "presentation consumes pure pod solids")
	assert_float_equal(PodBody.TRAY_FLOOR_Y, PodGeometry.TRAY_FLOOR_Y, "tray floor has one owner")
	var expected := Exit.ExitPath.try_new(Pods.PodRegistry.frozen().player_pod().placement(), PodGeometry.TRAY_FLOOR_Y)
	assert_true(expected.is_ok(), "pure tray floor supports the existing exit path")
	assert_vec3_equal(PlacementTruth.player_exit_path().poses()[0].foot(), ShipLayout.authored().layout.bay_to_world() * expected.path.poses()[0].foot(), "path starts at the shared tray floor")

func test_lids_follow_each_state_about_the_authored_pivot() -> void:
	var registry := Pods.PodRegistry.frozen()
	var pods := StasisPods.build(registry)
	for pod: Pods.Pod in registry.pods():
		var shell := _shell_of(pods.get_child(pod.id().index()))
		var lid: Node3D = shell.get_node("PodLid")
		var expected := {Pods.PodState.SEALED: 0.0, Pods.PodState.EMPTY_OPEN: -67.7295, Pods.PodState.PLAYER: -67.7295}
		# #88: a seam-level hinge stays in contact and the rear sweep limits opening.
		assert_close(lid.position, Vector3(0, 0.437, -1.17250931), "hidden hinge")
		assert_true(absf(rad_to_deg(lid.rotation.x) - expected[pod.state()]) < 1e-4, "state lid angle")
		assert_true(lid.has_node("WindowPane"), "pane moves with the lid")
		assert_true(shell.get_node("PodBase").has_node("Couch") and shell.get_node("PodBase").has_node("Pillow"), "upholstery stays under the base")
	pods.free()

func test_open_lid_uses_the_largest_angle_inside_the_wall_sweep_budget() -> void:
	# #88: the 2.5 m walkway and 20 mm wall reserve now limit opening, not height.
	var source: PackedScene = load(PodMesh.POD_PATH)
	var shell: Node3D = source.instantiate()
	var lid: MeshInstance3D = shell.get_node("PodLid")
	lid.rotation.x = PodGeometry.lid_angle(Pods.PodState.PLAYER)
	var top := _lid_top(lid)
	assert_float_in_range(top, 2.6313, 2.6316, "#88: measured seam-hinge open height")
	assert_true(Pods.ROOM_CEILING_HEIGHT - top >= 0.05, "player lid leaves at least 50 mm ceiling clearance")
	assert_true(_lid_rear(lid) <= Pods.ROW_WALL_OFFSET - 0.02 + 1e-6, "open lid retains 20 mm wall clearance")
	lid.rotation.x -= deg_to_rad(0.001)
	assert_true(_lid_rear(lid) > Pods.ROW_WALL_OFFSET - 0.02, "the next millidegree exceeds the wall sweep budget")
	shell.free()

func _lid_top(lid: MeshInstance3D) -> float:
	var top := -INF
	var pane: MeshInstance3D = lid.get_node("WindowPane")
	for instance: MeshInstance3D in [lid, pane]:
		var frame := lid.transform if instance == lid else lid.transform * pane.transform
		for surface: int in range(instance.mesh.get_surface_count()):
			var vertices: PackedVector3Array = instance.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
			for vertex: Vector3 in vertices:
				top = maxf(top, (frame * vertex).y)
	return top

func _lid_rear(lid: MeshInstance3D) -> float:
	var rear := -Pods.POD_LENGTH / 2.0
	var pane: MeshInstance3D = lid.get_node("WindowPane")
	for instance: MeshInstance3D in [lid, pane]:
		var frame := lid.transform if instance == lid else lid.transform * pane.transform
		for surface: int in range(instance.mesh.get_surface_count()):
			for vertex: Vector3 in instance.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
				rear = minf(rear, (frame * vertex).z)
	return -Pods.POD_LENGTH / 2.0 - rear

func test_live_camera_interpolation_clears_the_model() -> void:
	_ensure_triangles()
	# New pod #88: actual rig interpolates the eye, rather than following
	# the capsule's quarter-circle. The final tick uses standing-eye height.
	var waypoints: Array[Vector3] = [Vector3(0, 0.545, -0.575), Vector3(0, 1.695, 0.575), Vector3(0, 1.695, 0.8865), Vector3(0, 1.695, 1.5065), Vector3(0, 1.605, 1.5065)]
	var placement := Pods.PodRegistry.frozen().player_pod().placement()
	var pod_to_bay := Transform3D(Basis(Vector3.UP, placement.yaw_radians), Vector3(placement.center.x, 0, placement.center.y))
	var path := Exit.ExitPath.try_new(placement, PodGeometry.TRAY_FLOOR_Y).path
	for index: int in range(5):
		var actual := path.poses()[index].head() if index < 4 else PlayerMotion.standing_eye(path.waypoint().capsule())
		assert_close(pod_to_bay.affine_inverse() * actual, waypoints[index], "measured path matches the rig's eye projection")
	for segment: int in range(4):
		for station: int in range(101):
			var point := waypoints[segment].lerp(waypoints[segment + 1], station / 100.0)
			assert_true(_min_distance(point, 2.0) >= 0.13, "the live eye stays at least 13 cm from pod-v4")
