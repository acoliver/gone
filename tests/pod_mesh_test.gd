extends SimTestCase
## Pins for the pod-v2 shell wiring: the GLB loads and yields exactly
## one cheap textured mesh, every pod instances that one shared mesh
## under the frozen transform, the transformed envelope matches the
## authored (0.9, 0.8, 2.2) footprint within 1% per axis, the authored
## sit-up corridor stays clear with its worst clearance at the lying
## eye, the transform derivation is deterministic, and the state
## dressing (sealed lids, tilted open lids, hanging blankets, indicator
## plates) survives at its authored placements while the player pod
## renders nothing beyond the shell's own raised canopy and its plate.

## The lying eye, pod-local, from the authored pose table (sim/exit.gd):
## the tray floor plus the capsule radius and penetration tolerance, at
## the head sphere's station.
const EYE_POD: Vector3 = Vector3(0.0, 0.417, -0.575)

## The sit-up arc's pivot and radius, pod-local: the capsule pivots
## about the foot sphere from lying to upright.
const ARC_CENTER: Vector3 = Vector3(0.0, 0.417, 0.575)
const ARC_RADIUS: float = 1.15
const ARC_SAMPLES: int = 17

var _tri_a: Array[Vector3] = []
var _tri_b: Array[Vector3] = []
var _tri_c: Array[Vector3] = []
var _tri_min: Array[Vector3] = []
var _tri_max: Array[Vector3] = []

func test_all_seven_pods_share_the_one_shell_mesh() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	var groups: Array[Node] = pods.get_children()
	assert_int_equal(groups.size(), Pods.POD_COUNT, "every registry pod gets a group")
	var total_shells := 0
	for group: Node in groups:
		var shells := 0
		for child: Node in group.get_children():
			var instance := child as MeshInstance3D
			if instance != null and instance.mesh == PodMesh.shell_mesh():
				shells += 1
		assert_int_equal(shells, 1, "%s carries exactly one shell instance" % group.name)
		total_shells += shells
	assert_int_equal(total_shells, Pods.POD_COUNT, "all seven pods share the one shell mesh")

func test_every_pod_envelope_matches_the_authored_footprint() -> void:
	var pods := StasisPods.build(Pods.PodRegistry.frozen())
	var bounds: AABB = PodMesh.shell_mesh().get_aabb()
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
					var corner: Vector3 = shell.transform * Vector3(x, y, z)
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
	assert_int_equal(_dressing_boxes(group).size(), 0, "the player pod drops the greybox canopy and tray dressing")
	var boxes := _box_children(group)
	if boxes.size() != 1:
		assert_true(false, "the player pod's only box child is the indicator plate, got %d" % boxes.size())
		return
	var plate: MeshInstance3D = boxes[0]
	var expected: Placement.SolidPlacement = Placement.indicator_plate()
	if not (plate.position == expected.center and plate.mesh is BoxMesh):
		assert_true(false, "the player pod's one box child is the authored plate")
		return
	var plate_box: BoxMesh = plate.mesh
	assert_vec3_equal(plate_box.size, expected.size, "the player pod's plate keeps its authored size")

func test_shell_resource_loads_and_stays_cheap() -> void:
	var scene: PackedScene = load(PodMesh.POD_PATH)
	assert_true(scene != null and scene.can_instantiate(), "the pod shell GLB loads and instantiates")
	if scene == null or not scene.can_instantiate():
		return
	var mesh: Mesh = PodMesh.shell_mesh()
	if mesh == null:
		assert_true(false, "the shell mesh extracts from the GLB")
		return
	assert_int_equal(mesh.get_surface_count(), 1, "the shell carries exactly one surface")
	var material: Material = mesh.surface_get_material(0)
	assert_true(material is StandardMaterial3D, "the shell's one material is the imported StandardMaterial3D")
	var arrays: Array = mesh.surface_get_arrays(0)
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var triangles: int = indices.size() / 3
	assert_int_equal(indices.size() % 3, 0, "the shell surface index buffer is whole triangles")
	assert_true(triangles > 0, "the shell mesh is not empty")
	assert_true(triangles <= 20000, "the shell stays cheap: %d tris must be <= 20000" % triangles)

func test_shell_transforms_are_deterministic() -> void:
	var first := PodMesh.shell_transform()
	var second := PodMesh.shell_transform()
	assert_vec3_equal(first.origin, second.origin, "the transform origin rebuilds identically")
	assert_true(first.basis == second.basis, "the transform basis rebuilds identically")
	var shell_a := PodMesh.make_shell()
	var shell_b := PodMesh.make_shell()
	assert_true(shell_a.transform == shell_b.transform, "fresh shell instances land on the identical transform")
	assert_true(shell_a.mesh == shell_b.mesh, "fresh shell instances share the one mesh")
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
		var distance := _min_distance(sample, 1.0)
		assert_true(distance < 1.5, "arc sample (%s) finds the shell, got %s" % [str(sample), str(distance)])
		if step == 0:
			assert_close(sample, EYE_POD, "the arc starts at the authored lying eye")
			assert_true(distance >= 0.04, "the lying eye clears the shell by >= 0.04 m, got %.4f" % distance)
		worst = minf(worst, distance)
	assert_true(worst >= 0.03, "the sit-up corridor's worst clearance is >= 0.03 m, got %.4f" % worst)

func test_state_dressing_is_retained() -> void:
	var registry := Pods.PodRegistry.frozen()
	var pods := StasisPods.build(registry)
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var sealed_lids := 0
	var open_lids := 0
	var blankets := 0
	var plates := 0
	for pod: Pods.Pod in registry.pods():
		var group: Node = pods.get_child(pod.id().index())
		var dressing_count := 0
		for instance: MeshInstance3D in _box_children(group):
			if instance.position == plate.center and (instance.mesh as BoxMesh).size == plate.size:
				plates += 1
				continue
			dressing_count += 1
			if _matches_solid(instance, PodBody.sealed_lid()):
				sealed_lids += 1
			if _matches_solid(instance, PodBody.open_lid()):
				open_lids += 1
			if _matches_solid(instance, PodBody.hanging_blanket()):
				blankets += 1
		var expected := 1
		if pod.state() == Pods.PodState.EMPTY_OPEN:
			expected = 2
		elif pod.state() == Pods.PodState.PLAYER:
			expected = 0
		assert_int_equal(dressing_count, expected, "pod %d keeps its state's dressing count" % pod.id().index())
	assert_int_equal(sealed_lids, 3, "all three sealed pods keep their flat lid")
	assert_int_equal(open_lids, 3, "all three empty-open pods keep their tilted lid")
	assert_int_equal(blankets, 3, "all three empty-open pods keep their hanging blanket")
	assert_int_equal(plates, Pods.POD_COUNT, "every pod keeps its authored indicator plate")

## The pod group's shell instance, or null when the group lacks one.
func _shell_of(group: Node) -> MeshInstance3D:
	for child: Node in group.get_children():
		var instance := child as MeshInstance3D
		if instance != null and instance.mesh == PodMesh.shell_mesh():
			return instance
	return null

## The group's BoxMesh instances, dressing and plate alike.
func _box_children(group: Node) -> Array[MeshInstance3D]:
	var boxes: Array[MeshInstance3D] = []
	for child: Node in group.get_children():
		var instance := child as MeshInstance3D
		if instance != null and instance.mesh is BoxMesh:
			boxes.append(instance)
	return boxes

## The group's dressing boxes: every BoxMesh child except the plate.
func _dressing_boxes(group: Node) -> Array[MeshInstance3D]:
	var plate: Placement.SolidPlacement = Placement.indicator_plate()
	var dressing: Array[MeshInstance3D] = []
	for instance: MeshInstance3D in _box_children(group):
		if instance.position == plate.center and (instance.mesh as BoxMesh).size == plate.size:
			continue
		dressing.append(instance)
	return dressing

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
	var arrays: Array = PodMesh.shell_mesh().surface_get_arrays(0)
	var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var to_pod := PodMesh.shell_transform()
	var count := indices.size() / 3
	_tri_a.resize(count)
	_tri_b.resize(count)
	_tri_c.resize(count)
	_tri_min.resize(count)
	_tri_max.resize(count)
	for index: int in range(count):
		var a: Vector3 = to_pod * verts[indices[index * 3]]
		var b: Vector3 = to_pod * verts[indices[index * 3 + 1]]
		var c: Vector3 = to_pod * verts[indices[index * 3 + 2]]
		_tri_a[index] = a
		_tri_b[index] = b
		_tri_c[index] = c
		_tri_min[index] = a.min(b.min(c))
		_tri_max[index] = a.max(b.max(c))

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
